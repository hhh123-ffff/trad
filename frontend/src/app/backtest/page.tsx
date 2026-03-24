"use client";

import { ReloadOutlined } from "@ant-design/icons";
import { Alert, Button, Col, Empty, Row, Space, Spin, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useCallback, useMemo } from "react";

import { MetricTile } from "@/components/metric-tile";
import { SectionCard } from "@/components/section-card";
import { apiGet } from "@/lib/api";
import { formatDate, formatNumber, formatPercent } from "@/lib/format";
import { usePollingQuery } from "@/lib/hooks";
import { BacktestOverview, BacktestRunItem, BacktestRunListResponse } from "@/types/trading";

const { Title, Text } = Typography;

/** Backtest page showing historical metrics and curve visualization. */
export default function BacktestPage() {
  const overviewRequest = useCallback(() => apiGet<BacktestOverview>("/backtest"), []);
  const runsRequest = useCallback(
    () =>
      apiGet<BacktestRunListResponse>("/backtest/runs", {
        strategy_name: "multi_factor_v1",
        limit: 20,
        offset: 0,
      }),
    [],
  );

  const overviewState = usePollingQuery(overviewRequest, [], { intervalMs: 60000 });
  const runsState = usePollingQuery(runsRequest, [], { intervalMs: 60000 });

  const overview = overviewState.data;
  const curveData = useMemo(
    () =>
      (overview?.curve ?? []).map((item) => ({
        date: formatDate(item.trade_date),
        nav: item.nav,
        drawdown: item.drawdown * 100,
        benchmark: item.benchmark_nav,
      })),
    [overview?.curve],
  );

  const runRows = runsState.data?.items ?? [];

  const columns: ColumnsType<BacktestRunItem> = [
    { title: "Run ID", dataIndex: "run_id", key: "run_id", width: 90 },
    { title: "策略", dataIndex: "strategy_name", key: "strategy_name", width: 150 },
    { title: "区间", key: "range", width: 220, render: (_, row) => `${row.start_date} ~ ${row.end_date}` },
    {
      title: "年化",
      dataIndex: "annual_return",
      key: "annual_return",
      align: "right",
      render: (value: number) => (
        <span className={value >= 0 ? "table-highlight-positive" : "table-highlight-danger"}>{formatPercent(value)}</span>
      ),
    },
    {
      title: "回撤",
      dataIndex: "max_drawdown",
      key: "max_drawdown",
      align: "right",
      render: (value: number) => <span className="table-highlight-danger">{formatPercent(value)}</span>,
    },
    {
      title: "夏普",
      dataIndex: "sharpe_ratio",
      key: "sharpe_ratio",
      align: "right",
      render: (value: number) => formatNumber(value, 3),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (value: string) => <Tag color={value === "SUCCESS" ? "green" : "default"}>{value}</Tag>,
    },
  ];

  return (
    <div className="page-enter">
      <Space direction="vertical" size={16} style={{ width: "100%" }}>
        <Space direction="vertical" size={2}>
          <Title level={3} style={{ margin: 0 }}>
            回测分析
          </Title>
          <Text type="secondary">查看历史收益曲线、回撤曲线与关键绩效指标</Text>
        </Space>

        {overviewState.error ? (
          <Alert
            type="error"
            showIcon
            message="回测概览加载失败"
            description={overviewState.error}
            action={
              <Button type="primary" onClick={() => void overviewState.refresh()}>
                重试
              </Button>
            }
          />
        ) : null}

        <Row gutter={[16, 16]} className="stagger">
          <Col xs={24} md={8}>
            <MetricTile
              title="年化收益"
              value={formatPercent(overview?.annual_return ?? 0)}
              tone={(overview?.annual_return ?? 0) >= 0 ? "positive" : "danger"}
              hint={overview?.run_id ? `Run #${overview.run_id}` : "暂无回测"}
            />
          </Col>
          <Col xs={24} md={8}>
            <MetricTile
              title="最大回撤"
              value={formatPercent(overview?.max_drawdown ?? 0)}
              tone="danger"
              hint={overview?.benchmark_symbol ? `基准 ${overview.benchmark_symbol}` : "未配置基准"}
            />
          </Col>
          <Col xs={24} md={8}>
            <MetricTile
              title="夏普比率"
              value={formatNumber(overview?.sharpe_ratio ?? 0, 3)}
              hint={`胜率 ${formatPercent(overview?.win_rate ?? 0)}`}
              tone="neutral"
            />
          </Col>
        </Row>

        <Row gutter={[16, 16]} className="stagger">
          <Col xs={24} xl={16}>
            <SectionCard
              title="净值与基准曲线"
              subtitle="同图区分策略表现和基准表现"
              extra={
                <Button
                  icon={<ReloadOutlined />}
                  loading={overviewState.loading || runsState.loading}
                  onClick={() => {
                    void overviewState.refresh();
                    void runsState.refresh();
                  }}
                >
                  刷新
                </Button>
              }
            >
              {overviewState.loading && !overview ? (
                <div style={{ padding: "60px 0", textAlign: "center" }}>
                  <Spin size="large" />
                </div>
              ) : curveData.length === 0 ? (
                <Empty description="暂无回测曲线" />
              ) : (
                <ResponsiveContainer width="100%" height={330}>
                  <LineChart data={curveData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(18,35,58,0.12)" />
                    <XAxis dataKey="date" minTickGap={24} />
                    <YAxis domain={["auto", "auto"]} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="nav" name="策略净值" stroke="#0E5EA8" strokeWidth={2.5} dot={false} />
                    <Line
                      type="monotone"
                      dataKey="benchmark"
                      name="基准净值"
                      stroke="#D97706"
                      strokeWidth={2}
                      dot={false}
                      connectNulls
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </SectionCard>
          </Col>

          <Col xs={24} xl={8}>
            <SectionCard title="回撤曲线" subtitle="百分比表示，越低风险越高">
              {curveData.length === 0 ? (
                <Empty description="暂无回撤曲线" />
              ) : (
                <ResponsiveContainer width="100%" height={330}>
                  <AreaChart data={curveData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(18,35,58,0.12)" />
                    <XAxis dataKey="date" minTickGap={24} />
                    <YAxis unit="%" />
                    <Tooltip formatter={(value: number) => `${value.toFixed(2)}%`} />
                    <Area type="monotone" dataKey="drawdown" name="回撤" stroke="#BE3D2B" fill="rgba(190,61,43,0.28)" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </SectionCard>
          </Col>
        </Row>

        <SectionCard title="历史回测记录" subtitle="支持按策略分页查询（当前展示最近 20 条）">
          {runsState.error ? (
            <Alert type="warning" showIcon message="历史记录加载失败" description={runsState.error} />
          ) : runsState.loading && runRows.length === 0 ? (
            <div style={{ padding: "50px 0", textAlign: "center" }}>
              <Spin size="large" />
            </div>
          ) : runRows.length === 0 ? (
            <Empty description="暂无历史回测记录" />
          ) : (
            <Table
              rowKey={(row) => row.run_id}
              columns={columns}
              dataSource={runRows}
              pagination={{ pageSize: 10, showSizeChanger: false }}
              scroll={{ x: 980 }}
            />
          )}
        </SectionCard>
      </Space>
    </div>
  );
}
