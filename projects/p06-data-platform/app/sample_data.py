"""Generate realistic e-commerce sample data across all warehouse layers.

Uses DuckDB SQL for fast vectorized data generation instead of Python loops.
Creates 5 source tables (ODS) with 3 months of simulated data,
then derives DWD / DWS / ADS layers to demonstrate the full lineage.
"""

from __future__ import annotations

from app import duckdb_engine as db


def generate_all():
    """Generate the complete sample dataset using SQL-based generation."""
    conn = db.get_conn()

    # ── Dimension tables (static data) ──────────────────────────

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ods_stores (
            store_id VARCHAR PRIMARY KEY,
            store_name VARCHAR,
            platform VARCHAR,
            category VARCHAR,
            created_at DATE
        )
    """)
    conn.execute("DELETE FROM ods_stores")
    conn.execute("""
        INSERT INTO ods_stores VALUES
        ('S001', '示例旗舰店', '天猫', '美妆', '2024-01-15'),
        ('S002', '示例京东自营店', '京东', '美妆', '2024-02-20'),
        ('S003', '示例抖音旗舰店', '抖音', '美妆', '2024-03-10'),
        ('S004', '示例拼多多官方店', '拼多多', '家居', '2024-04-05'),
        ('S005', '示例小红书旗舰店', '小红书', '个护', '2024-05-01')
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ods_products (
            product_id VARCHAR PRIMARY KEY,
            product_name VARCHAR,
            category_id VARCHAR,
            price DOUBLE,
            cost DOUBLE,
            created_at DATE
        )
    """)
    conn.execute("DELETE FROM ods_products")
    conn.execute("""
        INSERT INTO ods_products VALUES
        ('P001', '烟酰胺亮肤精华液 30ml', 'C01', 199.00, 58.00, '2024-01-01'),
        ('P002', '玻尿酸补水面膜 5片装', 'C02', 89.00, 22.00, '2024-01-01'),
        ('P003', '清透防晒乳 SPF50+', 'C03', 149.00, 38.00, '2024-01-01'),
        ('P004', '氨基酸温和洁面乳 120ml', 'C04', 79.00, 18.00, '2024-01-01'),
        ('P005', '神经酰胺身体乳 400ml', 'C05', 129.00, 32.00, '2024-01-01'),
        ('P006', '白茶香薰蜡烛 200g', 'C06', 168.00, 45.00, '2024-01-01'),
        ('P007', '桌面收纳盒 三件套', 'C07', 59.00, 15.00, '2024-01-01'),
        ('P008', '玫瑰保湿喷雾 150ml', 'C08', 69.00, 16.00, '2024-01-01'),
        ('P009', '维C美白精华 50ml', 'C01', 299.00, 78.00, '2024-02-01'),
        ('P010', '胶原蛋白面膜 10片装', 'C02', 159.00, 40.00, '2024-02-01'),
        ('P011', '物理防晒隔离霜 60ml', 'C03', 119.00, 28.00, '2024-03-01'),
        ('P012', '茶树精油洁面皂 100g', 'C04', 49.00, 12.00, '2024-03-01')
    """)

    # ── Generate customers using SQL ────────────────────────────

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ods_customers (
            customer_id VARCHAR PRIMARY KEY,
            nickname VARCHAR,
            gender VARCHAR,
            province VARCHAR,
            register_date DATE,
            last_login DATE
        )
    """)
    conn.execute("DELETE FROM ods_customers")
    conn.execute("""
        INSERT INTO ods_customers
        SELECT
            'U' || LPAD(CAST(seq AS VARCHAR), 5, '0') AS customer_id,
            ['张','王','李','赵','刘','陈','杨','黄','周','吴','徐','孙','马','朱','胡','郭','林','何','高','罗'][floor(random()*20)::int + 1]
                || '**' || ['小姐','先生','同学','',''][floor(random()*5)::int] AS nickname,
            ['女','女','女','男','男'][floor(random()*5)::int + 1] AS gender,
            ['广东','浙江','江苏','上海','北京','四川','湖北','山东','福建','河南','湖南','安徽','重庆','天津','陕西'][floor(random()*15)::int + 1] AS province,
            DATE '2024-07-01' - (floor(random()*500)::INTEGER) AS register_date,
            DATE '2024-07-01' + (floor(random()*92)::INTEGER) AS last_login
        FROM generate_series(1, 2000) AS t(seq)
    """)

    # ── Generate orders using SQL ───────────────────────────────

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ods_orders (
            order_id VARCHAR PRIMARY KEY,
            customer_id VARCHAR,
            store_id VARCHAR,
            product_id VARCHAR,
            quantity INTEGER,
            unit_price DOUBLE,
            total_amount DOUBLE,
            payment_method VARCHAR,
            status VARCHAR,
            order_date TIMESTAMP,
            pay_date TIMESTAMP
        )
    """)
    conn.execute("DELETE FROM ods_orders")
    conn.execute("""
        INSERT INTO ods_orders
        WITH dates AS (
            SELECT DATE '2024-07-01' + d::INTEGER AS order_day
            FROM generate_series(0, 91) AS t(d)
        ),
        order_nums AS (
            SELECT
                ROW_NUMBER() OVER () AS seq,
                order_day,
                -- 80-160 orders per day with weekend boost
                (80 + floor(random()*80)::int) * CASE WHEN EXTRACT(DOW FROM order_day) IN (0,6) THEN 1.3 ELSE 1.0 END * CASE WHEN EXTRACT(MONTH FROM order_day) = 9 THEN 1.15 ELSE 1.0 END AS daily_count
            FROM dates
            CROSS JOIN generate_series(1, 1) AS t(x)
        ),
        expanded AS (
            SELECT
                ROW_NUMBER() OVER (ORDER BY order_day, n) AS seq,
                order_day,
                'U' || LPAD(CAST(1 + floor(random()*2000)::int AS VARCHAR), 5, '0') AS customer_id,
                ['S001','S002','S003','S004','S005'][floor(random()*5)::int + 1] AS store_id,
                ['P001','P002','P003','P004','P005','P006','P007','P008','P009','P010','P011','P012'][floor(random()*12)::int + 1] AS product_id,
                [1,1,1,1,2,2,2,3,3,4,5][floor(random()*11)::int + 1] AS quantity,
                ['支付宝','微信支付','花呗','信用卡','京东白条'][floor(random()*5)::int + 1] AS payment_method,
                ['已完成','已完成','已完成','已完成','已退货','已取消'][floor(random()*6)::int + 1] AS status,
                floor(random()*24)::int AS hour,
                floor(random()*60)::int AS minute
            FROM dates
            CROSS JOIN generate_series(1, 160) AS t(n)
            WHERE n <= (80 + floor(random()*80)::int) * CASE WHEN EXTRACT(DOW FROM order_day) IN (0,6) THEN 1.3 ELSE 1.0 END
        )
        SELECT
            'OD' || LPAD(CAST(e.seq AS VARCHAR), 7, '0') AS order_id,
            e.customer_id,
            e.store_id,
            e.product_id,
            e.quantity,
            CASE WHEN random() < 0.3 THEN ROUND(p.price * (0.7 + random()*0.25), 2) ELSE p.price END AS unit_price,
            CASE WHEN random() < 0.3
                THEN ROUND(e.quantity * p.price * (0.7 + random()*0.25), 2)
                ELSE ROUND(e.quantity * p.price, 2)
            END AS total_amount,
            e.payment_method,
            e.status,
            e.order_day + INTERVAL (e.hour || ' hours') + INTERVAL (e.minute || ' minutes') AS order_date,
            CASE WHEN e.status != '已取消'
                THEN e.order_day + INTERVAL (e.hour || ' hours') + INTERVAL ((e.minute + floor(random()*30)::INTEGER) || ' minutes')
                ELSE NULL
            END AS pay_date
        FROM expanded e
        JOIN ods_products p ON e.product_id = p.product_id
    """)

    # ── Generate traffic using SQL ──────────────────────────────

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ods_traffic (
            id INTEGER,
            store_id VARCHAR,
            visit_date DATE,
            channel VARCHAR,
            uv INTEGER,
            pv INTEGER,
            avg_duration DOUBLE,
            bounce_rate DOUBLE
        )
    """)
    conn.execute("DELETE FROM ods_traffic")
    conn.execute("""
        INSERT INTO ods_traffic
        SELECT
            ROW_NUMBER() OVER () AS id,
            store_id,
            visit_date,
            channel,
            uv,
            GREATEST(uv, (uv * (2 + random()*3))::INTEGER) AS pv,
            ROUND(30 + random()*270, 1) AS avg_duration,
            ROUND(0.2 + random()*0.5, 3) AS bounce_rate
        FROM (
            SELECT
                store_id,
                visit_date,
                channel,
                GREATEST(10, base_uv + (floor(random()*100)::INTEGER - 50)) AS uv
            FROM (
                SELECT
                    s.store_id,
                    DATE '2024-07-01' + d::INTEGER AS visit_date,
                    ch.channel,
                    (200 + floor(random()*1300)::INTEGER)
                        * CASE WHEN EXTRACT(DOW FROM DATE '2024-07-01' + d::INTEGER) IN (0,6) THEN 1.2 ELSE 1.0 END
                        * CASE WHEN ch.channel = '直播' THEN 2.5 ELSE 1.0 END
                        AS base_uv
                FROM ods_stores s
                CROSS JOIN generate_series(0, 91) AS days(d)
                CROSS JOIN (SELECT UNNEST(['自然搜索','直通车','抖音信息流','小红书种草','直播','活动页','直接访问']) AS channel) ch
                WHERE random() < 0.7
            ) inner_t
        ) t
    """)

    # ── Build derived layers ────────────────────────────────────

    _build_dwd()
    _build_dws()
    _build_ads()


