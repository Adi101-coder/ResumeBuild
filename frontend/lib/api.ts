const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type CandidateProfile = {
  name: string;
  email: string;
  phone?: string;
  location?: string;
  notice_period?: string;
  preferred_roles?: string[];
  skills: string[];
  experience: Array<{ company: string; role: string; bullets: string[]; location?: string }>;
  projects: Array<{ name: string; description: string; technologies: string[] }>;
  education: Array<{ institution: string; degree: string; field?: string; cgpa?: string }>;
  certifications?: string[];
  linkedin: string;
  github: string;
  summary?: string;
};

export type MatchResult = {
  job_id: number;
  title: string;
  company: string;
  location: string;
  apply_url: string;
  score: number;
  skills_score: number;
  experience_score: number;
  embedding_score: number;
  location_score: number;
  passed_threshold: boolean;
};

export type Application = {
  id: number;
  candidate_id: number;
  job_id: number;
  status: string;
  applied_at: string | null;
  ats_score: number | null;
  notes: string;
  job_title: string;
  job_company: string;
  job_location: string;
  apply_url: string;
  match_score: number | null;
};

export type DiscoveryResult = {
  candidate_id: number;
  search_queries: string[];
  scraped: number;
  created: number;
  skipped_duplicates: number;
  total_jobs_in_db: number;
  sources?: Record<string, { fetched: number; errors: number }>;
};

export type JobSource = {
  key: string;
  name: string;
  auth: string;
  status: string;
  enabled: boolean;
};

export function logClick(
  action: string,
  detail = "",
  meta: Record<string, string | number | boolean> = {},
  page = typeof window !== "undefined" ? window.location.pathname : "",
) {
  void fetch(`${API_URL}/api/events/client`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, page, detail, meta }),
  }).catch(() => {});
}

export async function uploadResume(file: File) {
  logClick("upload_resume", file.name, { size: file.size });
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/api/resumes/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{
    candidate_id: number;
    resume_id: number;
    profile: CandidateProfile;
  }>;
}

export async function getJobSources() {
  const res = await fetch(`${API_URL}/api/jobs/sources`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ sources: JobSource[] }>;
}

export async function discoverJobs(candidateId: number) {
  logClick("discover_jobs", "profile-based discovery", { candidateId });
  await fetch(`${API_URL}/api/jobs/seed`, { method: "POST" });
  const res = await fetch(`${API_URL}/api/jobs/discover/${candidateId}`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<DiscoveryResult>;
}

export async function matchJobs(candidateId: number) {
  logClick("run_matching", "score all jobs", { candidateId });
  const res = await fetch(`${API_URL}/api/matching/${candidateId}`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<MatchResult[]>;
}

export async function personalizeResume(candidateId: number, jobId: number) {
  logClick("personalize_resume", `job ${jobId}`, { candidateId, jobId });
  const res = await fetch(`${API_URL}/api/matching/${candidateId}/personalize/${jobId}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function createApplication(
  candidateId: number,
  jobId: number,
  atsScore?: number,
) {
  logClick("apply_to_job", `job ${jobId}`, { candidateId, jobId });
  const res = await fetch(`${API_URL}/api/applications`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      candidate_id: candidateId,
      job_id: jobId,
      status: "applied",
      ats_score: atsScore ?? null,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Application>;
}

export async function getApplications(candidateId: number) {
  const res = await fetch(`${API_URL}/api/applications/candidate/${candidateId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Application[]>;
}

export async function updateApplicationStatus(applicationId: number, status: string) {
  logClick("update_application_status", status, { applicationId });
  const res = await fetch(`${API_URL}/api/applications/${applicationId}/status?status=${status}`, {
    method: "PATCH",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Application>;
}

export async function getAnalytics(candidateId: number) {
  const res = await fetch(`${API_URL}/api/applications/analytics/${candidateId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
