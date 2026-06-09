import type { Metadata } from "next";

import { AuthProvider } from "@/lib/auth";

import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Kubernetes Agent",
  description: "Troubleshoot Kubernetes with AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <AuthProvider>{children}</AuthProvider>
        </Providers>
      </body>
    </html>
  );
}
