"""Generic form filling helpers for job application pages."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from playwright.sync_api import Locator, Page

logger = logging.getLogger("app.browser.forms")


def _first_name(full_name: str) -> str:
    parts = full_name.strip().split()
    return parts[0] if parts else ""


def _last_name(full_name: str) -> str:
    parts = full_name.strip().split()
    return " ".join(parts[1:]) if len(parts) > 1 else ""


def _try_fill(locator: Locator, value: str) -> bool:
    if not value:
        return False
    try:
        if locator.count() == 0:
            return False
        target = locator.first
        if not target.is_visible():
            return False
        target.fill(value)
        return True
    except Exception:
        return False


def fill_standard_fields(page: Page, profile: dict) -> int:
    """Fill common application fields. Returns count of fields filled."""
    filled = 0
    name = profile.get("name", "")
    email = profile.get("email", "")
    phone = profile.get("phone", "")
    location = profile.get("location", "")
    linkedin = profile.get("linkedin", "")
    github = profile.get("github", "") or profile.get("portfolio", "")

    pairs: list[tuple[str, str]] = [
        ("input[name*='email' i]", email),
        ("input[type='email']", email),
        ("input[name*='phone' i]", phone),
        ("input[type='tel']", phone),
        ("input[name*='first' i]", _first_name(name)),
        ("input[name*='last' i]", _last_name(name)),
        ("input[name*='name' i]", name),
        ("input[placeholder*='email' i]", email),
        ("input[placeholder*='phone' i]", phone),
        ("input[placeholder*='name' i]", name),
        ("input[name*='location' i]", location),
        ("input[name*='city' i]", location),
        ("input[name*='linkedin' i]", linkedin),
        ("input[name*='github' i]", github),
        ("textarea[name*='cover' i]", profile.get("summary", "")[:2000]),
    ]

    for selector, value in pairs:
        if _try_fill(page.locator(selector), value):
            filled += 1

    # Label-based fills (Playwright get_by_label)
    label_map = {
        r"email": email,
        r"phone|mobile": phone,
        r"first name": _first_name(name),
        r"last name": _last_name(name),
        r"full name|^name$": name,
        r"location|city": location,
        r"linkedin": linkedin,
    }
    for pattern, value in label_map.items():
        if not value:
            continue
        try:
            loc = page.get_by_label(re.compile(pattern, re.I))
            if _try_fill(loc, value):
                filled += 1
        except Exception:
            pass

    logger.info("Filled %d standard fields", filled)
    filled += fill_custom_questions(page, profile)
    return filled


def fill_custom_questions(page: Page, profile: dict) -> int:
    """Fill common screening questions (work auth, sponsorship, experience)."""
    filled = 0
    skills = profile.get("skills") or []
    experience = profile.get("experience") or []
    years = max(len(experience), 2)

    qa_pairs: list[tuple[str, str]] = [
        (r"authorized|legally authorized|eligible to work|work authorization", "Yes"),
        (r"require sponsorship|visa sponsorship|need sponsorship", "No"),
        (r"willing to relocate", "Yes"),
        (r"remote|work from home", "Yes"),
        (r"years?.{0,5}experience|how many years", str(years)),
        (r"expected salary|desired salary|salary expectation", profile.get("salary_expectation", "Negotiable")),
        (r"linkedin profile|linkedin url", profile.get("linkedin", "")),
        (r"github|portfolio|website", profile.get("github", "") or profile.get("portfolio", "")),
    ]

    for skill in skills[:8]:
        qa_pairs.append((rf"experience with {re.escape(skill)}|{re.escape(skill)}", "Yes"))

    for pattern, answer in qa_pairs:
        if not answer:
            continue
        try:
            loc = page.get_by_label(re.compile(pattern, re.I))
            if loc.count() > 0:
                tag = loc.first.evaluate("el => el.tagName.toLowerCase()")
                if tag == "select":
                    loc.first.select_option(label=re.compile(answer, re.I))
                    filled += 1
                elif _try_fill(loc, answer):
                    filled += 1
        except Exception:
            pass
        try:
            radio = page.get_by_role("radio", name=re.compile(answer, re.I))
            if radio.count() > 0 and radio.first.is_visible():
                radio.first.click()
                filled += 1
        except Exception:
            pass

    # Generic blank required text inputs in modals
    try:
        for inp in page.locator("input[required]:not([type='hidden']), textarea[required]").all()[:6]:
            if not inp.is_visible():
                continue
            if inp.input_value():
                continue
            placeholder = (inp.get_attribute("placeholder") or "").lower()
            name = (inp.get_attribute("name") or "").lower()
            hint = placeholder + " " + name
            if "year" in hint:
                inp.fill(str(years))
                filled += 1
            elif "city" in hint or "location" in hint:
                inp.fill(profile.get("location", ""))
                filled += 1
    except Exception:
        pass

    return filled


def fill_greenhouse_fields(page: Page, profile: dict) -> int:
    """Greenhouse uses predictable field names on boards.greenhouse.io."""
    filled = fill_standard_fields(page, profile)
    name = profile.get("name", "")
    email = profile.get("email", "")
    phone = profile.get("phone", "")
    linkedin = profile.get("linkedin", "")

    gh_pairs: list[tuple[str, str]] = [
        ("#first_name", _first_name(name)),
        ("#last_name", _last_name(name)),
        ("#email", email),
        ("#phone", phone),
        ("input[name='job_application[first_name]']", _first_name(name)),
        ("input[name='job_application[last_name]']", _last_name(name)),
        ("input[name='job_application[email]']", email),
        ("input[name='job_application[phone]']", phone),
        ("input[name*='linkedin' i]", linkedin),
        ("input[name*='website' i]", profile.get("github", "") or profile.get("portfolio", "")),
    ]
    for selector, value in gh_pairs:
        if _try_fill(page.locator(selector), value):
            filled += 1

    logger.info("Greenhouse: filled %d fields total", filled)
    return filled


def upload_resume(page: Page, resume_path: str | Path) -> bool:
    path = Path(resume_path)
    if not path.exists():
        logger.warning("Resume not found: %s", path)
        return False

    selectors = (
        "input[type='file']",
        "input[accept*='pdf' i]",
        "input[name*='resume' i]",
        "input[name*='cv' i]",
    )
    for selector in selectors:
        try:
            loc = page.locator(selector)
            if loc.count() == 0:
                continue
            loc.first.set_input_files(str(path.resolve()))
            logger.info("Uploaded resume via %s", selector)
            return True
        except Exception as exc:
            logger.debug("Upload failed for %s: %s", selector, exc)

    return False


def click_first_matching(page: Page, texts: list[str], *, timeout_ms: int = 5000) -> bool:
    for text in texts:
        try:
            btn = page.get_by_role("button", name=re.compile(text, re.I))
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click(timeout=timeout_ms)
                logger.info("Clicked button matching %r", text)
                return True
        except Exception:
            pass
        try:
            link = page.get_by_role("link", name=re.compile(text, re.I))
            if link.count() > 0 and link.first.is_visible():
                link.first.click(timeout=timeout_ms)
                logger.info("Clicked link matching %r", text)
                return True
        except Exception:
            pass
    return False


def click_apply_entrypoint(page: Page) -> bool:
    return click_first_matching(
        page,
        [
            r"apply for this job",
            r"^easy apply$",
            r"apply now",
            r"quick apply",
            r"1.?click apply",
            r"^apply$",
            r"continue to apply",
            r"start application",
        ],
    )
