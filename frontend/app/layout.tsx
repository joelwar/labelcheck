import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TTB Label Verification",
  description: "Prototype verification flow for alcohol beverage labels"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
