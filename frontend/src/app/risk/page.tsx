"use client";

import { ReloadOutlined, SafetyCertificateOutlined } from "@ant-design/icons";
import { Alert, Button, Col, Empty, List, Progress, Row, Space, Spin, Tag, Typography } from "antd";
import { useCallback } from "react";

import { MetricTile } from "@/components/metric-tile";
import { SectionCard } from "@/components/section-card";
import { apiGet } from "@/lib/api";
import { formatPercent } from "@/lib/format";
import { usePollingQuery } from "@/lib/hooks";
import { RiskAlert, RiskStatus } from "@/types/trading";

const { Title, Text } = Typography;

/** Map risk level text to visual tag class. */
function levelClass(level: string): string {
  const normalized = level.toUpperCase();
  if (normalized === "CRITICAL") {
    return "level-tag-critical";
  }
  if (normalized === "WARNING") {
    return "level-tag-warning";
  }
  return "level-tag-info";
}

/** Convert risk level to progress color. */
function progressColor(level: string): string {
  const normalized = level.toUpperCase();
  if (normalized === "CRITICAL") {
    return "#BE3D2B";
  }
  if (normalized === "WARNING") {
    return "#D97706";
  }
  return "#0E5EA8";
}

/** Render one alert item with severity and message. */
function renderRiskAlert(item: RiskAlert): JSX.Element {
  const type = item.level === "CRITICAL" ? "error" : item.level === "WARNING" ? "warning" : "info";
  return <Alert type={type} showIcon message={`${item.risk_type} · ${item.level}`} description={item.message} />;
}

/** Risk control page showing drawdown, exposure, and active warnings. */
export default function RiskPage() {
  const request = useCallback(() => apiGet<RiskStatus>("/risk", { account_name: "paper_account" }), []);
  const { data, loading, error, refresh } = usePollingQuery(request, [], { intervalMs: 30000 });

  const status = data;

  return (
    <div className="page-enter">
      <Space direction="vertical" size={16} style={{ width: "100%" }}>
        <Space direction="vertical" size={2}>
          <Title level={3} style={{ margin: 0 }}>
            风控中心
          </Title>
          <Text type="secondary">监控回撤、仓位与止损触发情况，输出实时风险告警</Text>
        </Space>

        {error ? (
          <Alert
            type="error"
            showIcon
            message="风控状态加载失败"
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
            <MetricTile
              title="总体风险等级"
              value={status?.overall_level ?? "INFO"}
              hint="由告警级别自动聚合"
              tone={status?.overall_level === "CRITICAL" ? "danger" : status?.overall_level === "WARNING" ? "warning" : "neutral"}
            />
          </Col>
          <Col xs={24} md={8}>
            <MetricTile
              title="最大回撤"
              value={formatPercent(status?.max_drawdown ?? 0)}
              hint="阈值建议 < 10%"
              tone={(status?.max_drawdown ?? 0) >= 0.1 ? "danger" : "neutral"}
            />
          </Col>
          <Col xs={24} md={8}>
            <MetricTile
              title="当前仓位"
              value={formatPercent(status?.position_ratio ?? 0)}
              hint="阈值建议 < 90%"
              tone={(status?.position_ratio ?? 0) >= 0.9 ? "warning" : "neutral"}
            />
          </Col>
        </Row>

        <Row gutter={[16, 16]} className="stagger">
          <Col xs={24} xl={9}>
            <SectionCard
              title="风险刻度"
              subtitle="核心风险因子实时可视化"
              extra={
                <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void refresh()}>
                  刷新
                </Button>
              }
            >
              {loading && !status ? (
                <div style={{ padding: "50px 0", textAlign: "center" }}>
                  <Spin size="large" />
                </div>
              ) : !status ? (
                <Empty description="暂无风控数据" />
              ) : (
                <Space direction="vertical" size={22} style={{ width: "100%" }}>
                  <div>
                    <Space align="center">
                      <SafetyCertificateOutlined style={{ color: progressColor(status.overall_level) }} />
                      <Text strong>仓位风险</Text>
                    </Space>
                    <Progress
                      percent={Number(((status.position_ratio ?? 0) * 100).toFixed(2))}
                      strokeColor={progressColor(status.overall_level)}
                    />
                  </div>
                  <div>
                    <Space align="center">
                      <SafetyCertificateOutlined style={{ color: progressColor(status.overall_level) }} />
                      <Text strong>回撤风险</Text>
                    </Space>
                    <Progress
                      percent={Number(((status.max_drawdown ?? 0) * 100).toFixed(2))}
                      strokeColor={progressColor(status.overall_level)}
                    />
                  </div>
                  <div>
                    <Text type="secondary">当前等级</Text>
                    <div style={{ marginTop: 8 }}>
                      <Tag className={levelClass(status.overall_level)}>{status.overall_level}</Tag>
                    </div>
                  </div>
                </Space>
              )}
            </SectionCard>
          </Col>

          <Col xs={24} xl={15}>
            <SectionCard title="告警列表" subtitle="按最新风险状态返回，便于人工复核与记录">
              {loading && !status ? (
                <div style={{ padding: "50px 0", textAlign: "center" }}>
                  <Spin size="large" />
                </div>
              ) : !status || status.alerts.length === 0 ? (
                <Empty description="暂无告警" />
              ) : (
                <List
                  itemLayout="vertical"
                  dataSource={status.alerts}
                  split={false}
                  renderItem={(item) => (
                    <List.Item style={{ padding: "0 0 10px" }}>{renderRiskAlert(item)}</List.Item>
                  )}
                />
              )}
            </SectionCard>
          </Col>
        </Row>
      </Space>
    </div>
  );
}
