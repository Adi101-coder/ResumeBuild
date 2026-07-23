"use client";

import Link from "next/link";
import { ScoreRing } from "@/components/ScoreRing";
import { StatCard } from "@/components/StatCard";
import {
  logClick,
  type CandidateProfile,
  type DiscoveryResult,
  type MatchResult,
} from "@/lib/api";

const PIPELINE = [
  { id: "upload", label: "Parse resume" },
  { id: "discover", label: "Discover jobs" },
  { id: "match", label: "Score matches" },
  { id: "apply", label: "Track applications" },
];

type Props = {
  loading: boolean;
  candidateId: number | null;
  profile: CandidateProfile | null;
  discovery: DiscoveryResult | null;
  matches: MatchResult[];
  appliedIds: Set<number>;
  pipelineStep: number;
  message: string;
  error: string;
  onUpload: (file: File) => void;
  onDiscoverAndMatch: () => void;
  onPersonalize: (jobId: number) => void;
  onApply: (match: MatchResult) => void;
};

export function WorkflowPanel({
  loading,
  candidateId,
  profile,
  discovery,
  matches,
  appliedIds,
  pipelineStep,
  message,
  error,
  onUpload,
  onDiscoverAndMatch,
  onPersonalize,
  onApply,
}: Props) {
  const passedCount = matches.filter((m) => m.passed_threshold).length;
  const initials = profile?.name
    ? profile.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : "?";

  async function handlePersonalize(jobId: number) {
    if (!candidateId) return;
    onPersonalize(jobId);
  }

  async function handleApply(match: MatchResult) {
    if (!candidateId) return;
    onApply(match);
  }

  return (
    <section id="workspace" className="scroll-mt-24 bg-ink-50 py-24">
      <div className="mx-auto max-w-7xl px-6 lg:px-10">
        <div className="mx-auto max-w-2xl text-center">
          <p className="section-tag">Start now</p>
          <h2 className="mt-4 display-heading">
            Upload once.{" "}
            <span className="font-serif italic font-normal">Match everywhere.</span>
          </h2>
          <p className="mt-4 text-lg text-ink-500">
            Drop your PDF, discover jobs from your profile, and review scored matches in minutes.
          </p>
        </div>

        <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
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

        {message && <div className="alert-success mt-6">{message}</div>}
        {error && <div className="alert-error mt-6">{error}</div>}

        <div className="mt-10 grid gap-8 lg:grid-cols-2">
          <div className="card-light space-y-5">
            <div>
              <p className="section-tag">Step 1</p>
              <h3 className="mt-2 text-2xl font-semibold text-ink">Upload your resume</h3>
              <p className="mt-2 text-sm text-ink-500">
                PDF only. Works across engineering, finance, design, and more.
              </p>
            </div>

            <label className="upload-zone">
              <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl border border-ink-200 bg-white text-xs font-bold uppercase tracking-widest text-ink">
                PDF
              </span>
              <span className="font-medium text-ink">
                {loading ? "Processing…" : "Drop PDF or click to browse"}
              </span>
              <span className="mt-1 text-xs text-ink-400">Recommended · up to 2 pages</span>
              <input
                type="file"
                accept="application/pdf"
                className="hidden"
                disabled={loading}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onUpload(file);
                }}
              />
            </label>

            {profile && (
              <div className="rounded-3xl border border-ink-200 bg-ink-50 p-5">
                <div className="flex gap-4">
                  <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-ink text-lg font-bold text-white">
                    {initials}
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-lg font-semibold text-ink">
                      {profile.name || "Candidate"}
                    </p>
                    <p className="truncate text-sm text-ink-500">
                      {profile.email || "No email detected"}
                    </p>
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {profile.skills.slice(0, 10).map((skill) => (
                    <span key={skill} className="badge-neutral">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="card-light flex flex-col space-y-5">
            <div>
              <p className="section-tag">Step 2</p>
              <h3 className="mt-2 text-2xl font-semibold text-ink">Discover & match</h3>
              <p className="mt-2 text-sm text-ink-500">
                Profile-driven search across Greenhouse, RemoteOK, YC, and more.
              </p>
            </div>

            {discovery && (
              <div className="rounded-3xl border border-ink-200 bg-ink-50 p-4 text-sm text-ink-600">
                <p className="font-semibold text-ink">
                  +{discovery.created} new jobs · {discovery.total_jobs_in_db} in pool
                </p>
                <p className="mt-2 text-xs text-ink-500">
                  {discovery.search_queries.slice(0, 5).join(" · ")}
                </p>
              </div>
            )}

            <button
              className="btn-dark w-full"
              disabled={!candidateId || loading}
              onClick={() => {
                logClick("click_discover_and_match");
                onDiscoverAndMatch();
              }}
            >
              {loading ? "Discovering…" : "Discover & match jobs"}
            </button>

            {!candidateId && (
              <p className="text-center text-xs text-ink-400">Upload a resume first</p>
            )}

            {matches.length > 0 && (
              <div className="mt-auto grid grid-cols-3 gap-3">
                <StatCard label="Matches" value={matches.length} />
                <StatCard label="≥ 75%" value={passedCount} />
                <StatCard label="Applied" value={appliedIds.size} />
              </div>
            )}
          </div>
        </div>

        {matches.length > 0 && (
          <div className="mt-16 space-y-6">
            <div className="flex items-end justify-between gap-4">
              <div>
                <p className="section-tag">Results</p>
                <h3 className="mt-2 text-3xl font-bold text-ink">Top job matches</h3>
              </div>
              <Link href="/dashboard" className="btn-ghost text-sm">
                Track all →
              </Link>
            </div>

            <div className="space-y-4">
              {matches.map((match) => (
                <article
                  key={match.job_id}
                  className="flex flex-col gap-4 rounded-3xl border border-ink-200 bg-white p-5 shadow-card lg:flex-row lg:items-center"
                >
                  <ScoreRing score={match.score} passed={match.passed_threshold} />

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="font-semibold text-ink">{match.title}</h4>
                      {appliedIds.has(match.job_id) && (
                        <span className="badge-pass">Applied</span>
                      )}
                      {!match.passed_threshold && (
                        <span className="badge-fail">Below threshold</span>
                      )}
                    </div>
                    <p className="mt-1 text-sm text-ink-500">
                      {match.company}
                      {match.location && ` · ${match.location}`}
                    </p>
                    {match.apply_url && (
                      <a
                        href={match.apply_url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-2 inline-block text-xs font-medium text-ink underline-offset-2 hover:underline"
                      >
                        View posting ↗
                      </a>
                    )}
                  </div>

                  <div className="flex shrink-0 flex-wrap gap-2">
                    <button
                      className="btn-outline min-w-[120px]"
                      disabled={loading}
                      onClick={() => void handlePersonalize(match.job_id)}
                    >
                      Personalize
                    </button>
                    <button
                      className="btn-dark min-w-[120px]"
                      disabled={loading || appliedIds.has(match.job_id)}
                      onClick={() => void handleApply(match)}
                    >
                      {appliedIds.has(match.job_id) ? "Applied" : "Mark applied"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
