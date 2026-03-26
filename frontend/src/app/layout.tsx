import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dodge AI - Order to Cash Explorer",
  description: "Explore SAP O2C data with natural language queries",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
