"use client";

import { ReloadOutlined } from "@ant-design/icons";
import { Alert, Button, Col, Empty, Row, Space, Spin, Tag, Typography } from "antd";
import { CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useCallback } from "react";

import { MetricTile } from "@/components/metric-tile";
import { SectionCard } from "@/components/section-card";
import { apiGet } from "@/lib/api";
import { formatCurrency, formatDate, formatPercent } from "@/lib/format";
import { usePollingQuery } from "@/lib/hooks";
import { DashboardOverview } from "@/types/trading";

const { Title, Text } = Typography;

const pieColors = ["#0E5EA8", "#D97706"];

/** Resolve metric tone by profit direction. */
function resolvePnlTone(value: number): "positive" | "danger" | "neutral" {
  if (value > 0) {
    return "positive";
  }
  if (value < 0) {
    return "danger";
  }
  return "neutral";
}

/** Dashboard page showing capital overview and NAV trend. */
export default function DashboardPage() {
  const request = useCallback(
    () => apiGet<DashboardOverview>("/dashboard", { account_name: "paper_account", days: 180 }),
    [],
  );

  const { data, loading, error, lastUpdated, refresh } = usePollingQuery(request, [], {
    intervalMs: 60000,
  });

  const navData = (data?.nav_series ?? []).map((item) => ({
    date: formatDate(item.trade_date),
    nav: item.nav,
  }));

  const assetMix = [
    { name: "持仓市值", value: data?.market_value ?? 0 },
    { name: "现金余额", value: data?.cash ?? 0 },
  ];

  return (
    <div className="page-enter">
      <Space direction="vertical" size={16} style={{ width: "100%" }}>
        <Space direction="vertical" size={2}>
          <Title level={3} style={{ margin: 0 }}>
            Dashboard
          </Title>
          <Text type="secondary">总资产、收益、仓位和净值曲线的实时概览</Text>
        </Space>

        {error ? (
          <Alert
            type="error"
            showIcon
            message="看板数据加载失败"
            description={error}
            action={
              <Button type="primary" onClick={() => void refresh()}>
                重试
              </Button>
            }
          />
        ) : null}

        <Row gutter={[16, 16]} className="stagger">
          <Col xs={24} sm={12} xl={6}>
            <MetricTile title="总资产" value={formatCurrency(data?.total_asset ?? 0)} hint="账户权益（现金+持仓）" />
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <MetricTile
              title="今日收益"
              value={formatCurrency(data?.today_pnl ?? 0)}
              hint={lastUpdated ? `更新时间 ${lastUpdated.toLocaleTimeString("zh-CN")}` : "等待更新"}
              tone={resolvePnlTone(data?.today_pnl ?? 0)}
            />
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <MetricTile
              title="累计收益率"
              value={formatPercent(data?.cumulative_return ?? 0)}
              hint="相对初始资金"
              tone={resolvePnlTone(data?.cumulative_return ?? 0)}
            />
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <MetricTile
              title="当前仓位"
              value={formatPercent(data?.position_ratio ?? 0)}
              hint={`股票池 ${data?.stock_universe_size ?? 0} 只`}
              tone={(data?.position_ratio ?? 0) > 0.9 ? "warning" : "neutral"}
            />
          </Col>
        </Row>

        <Row gutter={[16, 16]} className="stagger">
          <Col xs={24} xl={16}>
            <SectionCard
              title="净值曲线"
              subtitle="近 180 个记录点"
              extra={
                <Space>
                  <Tag color="blue">最大回撤 {formatPercent(data?.max_drawdown ?? 0)}</Tag>
                  <Button icon={<ReloadOutlined />} onClick={() => void refresh()} loading={loading}>
                    刷新
                  </Button>
                </Space>
              }
            >
              {loading && !data ? (
                <div style={{ padding: "60px 0", textAlign: "center" }}>
                  <Spin size="large" />
                </div>
              ) : navData.length === 0 ? (
                <Empty description="暂无净值数据" />
              ) : (
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={navData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(18,35,58,0.15)" />
                    <XAxis dataKey="date" minTickGap={24} />
                    <YAxis domain={["auto", "auto"]} />
                    <Tooltip formatter={(value: number) => [value.toFixed(4), "净值"]} />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="nav"
                      name="策略净值"
                      stroke="#0E5EA8"
                      strokeWidth={2.5}
                      dot={false}
                      activeDot={{ r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </SectionCard>
          </Col>

          <Col xs={24} xl={8}>
            <SectionCard title="资产结构" subtitle="现金与持仓占比">
              {loading && !data ? (
                <div style={{ padding: "60px 0", textAlign: "center" }}>
                  <Spin size="large" />
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={320}>
                  <PieChart>
                    <Pie
                      data={assetMix}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      label={(entry) => `${entry.name} ${formatPercent(entry.percent ?? 0, 1)}`}
                    >
                      {assetMix.map((entry, index) => (
                        <Cell key={entry.name} fill={pieColors[index % pieColors.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: number) => formatCurrency(value)} />
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