def _build_dwd():
    """Build DWD (Data Warehouse Detail) layer."""
    conn = db.get_conn()

    conn.execute("DROP TABLE IF EXISTS dwd_order_detail")
    conn.execute("""
        CREATE TABLE dwd_order_detail AS
        SELECT
            o.order_id, o.customer_id, o.store_id, s.store_name,
            o.product_id, p.product_name,
            ['面部精华','面膜','防晒霜','洁面乳','身体乳','香薰蜡烛','收纳盒','保湿喷雾'][
                CASE WHEN p.category_id = 'C01' THEN 1
                     WHEN p.category_id = 'C02' THEN 2
                     WHEN p.category_id = 'C03' THEN 3
                     WHEN p.category_id = 'C04' THEN 4
                     WHEN p.category_id = 'C05' THEN 5
                     WHEN p.category_id = 'C06' THEN 6
                     WHEN p.category_id = 'C07' THEN 7
                     WHEN p.category_id = 'C08' THEN 8
                END
            ] AS category_name,
            o.quantity, o.unit_price, o.total_amount,
            p.cost,
            ROUND(o.total_amount - p.cost * o.quantity, 2) AS profit,
            o.payment_method, o.status,
            CAST(o.order_date AS DATE) AS order_date,
            cu.province
        FROM ods_orders o
        LEFT JOIN ods_stores s ON o.store_id = s.store_id
        LEFT JOIN ods_products p ON o.product_id = p.product_id
        LEFT JOIN ods_customers cu ON o.customer_id = cu.customer_id
    """)

    conn.execute("DROP TABLE IF EXISTS dwd_customer_profile")
    conn.execute("""
        CREATE TABLE dwd_customer_profile AS
        SELECT
            cu.customer_id, cu.nickname, cu.gender, cu.province, cu.register_date,
            COALESCE(agg.total_orders, 0) AS total_orders,
            COALESCE(agg.total_spent, 0) AS total_spent,
            COALESCE(agg.avg_order_value, 0) AS avg_order_value,
            agg.last_order_date
        FROM ods_customers cu
        LEFT JOIN (
            SELECT customer_id,
                   COUNT(*) AS total_orders,
                   ROUND(SUM(total_amount), 2) AS total_spent,
                   ROUND(AVG(total_amount), 2) AS avg_order_value,
                   MAX(CAST(order_date AS DATE)) AS last_order_date
            FROM ods_orders
            WHERE status = '已完成'
            GROUP BY customer_id
        ) agg ON cu.customer_id = agg.customer_id
    """)


