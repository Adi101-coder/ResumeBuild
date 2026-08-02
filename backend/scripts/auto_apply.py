#!/usr/bin/env python3
"""
ResumeBuild auto-apply bot (Playwright, headed browser).

Saves login sessions to the database (cookies only — never passwords).
Searches job boards for Software Developer / Frontend Developer roles and applies.

Examples
--------
# Log in once — session saved to DB when --candidate-id is set:
python scripts/auto_apply.py login --platform linkedin --candidate-id 18

# Search LinkedIn continuously until Ctrl+C:
python scripts/auto_apply.py linkedin-run --candidate-id 18

# Single pass (limited batch):
python scripts/auto_apply.py search-apply --candidate-id 18 --platform linkedin --limit 3

# All platforms:
python scripts/auto_apply.py search-apply --candidate-id 18 --all-platforms --limit 2

# Apply to matched jobs in DB:
python scripts/auto_apply.py run --candidate-id 18 --min-score 75 --limit 5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import httpx
from sqlalchemy.orm import Session

from app.agents.browser.runner import AutoApplyRunner
from app.config import settings
from app.database.models import Candidate, Job, JobMatch, Resume
from app.database.session import SessionLocal
from app.services.auto_apply_config import get_or_create_config, resolve_resume_path
from app.services.session_store import PLATFORMS, export_session_to_file

LOGIN_URLS = {
    "linkedin": "https://www.linkedin.com/login",
    "indeed": f"https://{settings.indeed_domain}",
    "ziprecruiter": "https://www.ziprecruiter.com/login",
    "glassdoor": "https://www.glassdoor.com/profile/login_input.htm",
}

SEARCH_PLATFORMS = ("linkedin", "indeed", "ziprecruiter", "glassdoor")


def _api_base() -> str:
    return os.getenv("API_URL", os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:8000")).rstrip("/")


def load_profile(db: Session, candidate_id: int) -> dict:
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise SystemExit(f"Candidate {candidate_id} not found.")
    return candidate.profile_json or {}


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
        raise SystemExit(f"No matched jobs ≥ {min_score}. Run Discover & match first.")

    return [
        {
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "apply_url": job.apply_url,
            "score": match.score,
        }
        for match, job in rows
        if job.apply_url
    ]


def load_jobs_from_api(candidate_id: int, *, min_score: float, limit: int) -> list[dict]:
    with httpx.Client(timeout=120.0) as client:
        res = client.post(f"{_api_base()}/api/matching/{candidate_id}")
        res.raise_for_status()
        matches = res.json()
    filtered = [m for m in matches if float(m.get("score", 0)) >= min_score]
    filtered.sort(key=lambda m: float(m.get("score", 0)), reverse=True)
    return [
        {
            "job_id": m.get("job_id"),
            "title": m.get("title"),
            "company": m.get("company"),
            "apply_url": m.get("apply_url"),
            "score": m.get("score"),
        }
        for m in filtered[:limit]
        if m.get("apply_url")
    ]


def parse_urls(raw: str | None) -> list[dict]:
    if not raw:
        return []
    return [{"title": "Manual", "company": "", "apply_url": u.strip()} for u in raw.split(",") if u.strip()]


def _sync_sessions_to_disk(db: Session, candidate_id: int, session_dir: Path) -> None:
    for platform in PLATFORMS:
        export_session_to_file(db, candidate_id, platform, session_dir / f"{platform}_session.json")


def cmd_login(args: argparse.Namespace) -> None:
    platform = args.platform.lower()
    if platform not in LOGIN_URLS:
        raise SystemExit(f"Choose platform: {', '.join(LOGIN_URLS)}")

    session_dir = Path(args.session_dir)
    db = SessionLocal() if args.candidate_id else None
    try:
        with AutoApplyRunner(
            session_dir=session_dir,
            headless=False,
            candidate_id=args.candidate_id,
            db=db,
        ) as runner:
            runner.login_once(platform, LOGIN_URLS[platform])
    finally:
        if db:
            db.close()

    if args.candidate_id:
        print(f"Session saved to database for candidate {args.candidate_id} / {platform}")
    print(f"File backup: {session_dir / f'{platform}_session.json'}")


def cmd_linkedin_run(args: argparse.Namespace) -> None:
    if not args.candidate_id:
        raise SystemExit("--candidate-id is required")

    db = SessionLocal()
    try:
        profile = load_profile(db, args.candidate_id)
        resume_path = resolve_resume_path(db, args.candidate_id)
        config = get_or_create_config(db, args.candidate_id)
        job_titles = config.job_titles or ["Software Developer", "Frontend Developer"]
        location = config.location or profile.get("location") or "Remote"
        session_dir = Path(args.session_dir)
        _sync_sessions_to_disk(db, args.candidate_id, session_dir)

        print(f"\nLinkedIn continuous auto-apply")
        print(f"  Candidate: {profile.get('name')} (id={args.candidate_id})")
        print(f"  Resume: {resume_path}")
        print(f"  Titles: {', '.join(job_titles)}")
        print(f"  Location: {location}")
        print(f"  Batch size: {args.batch_size} jobs per title per round")
        print(f"\nPress Ctrl+C to stop.\n")

        report_path = Path(args.report) if args.report else session_dir / "linkedin_apply_report.json"
        with AutoApplyRunner(
            session_dir=session_dir,
            headless=args.headless,
            slow_mo_ms=args.slow_mo,
            candidate_id=args.candidate_id,
            db=db,
        ) as runner:
            runner.linkedin_run_until_stop(
                profile,
                resume_path,
                job_titles,
                location,
                batch_size=args.batch_size,
                delay_sec=args.delay,
                max_rounds=None,
                report_path=report_path,
                debug=args.debug,
            )
    finally:
        db.close()


def cmd_search_apply(args: argparse.Namespace) -> None:
    if not args.candidate_id:
        raise SystemExit("--candidate-id is required for search-apply")

    db = SessionLocal()
    try:
        profile = load_profile(db, args.candidate_id)
        resume_path = resolve_resume_path(db, args.candidate_id)
        config = get_or_create_config(db, args.candidate_id)
        job_titles = config.job_titles or ["Software Developer", "Frontend Developer"]
        location = config.location or profile.get("location") or "Remote"

        platforms = list(SEARCH_PLATFORMS) if args.all_platforms else [args.platform.lower()]
        session_dir = Path(args.session_dir)
        _sync_sessions_to_disk(db, args.candidate_id, session_dir)

        print(f"\nAuto-apply bot")
        print(f"  Candidate: {profile.get('name')} (id={args.candidate_id})")
        print(f"  Resume: {resume_path}")
        print(f"  Search titles: {', '.join(job_titles)}")
        print(f"  Location: {location}")
        print(f"  Platforms: {', '.join(platforms)}")
        print("\nBrowser will open. Solve CAPTCHAs when prompted.\n")

        all_results: list[dict] = []
        with AutoApplyRunner(
            session_dir=session_dir,
            headless=args.headless,
            slow_mo_ms=args.slow_mo,
            candidate_id=args.candidate_id,
            db=db,
        ) as runner:
            for platform in platforms:
                if platform not in SEARCH_PLATFORMS:
                    print(f"Skipping unknown platform: {platform}")
                    continue
                results = runner.search_and_apply(
                    platform,
                    profile,
                    resume_path,
                    job_titles,
                    location,
                    limit_per_title=args.limit,
                    delay_sec=args.delay,
                )
                all_results.extend(results)

        report_path = Path(args.report) if args.report else session_dir / "search_apply_report.json"
        AutoApplyRunner.write_report(all_results, report_path)

        ok = sum(1 for r in all_results if r.get("status") == "submitted")
        review = sum(1 for r in all_results if r.get("status") == "review_required")
        print(f"\nDone: {ok} submitted, {review} need review, {len(all_results) - ok - review} other")
    finally:
        db.close()


def cmd_run(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        if args.profile_json:
            profile = json.loads(Path(args.profile_json).read_text(encoding="utf-8"))
            resume_path = args.resume or ""
            jobs = parse_urls(args.urls)
        elif args.candidate_id:
            profile = load_profile(db, args.candidate_id)
            resume_path = args.resume or resolve_resume_path(db, args.candidate_id)
            if args.urls:
                jobs = parse_urls(args.urls)
            elif args.from_api:
                jobs = load_jobs_from_api(args.candidate_id, min_score=args.min_score, limit=args.limit)
            else:
                jobs = load_jobs_from_db(db, args.candidate_id, min_score=args.min_score, limit=args.limit)
            _sync_sessions_to_disk(db, args.candidate_id, Path(args.session_dir))
        else:
            raise SystemExit("Provide --candidate-id or --profile-json")

        if not jobs:
            raise SystemExit("No jobs to apply to.")

        print(f"\nApplying to {len(jobs)} job(s) · resume: {resume_path}")
        session_dir = Path(args.session_dir)
        with AutoApplyRunner(
            session_dir=session_dir,
            headless=args.headless,
            candidate_id=args.candidate_id,
            db=db if args.candidate_id else None,
        ) as runner:
            results = runner.apply_many(jobs, profile, resume_path, delay_sec=args.delay)
            runner.write_report(results, session_dir / "last_apply_report.json")
    finally:
        db.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ResumeBuild auto-apply bot")
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="Log in once — saves session cookies to DB")
    login.add_argument("--platform", required=True, choices=list(LOGIN_URLS.keys()))
    login.add_argument("--candidate-id", type=int, help="Save session to database")
    login.add_argument("--session-dir", default="storage/browser_sessions")
    login.set_defaults(func=cmd_login)

    search = sub.add_parser("search-apply", help="Search job boards and auto-apply")
    search.add_argument("--candidate-id", type=int, required=True)
    search.add_argument("--platform", default="linkedin", choices=list(SEARCH_PLATFORMS))
    search.add_argument("--all-platforms", action="store_true")
    search.add_argument("--limit", type=int, default=3, help="Jobs per title per platform")
    search.add_argument("--session-dir", default="storage/browser_sessions")
    search.add_argument("--report", help="JSON report path")
    search.add_argument("--headless", action="store_true")
    search.add_argument("--slow-mo", type=int, default=100)
    search.add_argument("--delay", type=float, default=5.0)
    search.set_defaults(func=cmd_search_apply)

    linkedin = sub.add_parser("linkedin-run", help="LinkedIn Easy Apply until Ctrl+C")
    linkedin.add_argument("--candidate-id", type=int, required=True)
    linkedin.add_argument("--batch-size", type=int, default=5, help="Easy Apply attempts per title per round")
    linkedin.add_argument("--session-dir", default="storage/browser_sessions")
    linkedin.add_argument("--report", help="JSON report path")
    linkedin.add_argument("--headless", action="store_true")
    linkedin.add_argument("--slow-mo", type=int, default=100)
    linkedin.add_argument("--delay", type=float, default=5.0)
    linkedin.add_argument("--debug", action="store_true", help="Print visible button labels when Easy Apply fails")
    linkedin.set_defaults(func=cmd_linkedin_run)

    run = sub.add_parser("run", help="Apply to URLs or DB matched jobs")
    run.add_argument("--candidate-id", type=int)
    run.add_argument("--from-api", action="store_true")
    run.add_argument("--urls", help="Comma-separated URLs")
    run.add_argument("--profile-json", help="Offline profile JSON")
    run.add_argument("--resume", help="Override resume PDF path")
    run.add_argument("--min-score", type=float, default=75.0)
    run.add_argument("--limit", type=int, default=5)
    run.add_argument("--session-dir", default="storage/browser_sessions")
    run.add_argument("--headless", action="store_true")
    run.add_argument("--slow-mo", type=int, default=100)
    run.add_argument("--delay", type=float, default=4.0)
    run.set_defaults(func=cmd_run)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
