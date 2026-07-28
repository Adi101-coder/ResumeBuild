from __future__ import annotations

import logging
import re
from html import unescape

import httpx

from app.agents.scraper.base import BaseJobScraper, _matches_query

logger = logging.getLogger("app.scraper")


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
        "easy_apply": False,
        "remote_type": remote_type,
        "visa_required": False,
        "source": source,
    }


class LeverScraper(BaseJobScraper):
    source_name = "lever"

    def __init__(self, company_slug: str) -> None:
        self.company_slug = company_slug

    async def fetch_jobs(self, query: str = "", location: str = "", limit: int = 50) -> list[dict]:
        url = f"https://api.lever.co/v0/postings/{self.company_slug}?mode=json"
        logger.info("Lever fetch: company=%s", self.company_slug)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            if response.status_code == 404:
                logger.warning("Lever board not found: %s", self.company_slug)
                return []
            response.raise_for_status()
            payload = response.json()

        jobs: list[dict] = []
        for item in payload[: limit * 2]:
            title = item.get("text", "")
            desc = item.get("descriptionPlain", "") or item.get("description", "") or ""
            haystack = f"{title} {desc}"
            if query and not _matches_query(haystack, query):
                continue
            loc = (item.get("categories") or {}).get("location", "")
            jobs.append(
                _job(
                    title=title,
                    company=self.company_slug,
                    location=loc,
                    description=desc[:2000],
                    apply_url=item.get("hostedUrl", item.get("applyUrl", "")),
                    source=self.source_name,
                    application_type="lever",
                )
            )
            if len(jobs) >= limit:
                break
        logger.info("Lever %s kept %d jobs", self.company_slug, len(jobs))
        return jobs


class AshbyScraper(BaseJobScraper):
    source_name = "ashby"

    def __init__(self, board_name: str) -> None:
        self.board_name = board_name

    async def fetch_jobs(self, query: str = "", location: str = "", limit: int = 50) -> list[dict]:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{self.board_name}"
        logger.info("Ashby fetch: board=%s", self.board_name)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json={})
            if response.status_code >= 400:
                logger.warning("Ashby board unavailable: %s (%s)", self.board_name, response.status_code)
                return []
            payload = response.json()

        jobs: list[dict] = []
        for item in payload.get("jobs", [])[: limit * 2]:
            title = item.get("title", "")
            desc = item.get("descriptionPlain", "") or ""
            if query and not _matches_query(f"{title} {desc}", query):
                continue
            loc = item.get("location", "") or (item.get("locationName") or "")
            jobs.append(
                _job(
                    title=title,
                    company=item.get("companyName") or self.board_name,
                    location=str(loc),
                    description=desc[:2000],
                    apply_url=item.get("jobUrl", ""),
                    source=self.source_name,
                    application_type="ashby",
                )
            )
            if len(jobs) >= limit:
                break
        logger.info("Ashby %s kept %d jobs", self.board_name, len(jobs))
        return jobs


class YCJobsScraper(BaseJobScraper):
    """Y Combinator / Work at a Startup public listings."""

    source_name = "yc"
    API_URL = "https://www.workatastartup.com/jobs.json"

    async def fetch_jobs(self, query: str = "", location: str = "", limit: int = 50) -> list[dict]:
        logger.info("YC Jobs fetch")
        headers = {"User-Agent": "ResumeBuild/1.0"}
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(self.API_URL)
            if response.status_code >= 400:
                logger.warning("YC Jobs unavailable: HTTP %s", response.status_code)
                return []
            payload = response.json()

        jobs: list[dict] = []
        for item in payload[: limit * 3]:
            title = item.get("title", "")
            company = (item.get("company") or {}).get("name", "YC Startup")
            desc = item.get("description", "") or ""
            if query and not _matches_query(f"{title} {desc} {company}", query):
                continue
            jobs.append(
                _job(
                    title=title,
                    company=company,
                    location=item.get("location", "Remote"),
                    description=desc[:2000],
                    apply_url=f"https://www.workatastartup.com/jobs/{item.get('id', '')}",
                    source=self.source_name,
                )
            )
            if len(jobs) >= limit:
                break
        logger.info("YC Jobs kept %d jobs", len(jobs))
        return jobs


