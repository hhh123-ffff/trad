# 数据库设计说明（第一阶段）

本文档与 `schema.sql` 对应，说明每张表在系统中的职责与关系。

## 1. 设计目标

- 满足研究、回测、模拟盘、风控、可视化的统一数据底座。
- 保证每日批处理任务可幂等重跑。
- 保证查询性能：按交易日、账户、股票维度高频检索。
- 为后续实盘对接预留扩展字段。

## 2. 核心实体

### 2.1 `stocks`
- 职责：股票主数据。
- 关键点：`symbol` 唯一，`status` 控制是否可交易。

### 2.2 `prices`
- 职责：日线行情。
- 关键点：`(stock_id, trade_date)` 唯一，支持 upsert。
- 高频查询索引：`trade_date`、`(stock_id, trade_date)`。

### 2.3 `fundamentals`（预留）
- 职责：基本面指标。
- 关键点：`(stock_id, report_date)` 唯一。

### 2.4 `factors`
- 职责：按日因子快照与总分。
- 关键点：`(stock_id, trade_date, factor_version)` 唯一。
- 高频查询索引：`trade_date`、`(trade_date, total_score DESC)`。

### 2.5 `signals`
- 职责：策略信号（买卖持有建议）。
- 关键点：`(trade_date, stock_id, strategy_name)` 唯一，防止重复信号。

### 2.6 `orders`
- 职责：模拟订单流水。
- 关键点：关联 `signals`，状态流转（PENDING/FILLED/...）。

### 2.7 `positions`
- 职责：每日持仓快照。
- 关键点：`(account_name, stock_id, snapshot_date)` 唯一。

### 2.8 `portfolio`
- 职责：账户级资产快照（现金、市值、净值、回撤）。
- 关键点：`(account_name, as_of_date)` 唯一。

### 2.9 `risk_logs`
- 职责：风险告警与处理状态。
- 关键点：未解决告警建立部分索引，便于告警面板查询。

### 2.10 `backtest_runs` + `backtest_nav`
- 职责：回测结果汇总与净值曲线。
- 关键点：`backtest_nav` 对 `(run_id, trade_date)` 去重。

### 2.11 `job_runs`
- 职责：调度任务执行审计日志。
- 关键点：记录状态、耗时、消息，便于排障。

## 3. 关系与数据流

- `stocks` 1:N `prices` / `factors` / `signals` / `orders` / `positions` / `fundamentals`
- `signals` 1:N `orders`（订单可追溯到策略输出）
- `backtest_runs` 1:N `backtest_nav`

每日数据流：

1. 行情写入 `prices`
2. 因子写入 `factors`
3. 信号写入 `signals`
4. 模拟成交写入 `orders`
5. 持仓快照写入 `positions`
6. 资产快照写入 `portfolio`
7. 风控事件写入 `risk_logs`
8. 调度执行写入 `job_runs`

## 4. 数据一致性策略

- 所有关联使用外键。
- 高频重复写入表均设置唯一键，支持 upsert。
- 关键数值字段设置非负或区间约束。
- 对可变记录统一维护 `updated_at`。

## 5. PostgreSQL 与 SQLite 兼容策略

- `schema.sql` 为 PostgreSQL 主方案（包含 `JSONB`、`TIMESTAMPTZ`、触发器）。
<<<<<<< HEAD
- SQLite 开发模式下通过 SQLAlchemy 模型建表，不直接执行该 SQL。
=======
- SQLite 开发模式下通过 SQLAlchemy 模型建表，不直接执行该 SQL。
>>>>>>> cc26c140ab75982a625801f1e3e9b1339672ec2e
