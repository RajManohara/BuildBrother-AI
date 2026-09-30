import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "BuildBrother AI | From build to behavior",
  description:
    "Connect code changes, builds, deployments and runtime evidence in one investigation workspace.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
