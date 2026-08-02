"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getAutoApplyConfig,
  updateAutoApplyConfig,
  uploadAutoApplyResume,
  getBotAvailability,
  getBotStatus,
  startBot,
  stopBot,
  type AutoApplyConfig,
  type BotStatus,
} from "@/lib/api";

type Props = {
  candidateId: number | null;
  onApplicationsChanged?: () => void;
};

const PLATFORMS = ["linkedin", "indeed", "ziprecruiter", "glassdoor"];

export function AutoApplyPanel({ candidateId, onApplicationsChanged }: Props) {
  const [config, setConfig] = useState<AutoApplyConfig | null>(null);
  const [titlesInput, setTitlesInput] = useState("Software Developer, Frontend Developer");
  const [location, setLocation] = useState("Remote");
  const [platform, setPlatform] = useState("linkedin");
  const [botAvail, setBotAvail] = useState(false);
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async (id: number) => {
    try {
      const [data, avail, status] = await Promise.all([
        getAutoApplyConfig(id),
        getBotAvailability().catch(() => ({ available: false, message: "", platforms: [] })),
        getBotStatus(id).catch(() => null),
      ]);
      setConfig(data);
      setTitlesInput(data.job_titles.join(", "));
      setLocation(data.location || "Remote");
      setBotAvail(avail.available);
      if (status) setBotStatus(status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load auto-apply settings");
    }
  }, []);

  useEffect(() => {
    if (candidateId) void load(candidateId);
  }, [candidateId, load]);

  useEffect(() => {
    if (!candidateId || botStatus?.state !== "running") return;
    const timer = setInterval(() => {
      void getBotStatus(candidateId).then((s) => {
        setBotStatus(s);
        if (s.state === "idle" || s.state === "error") {
          onApplicationsChanged?.();
        }
      });
    }, 2000);
    return () => clearInterval(timer);
  }, [candidateId, botStatus?.state, onApplicationsChanged]);

  async function handleSaveTitles() {
    if (!candidateId) return;
    setLoading(true);
    setError("");
    try {
      const titles = titlesInput.split(",").map((t) => t.trim()).filter(Boolean);
      const updated = await updateAutoApplyConfig(candidateId, titles, location);
      setConfig(updated);
      setMessage("Job search preferences saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleResumeUpload(file: File) {
    if (!candidateId) return;
    setLoading(true);
    setError("");
    try {
      await uploadAutoApplyResume(candidateId, file);
      await load(candidateId);
      setMessage(`Auto-apply resume uploaded: ${file.name}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleStartBot() {
    if (!candidateId) return;
    setLoading(true);
    setError("");
    try {
      const status = await startBot(candidateId, { platform, continuous: true, batchSize: 5 });
      setBotStatus(status);
      setMessage(`Bot started on ${platform}. Watch the browser window.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start bot");
    } finally {
      setLoading(false);
    }
  }

  async function handleStopBot() {
    if (!candidateId) return;
    try {
      const status = await stopBot(candidateId);
      setBotStatus(status);
      setMessage("Stop requested — bot will finish the current job.");
      onApplicationsChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Stop failed");
    }
  }

  if (!candidateId) {
    return (
      <div className="card-light mt-8">
        <p className="section-tag">Auto-apply bot</p>
        <p className="mt-2 text-sm text-ink-500">Upload your main resume first to enable the apply bot.</p>
      </div>
    );
  }

  const running = botStatus?.state === "running" || botStatus?.state === "stopping";

  return (
    <div className="card-light mt-8 space-y-6">
      <div>
        <p className="section-tag">Auto-apply bot</p>
        <h3 className="mt-2 text-2xl font-semibold text-ink">Run bot from here</h3>
        <p className="mt-2 text-sm text-ink-500">
          Requires local backend with Playwright. Applies sync to your dashboard automatically.
        </p>
      </div>

      {message && <div className="alert-success">{message}</div>}
      {error && <div className="alert-error">{error}</div>}

      {!botAvail && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          Bot runner unavailable — start backend locally with Playwright installed.
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-3">
          <label className="text-sm font-medium text-ink">Bot resume (PDF)</label>
          <label className="upload-zone block cursor-pointer">
            <span className="font-medium text-ink">
              {config?.resume_uploaded ? `✓ ${config.resume_filename || "resume.pdf"}` : "Upload bot resume PDF"}
            </span>
            <input
              type="file"
              accept="application/pdf"
              className="hidden"
              disabled={loading || running}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void handleResumeUpload(f);
              }}
            />
          </label>
        </div>

        <div className="space-y-3">
          <label className="text-sm font-medium text-ink">Platform</label>
          <select
            className="input w-full"
            value={platform}
            disabled={running}
            onChange={(e) => setPlatform(e.target.value)}
          >
            {PLATFORMS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <input
            className="input w-full"
            value={titlesInput}
            disabled={running}
            onChange={(e) => setTitlesInput(e.target.value)}
            placeholder="Software Developer, Frontend Developer"
          />
          <input
            className="input w-full"
            value={location}
            disabled={running}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="Remote"
          />
          <button className="btn-outline w-full" disabled={loading || running} onClick={() => void handleSaveTitles()}>
            Save search preferences
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        {!running ? (
          <button className="btn-dark" disabled={loading || !botAvail} onClick={() => void handleStartBot()}>
            Start auto-apply
          </button>
        ) : (
          <button className="btn-dark" onClick={() => void handleStopBot()}>
            Stop bot
          </button>
        )}
        {botStatus && (
          <span className="self-center text-sm text-ink-500">
            {botStatus.state} · {botStatus.submitted ?? 0} submitted · {botStatus.skipped ?? 0} skipped
          </span>
        )}
      </div>

      {config?.sessions && (
        <div>
          <p className="mb-2 text-sm font-medium text-ink">Login status</p>
          <div className="flex flex-wrap gap-2">
            {config.sessions.map((s) => (
              <span
                key={s.platform}
                className={`source-pill ${s.logged_in ? "border-ink bg-ink text-white" : ""}`}
              >
                {s.platform} {s.logged_in ? "✓" : "— log in via script"}
              </span>
            ))}
          </div>
        </div>
      )}

      {botStatus?.recent_events && botStatus.recent_events.length > 0 && (
        <div className="max-h-48 overflow-y-auto rounded-2xl border border-ink-200 bg-ink-50 p-4 font-mono text-xs text-ink-600">
          {botStatus.recent_events.slice(-12).map((ev, i) => (
            <p key={`${ev.ts}-${i}`} className="py-0.5">
              [{ev.level}] {ev.message}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
