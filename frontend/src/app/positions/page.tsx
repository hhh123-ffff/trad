"use client";

import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Col, DatePicker, Empty, Input, Row, Space, Spin, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { Dayjs } from "dayjs";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useCallback, useMemo, useState } from "react";

import { MetricTile } from "@/components/metric-tile";
import { SectionCard } from "@/components/section-card";
import { apiGet } from "@/lib/api";
import { formatCurrency, formatPercent } from "@/lib/format";
import { usePollingQuery } from "@/lib/hooks";
import { PositionView } from "@/types/trading";

const { Title, Text } = Typography;

/** Positions page for account holdings and PnL analysis. */
export default function PositionsPage() {
  const [symbolDraft, setSymbolDraft] = useState<string>("");
  const [symbol, setSymbol] = useState<string>("");
  const [snapshotDate, setSnapshotDate] = useState<Dayjs | null>(null);

  const request = useCallback(
    () =>
      apiGet<PositionView[]>("/positions", {
        account_name: "paper_account",
        symbol: symbol || undefined,
        snapshot_date: snapshotDate ? snapshotDate.format("YYYY-MM-DD") : undefined,
        limit: 200,
        offset: 0,
      }),
    [snapshotDate, symbol],
  );

  const { data, loading, error, refresh } = usePollingQuery(request, [snapshotDate, symbol], {
    intervalMs: 45000,
  });

  const positions = data ?? [];

  const totalMarketValue = useMemo(
    () => positions.reduce((sum, item) => sum + item.market_value, 0),
    [positions],
  );

  const totalPnl = useMemo(
    () => positions.reduce((sum, item) => sum + item.unrealized_pnl, 0),
    [positions],
  );

  const chartData = useMemo(
    () =>
      [...positions]
        .sort((a, b) => b.weight - a.weight)
        .slice(0, 8)
        .map((item) => ({ symbol: item.symbol, weight: Number((item.weight * 100).toFixed(2)) })),
    [positions],
  );

  const columns: ColumnsType<PositionView> = [
    {
      title: "股票",
      dataIndex: "symbol",
      key: "symbol",
      width: 120,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <Text strong>{row.symbol}</Text>
          <Text type="secondary">{row.name}</Text>
        </Space>
      ),
    },
    {
      title: "数量",
      dataIndex: "quantity",
      key: "quantity",
      align: "right",
      render: (value: number) => value.toLocaleString("zh-CN"),
    },
    {
      title: "成本价",
      dataIndex: "avg_cost",
      key: "avg_cost",
      align: "right",
      render: (value: number) => formatCurrency(value),
    },
    {
      title: "现价",
      dataIndex: "last_price",
      key: "last_price",
      align: "right",
      render: (value: number) => formatCurrency(value),
    },
    {
      title: "市值",
      dataIndex: "market_value",
      key: "market_value",
      align: "right",
      render: (value: number) => formatCurrency(value),
    },
    {
      title: "浮盈亏",
      dataIndex: "unrealized_pnl",
      key: "unrealized_pnl",
      align: "right",
      render: (value: number) => (
        <span className={value >= 0 ? "table-highlight-positive" : "table-highlight-danger"}>{formatCurrency(value)}</span>
      ),
    },
    {
      title: "浮盈亏率",
      dataIndex: "unrealized_pnl_pct",
      key: "unrealized_pnl_pct",
      align: "right",
      render: (value: number) => (
        <span className={value >= 0 ? "table-highlight-positive" : "table-highlight-danger"}>{formatPercent(value)}</span>
      ),
    },
    {
      title: "权重",
      dataIndex: "weight",
      key: "weight",
      align: "right",
      render: (value: number) => <Tag color="blue">{formatPercent(value)}</Tag>,
    },
  ];

  return (
    <div className="page-enter">
      <Space direction="vertical" size={16} style={{ width: "100%" }}>
        <Space direction="vertical" size={2}>
          <Title level={3} style={{ margin: 0 }}>
            持仓管理
          </Title>
          <Text type="secondary">展示模拟盘持仓、成本、盈亏与仓位分布</Text>
        </Space>

        {error ? (
          <Alert
            type="error"
            showIcon
            message="持仓数据加载失败"
            description={error}
            action={
              <Button type="primary" onClick={() => void refresh()}>
                重试
              </Button>
            }
          />
        ) : null}

        <Row gutter={[16, 16]} className="stagger">
          <Col xs={24} sm={12} xl={8}>
            <MetricTile title="持仓市值" value={formatCurrency(totalMarketValue)} hint={`持仓数量 ${positions.length} 只`} />
          </Col>
          <Col xs={24} sm={12} xl={8}>
            <MetricTile
              title="总浮盈亏"
              value={formatCurrency(totalPnl)}
              tone={totalPnl >= 0 ? "positive" : "danger"}
              hint="按最新快照计算"
            />
          </Col>
          <Col xs={24} sm={12} xl={8}>
            <MetricTile
              title="持仓日期"
              value={positions[0]?.snapshot_date ?? "-"}
              hint="最新或筛选快照"
              tone="neutral"
            />
          </Col>
        </Row>

        <SectionCard
          title="筛选条件"
          subtitle="按股票和快照日期过滤"
          extra={
            <Button icon={<ReloadOutlined />} onClick={() => void refresh()} loading={loading}>
              刷新
            </Button>
          }
        >
          <Row gutter={[12, 12]} className="filter-bar">
            <Col xs={24} md={10} lg={8}>
              <Input
                placeholder="输入股票代码，例如 600519.SH"
                value={symbolDraft}
                onChange={(event) => setSymbolDraft(event.target.value.toUpperCase())}
                allowClear
              />
            </Col>
            <Col xs={24} md={10} lg={8}>
              <DatePicker
                style={{ width: "100%" }}
                value={snapshotDate}
                onChange={(value) => setSnapshotDate(value)}
                placeholder="选择快照日期"
              />
            </Col>
            <Col xs={24} md={4} lg={8}>
              <Space>
                <Button type="primary" icon={<SearchOutlined />} onClick={() => setSymbol(symbolDraft.trim())}>
                  查询
                </Button>
                <Button
                  onClick={() => {
                    setSymbol("");
                    setSymbolDraft("");
                    setSnapshotDate(null);
                  }}
                >
                  重置
                </Button>
              </Space>
            </Col>
          </Row>
        </SectionCard>

        <Row gutter={[16, 16]} className="stagger">
          <Col xs={24} xl={16}>
            <SectionCard title="持仓列表" subtitle="支持移动端横向滚动查看">
              {loading && positions.length === 0 ? (
                <div style={{ padding: "60px 0", textAlign: "center" }}>
                  <Spin size="large" />
                </div>
              ) : positions.length === 0 ? (
                <Empty description="暂无持仓数据" />
              ) : (
                <Table
                  rowKey={(row) => `${row.snapshot_date}-${row.symbol}`}
                  columns={columns}
                  dataSource={positions}
                  pagination={{ pageSize: 20, showSizeChanger: false }}
                  scroll={{ x: 1080 }}
                />
              )}
            </SectionCard>
          </Col>

          <Col xs={24} xl={8}>
            <SectionCard title="权重分布" subtitle="Top 8 持仓">
              {chartData.length === 0 ? (
                <Empty description="暂无权重数据" />
              ) : (
                <ResponsiveContainer width="100%" height={340}>
                  <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 16, left: 16, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(18,35,58,0.12)" />
                    <XAxis type="number" unit="%" />
                    <YAxis type="category" dataKey="symbol" width={90} />
                    <Tooltip formatter={(value: number) => `${value.toFixed(2)}%`} />
                    <Bar dataKey="weight" fill="#0E5EA8" radius={[0, 8, 8, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </SectionCard>
          </Col>
        </Row>
      </Space>
    </div>
  );
}
