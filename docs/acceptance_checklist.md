# 全链路验收清单（第十一阶段）

本清单用于快速确认“个人量化交易平台”在本地或容器环境可运行。

## A. 后端服务

1. 安装依赖并启动：

```bash
cd backend
pip install -e .[dev]
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

2. 验证健康接口：

```bash
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api/v1/ready
```

预期：返回 `status=ok/ready`。

## B. 数据与策略链路

1. 数据同步：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/data/sync -H "Content-Type: application/json" -d "{\"symbols\":[\"000001.SZ\",\"600000.SH\"],\"start_date\":\"2024-01-01\",\"end_date\":\"2024-04-30\",\"include_stock_universe\":true}"
```

2. 因子计算：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/factors/calculate -H "Content-Type: application/json" -d "{\"symbols\":[\"000001.SZ\",\"600000.SH\"],\"start_date\":\"2024-01-01\",\"end_date\":\"2024-04-30\",\"factor_version\":\"v1\"}"
```

3. 策略生成：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/strategy/run -H "Content-Type: application/json" -d "{\"trade_date\":\"2024-04-30\",\"top_n\":2,\"strategy_name\":\"multi_factor_v1\",\"factor_version\":\"v1\",\"force_rebalance\":true}"
```

预期：返回 buy/sell/hold 数量。

## C. 模拟盘与风控

1. 模拟盘执行：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/simulation/run -H "Content-Type: application/json" -d "{\"trade_date\":\"2024-04-30\",\"account_name\":\"paper_account\"}"
```

2. 查看风控：

```bash
curl http://127.0.0.1:8000/api/v1/risk
```

预期：返回 `overall_level` 与 `alerts`。

## D. 前端

1. 启动：

```bash
cd frontend
npm install
npm run dev
```

2. 页面验收：

- `/dashboard`
- `/positions`
- `/orders`
- `/signals`
- `/backtest`
- `/risk`

预期：页面可正常渲染并能拉取后端数据。

## E. 调度

1. 单次执行验证：

```bash
cd backend
python -m app.scheduler.runner --once data
python -m app.scheduler.runner --once strategy
```

2. 守护进程：

```bash
python -m app.scheduler.runner
```

预期：日志打印调度计划，任务执行结果写入 `job_runs`。

## F. Docker

1. 启动：

```bash
cd docker
cp .env.example .env
cd ..
docker compose -f docker/docker-compose.yml --env-file docker/.env up -d --build
```

2. 检查服务：

```bash
docker compose -f docker/docker-compose.yml ps
docker compose -f docker/docker-compose.yml logs -f backend
docker compose -f docker/docker-compose.yml logs -f scheduler
```

预期：`postgres/backend/frontend/scheduler` 均为 healthy 或 running。

## G. 自动化测试

```bash
cd backend
pytest -q
```

预期：全部通过。
