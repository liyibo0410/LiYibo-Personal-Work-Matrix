# P02 → P06 跨模块真实 HTTP 调用验证

时间: 2026-10-13 08:34:18

## 架构规范落实
- 目标地址由 portfolio_config.api_url('p06','/metrics/summary') 从 shared/config/services.json 解析，**未硬编码端口**
- 支持 CP_P06_METRICS_URL 显式覆盖（降级演练用）

## 1. 正常路径（SERVICE_REGISTRY → 8060 活实例）
```
base_url: http://127.0.0.1:8060/api/v1/metrics/summary
health ok=True status=200
ok=True degraded=False source=p06-live metrics_count=7
  - gmv 成交总额 35958.37 元
  - order_count 订单量 133 单
  - conversion_rate 转化率 0.0044 %
  - avg_order_value 客单价 270.36 元
  - return_rate 退货率 0.203 %
  - traffic_uv 独立访客数 30410 人
  - traffic_pv 页面浏览量 96864 次
```

## 2. 降级演练（CP_P06_METRICS_URL 指向死端口 59999）
```
base_url: http://127.0.0.1:59999/api/v1/metrics/summary
ok=False degraded=True source=unavailable
error: P06 数据中台不可达：timed out
metrics key present: False -> 降级不伪造数据
```

## 结论
- 正常路径: 真实拉取 P06 的 7 项指标, source=p06-live
- 降级路径: ok=False/degraded=True/source=unavailable, 不含 metrics 字段（未伪造）
- 前端 dashboard 依据 metrics_source 双处标注: p06-live=绿色实时 / 降级=黄色告警