class RedditJobsScraper(BaseJobScraper):
    """Hiring posts from job subreddits (public JSON)."""

    source_name = "reddit"
    SUBREDDITS = ("forhire", "remotejobs", "jobbit")

    async def fetch_jobs(self, query: str = "", location: str = "", limit: int = 50) -> list[dict]:
        headers = {"User-Agent": "ResumeBuild/1.0 (job discovery)"}
        jobs: list[dict] = []

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            for sub in self.SUBREDDITS:
                url = f"https://www.reddit.com/r/{sub}/search.json?q=hiring&restrict_sr=1&sort=new&limit=25"
                logger.info("Reddit fetch: r/%s", sub)
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    posts = response.json().get("data", {}).get("children", [])
                except Exception as exc:
                    logger.warning("Reddit r/%s failed: %s", sub, exc)
                    continue

                for post in posts:
                    data = post.get("data", {})
                    title = data.get("title", "")
                    body = data.get("selftext", "") or ""
                    if query and not _matches_query(f"{title} {body}", query):
                        continue
                    if "[hiring]" not in title.lower() and "hiring" not in title.lower():
                        continue
                    jobs.append(
                        _job(
                            title=title[:200],
                            company=f"r/{sub}",
                            location="Remote",
                            description=body[:2000],
                            apply_url=f"https://reddit.com{data.get('permalink', '')}",
                            source=self.source_name,
                            application_type="reddit",
                        )
                    )
                    if len(jobs) >= limit:
                        break
                if len(jobs) >= limit:
                    break

        logger.info("Reddit kept %d jobs", len(jobs))
        return jobs


class WellfoundScraper(BaseJobScraper):
    source_name = "wellfound"

    async def fetch_jobs(self, query: str = "", location: str = "", limit: int = 50) -> list[dict]:
        logger.warning("Wellfound requires API credentials — set WELLFOUND_API_TOKEN in .env")
        return []


class LinkedInScraper(BaseJobScraper):
    source_name = "linkedin"

    async def fetch_jobs(self, query: str = "", location: str = "", limit: int = 50) -> list[dict]:
        logger.warning("LinkedIn requires authenticated API/session — set LINKEDIN credentials in .env")
        return []


class TwitterJobsScraper(BaseJobScraper):
    source_name = "twitter"

    async def fetch_jobs(self, query: str = "", location: str = "", limit: int = 50) -> list[dict]:
        logger.warning("Twitter/X requires BEARER_TOKEN — set TWITTER_BEARER_TOKEN in .env")
        return []


class CareerPageRSSScraper(BaseJobScraper):
    source_name = "career_page"

    def __init__(self, feed_url: str, company: str = "") -> None:
        self.feed_url = feed_url
        self.company = company or "Company"

    async def fetch_jobs(self, query: str = "", location: str = "", limit: int = 50) -> list[dict]:
        logger.info("Career RSS fetch: %s", self.feed_url)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.feed_url)
            response.raise_for_status()
            text = response.text

        titles = re.findall(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", text)
        links = re.findall(r"<link>(.*?)</link>", text)
        jobs: list[dict] = []
        for title, link in zip(titles[1:], links[1:]):  # skip feed title
            title = unescape(title.strip())
            if query and not _matches_query(title, query):
                continue
            jobs.append(
                _job(
                    title=title,
                    company=self.company,
                    apply_url=link.strip(),
                    source=self.source_name,
                )
            )
            if len(jobs) >= limit:
                break
        logger.info("Career RSS kept %d jobs from %s", len(jobs), self.company)
        return jobs
