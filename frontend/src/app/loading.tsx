import { Spin } from "antd";

/** Global loading fallback used by Next.js route transitions. */
export default function Loading() {
  return (
    <div style={{ minHeight: "55vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Spin size="large" />
    </div>
  );
}
