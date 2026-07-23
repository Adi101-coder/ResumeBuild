"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-surface-950/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="group flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-sm font-bold text-white shadow-lg shadow-brand-500/30">
            RB
          </div>
          <div>
            <p className="font-semibold tracking-tight text-white group-hover:text-brand-200">
              ResumeBuild
            </p>
                <p className="text-[11px] text-slate-500">AI job platform</p>
          </div>
        </Link>

        <nav className="flex items-center gap-1">
          <Link
            href="/"
            className={`nav-link ${pathname === "/" ? "nav-link-active" : ""}`}
          >
            Home
          </Link>
          <Link
            href="/dashboard"
            className={`nav-link ${pathname === "/dashboard" ? "nav-link-active" : ""}`}
          >
            Applications
          </Link>
        </nav>
      </div>
    </header>
  );
}
