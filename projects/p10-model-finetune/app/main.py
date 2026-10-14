"""
P10 模型微调平台 - 云枢智能（CloudPivot AI）
模型微调全链路管理平台：数据集 → 训练 → 评测 → 部署（内存态演示数据，无数据库）。

模拟边界（MOCK BOUNDARIES）：
- 训练：损失曲线为模拟生成，未使用真实 GPU 训练
- 部署：仅注册模拟端点，实际无模型推理服务
- 评测：打分为规则模拟值，未做真实模型推理
"""

from __future__ import annotations

import json
import math
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="P10 模型微调平台",
    description="云枢智能（CloudPivot AI）- 模型微调管理平台（训练/评测/部署均为模拟演示）",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

# 统一设计系统：挂载仓库根 shared/ 到 /shared，前端引用 tokens.css（配色唯一真源）+ ui-kit.js（主题桥接）
_SHARED_DIR = Path(__file__).resolve().parents[3] / "shared"
if _SHARED_DIR.exists():
    app.mount("/shared", StaticFiles(directory=str(_SHARED_DIR)), name="shared")

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class DatasetCreate(BaseModel):
    name: str
    description: str = ""
    format: str = "jsonl"  # json | jsonl
    sample_count: int = 0
    tags: list[str] = []


class DatasetOut(DatasetCreate):
    id: str
    created_at: str
    file_size_bytes: int | None = None
    avg_tokens: float | None = None
    validation_status: str  # valid | invalid | pending
    # 口径标记：measured-from-upload = 按上传文件真实统计；seed_demo = 演示预置数据，不是测量值。
    # 加这两个字段的原因：本模块原先对「用户上传的文件」也返回 random 造出来的大小/样本数，
    # 而字节数和行数明明是可以真算的 —— 那是把可测的东西写成假数字，属于红线「禁止编造」。
    provenance: str = "seed_demo"
    measured_fields: list[str] = []


class TrainingConfig(BaseModel):
    base_model: str = "Qwen/Qwen2.5-7B-Instruct"
    method: str = "lora"  # lora | qlora
    lora_rank: int = 16
    lora_alpha: int = 32
    target_modules: list[str] = ["q_proj", "v_proj", "k_proj", "o_proj"]
    learning_rate: float = 2e-4
    num_epochs: int = 3
    batch_size: int = 4
    gradient_accumulation_steps: int = 8
    max_seq_length: int = 2048
    warmup_ratio: float = 0.05
    weight_decay: float = 0.01


class TrainingStart(BaseModel):
    dataset_id: str
    config: TrainingConfig
    name: str = ""


class LossPoint(BaseModel):
    step: int
    loss: float
    learning_rate: float
    eval_loss: float | None = None


class TrainingOut(BaseModel):
    id: str
    name: str
    dataset_id: str
    dataset_name: str
    config: TrainingConfig
    status: str  # pending | running | completed | failed
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    total_steps: int
    current_step: int
    final_loss: float | None = None
    final_eval_loss: float | None = None
    duration_seconds: float | None = None
    loss_curve: list[LossPoint] = []


class EvaluationResult(BaseModel):
    id: str
    training_id: str
    model_version: str
    dataset_name: str
    created_at: str
    accuracy: float
    format_compliance: float
    llm_judge_score: float
    avg_response_quality: float
    sample_count: int
    details: dict[str, Any] = {}
    # 本模块没有任何真实推理：下面所有分数都是模拟值。字段显式带出来，
    # 免得接口被 curl 出去之后被当成实测指标（UI 的黄条只在页面内有效）。
    simulated: bool = True
    provenance: str = "seed_demo (simulated scores, no real inference run)"


class CompareRequest(BaseModel):
    before_training_id: str | None = None
    after_training_id: str
    dataset_id: str | None = None


class CompareOut(BaseModel):
    before: dict[str, float] | None
    after: dict[str, float]
    delta: dict[str, float] | None
    simulated: bool = True
    note: str = (
        "before / after / delta 全部来自模拟评测，未做真实微调与真实推理，"
        "不能作为「效果提升 X」的证据"
    )


