import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { SiteHeader } from "@/components/SiteHeader";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "ResumeBuild",
  description: "AI-powered resume parsing, job matching, and application automation",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrains.variable}`}>
      <body>
        <div className="mesh-bg min-h-screen">
          <SiteHeader />
          <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
          <footer className="border-t border-white/[0.04] py-8 text-center text-xs text-slate-600">
            ResumeBuild · Parse → Discover → Match → Apply
          </footer>
        </div>
      </body>
    </html>
  );
}
