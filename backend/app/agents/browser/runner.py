"""Headed Playwright runner for auto-apply with saved login sessions."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from app.agents.browser.platform_handlers import ApplyOutcome, apply_for_platform, detect_platform

logger = logging.getLogger("app.browser.runner")

DEFAULT_SESSION_DIR = Path("storage/browser_sessions")


class AutoApplyRunner:
    """Runs job applications in a visible browser; pauses for CAPTCHA / login."""

    def __init__(
        self,
        *,
        session_dir: Path | None = None,
        headless: bool = False,
        slow_mo_ms: int = 100,
    ) -> None:
        self.session_dir = session_dir or DEFAULT_SESSION_DIR
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.slow_mo_ms = slow_mo_ms
        self._playwright = None
        self._browser: Browser | None = None

    def __enter__(self) -> "AutoApplyRunner":
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo_ms,
        )
        return self

    def __exit__(self, *args) -> None:
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def _session_file(self, platform: str) -> Path:
        return self.session_dir / f"{platform}_session.json"

    def save_session(self, context: BrowserContext, platform: str) -> None:
        path = self._session_file(platform)
        context.storage_state(path=path)
        logger.info("Saved %s session → %s", platform, path)

    def _new_context(self, platform: str | None) -> BrowserContext:
        assert self._browser is not None
        kwargs: dict = {"viewport": {"width": 1280, "height": 900}}
        if platform:
            session = self._session_file(platform)
            if session.exists():
                kwargs["storage_state"] = str(session)
        return self._browser.new_context(**kwargs)

    def login_once(self, platform: str, start_url: str) -> None:
        """Open browser so user can log in; saves cookies for future runs."""
        assert self._browser is not None
        context = self._browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.goto(start_url, wait_until="domcontentloaded")
        print(f"\nLog in to {platform} in the browser window.")
        input("Press ENTER here after you are fully logged in...")
        self.save_session(context, platform)
        context.close()

    def apply(self, url: str, profile: dict, resume_path: str) -> ApplyOutcome:
        assert self._browser is not None
        platform = detect_platform(url) or "generic"
        context = self._new_context(platform if platform != "generic" else None)
        page = context.new_page()
        try:
            outcome = apply_for_platform(page, url, profile, resume_path)
            if platform != "generic" and outcome.status in {"submitted", "review_required"}:
                self.save_session(context, platform)
            return outcome
        finally:
            context.close()

    def apply_many(
        self,
        jobs: list[dict],
        profile: dict,
        resume_path: str,
        *,
        delay_sec: float = 3.0,
    ) -> list[dict]:
        results: list[dict] = []
        for i, job in enumerate(jobs, start=1):
            url = job.get("apply_url") or job.get("url", "")
            title = job.get("title", "?")
            company = job.get("company", "?")
            if not url:
                results.append({"title": title, "company": company, "status": "skipped", "message": "No apply URL"})
                continue

            print(f"\n[{i}/{len(jobs)}] Applying: {title} @ {company}")
            print(f"  URL: {url}")

            try:
                outcome = self.apply(url, profile, resume_path)
                results.append(
                    {
                        "title": title,
                        "company": company,
                        "url": url,
                        "platform": outcome.platform,
                        "status": outcome.status,
                        "message": outcome.message,
                    }
                )
                print(f"  → {outcome.status}: {outcome.message}")
            except Exception as exc:
                logger.exception("Apply failed for %s", url)
                results.append(
                    {
                        "title": title,
                        "company": company,
                        "url": url,
                        "status": "failed",
                        "message": str(exc),
                    }
                )
                print(f"  → failed: {exc}")

            if i < len(jobs):
                import time

                time.sleep(delay_sec)

        return results

    @staticmethod
    def write_report(results: list[dict], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nReport saved: {path}")
