"use client";

import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Col, DatePicker, Empty, Input, Row, Select, Space, Spin, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { Dayjs } from "dayjs";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { useCallback, useMemo, useState } from "react";

import { MetricTile } from "@/components/metric-tile";
import { SectionCard } from "@/components/section-card";
import { apiGet } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { usePollingQuery } from "@/lib/hooks";
import { OrderView } from "@/types/trading";

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const sideColors: Record<string, string> = {
  BUY: "#0E5EA8",
  SELL: "#D97706",
  UNKNOWN: "#8C9FB7",
};

/** Orders page for transaction records and execution status. */
export default function OrdersPage() {
  const [symbolDraft, setSymbolDraft] = useState<string>("");
  const [symbol, setSymbol] = useState<string>("");
  const [side, setSide] = useState<string | undefined>(undefined);
  const [status, setStatus] = useState<string | undefined>(undefined);
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);

  const request = useCallback(
    () =>
      apiGet<OrderView[]>("/orders", {
        account_name: "paper_account",
        symbol: symbol || undefined,
        side,
        status,
        date_from: dateRange?.[0] ? dateRange[0].format("YYYY-MM-DD") : undefined,
        date_to: dateRange?.[1] ? dateRange[1].format("YYYY-MM-DD") : undefined,
        limit: 300,
        offset: 0,
      }),
    [dateRange, side, status, symbol],
  );

  const { data, loading, error, refresh } = usePollingQuery(request, [dateRange, side, status, symbol], {
    intervalMs: 45000,
  });

  const orders = data ?? [];

  const totalTurnover = useMemo(
    () => orders.reduce((sum, item) => sum + item.price * item.filled_quantity, 0),
    [orders],
  );

  const totalFee = useMemo(() => orders.reduce((sum, item) => sum + item.fee, 0), [orders]);

  const sideDistribution = useMemo(() => {
    const counter = new Map<string, number>();
    for (const item of orders) {
      const key = item.side || "UNKNOWN";
      counter.set(key, (counter.get(key) ?? 0) + 1);
    }
    return Array.from(counter.entries()).map(([name, value]) => ({ name, value }));
  }, [orders]);

  const columns: ColumnsType<OrderView> = [
    { title: "订单ID", dataIndex: "order_id", key: "order_id", width: 92 },
    { title: "日期", dataIndex: "order_date", key: "order_date", width: 120 },
    { title: "股票", dataIndex: "symbol", key: "symbol", width: 120 },
    {
      title: "方向",
      dataIndex: "side",
      key: "side",
      width: 90,
      render: (value: string) => <Tag color={value === "BUY" ? "blue" : "orange"}>{value}</Tag>,
    },
    {
      title: "数量",
      dataIndex: "filled_quantity",
      key: "filled_quantity",
      align: "right",
      render: (value: number) => value.toLocaleString("zh-CN"),
    },
    {
      title: "成交价",
      dataIndex: "price",
      key: "price",
      align: "right",
      render: (value: number) => formatCurrency(value),
    },
    {
      title: "费用",
      dataIndex: "fee",
      key: "fee",
      align: "right",
      render: (value: number) => formatCurrency(value),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 110,
      render: (value: string) => <Tag color={value === "FILLED" ? "green" : value === "REJECTED" ? "red" : "default"}>{value}</Tag>,
    },
    {
      title: "备注",
      dataIndex: "note",
      key: "note",
      ellipsis: true,
      render: (value: string) => value || "-",
    },
  ];

  return (
    <div className="page-enter">
      <Space direction="vertical" size={16} style={{ width: "100%" }}>
        <Space direction="vertical" size={2}>
          <Title level={3} style={{ margin: 0 }}>
            交易记录
          </Title>
          <Text type="secondary">跟踪模拟盘的买卖执行明细、成交金额与成本</Text>
        </Space>

        {error ? (
          <Alert
            type="error"
            showIcon
            message="交易记录加载失败"
            description={error}
            action={
              <Button type="primary" onClick={() => void refresh()}>
                重试
              </Button>
            }
          />
        ) : null}

        <Row gutter={[16, 16]} className="stagger">
          <Col xs={24} md={8}>
            <MetricTile title="订单数量" value={orders.length.toString()} hint="当前筛选条件下" />
          </Col>
          <Col xs={24} md={8}>
            <MetricTile title="成交额" value={formatCurrency(totalTurnover)} hint="价格 × 成交数量" />
          </Col>
          <Col xs={24} md={8}>
            <MetricTile title="总手续费" value={formatCurrency(totalFee)} hint="模拟交易成本" tone="warning" />
          </Col>
        </Row>

        <SectionCard
          title="筛选条件"
          subtitle="支持按股票、方向、状态和日期过滤"
          extra={
            <Button icon={<ReloadOutlined />} onClick={() => void refresh()} loading={loading}>
              刷新
            </Button>
          }
        >
          <Row gutter={[12, 12]} className="filter-bar">
            <Col xs={24} md={12} lg={6}>
              <Input
                placeholder="股票代码"
                value={symbolDraft}
                onChange={(event) => setSymbolDraft(event.target.value.toUpperCase())}
                allowClear
              />
            </Col>
            <Col xs={12} md={6} lg={4}>
              <Select
                allowClear
                style={{ width: "100%" }}
                placeholder="方向"
                value={side}
                onChange={(value) => setSide(value)}
                options={[
                  { label: "BUY", value: "BUY" },
                  { label: "SELL", value: "SELL" },
                ]}
              />
            </Col>
            <Col xs={12} md={6} lg={4}>
              <Select
                allowClear
                style={{ width: "100%" }}
                placeholder="状态"
                value={status}
                onChange={(value) => setStatus(value)}
                options={[
                  { label: "FILLED", value: "FILLED" },
                  { label: "REJECTED", value: "REJECTED" },
                  { label: "PENDING", value: "PENDING" },
                ]}
              />
            </Col>
            <Col xs={24} md={12} lg={6}>
              <RangePicker
                style={{ width: "100%" }}
                value={dateRange}
                onChange={(value) => setDateRange(value)}
              />
            </Col>
            <Col xs={24} md={12} lg={4}>
              <Space>
                <Button type="primary" icon={<SearchOutlined />} onClick={() => setSymbol(symbolDraft.trim())}>
                  查询
                </Button>
                <Button
                  onClick={() => {
                    setSymbol("");
                    setSymbolDraft("");
                    setSide(undefined);
                    setStatus(undefined);
                    setDateRange(null);
                  }}
                >
                  重置
                </Button>
              </Space>
            </Col>
          </Row>
        </SectionCard>

        <Row gutter={[16, 16]} className="stagger">
          <Col xs={24} xl={17}>
            <SectionCard title="订单明细" subtitle="按时间倒序展示">
              {loading && orders.length === 0 ? (
                <div style={{ padding: "60px 0", textAlign: "center" }}>
                  <Spin size="large" />
                </div>
              ) : orders.length === 0 ? (
                <Empty description="暂无交易记录" />
              ) : (
                <Table
                  rowKey={(row) => row.order_id}
                  columns={columns}
                  dataSource={orders}
                  pagination={{ pageSize: 20, showSizeChanger: false }}
                  scroll={{ x: 1080 }}
                />
              )}
            </SectionCard>
          </Col>
          <Col xs={24} xl={7}>
            <SectionCard title="买卖占比" subtitle="按方向统计订单数量">
              {sideDistribution.length === 0 ? (
                <Empty description="暂无分布数据" />
              ) : (
                <ResponsiveContainer width="100%" height={340}>
                  <PieChart>
                    <Pie
                      data={sideDistribution}
                      dataKey="value"
                      nameKey="name"
                      outerRadius={112}
                      label={(entry) => `${entry.name} ${entry.value}`}
                    >
                      {sideDistribution.map((entry) => (
                        <Cell key={entry.name} fill={sideColors[entry.name] ?? sideColors.UNKNOWN} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: number) => `${value} 笔`} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </SectionCard>
          </Col>
        </Row>
      </Space>
    </div>
  );
}
