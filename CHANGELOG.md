# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-24

### Added

- 建立完整工程骨架（`backend` / `frontend` / `docker` / `scripts` / `docs`）。
- 后端 FastAPI 基础设施：配置管理、日志、异常处理、数据库会话与建表。
- 数据模块：行情采集、清洗、入库、API 触发同步。
- 因子模块：动量、成交量、波动率、基本面预留因子计算与存储。
- 策略模块：多因子评分、Top N 选股、调仓逻辑、择时过滤。
- 回测模块：回测执行、指标统计、净值曲线存储与查询。
- 模拟盘模块：信号落单、仓位更新、资产快照、订单查询。
- 风控模块：单票仓位限制、止损触发、最大回撤/暴露告警、风险日志持久化。
- 前端管理台：Dashboard、持仓、订单、信号、回测、风控六大页面。
- 调度系统：APScheduler 定时任务与 `job_runs` 执行审计。
- 容器化部署：后端/前端 Dockerfile + PostgreSQL + scheduler 的 compose 编排。
- 自动化测试：后端 API、数据、策略、模拟盘、风控专项测试。

### Changed

- 风险接口升级为“实时评估 + 未解决历史告警”合并输出。
- 模拟盘执行引擎接入强约束风控（止损强平、仓位上限、暴露上限）。
- 文档体系完善：架构、数据库、部署、验收清单、项目总 README。

### Fixed

- 修复调度器在缺失 `apscheduler` 依赖时的报错可读性，改为明确安装提示。
- 优化 Docker 构建上下文，避免将无关大目录打入镜像构建上下文。
