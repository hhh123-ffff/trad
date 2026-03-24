import { Card, Space, Typography } from "antd";
import { ReactNode } from "react";

const { Text, Title } = Typography;

/** Props used by reusable section container card. */
interface SectionCardProps {
  title: string;
  subtitle?: string;
  extra?: ReactNode;
  children: ReactNode;
}

/** Render consistent visual section wrapper for each page block. */
export function SectionCard({ title, subtitle, extra, children }: SectionCardProps) {
  return (
    <Card
      bordered={false}
      className="section-card"
      title={
        <Space direction="vertical" size={0}>
          <Title level={5} className="section-title">
            {title}
          </Title>
          {subtitle ? <Text className="section-subtitle">{subtitle}</Text> : null}
        </Space>
      }
      extra={extra}
    >
      {children}
    </Card>
  );
}
