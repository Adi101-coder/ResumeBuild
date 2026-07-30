#!/usr/bin/env python3
"""
ResumeBuild auto-apply script (Playwright, headed browser).

Fills application forms on Indeed, ZipRecruiter, LinkedIn, Glassdoor, and Greenhouse.
Pauses for you when CAPTCHA / login / custom questions appear.

Examples
--------
# Log in once (saves cookies for later runs):
python scripts/auto_apply.py login --platform linkedin

# Apply to specific job URLs:
python scripts/auto_apply.py run --candidate-id 18 \\
  --urls "https://www.linkedin.com/jobs/view/123,https://www.indeed.com/viewjob?jk=abc"

# Apply to top matched jobs from your ResumeBuild API:
python scripts/auto_apply.py run --candidate-id 18 --from-api --min-score 75 --limit 5

# Local profile + resume (no API):
python scripts/auto_apply.py run \\
  --profile-json storage/profile.json \\
  --resume path/to/resume.pdf \\
  --urls "https://boards.greenhouse.io/stripe/jobs/123"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Allow running as: python scripts/auto_apply.py from backend/
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import httpx
from sqlalchemy.orm import Session

from app.agents.browser.runner import AutoApplyRunner
from app.config import settings
from app.database.models import Candidate, Job, JobMatch, Resume
from app.database.session import SessionLocal

LOGIN_URLS = {
    "linkedin": "https://www.linkedin.com/login",
    "indeed": f"https://{settings.indeed_domain}",
    "ziprecruiter": "https://www.ziprecruiter.com/login",
    "glassdoor": "https://www.glassdoor.com/profile/login_input.htm",
}


def _api_base() -> str:
    return os.getenv("API_URL", os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:8000")).rstrip("/")


def load_profile_from_db(db: Session, candidate_id: int) -> tuple[dict, str]:
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise SystemExit(f"Candidate {candidate_id} not found in database.")

    profile = candidate.profile_json or {}
    resume = (
        db.query(Resume)
        .filter(Resume.candidate_id == candidate_id)
        .order_by(Resume.created_at.desc())
        .first()
    )
    if not resume or not Path(resume.file_path).exists():
        raise SystemExit(
            f"No resume PDF on disk for candidate {candidate_id}. "
            f"Upload a resume via the web app first."
        )
    return profile, resume.file_path


def load_jobs_from_db(db: Session, candidate_id: int, *, min_score: float, limit: int) -> list[dict]:
    rows = (
        db.query(JobMatch, Job)
        .join(Job, JobMatch.job_id == Job.id)
        .filter(JobMatch.candidate_id == candidate_id, JobMatch.score >= min_score)
        .order_by(JobMatch.score.desc())
        .limit(limit)
        .all()
    )
    if not rows:
        raise SystemExit(f"No matched jobs ≥ {min_score} for candidate {candidate_id}. Run matching first.")

    jobs = []
    for match, job in rows:
        if not job.apply_url:
            continue
        jobs.append(
            {
                "job_id": job.id,
                "title": job.title,
                "company": job.company,
                "apply_url": job.apply_url,
                "score": match.score,
                "source": job.source,
            }
        )
    return jobs


def load_jobs_from_api(candidate_id: int, *, min_score: float, limit: int) -> list[dict]:
    base = _api_base()
    with httpx.Client(timeout=120.0) as client:
        res = client.post(f"{base}/api/matching/{candidate_id}")
        res.raise_for_status()
        matches = res.json()

    filtered = [m for m in matches if float(m.get("score", 0)) >= min_score]
    filtered.sort(key=lambda m: float(m.get("score", 0)), reverse=True)
    jobs = []
    for m in filtered[:limit]:
        if not m.get("apply_url"):
            continue
        jobs.append(
            {
                "job_id": m.get("job_id"),
                "title": m.get("title"),
                "company": m.get("company"),
                "apply_url": m.get("apply_url"),
                "score": m.get("score"),
            }
        )
    return jobs


def parse_urls(raw: str | None) -> list[dict]:
    if not raw:
        return []
    jobs = []
    for url in raw.split(","):
        url = url.strip()
        if url:
            jobs.append({"title": "Manual URL", "company": "", "apply_url": url})
    return jobs


def cmd_login(args: argparse.Namespace) -> None:
    platform = args.platform.lower()
    if platform not in LOGIN_URLS:
        raise SystemExit(f"Unknown platform. Choose: {', '.join(LOGIN_URLS)}")

    session_dir = Path(args.session_dir)
    with AutoApplyRunner(session_dir=session_dir, headless=False) as runner:
        runner.login_once(platform, LOGIN_URLS[platform])
    print(f"Session saved. Future runs will reuse {session_dir / f'{platform}_session.json'}")


def cmd_run(args: argparse.Namespace) -> None:
    jobs: list[dict] = []

    if args.profile_json:
        profile = json.loads(Path(args.profile_json).read_text(encoding="utf-8"))
        if not args.resume:
            raise SystemExit("--resume is required with --profile-json")
        resume_path = args.resume
        jobs = parse_urls(args.urls)
    elif args.candidate_id:
        db = SessionLocal()
        try:
            profile, resume_path = load_profile_from_db(db, args.candidate_id)
            if args.urls:
                jobs = parse_urls(args.urls)
            elif args.from_api:
                jobs = load_jobs_from_api(args.candidate_id, min_score=args.min_score, limit=args.limit)
            else:
                jobs = load_jobs_from_db(db, args.candidate_id, min_score=args.min_score, limit=args.limit)
        finally:
            db.close()
    else:
        raise SystemExit("Provide --candidate-id or --profile-json")

    if args.resume:
        resume_path = args.resume

    if not jobs:
        raise SystemExit("No jobs to apply to. Pass --urls or run matching first.")

    print(f"\nAuto-apply: {len(jobs)} job(s)")
    print(f"Resume: {resume_path}")
    print(f"Candidate: {profile.get('name', 'Unknown')} · {profile.get('email', '')}")
    print("\nA browser window will open. Solve CAPTCHAs when prompted in this terminal.\n")

    session_dir = Path(args.session_dir)
    report_path = Path(args.report) if args.report else session_dir / "last_apply_report.json"

    with AutoApplyRunner(session_dir=session_dir, headless=args.headless, slow_mo_ms=args.slow_mo) as runner:
        results = runner.apply_many(jobs, profile, resume_path, delay_sec=args.delay)
        runner.write_report(results, report_path)

    submitted = sum(1 for r in results if r.get("status") == "submitted")
    review = sum(1 for r in results if r.get("status") == "review_required")
    failed = sum(1 for r in results if r.get("status") in {"failed", "unsupported"})
    print(f"\nDone: {submitted} submitted, {review} need review, {failed} failed/unsupported")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ResumeBuild Playwright auto-apply")
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="Log in once and save session cookies")
    login.add_argument("--platform", required=True, choices=list(LOGIN_URLS.keys()))
    login.add_argument("--session-dir", default="storage/browser_sessions")
    login.set_defaults(func=cmd_login)

    run = sub.add_parser("run", help="Auto-apply to job URLs or matched jobs")
    run.add_argument("--candidate-id", type=int, help="Candidate ID from ResumeBuild DB")
    run.add_argument("--from-api", action="store_true", help="Fetch matches from running API")
    run.add_argument("--urls", help="Comma-separated apply URLs")
    run.add_argument("--profile-json", help="Path to profile JSON (offline mode)")
    run.add_argument("--resume", help="Path to PDF resume")
    run.add_argument("--min-score", type=float, default=75.0, help="Minimum match score")
    run.add_argument("--limit", type=int, default=5, help="Max jobs per run")
    run.add_argument("--session-dir", default="storage/browser_sessions")
    run.add_argument("--report", help="Where to write JSON results")
    run.add_argument("--headless", action="store_true", help="Headless (not recommended — CAPTCHA)")
    run.add_argument("--slow-mo", type=int, default=100, help="Playwright slow_mo ms")
    run.add_argument("--delay", type=float, default=4.0, help="Seconds between jobs")
    run.set_defaults(func=cmd_run)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
