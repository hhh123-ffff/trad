# Docker 部署（第十阶段）

本目录提供个人量化交易平台的一键容器化部署能力，包含：

- `backend`：FastAPI + SQLAlchemy
- `frontend`：Next.js 管理后台
- `postgres`：PostgreSQL 数据库
- `scheduler`：APScheduler 定时任务进程

## 文件说明

- `docker-compose.yml`：本地整栈编排
- `backend.Dockerfile`：后端镜像构建
- `frontend.Dockerfile`：前端镜像构建
- `.env.example`：Compose 环境变量模板

## 快速启动

1. 复制环境变量模板：

```bash
cd docker
cp .env.example .env
```

2. 回到项目根目录启动：

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env up -d --build
```

3. 访问服务：

- 前端：`http://localhost:3000`
- 后端：`http://localhost:8000`
- 健康检查：`http://localhost:8000/api/v1/health`

4. 查看日志：

```bash
docker compose -f docker/docker-compose.yml logs -f backend
docker compose -f docker/docker-compose.yml logs -f scheduler
```

5. 停止服务：

```bash
docker compose -f docker/docker-compose.yml down
```

## 定时任务说明（APScheduler）

`scheduler` 服务默认在 `Asia/Shanghai` 时区运行以下任务：

- `SCHEDULER_DATA_CRON=30 15 * * 1-5`：工作日 15:30 更新行情
- `SCHEDULER_STRATEGY_CRON=40 15 * * 1-5`：工作日 15:40 生成策略信号
- `SCHEDULER_PAPER_TRADING_CRON=50 15 * * 1-5`：工作日 15:50 执行模拟盘
- `SCHEDULER_BACKTEST_CRON=0 9 * * 6`：周六 09:00 跑周期回测

任务执行记录会写入数据库表 `job_runs`。

## 常用运维命令

- 仅运行一次某个任务（容器内）：

```bash
docker compose -f docker/docker-compose.yml exec scheduler python -m app.scheduler.runner --once data
docker compose -f docker/docker-compose.yml exec scheduler python -m app.scheduler.runner --once strategy
```

- 清理并重建（会删除容器和匿名卷，请谨慎）：

```bash
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml --env-file docker/.env up -d --build
```
