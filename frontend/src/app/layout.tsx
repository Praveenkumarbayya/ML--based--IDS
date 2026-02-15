import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { Sidebar } from "@/components/nav";
import { Providers } from "@/components/providers";
import { Topbar } from "@/components/topbar";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "IDS Console — Network Intrusion Detection",
  description:
    "Real-time ML-based network intrusion detection console for the NSL-KDD capstone project.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="min-h-screen antialiased">
        <Providers>
          <div className="flex">
            <Sidebar />
            <div className="flex-1 min-h-screen">
              <Topbar />
              <main className="p-6">{children}</main>
            </div>
          </div>
        </Providers>
      </body>
    </html>
  );
}
