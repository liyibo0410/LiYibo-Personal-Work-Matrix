from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes.auth import get_current_user
from app.db.session import get_db
from app.main import app
from app.models import (
    AdExperiment,
    AdRecommendation,
    AgentApproval,
    AgentRiskLevel,
    AgentRun,
    AgentTask,
    Base,
    Competitor,
    CompetitorMonitor,
    CompetitorMonitorSnapshot,
    CreativePlan,
    CreativePlanType,
    GeneratedAsset,
    GenerationJob,
    GenerationJobKind,
    InventoryItem,
    InventoryMovement,
    InventoryMovementType,
    PerformanceRecord,
    Platform,
    Product,
    ProductDiagnosis,
    ProductSku,
    PlatformProductMapping,
    PromotionLink,
    PromotionLinkClick,
    PublicLinkParseTask,
    ReviewReport,
    User,
    UserRole,
    Workspace,
    WorkspaceMembership,
)


def test_delete_product_cascades_operational_graph_and_keeps_audit() -> None:
    """验证「删除商品级联清除运营数据」场景，确保重构后仍满足预期业务与安全边界。"""
    # 按 Arrange、Act、Assert 组织场景，重点检查可观察状态和副作用。
    # 连接层开启 PRAGMA foreign_keys，让漏删的子表像在 PostgreSQL 上一样直接触发约束错误。
    engine = _engine()
    Base.metadata.create_all(engine)
    workspace_id, user_id, product_id = _seed_product_graph(engine)

    with Session(engine) as db:
        seeded = {
            model.__mapper__.local_table.name: db.scalar(
                select(func.count()).select_from(model.__mapper__.local_table)
            )
            for model in _OPERATIONAL_MODELS
        }
    # 先确认每张子表都有数据，否则「删除后为空」的断言会因为没种数据而空过。
    assert all(count > 0 for count in seeded.values()), seeded

    app.dependency_overrides[get_db] = _override_db(engine)
    app.dependency_overrides[get_current_user] = lambda: _user(user_id, UserRole.OPERATOR)
    try:
        response = TestClient(app).delete(
            f"/api/v1/products/{product_id}",
            headers={"Authorization": "Bearer test", "X-Workspace-ID": str(workspace_id)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204

    with Session(engine) as db:
        assert db.get(Product, product_id) is None
        for model in _OPERATIONAL_MODELS:
            table = model.__mapper__.local_table
            count = db.scalar(select(func.count()).select_from(table))
            assert count == 0, f"{table.name} 未被级联删除，剩余 {count} 行"

        # Agent 运行与人工审批是审计事实，只解除商品关联，不随商品删除。
        run = db.scalars(select(AgentRun)).one()
        assert run.product_id is None
        assert db.scalar(select(func.count(AgentApproval.id))) == 1


def test_delete_product_is_scoped_to_workspace() -> None:
    """验证「删除商品按workspace隔离」场景，确保重构后仍满足预期业务与安全边界。"""
    # 按 Arrange、Act、Assert 组织场景，重点检查可观察状态和副作用。
    engine = _engine()
    Base.metadata.create_all(engine)
    workspace_id, user_id, _ = _seed_product_graph(engine)
    foreign_product_id = _seed_foreign_product(engine)

    app.dependency_overrides[get_db] = _override_db(engine)
    app.dependency_overrides[get_current_user] = lambda: _user(user_id, UserRole.OPERATOR)
    try:
        response = TestClient(app).delete(
            f"/api/v1/products/{foreign_product_id}",
            headers={"Authorization": "Bearer test", "X-Workspace-ID": str(workspace_id)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    with Session(engine) as db:
        assert db.get(Product, foreign_product_id) is not None


def test_viewer_role_cannot_delete_product() -> None:
    """验证「客服角色不能删除商品」场景，确保重构后仍满足预期业务与安全边界。"""
    # 按 Arrange、Act、Assert 组织场景，重点检查可观察状态和副作用。
    engine = _engine()
    Base.metadata.create_all(engine)
    workspace_id, user_id, product_id = _seed_product_graph(engine, role=UserRole.CS)

    app.dependency_overrides[get_db] = _override_db(engine)
    app.dependency_overrides[get_current_user] = lambda: _user(user_id, UserRole.CS)
    try:
        response = TestClient(app).delete(
            f"/api/v1/products/{product_id}",
            headers={"Authorization": "Bearer test", "X-Workspace-ID": str(workspace_id)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    with Session(engine) as db:
        assert db.get(Product, product_id) is not None


def test_anonymous_cannot_delete_product() -> None:
    """验证「未登录不能删除商品」场景，确保重构后仍满足预期业务与安全边界。"""
    # 按 Arrange、Act、Assert 组织场景，重点检查可观察状态和副作用。
    engine = _engine()
    Base.metadata.create_all(engine)
    _, _, product_id = _seed_product_graph(engine)

    app.dependency_overrides[get_db] = _override_db(engine)
    try:
        response = TestClient(app).delete(f"/api/v1/products/{product_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    with Session(engine) as db:
        assert db.get(Product, product_id) is not None


_OPERATIONAL_MODELS = (
    ProductSku,
    InventoryItem,
    InventoryMovement,
    PlatformProductMapping,
    Competitor,
    CompetitorMonitor,
    CompetitorMonitorSnapshot,
    PublicLinkParseTask,
    CreativePlan,
    PerformanceRecord,
    ReviewReport,
    AdRecommendation,
    AdExperiment,
    PromotionLink,
    PromotionLinkClick,
    GeneratedAsset,
    ProductDiagnosis,
    GenerationJob,
)


def _seed_product_graph(engine, role: UserRole = UserRole.OPERATOR) -> tuple[int, int, int]:
    """构造或执行测试所需的测试数据商品图，让测试数据、依赖替身与断言保持集中。"""
    # 覆盖商品聚合根下每一张子表，删除后任何一张仍有数据都算级联不完整。
    now = datetime.now(UTC)
    with Session(engine) as db:
        workspace = Workspace(slug="team-a", name="团队 A")
        user = User(email=f"{role.value}@example.com", display_name=role.value, role=role)
        db.add_all([workspace, user])
        db.flush()
        db.add(
            WorkspaceMembership(workspace_id=workspace.id, user_id=user.id, role=role)
        )
        product = Product(
            workspace_id=workspace.id,
            name="控油气垫",
            platform=Platform.DOUYIN,
            selling_points=["控油持妆"],
        )
        db.add(product)
        db.flush()

        sku = ProductSku(product_id=product.id, sku_code="SKU-1", name="正装 15g")
        db.add(sku)
        db.flush()
        item = InventoryItem(sku_id=sku.id, quantity=100)
        db.add(item)
        db.flush()
        db.add(
            InventoryMovement(
                inventory_item_id=item.id,
                sku_id=sku.id,
                movement_type=InventoryMovementType.INBOUND,
                quantity_delta=100,
                before_quantity=0,
                after_quantity=100,
                before_locked_quantity=0,
                after_locked_quantity=0,
            )
        )
        db.add(
            PlatformProductMapping(
                product_id=product.id,
                sku_id=sku.id,
                platform=Platform.DOUYIN,
                external_product_id="dy-1",
            )
        )

        competitor = Competitor(product_id=product.id, name="竞对 A 气垫")
        db.add(competitor)
        db.flush()
        monitor = CompetitorMonitor(product_id=product.id, competitor_id=competitor.id)
        db.add(monitor)
        db.flush()
        snapshot = CompetitorMonitorSnapshot(
            monitor_id=monitor.id,
            product_id=product.id,
            competitor_id=competitor.id,
            status="success",
        )
        db.add(snapshot)
        db.flush()
        monitor.last_snapshot_id = snapshot.id

        plan = CreativePlan(
            product_id=product.id,
            type=CreativePlanType.MAIN_IMAGE,
            title="通勤控油主图",
        )
        db.add(plan)
        db.flush()
        asset = GeneratedAsset(
            product_id=product.id,
            creative_plan_id=plan.id,
            asset_type="image",
            url="/uploads/main.png",
        )
        job = GenerationJob(
            product_id=product.id,
            creative_plan_id=plan.id,
            kind=GenerationJobKind.MAIN_IMAGE_ASSET,
        )
        link = PromotionLink(product_id=product.id, label="直播挂车", url="https://example.com/a")
        db.add_all([asset, job, link])
        db.flush()
        db.add(
            PromotionLinkClick(product_id=product.id, promotion_link_id=link.id, clicked_at=now)
        )
        record = PerformanceRecord(
            product_id=product.id,
            period_start=now,
            period_end=now,
            generated_asset_id=asset.id,
            promotion_link_id=link.id,
        )
        db.add(record)
        db.flush()
        db.add(
            AdExperiment(
                product_id=product.id,
                name="主图 A/B",
                objective="提升点击率",
                generated_asset_id=asset.id,
                promotion_link_id=link.id,
            )
        )
        db.add_all(
            [
                ReviewReport(
                    product_id=product.id,
                    period_start=now,
                    period_end=now,
                    summary="本周复盘",
                ),
                AdRecommendation(product_id=product.id, summary="加大主图预算"),
                ProductDiagnosis(
                    product_id=product.id,
                    positioning="通勤控油底妆",
                    price_band="中位价格带",
                ),
                PublicLinkParseTask(product_id=product.id, url="https://example.com/comp"),
            ]
        )

        task = AgentTask(
            workspace_id=workspace.id,
            requested_by_user_id=user.id,
            workflow_key="product_operation",
            workflow_version="1.0.0",
            title="生成主图方案",
        )
        run = AgentRun(
            thread_id="00000000-0000-0000-0000-0000000000aa",
            workspace_id=workspace.id,
            product_id=product.id,
            requested_by_user_id=user.id,
            workflow_key="product_operation",
            workflow_version="1.0.0",
        )
        db.add_all([task, run])
        db.flush()
        db.add(
            AgentApproval(
                workspace_id=workspace.id,
                task_id=task.id,
                run_id=run.id,
                requested_by_user_id=user.id,
                action_key="publish_main_image",
                risk_level=AgentRiskLevel.R2,
            )
        )
        db.commit()
        return workspace.id, user.id, product.id


def _seed_foreign_product(engine) -> int:
    """构造或执行测试所需的测试数据团队 B 商品，让测试数据、依赖替身与断言保持集中。"""
    # 按 Arrange、Act、Assert 组织场景，重点检查可观察状态和副作用。
    with Session(engine) as db:
        other_workspace = Workspace(slug="team-b", name="团队 B")
        foreign = Product(name="竞品同款气垫", platform=Platform.TMALL)
        db.add_all([other_workspace, foreign])
        db.flush()
        foreign.workspace_id = other_workspace.id
        db.commit()
        return foreign.id


def _override_db(engine):
    """构造或执行测试所需的覆盖db，让测试数据、依赖替身与断言保持集中。"""
    def override_db():
        """构造或执行测试所需的覆盖db，让测试数据、依赖替身与断言保持集中。"""
        with Session(engine) as db:
            yield db

    return override_db


def _user(user_id: int, role: UserRole) -> User:
    """构造或执行测试所需的用户，让测试数据、依赖替身与断言保持集中。"""
    return User(
        id=user_id,
        email=f"{role.value}@example.com",
        display_name=role.value,
        role=role,
    )


def _engine():
    """构造或执行测试所需的engine，让测试数据、依赖替身与断言保持集中。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine
