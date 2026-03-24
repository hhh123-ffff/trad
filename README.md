# 个人量化交易平台（0 到 1 工程化实现）

本项目是一个可落地、可运行、可扩展的“个人版量化交易平台”，覆盖：

- 策略研究（因子 + 回测）
- 模拟交易（每日信号 + 持仓变化）
- 风控（仓位、止损、回撤告警）
- 可视化前端（Dashboard/持仓/订单/信号/回测/风控）
- 工程化部署（Docker + docker-compose + APScheduler）

> 当前版本不直连真实券商账户，但已预留 broker 扩展接口（`backend/app/services/brokers/`）。

## 1. 技术栈

### 后端

- Python 3.11+
- FastAPI
- pandas / numpy
- akshare / tushare
- SQLAlchemy
- PostgreSQL（生产）/ SQLite（开发）
- pydantic
- loguru（兼容标准 logging）
- APScheduler
- pytest

### 前端

- Next.js 14 + React 18
- TypeScript
- Ant Design
- Recharts

### 部署

- Docker
- docker-compose

## 2. 项目结构

```text
Quant Trading/
├─ backend/                  # 后端服务（API、量化引擎、任务）
│  ├─ app/
│  │  ├─ api/                # 路由层
│  │  ├─ core/               # 配置、日志、异常
│  │  ├─ db/                 # 数据库连接与建表
│  │  ├─ models/             # ORM 模型
│  │  ├─ schemas/            # Pydantic schema
│  │  ├─ services/           # 数据/因子/策略/回测/模拟盘/风控服务
│  │  ├─ scheduler/          # APScheduler 调度入口
│  │  └─ tasks/              # 调度任务封装
│  ├─ tests/                 # pytest 测试
│  ├─ .env.example
│  └─ pyproject.toml
├─ frontend/                 # 前端管理平台
│  ├─ src/app/               # 页面路由
│  ├─ src/components/        # UI 组件
│  ├─ src/lib/               # API 访问/工具
│  └─ .env.example
├─ docker/                   # 容器化与编排
│  ├─ backend.Dockerfile
│  ├─ frontend.Dockerfile
│  ├─ docker-compose.yml
│  └─ .env.example
├─ docs/                     # 架构与数据库文档
└─ scripts/                  # 一键脚本（数据/策略/回测/模拟盘/调度）
```

## 3. 功能模块

- 数据模块：股票日线采集、清洗、入库、定时更新
- 因子模块：20/60 日动量、成交量、波动率、基本面预留
- 策略模块：多因子打分、Top N 选股、每周调仓、沪深300均线择时
- 回测模块：年化收益/最大回撤/夏普/胜率/净值曲线
- 模拟盘模块：信号转订单、持仓更新、资产快照
- 风控模块：单票仓位限制、-8%止损、最大回撤告警、仓位暴露控制
- API 模块：`/dashboard`、`/positions`、`/orders`、`/signals`、`/backtest`、`/risk`
- 前端模块：六大页面完整对接
- 调度模块：每日自动更新数据、策略、模拟盘，周期回测

## 4. 本地开发启动（推荐）

### 4.1 后端启动

```bash
cd backend
cp .env.example .env
pip install -e .[dev]
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端默认地址：`http://127.0.0.1:8000`

健康检查：

- `GET /api/v1/health`
- `GET /api/v1/ready`

### 4.2 前端启动

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

前端默认地址：`http://localhost:3000`

## 5. 一键流水线脚本

`scripts/` 下提供常用脚本：

```bash
python scripts/run_data_ingestion.py
python scripts/run_strategy_pipeline.py
python scripts/run_backtest.py
python scripts/run_paper_trading.py
python scripts/run_scheduler.py --once data
```

## 6. API 总览

基础前缀：`/api/v1`

- `GET /health`：服务存活
- `GET /ready`：服务就绪
- `POST /data/sync`：行情同步
- `POST /factors/calculate`：因子计算
- `POST /strategy/run`：策略信号生成
- `POST /backtest/run`：回测执行
- `GET /backtest`：回测结果
- `POST /simulation/run`：模拟盘执行
- `GET /dashboard`：资产总览
- `GET /positions`：持仓
- `GET /orders`：交易记录
- `GET /signals`：信号
- `GET /risk`：风控状态

## 7. 调度系统（APScheduler）

本地运行：

```bash
cd backend
python -m app.scheduler.runner
```

单次执行（建议先验证）：

```bash
python -m app.scheduler.runner --once data
python -m app.scheduler.runner --once strategy
python -m app.scheduler.runner --once paper
python -m app.scheduler.runner --once backtest
```

可配置环境变量（见 `backend/.env.example`）：

- `SCHEDULER_TIMEZONE`
- `SCHEDULER_DATA_CRON`
- `SCHEDULER_STRATEGY_CRON`
- `SCHEDULER_PAPER_TRADING_CRON`
- `SCHEDULER_BACKTEST_CRON`

> 注意：调度守护模式依赖 `apscheduler`。若本机网络受限无法安装，可先使用 `--once` 模式，或直接使用 Docker 方式运行。

## 8. Docker 部署

详细说明见：`docker/README.md`

快速启动：

```bash
cd docker
cp .env.example .env
cd ..
docker compose -f docker/docker-compose.yml --env-file docker/.env up -d --build
```

服务包括：

- `postgres`
- `backend`
- `scheduler`
- `frontend`

## 9. 测试与质量验证

### 后端测试

```bash
cd backend
pytest -q
```

### 前端构建验证

```bash
cd frontend
npm run build
```

### Compose 配置校验

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env.example config
```

## 10. 默认数据库表

核心表（与需求一致）：

- `stocks`
- `prices`
- `factors`
- `signals`
- `positions`
- `orders`
- `portfolio`
- `risk_logs`

附加表：

- `backtest_runs`
- `backtest_nav`
- `job_runs`

## 11. 常见问题

1. `ModuleNotFoundError: No module named 'apscheduler'`
- 说明：调度守护进程依赖缺失。
- 解决：`python -m pip install apscheduler` 或使用 Docker 方式运行 scheduler。

2. `Could not find a version that satisfies the requirement ...`
- 说明：网络/代理问题导致 pip 无法拉包。
- 解决：检查代理配置或切换可用源。

3. 前端请求失败（接口 404 或 CORS）
- 说明：`NEXT_PUBLIC_API_BASE_URL` 配置错误。
- 解决：本地开发设置为 `http://127.0.0.1:8000/api/v1` 或 `http://localhost:8000/api/v1`。

4. Docker 启动后前端无数据
- 说明：后端未完成初始化或数据尚未生成。
- 解决：先调用 `/api/v1/data/sync`、`/api/v1/strategy/run`、`/api/v1/simulation/run`，或在 scheduler 中执行 `--once all`。

## 12. 下一步扩展建议

- 接入真实 broker（实盘风控隔离）
- 引入策略参数寻优/网格搜索
- 增加多账户与多策略组合管理
- 增加通知系统（企业微信/钉钉/Telegram）
<<<<<<< HEAD
- 引入可观测性（Prometheus + Grafana）
=======
- 引入可观测性（Prometheus + Grafana）
>>>>>>> cc26c140ab75982a625801f1e3e9b1339672ec2e

## 发布资料

- 变更历史：`CHANGELOG.md`
- 版本策略：`docs/versioning.md`
<<<<<<< HEAD
- 当前发布说明：`docs/releases/v0.1.0.md`
=======
- 当前发布说明：`docs/releases/v0.1.0.md`
>>>>>>> cc26c140ab75982a625801f1e3e9b1339672ec2e
