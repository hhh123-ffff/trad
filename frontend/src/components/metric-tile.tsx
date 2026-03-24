import { Card, Space, Typography } from "antd";

const { Text, Title } = Typography;

/** Props for metric tile component. */
interface MetricTileProps {
  title: string;
  value: string;
  hint?: string;
  tone?: "neutral" | "positive" | "warning" | "danger";
}

/** Render one prominent metric card used across dashboard pages. */
export function MetricTile({ title, value, hint, tone = "neutral" }: MetricTileProps) {
  return (
    <Card className={`metric-card metric-${tone}`} bordered={false}>
      <Space direction="vertical" size={4}>
        <Text className="metric-title">{title}</Text>
        <Title level={3} className="metric-value">
          {value}
        </Title>
        {hint ? <Text className="metric-hint">{hint}</Text> : null}
      </Space>
    </Card>
  );
}
