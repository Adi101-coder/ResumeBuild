"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ScoreRing } from "@/components/ScoreRing";
import { StatCard } from "@/components/StatCard";
import {
  createApplication,
  discoverJobs,
  getApplications,
  getJobSources,
  logClick,
  matchJobs,
  personalizeResume,
  uploadResume,
  type CandidateProfile,
  type DiscoveryResult,
  type JobSource,
  type MatchResult,
} from "@/lib/api";

const PIPELINE = [
  { id: "upload", label: "Parse resume" },
  { id: "discover", label: "Discover jobs" },
  { id: "match", label: "Score matches" },
  { id: "apply", label: "Track applications" },
];

const STEPS = [
  { n: "01", title: "Upload resume", desc: "PDF → structured profile" },
  { n: "02", title: "Discover jobs", desc: "Queries from your background" },
  { n: "03", title: "Match & score", desc: "AI ranks 0–100" },
  { n: "04", title: "Apply & track", desc: "Personalize + dashboard" },
];

export default function HomePage() {
  const [loading, setLoading] = useState(false);
  const [candidateId, setCandidateId] = useState<number | null>(null);
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [discovery, setDiscovery] = useState<DiscoveryResult | null>(null);
  const [matches, setMatches] = useState<MatchResult[]>([]);
  const [appliedIds, setAppliedIds] = useState<Set<number>>(new Set());
  const [jobSources, setJobSources] = useState<JobSource[]>([]);
  const [pipelineStep, setPipelineStep] = useState(0);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    void getJobSources().then((r) => setJobSources(r.sources)).catch(() => {});
  }, []);

  useEffect(() => {
    const stored = window.localStorage.getItem("candidateId");
    if (stored) {
      const id = Number(stored);
      setCandidateId(id);
      void getApplications(id).then((apps) =>
        setAppliedIds(new Set(apps.map((a) => a.job_id))),
      ).catch(() => {});
    }
  }, []);

  async function handleUpload(file: File) {
    setLoading(true);
    setError("");
    setMessage("");
    setMatches([]);
    setDiscovery(null);
    try {
      const result = await uploadResume(file);
      setCandidateId(result.candidate_id);
      window.localStorage.setItem("candidateId", String(result.candidate_id));
      setProfile(result.profile);
      setPipelineStep(1);
      setMessage(`Resume parsed for ${result.profile.name || "candidate"}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleDiscoverAndMatch() {
    if (!candidateId) return;
    setLoading(true);
    setError("");
    setPipelineStep(2);
    try {
      const disc = await discoverJobs(candidateId);
      setDiscovery(disc);
      setPipelineStep(3);
      const results = await matchJobs(candidateId);
      setMatches(results);
      setPipelineStep(4);
      const sourceCount = disc.sources ? Object.keys(disc.sources).length : 0;
      setMessage(
        `${disc.created} new jobs from ${sourceCount} sources · ${results.length} top matches`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Discovery failed");
    } finally {
      setLoading(false);
    }
  }

  async function handlePersonalize(jobId: number) {
    if (!candidateId) return;
    setLoading(true);
    setError("");
    try {
      const result = await personalizeResume(candidateId, jobId);
      setMessage(`Optimized resume ready · ATS ${result.ats_report.overall_score}%`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Personalization failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleApply(match: MatchResult) {
    if (!candidateId) return;
    setLoading(true);
    setError("");
    try {
      await createApplication(candidateId, match.job_id, match.score);
      setAppliedIds((prev) => new Set(prev).add(match.job_id));
      setMessage(`Tracked application to ${match.title} at ${match.company}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Apply failed");
    } finally {
      setLoading(false);
    }
  }

  const passedCount = matches.filter((m) => m.passed_threshold).length;
  const initials = profile?.name
    ? profile.name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()
    : "?";

  return (
    <div className="animate-fade-up space-y-12">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-3xl border border-white/[0.08] bg-gradient-to-br from-surface-900 via-surface-900 to-brand-900/20 p-8 md:p-12">
        <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-brand-500/20 blur-3xl animate-pulse-soft" />
        <div className="pointer-events-none absolute -bottom-16 left-1/4 h-48 w-48 rounded-full bg-emerald-500/10 blur-3xl" />

        <div className="relative max-w-3xl space-y-6">
          <span className="section-label">Multi-source job platform</span>
          <h1 className="text-4xl font-bold leading-tight tracking-tight md:text-5xl">
            <span className="gradient-text">Your resume. Every job board.</span>
            <span className="block text-slate-300">Matched, scored, and tracked.</span>
          </h1>
          <p className="text-lg leading-relaxed text-slate-400">
            ResumeBuild pulls from Greenhouse, Lever, Ashby, YC, RemoteOK, Reddit, and more —
            scores each role against your profile, and stores every application in your database.
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <Link href="#upload" className="btn-primary">
              Get started
            </Link>
            {candidateId && (
              <Link href="/dashboard" className="btn-secondary">
                View applications
              </Link>
            )}
          </div>

          {candidateId && (
            <p className="font-mono text-xs text-slate-500">
              Session · candidate #{candidateId}
            </p>
          )}
        </div>
      </section>

      {/* Pipeline progress */}
      <section className="card">
        <span className="section-label">Live pipeline</span>
        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {PIPELINE.map((step, i) => (
            <div
              key={step.id}
              className={`progress-step ${
                pipelineStep > i + 1
                  ? "progress-step-done"
                  : pipelineStep === i + 1
                    ? "progress-step-active"
                    : ""
              }`}
            >
              <span className="font-mono text-xs opacity-60">{String(i + 1).padStart(2, "0")}</span>
              <span>{step.label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Job sources */}
      {jobSources.length > 0 && (
        <section className="card">
          <span className="section-label">Job sources</span>
          <div className="mt-3 flex flex-wrap gap-2">
            {jobSources.map((s) => (
              <span
                key={s.key}
                className={`source-pill ${
                  s.status === "active"
                    ? "source-active"
                    : s.status === "needs_credentials"
                      ? "source-needs-auth"
                      : "source-config"
                }`}
              >
                {s.name}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Steps */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((step) => (
          <div key={step.n} className="card-hover group">
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl border border-brand-500/20 bg-brand-500/10 font-mono text-sm font-semibold text-brand-300">
              {step.n}
            </div>
            <h3 className="font-semibold text-white">{step.title}</h3>
            <p className="mt-1 text-sm text-slate-500">{step.desc}</p>
          </div>
        ))}
      </section>

      {/* Alerts */}
      {message && <div className="alert-success">{message}</div>}
      {error && <div className="alert-error">{error}</div>}

      {/* Upload + Discover */}
      <section id="upload" className="grid gap-6 lg:grid-cols-2">
        <div className="card space-y-5">
          <div>
            <span className="section-label">Step 1</span>
            <h2 className="mt-2 text-xl font-semibold">Upload your resume</h2>
            <p className="mt-1 text-sm text-slate-400">
              PDF · engineering, finance, healthcare, sales, design, and more.
            </p>
          </div>

          <label className="upload-zone">
            <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-xs font-semibold uppercase tracking-widest text-slate-400">
              PDF
            </span>
            <span className="font-medium text-slate-200">
              {loading ? "Processing…" : "Drop PDF or click to browse"}
            </span>
            <span className="mt-1 text-xs text-slate-500">Max recommended · 2 pages</span>
            <input
              type="file"
              accept="application/pdf"
              className="hidden"
              disabled={loading}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void handleUpload(file);
              }}
            />
          </label>

          {profile && (
            <div className="rounded-2xl border border-white/[0.06] bg-surface-950/80 p-5">
              <div className="flex gap-4">
                <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-lg font-bold text-white">
                  {initials}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-lg font-semibold">{profile.name || "Candidate"}</p>
                  <p className="truncate text-sm text-slate-400">{profile.email || "No email detected"}</p>
                  {profile.location && (
                    <p className="text-xs text-slate-500">{profile.location}</p>
                  )}
                </div>
              </div>

              {profile.preferred_roles && profile.preferred_roles.length > 0 && (
                <div className="mt-4">
                  <p className="section-label mb-2">Target roles</p>
                  <div className="flex flex-wrap gap-2">
                    {profile.preferred_roles.map((r) => (
                      <span key={r} className="badge border-brand-500/30 bg-brand-500/10 text-brand-200">
                        {r}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-4">
                <p className="section-label mb-2">Skills</p>
                <div className="flex flex-wrap gap-1.5">
                  {profile.skills.slice(0, 14).map((skill) => (
                    <span key={skill} className="badge-neutral">{skill}</span>
                  ))}
                  {profile.skills.length > 14 && (
                    <span className="badge-neutral">+{profile.skills.length - 14}</span>
                  )}
                </div>
              </div>

              {profile.experience.length > 0 && (
                <div className="mt-4 space-y-2 border-t border-white/[0.06] pt-4">
                  <p className="section-label">Experience</p>
                  {profile.experience.slice(0, 2).map((exp, i) => (
                    <div key={i} className="text-sm">
                      <p className="font-medium text-slate-200">{exp.role}</p>
                      <p className="text-slate-500">{exp.company}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="card flex flex-col space-y-5">
          <div>
            <span className="section-label">Step 2</span>
            <h2 className="mt-2 text-xl font-semibold">Discover & match</h2>
            <p className="mt-1 text-sm text-slate-400">
              Profile-driven queries across Greenhouse, Lever, Ashby, YC, RemoteOK, Reddit, and career pages.
            </p>
          </div>

          {discovery?.sources && (
            <div className="rounded-2xl border border-white/[0.06] bg-surface-950/80 p-4">
              <p className="section-label mb-2">Source breakdown</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {Object.entries(discovery.sources).map(([name, stat]) => (
                  <div key={name} className="flex justify-between text-xs">
                    <span className="capitalize text-slate-400">{name}</span>
                    <span className="font-mono text-slate-300">
                      {stat.fetched} jobs{stat.errors ? " · error" : ""}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {discovery && (
            <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4">
              <p className="font-semibold text-emerald-300">
                +{discovery.created} jobs added
              </p>
              <p className="mt-2 text-xs leading-relaxed text-slate-400">
                <span className="text-slate-500">Queries · </span>
                {discovery.search_queries.slice(0, 6).join(" · ")}
                {discovery.search_queries.length > 6 && " …"}
              </p>
              <p className="mt-2 font-mono text-xs text-slate-500">
                {discovery.total_jobs_in_db} jobs in pool
              </p>
            </div>
          )}

          <button
            className="btn-primary w-full py-3"
            disabled={!candidateId || loading}
            onClick={() => {
              logClick("click_discover_and_match");
              void handleDiscoverAndMatch();
            }}
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                Discovering…
              </span>
            ) : (
              "Discover & Match Jobs"
            )}
          </button>

          {!candidateId && (
            <p className="text-center text-xs text-slate-500">Upload a resume first</p>
          )}

          {matches.length > 0 && (
            <div className="mt-auto grid grid-cols-3 gap-3">
              <StatCard label="Matches" value={matches.length} />
              <StatCard label="≥ 75%" value={passedCount} accent="text-emerald-400" />
              <StatCard label="Applied" value={appliedIds.size} accent="text-brand-300" />
            </div>
          )}
        </div>
      </section>

      {/* Matches */}
      {matches.length > 0 && (
        <section className="space-y-6">
          <div className="flex items-end justify-between">
            <div>
              <span className="section-label">Results</span>
              <h2 className="mt-2 text-2xl font-bold">Top job matches</h2>
            </div>
            <Link href="/dashboard" className="btn-ghost text-brand-400">
              Track all →
            </Link>
          </div>

          <div className="space-y-4">
            {matches.map((match, i) => (
              <article
                key={match.job_id}
                className="card-hover flex flex-col gap-4 p-5 lg:flex-row lg:items-center"
                style={{ animationDelay: `${i * 50}ms` }}
              >
                <ScoreRing score={match.score} passed={match.passed_threshold} />

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold text-white">{match.title}</h3>
                    {appliedIds.has(match.job_id) && (
                      <span className="badge-pass">Applied</span>
                    )}
                    {!match.passed_threshold && (
                      <span className="badge-fail">Below threshold</span>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-slate-400">
                    {match.company}
                    {match.location && ` · ${match.location}`}
                  </p>

                  <div className="mt-3 flex flex-wrap gap-2">
                    {[
                      ["Skills", match.skills_score],
                      ["Experience", match.experience_score],
                      ["Fit", match.embedding_score],
                      ["Location", match.location_score],
                    ].map(([label, val]) => (
                      <span key={label as string} className="badge-neutral font-mono text-[10px]">
                        {label} {val}%
                      </span>
                    ))}
                  </div>

                  {match.apply_url && (
                    <a
                      href={match.apply_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-block text-xs text-brand-400 hover:text-brand-300"
                    >
                      View posting ↗
                    </a>
                  )}
                </div>

                <div className="flex shrink-0 flex-wrap gap-2 lg:flex-col xl:flex-row">
                  <button
                    className="btn-secondary min-w-[120px]"
                    disabled={loading}
                    onClick={() => void handlePersonalize(match.job_id)}
                  >
                    Personalize
                  </button>
                  <button
                    className="btn-primary min-w-[120px]"
                    disabled={loading || appliedIds.has(match.job_id)}
                    onClick={() => void handleApply(match)}
                  >
                    {appliedIds.has(match.job_id) ? "Applied" : "Mark applied"}
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