def _build_dws():
    """Build DWS (Data Warehouse Summary) layer."""
    conn = db.get_conn()

    conn.execute("DROP TABLE IF EXISTS dws_daily_shop")
    conn.execute("""
        CREATE TABLE dws_daily_shop AS
        SELECT
            order_date AS stat_date,
            store_id, store_name,
            COUNT(*) AS order_count,
            ROUND(SUM(total_amount), 2) AS gmv,
            COUNT(DISTINCT customer_id) AS paying_customers,
            ROUND(AVG(total_amount), 2) AS avg_order_value,
            SUM(CASE WHEN status = '已退货' THEN 1 ELSE 0 END) AS return_count,
            ROUND(SUM(CASE WHEN status = '已退货' THEN 1.0 ELSE 0.0 END) / COUNT(*), 4) AS return_rate
        FROM dwd_order_detail
        GROUP BY order_date, store_id, store_name
    """)

    conn.execute("DROP TABLE IF EXISTS dws_daily_product")
    conn.execute("""
        CREATE TABLE dws_daily_product AS
        SELECT
            order_date AS stat_date,
            product_id, product_name,
            COUNT(*) AS order_count,
            SUM(quantity) AS quantity_sold,
            ROUND(SUM(total_amount), 2) AS gmv,
            SUM(CASE WHEN status = '已退货' THEN 1 ELSE 0 END) AS return_count
        FROM dwd_order_detail
        GROUP BY order_date, product_id, product_name
    """)


