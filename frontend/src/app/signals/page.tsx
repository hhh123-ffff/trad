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
import { formatPercent } from "@/lib/format";
import { usePollingQuery } from "@/lib/hooks";
import { SignalView } from "@/types/trading";

const { Title, Text } = Typography;

const actionColors: Record<string, string> = {
  BUY: "#0E5EA8",
  SELL: "#D97706",
  HOLD: "#1F9D58",
  UNKNOWN: "#8C9FB7",
};

/** Format nullable factor values for table rendering. */
function renderFactorValue(value: number | null): string {
  if (value === null || value === undefined) {
    return "-";
  }
  return value.toFixed(4);
}

/** Signals page for strategy recommendations and factor scores. */
export default function SignalsPage() {
  const [strategyDraft, setStrategyDraft] = useState<string>("multi_factor_v1");
  const [strategyName, setStrategyName] = useState<string>("multi_factor_v1");
  const [tradeDate, setTradeDate] = useState<Dayjs | null>(null);
  const [action, setAction] = useState<string | undefined>(undefined);

  const request = useCallback(
    () =>
      apiGet<SignalView[]>("/signals", {
        strategy_name: strategyName || undefined,
        trade_date: tradeDate ? tradeDate.format("YYYY-MM-DD") : undefined,
        action,
        limit: 300,
        offset: 0,
      }),
    [action, strategyName, tradeDate],
  );

  const { data, loading, error, refresh } = usePollingQuery(request, [action, strategyName, tradeDate], {
    intervalMs: 45000,
  });

  const signals = data ?? [];

  const actionDistribution = useMemo(() => {
    const counter = new Map<string, number>();
    for (const item of signals) {
      counter.set(item.action, (counter.get(item.action) ?? 0) + 1);
    }
    return Array.from(counter.entries()).map(([name, value]) => ({ name, value }));
  }, [signals]);

  const avgScore = useMemo(() => {
    if (signals.length === 0) {
      return 0;
    }
    return signals.reduce((sum, item) => sum + item.score, 0) / signals.length;
  }, [signals]);

  const avgWeight = useMemo(() => {
    if (signals.length === 0) {
      return 0;
    }
    return signals.reduce((sum, item) => sum + item.target_weight, 0) / signals.length;
  }, [signals]);

  const columns: ColumnsType<SignalView> = [
    {
      title: "日期",
      dataIndex: "trade_date",
      key: "trade_date",
      width: 120,
    },
    {
      title: "股票",
      dataIndex: "symbol",
      key: "symbol",
      width: 120,
    },
    {
      title: "动作",
      dataIndex: "action",
      key: "action",
      width: 90,
      render: (value: string) => (
        <Tag color={value === "BUY" ? "blue" : value === "SELL" ? "orange" : "green"}>{value}</Tag>
      ),
    },
    {
      title: "评分",
      dataIndex: "score",
      key: "score",
      align: "right",
      width: 100,
      render: (value: number) => value.toFixed(4),
    },
    {
      title: "目标权重",
      dataIndex: "target_weight",
      key: "target_weight",
      align: "right",
      width: 110,
      render: (value: number) => formatPercent(value),
    },
    {
      title: "M20",
      dataIndex: "momentum_20",
      key: "momentum_20",
      align: "right",
      width: 90,
      render: renderFactorValue,
    },
    {
      title: "M60",
      dataIndex: "momentum_60",
      key: "momentum_60",
      align: "right",
      width: 90,
      render: renderFactorValue,
    },
    {
      title: "量价",
      dataIndex: "volume_factor",
      key: "volume_factor",
      align: "right",
      width: 90,
      render: renderFactorValue,
    },
    {
      title: "波动",
      dataIndex: "volatility_20",
      key: "volatility_20",
      align: "right",
      width: 90,
      render: renderFactorValue,
    },
    {
      title: "说明",
      dataIndex: "reason",
      key: "reason",
      ellipsis: true,
      render: (value: string) => value || "-",
    },
  ];

  return (
    <div className="page-enter">
      <Space direction="vertical" size={16} style={{ width: "100%" }}>
        <Space direction="vertical" size={2}>
          <Title level={3} style={{ margin: 0 }}>
            策略信号
          </Title>
          <Text type="secondary">展示多因子策略给出的买卖建议及对应因子评分</Text>
        </Space>

        {error ? (
          <Alert
            type="error"
            showIcon
            message="策略信号加载失败"
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
            <MetricTile title="信号总数" value={signals.length.toString()} hint="当前筛选结果" />
          </Col>
          <Col xs={24} md={8}>
            <MetricTile title="平均评分" value={avgScore.toFixed(4)} hint="多因子综合得分" />
          </Col>
          <Col xs={24} md={8}>
            <MetricTile title="平均目标权重" value={formatPercent(avgWeight)} hint="组合配置建议" />
          </Col>
        </Row>

        <SectionCard
          title="筛选条件"
          subtitle="按日期、策略名与动作过滤"
          extra={
            <Button icon={<ReloadOutlined />} onClick={() => void refresh()} loading={loading}>
              刷新
            </Button>
          }
        >
          <Row gutter={[12, 12]} className="filter-bar">
            <Col xs={24} md={10} lg={8}>
              <Input
                placeholder="策略名称"
                value={strategyDraft}
                onChange={(event) => setStrategyDraft(event.target.value)}
                allowClear
              />
            </Col>
            <Col xs={24} md={7} lg={6}>
              <DatePicker
                style={{ width: "100%" }}
                value={tradeDate}
                onChange={(value) => setTradeDate(value)}
                placeholder="交易日期"
              />
            </Col>
            <Col xs={24} md={7} lg={4}>
              <Select
                allowClear
                style={{ width: "100%" }}
                placeholder="动作"
                value={action}
                onChange={(value) => setAction(value)}
                options={[
                  { label: "BUY", value: "BUY" },
                  { label: "SELL", value: "SELL" },
                  { label: "HOLD", value: "HOLD" },
                ]}
              />
            </Col>
            <Col xs={24} md={24} lg={6}>
              <Space>
                <Button type="primary" icon={<SearchOutlined />} onClick={() => setStrategyName(strategyDraft.trim())}>
                  查询
                </Button>
                <Button
                  onClick={() => {
                    setStrategyDraft("multi_factor_v1");
                    setStrategyName("multi_factor_v1");
                    setTradeDate(null);
                    setAction(undefined);
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
            <SectionCard title="信号列表" subtitle="因子评分与动作详情">
              {loading && signals.length === 0 ? (
                <div style={{ padding: "60px 0", textAlign: "center" }}>
                  <Spin size="large" />
                </div>
              ) : signals.length === 0 ? (
                <Empty description="暂无策略信号" />
              ) : (
                <Table
                  rowKey={(row) => `${row.trade_date}-${row.symbol}-${row.action}`}
                  columns={columns}
                  dataSource={signals}
                  pagination={{ pageSize: 20, showSizeChanger: false }}
                  scroll={{ x: 1180 }}
                />
              )}
            </SectionCard>
          </Col>
          <Col xs={24} xl={7}>
            <SectionCard title="动作分布" subtitle="BUY / SELL / HOLD 数量占比">
              {actionDistribution.length === 0 ? (
                <Empty description="暂无分布数据" />
              ) : (
                <ResponsiveContainer width="100%" height={340}>
                  <PieChart>
                    <Pie
                      data={actionDistribution}
                      dataKey="value"
                      nameKey="name"
                      outerRadius={112}
                      label={(entry) => `${entry.name} ${entry.value}`}
                    >
                      {actionDistribution.map((entry) => (
                        <Cell key={entry.name} fill={actionColors[entry.name] ?? actionColors.UNKNOWN} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: number) => `${value} 条`} />
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
