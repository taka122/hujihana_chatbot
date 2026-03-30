import type { Metadata } from "next";

import { AppProviders } from "@/app/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Universal RAG PoC",
  description: "Upload docs, ask quickly, verify citations"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body className="font-sans">
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
