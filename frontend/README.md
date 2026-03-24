# frontend

个人量化交易平台前端（第八阶段）

## 技术栈

- Next.js 14（App Router）
- TypeScript
- Ant Design
- Recharts

## 目录结构

- `src/app`：页面路由（Dashboard/Positions/Orders/Signals/Backtest/Risk）
- `src/components`：布局与复用组件（导航壳、指标卡、分区卡）
- `src/lib`：API 请求、格式化、轮询 Hook
- `src/types`：后端响应类型定义

## 环境变量

复制 `.env.example` 为 `.env.local`：

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## 启动方式

```bash
npm install
npm run dev
```

默认访问：`http://localhost:3000`

## 构建验证

```bash
npm run build
```

## 页面说明

1. `/dashboard`
- 总资产、今日收益、累计收益、仓位
- 净值曲线
- 资产结构饼图

2. `/positions`
- 持仓表格（成本价/现价/盈亏）
- 权重分布图
- 按代码与快照日期筛选

3. `/orders`
- 交易记录表格
- 买卖分布图
- 按代码/方向/状态/日期筛选

4. `/signals`
- 今日买卖建议
- 因子评分字段展示
- 动作分布图

5. `/backtest`
- 收益曲线（含基准）
- 回撤曲线
- 指标统计 + 历史回测列表

6. `/risk`
- 风险等级
- 回撤与仓位风险刻度
- 告警列表