def _build_ads():
    """Build ADS (Application Data Service) layer."""
    conn = db.get_conn()

    conn.execute("DROP TABLE IF EXISTS ads_key_metrics")
    conn.execute("""
        CREATE TABLE ads_key_metrics AS
        SELECT
            d.stat_date,
            d.gmv,
            d.order_count,
            d.paying_customers,
            d.avg_order_value,
            d.return_rate,
            COALESCE(t.uv, 0) AS uv,
            COALESCE(t.pv, 0) AS pv,
            CASE WHEN COALESCE(t.uv, 0) > 0
                 THEN ROUND(d.paying_customers * 1.0 / t.uv, 4)
                 ELSE 0 END AS conversion_rate
        FROM (
            SELECT stat_date,
                   ROUND(SUM(gmv), 2) AS gmv,
                   SUM(order_count) AS order_count,
                   SUM(paying_customers) AS paying_customers,
                   ROUND(SUM(gmv) / SUM(order_count), 2) AS avg_order_value,
                   ROUND(SUM(return_count) * 1.0 / SUM(order_count), 4) AS return_rate
            FROM dws_daily_shop
            GROUP BY stat_date
        ) d
        LEFT JOIN (
            SELECT visit_date, SUM(uv) AS uv, SUM(pv) AS pv
            FROM ods_traffic
            GROUP BY visit_date
        ) t ON d.stat_date = t.visit_date
    """)

    conn.execute("DROP TABLE IF EXISTS ads_product_ranking")
    conn.execute("""
        CREATE TABLE ads_product_ranking AS
        SELECT
            stat_date, product_id, product_name,
            gmv, order_count, quantity_sold,
            CASE WHEN order_count > 0
                 THEN ROUND(return_count * 1.0 / order_count, 4)
                 ELSE 0 END AS return_rate,
            ROW_NUMBER() OVER (PARTITION BY stat_date ORDER BY gmv DESC) AS rank_no
        FROM dws_daily_product
    """)


def rebuild_derived():
    """Rebuild DWD/DWS/ADS from ODS (useful after data ingestion)."""
    _build_dwd()
    _build_dws()
    _build_ads()
