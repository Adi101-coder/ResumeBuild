"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { StatCard } from "@/components/StatCard";
import {
  getAnalytics,
  getApplications,
  logClick,
  updateApplicationStatus,
  type Application,
} from "@/lib/api";

const STATUS_OPTIONS = ["applied", "interview", "offer", "rejected", "pending"];

const STATUS_STYLES: Record<string, string> = {
  applied: "border-blue-500/30 bg-blue-500/10 text-blue-200",
  interview: "border-amber-500/30 bg-amber-500/10 text-amber-200",
  offer: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
  rejected: "border-rose-500/30 bg-rose-500/10 text-rose-200",
  pending: "border-white/10 bg-white/5 text-slate-300",
};

export default function DashboardPage() {
  const [candidateId, setCandidateId] = useState("");
  const [applications, setApplications] = useState<Application[]>([]);
  const [analytics, setAnalytics] = useState<{
    total_applications: number;
    interview_rate: number;
    status_breakdown: Record<string, number>;
    average_ats_score: number | null;
  } | null>(null);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (id: number) => {
    setLoading(true);
    setError("");
    try {
      const [apps, stats] = await Promise.all([getApplications(id), getAnalytics(id)]);
      setApplications(apps);
      setAnalytics(stats);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const stored = window.localStorage.getItem("candidateId");
    if (stored) {
      setCandidateId(stored);
      void load(Number(stored));
    }
  }, [load]);

  async function handleLoad() {
    const id = Number(candidateId);
    if (!id) return;
    window.localStorage.setItem("candidateId", String(id));
    logClick("load_dashboard", `candidate ${id}`);
    await load(id);
  }

  async function handleStatusChange(appId: number, status: string) {
    try {
      const updated = await updateApplicationStatus(appId, status);
      setApplications((prev) => prev.map((a) => (a.id === appId ? updated : a)));
      if (candidateId) await load(Number(candidateId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Status update failed");
    }
  }

  const filtered =
    filter === "all" ? applications : applications.filter((a) => a.status === filter);

  return (
    <div className="animate-fade-up space-y-10">
      <section className="relative overflow-hidden rounded-3xl border border-white/[0.08] bg-gradient-to-br from-surface-900 to-brand-900/10 p-8">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <span className="section-label">Dashboard</span>
            <h1 className="mt-2 text-3xl font-bold tracking-tight">Your applications</h1>
            <p className="mt-2 max-w-lg text-slate-400">
              Every application is saved to your database — status, match score, company, and apply link persist across sessions.
            </p>
          </div>
          <Link href="/" className="btn-secondary shrink-0">
            ← Back to home
          </Link>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <input
            className="input max-w-[140px] font-mono"
            placeholder="ID"
            value={candidateId}
            onChange={(e) => setCandidateId(e.target.value)}
          />
          <button className="btn-primary" disabled={loading} onClick={() => void handleLoad()}>
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>
        {error && <div className="alert-error mt-4">{error}</div>}
      </section>

      {analytics && (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Total applied" value={analytics.total_applications} />
          <StatCard
            label="Interview rate"
            value={`${analytics.interview_rate}%`}
            accent="text-amber-400"
          />
          <StatCard
            label="Avg match score"
            value={analytics.average_ats_score ?? "—"}
            accent="text-brand-300"
          />
          <StatCard
            label="In interview"
            value={analytics.status_breakdown.interview ?? 0}
            accent="text-emerald-400"
          />
        </section>
      )}

      <section className="card">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-lg font-semibold">Application history</h2>
          <div className="flex flex-wrap gap-2">
            {["all", ...STATUS_OPTIONS].map((s) => (
              <button
                key={s}
                className={`filter-pill ${filter === s ? "filter-pill-active" : "filter-pill-inactive"}`}
                onClick={() => setFilter(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 py-16 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-sm font-semibold text-slate-500">
              0
            </div>
            <p className="text-slate-400">No applications yet</p>
            <p className="mt-2 max-w-sm text-sm text-slate-500">
              Match jobs on the home page and click &quot;Mark applied&quot; to track them here.
            </p>
            <Link href="/" className="btn-primary mt-6">
              Find jobs
            </Link>
          </div>
        ) : (
          <>
            {/* Mobile cards */}
            <div className="space-y-3 lg:hidden">
              {filtered.map((app) => (
                <div
                  key={app.id}
                  className="rounded-2xl border border-white/[0.06] bg-surface-950/50 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold">{app.job_title}</p>
                      <p className="text-sm text-slate-400">{app.job_company}</p>
                    </div>
                    {app.match_score != null && (
                      <span className="badge-neutral font-mono">{app.match_score}%</span>
                    )}
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <select
                      className={`rounded-lg border px-2 py-1 text-xs capitalize ${STATUS_STYLES[app.status] ?? ""}`}
                      value={app.status}
                      onChange={(e) => void handleStatusChange(app.id, e.target.value)}
                    >
                      {STATUS_OPTIONS.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                    {app.apply_url && (
                      <a
                        href={app.apply_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-brand-400"
                      >
                        Open ↗
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Desktop table */}
            <div className="hidden overflow-x-auto lg:block">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-white/[0.06] text-xs uppercase tracking-wide text-slate-500">
                    <th className="pb-4 pr-4 font-medium">Role</th>
                    <th className="pb-4 pr-4 font-medium">Company</th>
                    <th className="pb-4 pr-4 font-medium">Location</th>
                    <th className="pb-4 pr-4 font-medium">Match</th>
                    <th className="pb-4 pr-4 font-medium">Status</th>
                    <th className="pb-4 pr-4 font-medium">Applied</th>
                    <th className="pb-4 font-medium">Link</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((app) => (
                    <tr key={app.id} className="table-row">
                      <td className="py-4 pr-4 font-medium text-white">{app.job_title}</td>
                      <td className="py-4 pr-4 text-slate-300">{app.job_company}</td>
                      <td className="py-4 pr-4 text-slate-500">{app.job_location || "—"}</td>
                      <td className="py-4 pr-4 font-mono text-brand-300">
                        {app.match_score != null ? `${app.match_score}%` : "—"}
                      </td>
                      <td className="py-4 pr-4">
                        <select
                          className={`rounded-lg border px-2.5 py-1.5 text-xs capitalize ${STATUS_STYLES[app.status] ?? ""}`}
                          value={app.status}
                          onChange={(e) => void handleStatusChange(app.id, e.target.value)}
                        >
                          {STATUS_OPTIONS.map((s) => (
                            <option key={s} value={s}>{s}</option>
                          ))}
                        </select>
                      </td>
                      <td className="py-4 pr-4 text-slate-500">
                        {app.applied_at
                          ? new Date(app.applied_at).toLocaleDateString()
                          : "—"}
                      </td>
                      <td className="py-4">
                        {app.apply_url ? (
                          <a
                            href={app.apply_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-brand-400 hover:text-brand-300"
                          >
                            Open ↗
                          </a>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
