import Link from "next/link";

const FOOTER_LINKS = {
  Product: [
    { label: "How it works", href: "/#how-it-works" },
    { label: "Features", href: "/#features" },
    { label: "Job sources", href: "/#sources" },
    { label: "Get started", href: "/#workspace" },
  ],
  Company: [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Applications", href: "/dashboard" },
  ],
  Legal: [
    { label: "Privacy", href: "#" },
    { label: "Terms", href: "#" },
  ],
  Socials: [
    { label: "LinkedIn", href: "#" },
    { label: "Twitter", href: "#" },
  ],
};

export function LandingFooter() {
  return (
    <footer className="relative overflow-hidden bg-ink text-white">
      <div className="mx-auto max-w-7xl px-6 py-16 lg:px-10">
        <div className="grid gap-12 lg:grid-cols-[1.2fr_2fr]">
          <div className="space-y-4">
            <span className="text-xl font-semibold">ResumeBuild</span>
            <p className="max-w-sm text-sm leading-relaxed text-white/60">
              Parse your resume once. Discover jobs across every major board. Match, personalize,
              and track every application in one place.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
            {Object.entries(FOOTER_LINKS).map(([title, links]) => (
              <div key={title}>
                <p className="mb-4 text-sm font-semibold text-white">{title}</p>
                <ul className="space-y-3">
                  {links.map((link) => (
                    <li key={link.label}>
                      <Link
                        href={link.href}
                        className="text-sm text-white/50 transition hover:text-white"
                      >
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-16 border-t border-white/10 pt-8 text-center text-xs text-white/40">
          © {new Date().getFullYear()} ResumeBuild. All rights reserved.
        </div>
      </div>

      <p
        aria-hidden
        className="pointer-events-none absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-[28%] select-none text-[clamp(5rem,18vw,14rem)] font-bold leading-none text-white/[0.04]"
      >
        ResumeBuild
      </p>
    </footer>
  );
}