class ModelVersion(BaseModel):
    id: str
    name: str
    version: str
    base_model: str
    training_id: str
    created_at: str
    metrics: dict[str, float]
    config: TrainingConfig
    status: str  # registered | deployed_simulated | archived
    endpoint_url: str | None = None
    endpoint_status: str | None = None
    simulated: bool = True
    metrics_note: str = "metrics 为模拟评测值，未做真实训练/推理，不是实测准确率"


class DeployRequest(BaseModel):
    endpoint_name: str = ""
    max_concurrent: int = 10


# ---------------------------------------------------------------------------
# In-memory data store with sample data
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _percentile(sorted_values: list[int], q: int) -> float:
    """线性插值分位数（入参必须已排序）。用于把数据集样本长度分布算成真实数字。"""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    pos = (len(sorted_values) - 1) * (q / 100)
    lo = math.floor(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = pos - lo
    return float(round(sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac, 1))


def _generate_loss_curve(total_steps: int, base_loss: float = 2.8, seed: int = 42) -> list[LossPoint]:
    """生成带噪声的模拟损失曲线（指数衰减 + warmup/cosine 学习率）。"""
    rng = random.Random(seed)
    points: list[LossPoint] = []
    for step in range(0, total_steps + 1, max(1, total_steps // 100)):
        progress = step / total_steps
        # Exponential decay + noise
        loss = base_loss * math.exp(-2.5 * progress) + 0.15 + rng.gauss(0, 0.03)
        loss = max(0.1, loss)
        lr = 2e-4 * min(1.0, step / (total_steps * 0.05)) * (
            0.5 * (1 + math.cos(math.pi * step / total_steps))
        )
        eval_loss = None
        if step % (total_steps // 5) == 0 and step > 0:
            eval_loss = loss + rng.uniform(0.02, 0.08)
        points.append(LossPoint(
            step=step,
            loss=round(loss, 4),
            learning_rate=round(lr, 8),
            eval_loss=round(eval_loss, 4) if eval_loss else None,
        ))
    return points


# -- Sample datasets --
_sample_datasets: dict[str, DatasetOut] = {}

_ds1_id = "ds-001"
_sample_datasets[_ds1_id] = DatasetOut(
    id=_ds1_id,
    name="customer-service-qa-2024q4",
    description="2024 年 Q4 电商客服问答对，覆盖退换货、物流发货、商品咨询三类场景",
    format="jsonl",
    sample_count=12500,
    tags=["客服", "问答", "中文"],
    created_at="2024-12-01T08:00:00+00:00",
    file_size_bytes=45_200_000,
    avg_tokens=186.5,
    validation_status="valid",
)

_ds2_id = "ds-002"
_sample_datasets[_ds2_id] = DatasetOut(
    id=_ds2_id,
    name="product-description-generation",
    description="服饰类目「商品标题 + 属性 → 营销详情页文案」生成对，用于文案风格微调",
    format="jsonl",
    sample_count=8200,
    tags=["商品", "文案生成", "服饰"],
    created_at="2024-12-05T10:30:00+00:00",
    file_size_bytes=28_700_000,
    avg_tokens=245.3,
    validation_status="valid",
)

_ds3_id = "ds-003"
_sample_datasets[_ds3_id] = DatasetOut(
    id=_ds3_id,
    name="ecommerce-intent-classification",
    description="客服消息多分类意图标注：咨询、投诉、退货、好评、其他",
    format="json",
    sample_count=25000,
    tags=["意图识别", "分类", "多分类"],
    created_at="2024-12-10T14:00:00+00:00",
    file_size_bytes=18_400_000,
    avg_tokens=62.8,
    validation_status="valid",
)

# -- Sample training runs --
_sample_trainings: dict[str, TrainingOut] = {}

_cfg1 = TrainingConfig(
    base_model="Qwen/Qwen2.5-7B-Instruct",
    method="lora",
    lora_rank=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    learning_rate=2e-4,
    num_epochs=3,
    batch_size=4,
    gradient_accumulation_steps=8,
    max_seq_length=2048,
    warmup_ratio=0.05,
    weight_decay=0.01,
)

_t1_id = "train-001"
_loss1 = _generate_loss_curve(3750, base_loss=2.85, seed=42)
_sample_trainings[_t1_id] = TrainingOut(
    id=_t1_id,
    name="cs-qa-lora-run1",
    dataset_id=_ds1_id,
    dataset_name="customer-service-qa-2024q4",
    config=_cfg1,
    status="completed",
    created_at="2024-12-15T09:00:00+00:00",
    started_at="2024-12-15T09:05:00+00:00",
    completed_at="2024-12-15T14:32:00+00:00",
    total_steps=3750,
    current_step=3750,
    final_loss=_loss1[-1].loss,
    final_eval_loss=_loss1[-1].eval_loss,
    duration_seconds=19620.0,
    loss_curve=_loss1,
)

_cfg2 = TrainingConfig(
    base_model="Qwen/Qwen2.5-7B-Instruct",
    method="qlora",
    lora_rank=32,
    lora_alpha=64,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    learning_rate=1e-4,
    num_epochs=5,
    batch_size=2,
    gradient_accumulation_steps=16,
    max_seq_length=4096,
    warmup_ratio=0.03,
    weight_decay=0.005,
)

_t2_id = "train-002"
_loss2 = _generate_loss_curve(5120, base_loss=3.1, seed=99)
_sample_trainings[_t2_id] = TrainingOut(
    id=_t2_id,
    name="product-desc-qlora-run2",
    dataset_id=_ds2_id,
    dataset_name="product-description-generation",
    config=_cfg2,
    status="completed",
    created_at="2024-12-18T08:00:00+00:00",
    started_at="2024-12-18T08:10:00+00:00",
    completed_at="2024-12-18T22:45:00+00:00",
    total_steps=5120,
    current_step=5120,
    final_loss=_loss2[-1].loss,
    final_eval_loss=_loss2[-1].eval_loss,
    duration_seconds=52500.0,
    loss_curve=_loss2,
)

# -- Sample evaluations --
_sample_evaluations: dict[str, EvaluationResult] = {}

_e1_id = "eval-001"
_sample_evaluations[_e1_id] = EvaluationResult(
    id=_e1_id,
    training_id=_t1_id,
    model_version="cs-qa-lora-v1.0",
    dataset_name="customer-service-qa-2024q4",
    created_at="2024-12-16T10:00:00+00:00",
    accuracy=0.847,
    format_compliance=0.963,
    llm_judge_score=4.12,
    avg_response_quality=0.812,
    sample_count=2500,
    details={
        "bleu_score": 0.384,
        "rouge_l": 0.521,
        "hallucination_rate": 0.042,
        # 延迟原先写死 320 / 890：本模块没有推理服务，这两个数不可能被测出来。
        # 字段保留但置空，避免 curl 出去被当成实测 P50/P95。
        "response_latency_p50_ms": None,
        "response_latency_p95_ms": None,
        "latency_note": "未测量：无真实推理服务，无法产生延迟",
    },
)

_e2_id = "eval-002"
_sample_evaluations[_e2_id] = EvaluationResult(
    id=_e2_id,
    training_id=_t2_id,
    model_version="product-desc-qlora-v1.0",
    dataset_name="product-description-generation",
    created_at="2024-12-19T10:00:00+00:00",
    accuracy=0.792,
    format_compliance=0.981,
    llm_judge_score=3.87,
    avg_response_quality=0.756,
    sample_count=1640,
    details={
        "bleu_score": 0.312,
        "rouge_l": 0.478,
        "hallucination_rate": 0.061,
        "response_latency_p50_ms": None,
        "response_latency_p95_ms": None,
        "latency_note": "未测量：没有真实推理服务，无法产生延迟",
    },
)

# Baseline evaluation (before fine-tuning)
_e0_id = "eval-baseline"
_sample_evaluations[_e0_id] = EvaluationResult(
    id=_e0_id,
    training_id="",
    model_version="Qwen/Qwen2.5-7B-Instruct（基座模型）",
    dataset_name="customer-service-qa-2024q4",
    created_at="2024-12-14T10:00:00+00:00",
    accuracy=0.612,
    format_compliance=0.891,
    llm_judge_score=3.21,
    avg_response_quality=0.584,
    sample_count=2500,
    details={
        "bleu_score": 0.241,
        "rouge_l": 0.389,
        "hallucination_rate": 0.118,
        "response_latency_p50_ms": None,
        "response_latency_p95_ms": None,
        "latency_note": "未测量：基座模型同样没有在本模块起服务",
    },
)

# -- Sample model versions --
_sample_models: dict[str, ModelVersion] = {}

_m1_id = "model-001"
_sample_models[_m1_id] = ModelVersion(
    id=_m1_id,
    name="CS-QA-LoRA",
    version="v1.0",
    base_model="Qwen/Qwen2.5-7B-Instruct",
    training_id=_t1_id,
    created_at="2024-12-16T12:00:00+00:00",
    metrics={"accuracy": 0.847, "format_compliance": 0.963, "llm_judge_score": 4.12},
    config=_cfg1,
    # 原先这里是 status="deployed" + endpoint_url="http://127.0.0.1:8101/v1" + endpoint_status="healthy"。
    # 8101 是 P10 自己的 FastAPI 端口，/v1/chat/completions 会直接 404 ——
    # 那是「把一个不存在的服务标成 healthy」，属于把 mock 冒充真实，已改为显式 simulated。
    status="deployed_simulated",
    endpoint_url=None,
    endpoint_status="simulated",
)

_m2_id = "model-002"
_sample_models[_m2_id] = ModelVersion(
    id=_m2_id,
    name="CS-QA-LoRA",
    version="v1.1",
    base_model="Qwen/Qwen2.5-7B-Instruct",
    training_id=_t1_id,
    created_at="2024-12-20T09:00:00+00:00",
    metrics={"accuracy": 0.871, "format_compliance": 0.972, "llm_judge_score": 4.28},
    config=_cfg1.model_copy(update={"lora_rank": 32, "learning_rate": 1.5e-4}),
    status="registered",
    endpoint_url=None,
    endpoint_status=None,
)

_m3_id = "model-003"
_sample_models[_m3_id] = ModelVersion(
    id=_m3_id,
    name="Product-Desc-QLoRA",
    version="v1.0",
    base_model="Qwen/Qwen2.5-7B-Instruct",
    training_id=_t2_id,
    created_at="2024-12-19T14:00:00+00:00",
    metrics={"accuracy": 0.792, "format_compliance": 0.981, "llm_judge_score": 3.87},
    config=_cfg2,
    status="registered",
    endpoint_url=None,
    endpoint_status=None,
)

# Dynamic counters for user-created resources
_user_dataset_counter = 100
_user_training_counter = 100
_user_eval_counter = 100
_user_model_counter = 100


# ---------------------------------------------------------------------------
# Routes: Health & Static
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "p10-model-finetune",
        "version": "1.0.0",
        "mock_mode": True,
    }


@app.get("/")
async def serve_index():
    return FileResponse(WEB_DIR / "index.html")


# ---------------------------------------------------------------------------
# Routes: Stats / Dashboard
# ---------------------------------------------------------------------------


@app.get("/api/v1/stats")
async def get_stats():
    total_datasets = len(_sample_datasets)
    total_trainings = len(_sample_trainings)
    total_models = len(_sample_models)
    completed = sum(1 for t in _sample_trainings.values() if t.status == "completed")
    # 本模块没有真实推理服务，所以只有「模拟部署」这一种状态，不存在真已部署的模型
    deployed_simulated = sum(1 for m in _sample_models.values() if m.status == "deployed_simulated")
    total_samples = sum(d.sample_count for d in _sample_datasets.values())
    avg_accuracy = (
        sum(m.metrics.get("accuracy", 0) for m in _sample_models.values()) / total_models
        if total_models
        else 0
    )
    return {
        "datasets": total_datasets,
        "training_runs": total_trainings,
        "completed_runs": completed,
        "model_versions": total_models,
        "deployed_models": deployed_simulated,
        "deployed_simulated_models": deployed_simulated,
        "real_served_models": 0,
        "total_samples": total_samples,
        "avg_accuracy": round(avg_accuracy, 4),
        "mock_mode": True,
        "metrics_provenance": (
            "total_samples / avg_accuracy 是由预置演示数据算出来的聚合值，"
            "其中模型 accuracy 是模拟评分、未上传数据集的样本数是预置常量，均非实测"
        ),
    }


# ---------------------------------------------------------------------------
# Routes: Datasets
# ---------------------------------------------------------------------------


@app.get("/api/v1/datasets")
async def list_datasets():
    return list(_sample_datasets.values())


# 用户上传文件的真实统计缓存：rows 用来现算样本数/重复数/标签分布，进程重启即失效
# （本模块整体就是内存态演示，没有数据库）。
_dataset_uploads: dict[str, dict[str, Any]] = {}


@app.post("/api/v1/datasets")
async def create_dataset(
    name: str = "",
    description: str = "",
    format: str = "jsonl",
    file: UploadFile | None = None,
):
    global _user_dataset_counter
    _user_dataset_counter += 1
    ds_id = f"ds-{_user_dataset_counter:03d}"

    # 能真算的一律真算：字节数、非空行数、完全重复行数。
    # 没有接 tokenizer，所以 avg_tokens 显式为 null —— 原先它是 random.uniform(50, 300) 编出来的，
    # 而上传的字节和行数明明就在手上，把可测的写成随机数属于红线「禁止编造」。
    file_size: int | None = None
    sample_count = 0
    avg_tokens: float | None = None
    duplicates_removed = 0
    rows: list[str] = []
    if file is not None:
        content = await file.read()
        file_size = len(content)
        text = content.decode("utf-8", errors="replace")
        rows = [ln.strip() for ln in text.splitlines() if ln.strip()]
        sample_count = len(rows)
        seen: set[str] = set()
        for ln in rows:
            if ln in seen:
                duplicates_removed += 1
            else:
                seen.add(ln)
        _dataset_uploads[ds_id] = {
            "rows": rows,
            "duplicates_removed": duplicates_removed,
            "avg_chars_per_sample": round(sum(len(r) for r in rows) / len(rows), 1) if rows else None,
        }

    measured = ["file_size_bytes", "sample_count", "duplicates_removed"] if rows else []
    default_desc = (
        "用户上传数据集：文件大小/样本行数/重复行数由上传内容真实统计；"
        "未接 tokenizer，故不给 Token 长度估值"
        if rows
        else "未上传文件的数据集登记：只有名称与格式，没有任何统计口径，不可当实测数据引用"
    )

    ds = DatasetOut(
        id=ds_id,
        name=name or (file.filename if file else "") or f"dataset-{ds_id}",
        description=description or default_desc,
        format=format,
        sample_count=sample_count,
        tags=["用户上传"],
        created_at=_now(),
        file_size_bytes=file_size,
        avg_tokens=avg_tokens,
        validation_status="valid" if rows else "pending",
        provenance="measured-from-upload" if rows else "metadata-only",
        measured_fields=measured,
    )
    _sample_datasets[ds_id] = ds
    return ds


@app.get("/api/v1/datasets/{dataset_id}")
async def get_dataset(dataset_id: str):
    if dataset_id not in _sample_datasets:
        raise HTTPException(status_code=404, detail="数据集不存在")
    ds = _sample_datasets[dataset_id]
    upload = _dataset_uploads.get(dataset_id)

    label_distribution: dict[str, float] | None = None
    char_length_percentiles: dict[str, float] | None = None
    duplicates_removed: int | None = None
    unmeasured = [
        "avg_tokens（未接 tokenizer，不给估值）",
        "token_histogram（同上）",
    ]

    if upload:
        rows = upload["rows"]
        duplicates_removed = upload["duplicates_removed"]
        # 标签分布：只有当样本行里真的带 label/category/intent 字段时才统计出来，
        # 统计不出来就返回 null，不再用一组写死的中文占比冒充分布。
        counts: dict[str, int] = {}
        for ln in rows:
            try:
                obj = json.loads(ln)
            except (ValueError, TypeError):
                continue
            if not isinstance(obj, dict):
                continue
            label = obj.get("label") or obj.get("category") or obj.get("intent")
            if isinstance(label, str) and label.strip():
                counts[label.strip()] = counts.get(label.strip(), 0) + 1
        labelled = sum(counts.values())
        if labelled:
            label_distribution = {
                k: round(v / labelled, 4) for k, v in sorted(counts.items(), key=lambda kv: -kv[1])
            }
        else:
            unmeasured.append("label_distribution（样本里没有可解析的 label/category/intent 字段）")
        lengths = sorted(len(r) for r in rows)
        if lengths:
            char_length_percentiles = {
                f"p{q}": _percentile(lengths, q) for q in (10, 25, 50, 75, 90, 99)
            }
    else:
        unmeasured += [
            "label_distribution（预置演示数据，没有真实样本可统计）",
            "duplicates_removed（同上）",
        ]

    extra = {
        **ds.model_dump(),
        "label_distribution": label_distribution,
        "language": "zh-CN",
        "token_histogram": None,
        "char_length_percentiles": char_length_percentiles,
        "duplicates_removed": duplicates_removed,
        "unmeasured": unmeasured,
        "format_validation": {
            "status": ds.validation_status,
            "schema_checked": bool(upload),
            "encoding": "utf-8",
        },
    }
    return extra


# ---------------------------------------------------------------------------
# Routes: Training
# ---------------------------------------------------------------------------


@app.post("/api/v1/training/start")
async def start_training(req: TrainingStart):
    global _user_training_counter

    if req.dataset_id not in _sample_datasets:
        raise HTTPException(status_code=404, detail="数据集不存在")

    _user_training_counter += 1
    t_id = f"train-{_user_training_counter:03d}"
    ds = _sample_datasets[req.dataset_id]

    # Calculate mock total steps
    effective_batch = req.config.batch_size * req.config.gradient_accumulation_steps
    steps_per_epoch = math.ceil(ds.sample_count / effective_batch)
    total_steps = steps_per_epoch * req.config.num_epochs

    # Generate loss curve (training is "completed" instantly in mock)
    loss_curve = _generate_loss_curve(total_steps, seed=_user_training_counter)

    training = TrainingOut(
        id=t_id,
        name=req.name or f"微调任务-{t_id}",
        dataset_id=req.dataset_id,
        dataset_name=ds.name,
        config=req.config,
        status="completed",
        created_at=_now(),
        started_at=_now(),
        completed_at=_now(),
        total_steps=total_steps,
        current_step=total_steps,
        final_loss=loss_curve[-1].loss,
        final_eval_loss=loss_curve[-1].eval_loss,
        # 原先写 random.uniform(3600, 28800) 冒充实测训练时长（1~8 小时）。
        # 本函数是瞬时生成模拟曲线，真实耗时接近 0，报时长只会误导 GPU 成本。
        duration_seconds=None,
        loss_curve=loss_curve,
    )
    _sample_trainings[t_id] = training
    return training


@app.get("/api/v1/training/{training_id}")
async def get_training(training_id: str):
    if training_id not in _sample_trainings:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    return _sample_trainings[training_id]


@app.get("/api/v1/training/{training_id}/loss")
async def get_loss_curve(training_id: str):
    if training_id not in _sample_trainings:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    t = _sample_trainings[training_id]
    return {
        "training_id": training_id,
        "total_steps": t.total_steps,
        "points": t.loss_curve,
    }


# ---------------------------------------------------------------------------
# Routes: Evaluations
# ---------------------------------------------------------------------------


@app.get("/api/v1/evaluations")
async def list_evaluations():
    return list(_sample_evaluations.values())


@app.post("/api/v1/evaluations/compare")
async def compare_evaluations(req: CompareRequest):
    after_eval = None
    before_eval = None

    # Find the after evaluation
    for e in _sample_evaluations.values():
        if e.training_id == req.after_training_id:
            after_eval = e
            break

    if not after_eval:
        raise HTTPException(status_code=404, detail="未找到微调后的评测记录")

    # Find the before evaluation
    if req.before_training_id:
        for e in _sample_evaluations.values():
            if e.training_id == req.before_training_id:
                before_eval = e
                break
    else:
        # Use baseline
        before_eval = _sample_evaluations.get(_e0_id)

    before_metrics = None
    after_metrics = {
        "accuracy": after_eval.accuracy,
        "format_compliance": after_eval.format_compliance,
        "llm_judge_score": after_eval.llm_judge_score,
        "avg_response_quality": after_eval.avg_response_quality,
    }

    delta = None
    if before_eval:
        before_metrics = {
            "accuracy": before_eval.accuracy,
            "format_compliance": before_eval.format_compliance,
            "llm_judge_score": before_eval.llm_judge_score,
            "avg_response_quality": before_eval.avg_response_quality,
        }
        delta = {
            k: round(after_metrics[k] - before_metrics[k], 4)
            for k in after_metrics
        }

    return CompareOut(before=before_metrics, after=after_metrics, delta=delta)


# ---------------------------------------------------------------------------
# Routes: Model Registry
# ---------------------------------------------------------------------------


@app.get("/api/v1/models")
async def list_models():
    return list(_sample_models.values())


@app.get("/api/v1/models/{model_id}")
async def get_model(model_id: str):
    if model_id not in _sample_models:
        raise HTTPException(status_code=404, detail="模型版本不存在")
    return _sample_models[model_id]


@app.post("/api/v1/models/{model_id}/deploy")
async def deploy_model(model_id: str, req: DeployRequest | None = None):
    """模拟部署：只在模型仓库登记一条「已模拟部署」状态，不启动任何推理服务。

    原先这里用 `random.randint(8101, 8199)` 拼一个 `http://127.0.0.1:<port>/v1` 并标成 healthy，
    而那个端口上没有任何服务 —— 门禁要的是「微调后模型可通过 OpenAI 兼容接口调用成功（有 curl 证据）」，
    在没有真实服务时必须显式回答「未服务」，不能给一个看起来能调的地址。
    """
    if model_id not in _sample_models:
        raise HTTPException(status_code=404, detail="模型版本不存在")

    model = _sample_models[model_id]
    endpoint_name = (req.endpoint_name if req else "") or f"{model.name}-{model.version}"

    model.status = "deployed_simulated"
    model.endpoint_url = None
    model.endpoint_status = "simulated"

    return {
        "model_id": model_id,
        "status": model.status,
        "endpoint_name": endpoint_name,
        "endpoint_url": None,
        "simulated": True,
        "openai_compatible": False,
        "inference_served": False,
        "message": (
            "【模拟】只在模型仓库登记了部署状态，没有启动推理服务，"
            "因此不存在可调用的 OpenAI 兼容端点（真实训练与服务化见 README「已知限制」）。"
        ),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  P10 模型微调平台 - 云枢智能（CloudPivot AI）")
    print("  http://127.0.0.1:8101")
    print("  【模拟模式】训练、评测、部署均为演示模拟，")
    print("              未做真实 GPU 训练与模型推理。")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8101)
