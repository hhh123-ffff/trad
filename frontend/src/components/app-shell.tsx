"use client";

import {
  AlertOutlined,
  BarChartOutlined,
  DashboardOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  StockOutlined,
  SwapOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { App, Button, ConfigProvider, Drawer, Grid, Layout, Menu, Space, Typography, type MenuProps } from "antd";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useMemo, useState } from "react";

const { Header, Sider, Content } = Layout;
const { Text, Title } = Typography;

/** Props for application shell wrapper. */
interface AppShellProps {
  children: ReactNode;
}

/** Navigation menu item definition. */
type NavigationItem = Required<MenuProps>["items"][number];

/** Build static menu entries for all platform modules. */
const menuItems: NavigationItem[] = [
  { key: "/dashboard", icon: <DashboardOutlined />, label: "资产看板" },
  { key: "/positions", icon: <StockOutlined />, label: "持仓管理" },
  { key: "/orders", icon: <SwapOutlined />, label: "交易记录" },
  { key: "/signals", icon: <ThunderboltOutlined />, label: "策略信号" },
  { key: "/backtest", icon: <BarChartOutlined />, label: "回测分析" },
  { key: "/risk", icon: <AlertOutlined />, label: "风控中心" },
];

/** Resolve selected sidebar key from current pathname. */
function resolveMenuKey(pathname: string): string {
  const found = menuItems?.find((item) => {
    if (!item || typeof item === "string") {
      return false;
    }
    const key = item.key?.toString() ?? "";
    return pathname.startsWith(key);
  });
  return found && typeof found !== "string" ? (found.key?.toString() ?? "/dashboard") : "/dashboard";
}

/** Main shell that provides responsive navigation and themed layout. */
export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.lg;
  const [collapsed, setCollapsed] = useState<boolean>(false);
  const [mobileOpen, setMobileOpen] = useState<boolean>(false);

  const selectedKey = useMemo(() => resolveMenuKey(pathname), [pathname]);

  /** Handle route navigation from menu click. */
  const handleMenuClick: MenuProps["onClick"] = ({ key }) => {
    const target = key.toString();
    router.push(target);
    setMobileOpen(false);
  };

  const sideMenu = (
    <Menu
      mode="inline"
      selectedKeys={[selectedKey]}
      items={menuItems}
      onClick={handleMenuClick}
      className="shell-menu"
    />
  );

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: "#0E5EA8",
          borderRadius: 12,
          colorBgContainer: "rgba(255, 255, 255, 0.86)",
          colorText: "#12233A",
          colorTextSecondary: "#5F6F85",
        },
      }}
    >
      <App>
        <Layout className="shell-root">
          {isMobile ? null : (
            <Sider
              className="shell-sider"
              width={250}
              collapsible
              collapsed={collapsed}
              trigger={null}
              breakpoint="lg"
              onBreakpoint={(broken) => {
                if (broken) {
                  setCollapsed(false);
                }
              }}
            >
              <div className="brand-block">
                <Title level={4} className="brand-title">
                  Q-Trade
                </Title>
                <Text className="brand-subtitle">个人量化交易平台</Text>
              </div>
              {sideMenu}
            </Sider>
          )}

          <Layout>
            <Header className="shell-header">
              <Space size={12} align="center">
                {isMobile ? (
                  <Button
                    type="text"
                    icon={<MenuUnfoldOutlined />}
                    onClick={() => setMobileOpen(true)}
                    aria-label="open navigation"
                  />
                ) : (
                  <Button
                    type="text"
                    icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                    onClick={() => setCollapsed((value) => !value)}
                    aria-label="toggle sidebar"
                  />
                )}
                <div>
                  <Title level={5} className="header-title">
                    实盘前模拟与研究一体化控制台
                  </Title>
                  <Text className="header-subtitle">数据更新、信号追踪、风控联动</Text>
                </div>
              </Space>
            </Header>

            <Content className="shell-content">
              <div className="page-container">{children}</div>
            </Content>
          </Layout>
        </Layout>

        <Drawer
          title="导航菜单"
          placement="left"
          width={280}
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          className="mobile-drawer"
        >
          {sideMenu}
        </Drawer>
      </App>
    </ConfigProvider>
  );
}
