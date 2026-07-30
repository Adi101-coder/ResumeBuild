"""Job board scrapers — Indeed, ZipRecruiter, LinkedIn, Glassdoor only."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from html import unescape
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from app.agents.scraper.base import BaseJobScraper, _matches_query
from app.config import settings

logger = logging.getLogger("app.scraper")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _job(
    *,
    title: str,
    company: str,
    location: str = "",
    description: str = "",
    apply_url: str = "",
    skills: list | None = None,
    source: str,
    application_type: str = "external",
    remote_type: str = "",
    salary: str = "",
    easy_apply: bool = False,
) -> dict:
    return {
        "title": title,
        "company": company,
        "location": location or "Remote",
        "salary": salary,
        "experience_required": "",
        "skills": skills or [],
        "description": description,
        "apply_url": apply_url,
        "application_type": application_type,
        "easy_apply": easy_apply,
        "remote_type": remote_type,
        "visa_required": False,
        "source": source,
    }


def _split_title_company(raw_title: str) -> tuple[str, str]:
    """Parse 'Role - Company' titles from RSS/listings."""
    title = unescape(raw_title.strip())
    if " - " in title:
        role, company = title.rsplit(" - ", 1)
        return role.strip(), company.strip()
    return title, ""


async def _get_text(client: httpx.AsyncClient, url: str, *, headers: dict | None = None) -> str:
    merged = {**DEFAULT_HEADERS, **(headers or {})}
    response = await client.get(url, headers=merged, follow_redirects=True)
    response.raise_for_status()
    return response.text


class IndeedScraper(BaseJobScraper):
    """Indeed job discovery via public RSS feeds."""

    source_name = "indeed"

    async def fetch_jobs(self, query: str = "", location: str = "", limit: int = 50) -> list[dict]:
        q = quote_plus(query or "software engineer")
        loc = quote_plus(location or "remote")
        domain = settings.indeed_domain.strip() or "www.indeed.com"
        url = f"https://{domain}/rss?q={q}&l={loc}"
        logger.info("Indeed RSS fetch: query=%r location=%r", query or "(default)", location or "(default)")

        jobs: list[dict] = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                text = await _get_text(client, url)
            root = ET.fromstring(text)
            channel = root.find("channel")
            if channel is None:
                return jobs
            for item in channel.findall("item")[: limit * 2]:
                raw_title = item.findtext("title", "")
                link = item.findtext("link", "")
                description = item.findtext("description", "") or ""
                company = item.findtext("source", "") or ""
                title, parsed_company = _split_title_company(raw_title)
                if not company:
                    company = parsed_company or "Indeed Employer"
                if query and not _matches_query(f"{title} {company} {description}", query):
                    continue
                jobs.append(
                    _job(
                        title=title,
                        company=company,
                        location=location or "Remote",
                        description=description[:2000],
                        apply_url=link,
                        source=self.source_name,
                        application_type="indeed",
                    )
                )
                if len(jobs) >= limit:
                    break
        except Exception as exc:
            logger.warning("Indeed fetch failed: %s", exc)

        logger.info("Indeed kept %d jobs", len(jobs))
        return jobs


class ZipRecruiterScraper(BaseJobScraper):
    """ZipRecruiter search results."""

    source_name = "ziprecruiter"

    async def fetch_jobs(self, query: str = "", location: str = "", limit: int = 50) -> list[dict]:
        q = quote_plus(query or "software engineer")
        loc = quote_plus(location or "remote")
        url = f"https://www.ziprecruiter.com/jobs-search?search={q}&location={loc}"
        logger.info("ZipRecruiter fetch: query=%r location=%r", query or "(default)", location or "(default)")

        jobs: list[dict] = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                html = await _get_text(client, url)
            soup = BeautifulSoup(html, "lxml")
            for article in soup.select("article.job_result, div.job_content")[: limit * 2]:
                title_el = article.select_one("h2, a.job_title")
                company_el = article.select_one("a.company_name, span.company_name")
                loc_el = article.select_one("a.job_location, span.job_location")
                link_el = article.select_one("a[href*='/Job/'], a.job_link")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True) if company_el else "ZipRecruiter Employer"
                loc_text = loc_el.get_text(strip=True) if loc_el else (location or "Remote")
                href = link_el.get("href", "") if link_el else ""
                apply_url = href if href.startswith("http") else f"https://www.ziprecruiter.com{href}"
                if query and not _matches_query(f"{title} {company}", query):
                    continue
                jobs.append(
                    _job(
                        title=title,
                        company=company,
                        location=loc_text,
                        apply_url=apply_url,
                        source=self.source_name,
                        application_type="ziprecruiter",
                    )
                )
                if len(jobs) >= limit:
                    break
        except Exception as exc:
            logger.warning("ZipRecruiter fetch failed: %s", exc)

        logger.info("ZipRecruiter kept %d jobs", len(jobs))
        return jobs


class LinkedInScraper(BaseJobScraper):
    """LinkedIn Jobs via guest search API (optional session cookie for reliability)."""

    source_name = "linkedin"

    async def fetch_jobs(self, query: str = "", location: str = "", limit: int = 50) -> list[dict]:
        keywords = quote_plus(query or "software engineer")
        loc = quote_plus(location or "Remote")
        url = (
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords={keywords}&location={loc}&start=0"
        )
        logger.info("LinkedIn fetch: query=%r location=%r", query or "(default)", location or "(default)")

        headers = dict(DEFAULT_HEADERS)
        if settings.linkedin_session_cookie:
            headers["Cookie"] = settings.linkedin_session_cookie
        elif settings.linkedin_access_token:
            headers["Authorization"] = f"Bearer {settings.linkedin_access_token}"

        jobs: list[dict] = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                html = await _get_text(client, url, headers=headers)
            soup = BeautifulSoup(html, "lxml")
            for card in soup.select("li, div.base-card")[: limit * 2]:
                title_el = card.select_one("h3, span.sr-only")
                company_el = card.select_one("h4, a.hidden-nested-link")
                loc_el = card.select_one("span.job-search-card__location")
                link_el = card.select_one("a[href*='/jobs/view/']")
                if not title_el or not link_el:
                    continue
                title = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True) if company_el else "LinkedIn Employer"
                loc_text = loc_el.get_text(strip=True) if loc_el else (location or "Remote")
                href = link_el.get("href", "")
                apply_url = href.split("?")[0] if href.startswith("http") else f"https://www.linkedin.com{href}"
                if query and not _matches_query(f"{title} {company}", query):
                    continue
                jobs.append(
                    _job(
                        title=title,
                        company=company,
                        location=loc_text,
                        apply_url=apply_url,
                        source=self.source_name,
                        application_type="linkedin",
                        easy_apply="easy" in href.lower(),
                    )
                )
                if len(jobs) >= limit:
                    break
        except Exception as exc:
            logger.warning("LinkedIn fetch failed (set LINKEDIN_SESSION_COOKIE for better results): %s", exc)

        logger.info("LinkedIn kept %d jobs", len(jobs))
        return jobs


class GlassdoorScraper(BaseJobScraper):
    """Glassdoor job search listings."""

    source_name = "glassdoor"

    async def fetch_jobs(self, query: str = "", location: str = "", limit: int = 50) -> list[dict]:
        q = quote_plus(query or "software engineer")
        loc = quote_plus(location or "remote")
        url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={q}&locT=C&locKeyword={loc}"
        logger.info("Glassdoor fetch: query=%r location=%r", query or "(default)", location or "(default)")

        headers = dict(DEFAULT_HEADERS)
        if settings.glassdoor_session_cookie:
            headers["Cookie"] = settings.glassdoor_session_cookie

        jobs: list[dict] = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                html = await _get_text(client, url, headers=headers)
            soup = BeautifulSoup(html, "lxml")
            for row in soup.select("li.react-job-listing, div.jobContainer, article")[: limit * 3]:
                title_el = row.select_one("a.jobLink, a[data-test='job-link'], a[href*='/job-listing/']")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                apply_url = href if href.startswith("http") else f"https://www.glassdoor.com{href}"
                company_el = row.select_one("div.jobHeader div, span.employerName, div.jobEmpolyerName")
                loc_el = row.select_one("span.loc, div.location")
                company = company_el.get_text(strip=True) if company_el else "Glassdoor Employer"
                loc_text = loc_el.get_text(strip=True) if loc_el else (location or "Remote")
                if query and not _matches_query(f"{title} {company}", query):
                    continue
                jobs.append(
                    _job(
                        title=title,
                        company=company,
                        location=loc_text,
                        apply_url=apply_url,
                        source=self.source_name,
                        application_type="glassdoor",
                    )
                )
                if len(jobs) >= limit:
                    break
        except Exception as exc:
            logger.warning("Glassdoor fetch failed (set GLASSDOOR_SESSION_COOKIE for better results): %s", exc)

        logger.info("Glassdoor kept %d jobs", len(jobs))
        return jobs
