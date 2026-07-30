"""Detect CAPTCHA / bot checks and pause for human intervention."""

from __future__ import annotations

import logging
import time

from playwright.sync_api import Page

logger = logging.getLogger("app.browser.captcha")

CAPTCHA_IFRAME_SELECTORS = (
    'iframe[src*="recaptcha"]',
    'iframe[src*="hcaptcha"]',
    'iframe[title*="captcha" i]',
    'iframe[title*="challenge" i]',
)

CAPTCHA_TEXT_HINTS = (
    "captcha",
    "verify you are human",
    "verify you're human",
    "security check",
    "unusual traffic",
    "robot",
    "challenge",
)


def captcha_present(page: Page) -> bool:
    for selector in CAPTCHA_IFRAME_SELECTORS:
        try:
            if page.locator(selector).count() > 0:
                return True
        except Exception:
            continue

    try:
        body = (page.inner_text("body") or "").lower()
        if any(hint in body for hint in CAPTCHA_TEXT_HINTS):
            # Avoid false positives on job descriptions mentioning "robotics"
            if "recaptcha" in body or "captcha" in body or "unusual traffic" in body:
                return True
    except Exception:
        pass
    return False


def wait_for_human(page: Page, reason: str, *, timeout_sec: int = 600) -> None:
    """Pause automation until user presses Enter in the terminal (after solving CAPTCHA)."""
    print("\n" + "=" * 60)
    print("HUMAN ACTION REQUIRED")
    print(reason)
    print("Complete the step in the browser window, then press ENTER here to continue.")
    print("Press Ctrl+C to abort this application.")
    print("=" * 60)

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if not captcha_present(page):
            # Give user a moment — they may still be filling extra fields
            try:
                input("\nPress ENTER when ready to continue (or after solving CAPTCHA)... ")
            except EOFError:
                time.sleep(5)
            return
        time.sleep(2)

    raise TimeoutError(f"Timed out waiting for human action: {reason}")
