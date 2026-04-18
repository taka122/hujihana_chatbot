import type { Metadata } from "next";

import { AppProviders } from "@/app/providers";
import { hasConfiguredLoginPassword } from "@/lib/auth-config";
import "./globals.css";

export const metadata: Metadata = {
  title: "藤花歯科クリニック専用Chatbot",
  description: "院内資料をすばやく確認できるチャットアプリ"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  const loginRequired = hasConfiguredLoginPassword();

  return (
    <html lang="ja">
      <body className="font-sans">
        <AppProviders loginRequired={loginRequired}>{children}</AppProviders>
      </body>
    </html>
  );
}
