import type { Metadata } from "next";
import { Manrope, Space_Grotesk } from "next/font/google";
import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";

import "antd/dist/reset.css";
import "./globals.css";

const titleFont = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "700"],
  variable: "--font-title",
});

const bodyFont = Manrope({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-body",
});

export const metadata: Metadata = {
  title: "个人量化交易平台",
  description: "策略研究、回测、模拟盘、风控一体化管理前端",
};

/** Root layout that applies fonts and global shell. */
export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN" className={`${titleFont.variable} ${bodyFont.variable}`}>
      <body className="app-body">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
