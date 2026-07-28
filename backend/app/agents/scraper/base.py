from __future__ import annotations

from abc import ABC, abstractmethod

import httpx
import logging
import re

logger = logging.getLogger("app.scraper")


def _matches_query(text: str, query: str) -> bool:
    if not query:
        return True
    return query.lower() in text.lower()


def _blob(item: dict, *keys: str) -> str:
    parts = [str(item.get(k, "")) for k in keys]
    tags = item.get("tags") or item.get("skills") or []
    if isinstance(tags, list):
        parts.extend(str(t) for t in tags)
    return " ".join(parts)


class BaseJobScraper(ABC):
    source_name: str = "base"

    @abstractmethod
    async def fetch_jobs(self, query: str = "", location: str = "", limit: int = 50) -> list[dict]:
        raise NotImplementedError


class RemoteOKScraper(BaseJobScraper):
    source_name = "remoteok"
    API_URL = "https://remoteok.com/api"

    async def fetch_jobs(self, query: str = "", location: str = "", limit: int = 50) -> list[dict]:
        headers = {"User-Agent": "ResumeBuild/0.1 (prototype)"}
        logger.info("RemoteOK fetch: query=%r limit=%d", query or "(all)", limit)
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(self.API_URL)
            response.raise_for_status()
            payload = response.json()

        jobs: list[dict] = []
        for item in payload[1 : limit + 1]:
            title = item.get("position", "")
            description = item.get("description", "") or ""
            tags = [tag.strip() for tag in (item.get("tags") or []) if isinstance(tag, str)]
            haystack = f"{title} {description} {' '.join(tags)}"
            if query and not _matches_query(haystack, query):
                continue

            loc = item.get("location") or "Remote"
            if location and location.lower() not in loc.lower() and "remote" not in loc.lower():
                continue

            jobs.append(
                {
                    "title": title,
                    "company": item.get("company", ""),
                    "location": loc,
                    "salary": str(item.get("salary", "") or ""),
                    "experience_required": "",
                    "skills": tags,
                    "description": description,
                    "apply_url": item.get("url", item.get("apply_url", "")),
                    "application_type": "external",
                    "easy_apply": False,
                    "remote_type": "remote",
                    "visa_required": False,
                    "source": self.source_name,
                }
            )

        logger.info("RemoteOK kept %d jobs for query=%r", len(jobs), query or "(all)")
        return jobs


class ArbeitnowScraper(BaseJobScraper):
    """Public job board API — mixed industries, not tech-only."""

    source_name = "arbeitnow"
    API_URL = "https://www.arbeitnow.com/api/job-board-api"

    async def fetch_jobs(self, query: str = "", location: str = "", limit: int = 50) -> list[dict]:
        logger.info("Arbeitnow fetch: query=%r limit=%d", query or "(all)", limit)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.API_URL)
            response.raise_for_status()
            payload = response.json()

        jobs: list[dict] = []
        for item in payload.get("data", [])[: limit * 3]:
            title = item.get("title", "")
            description = item.get("description", "") or ""
            tags = item.get("tags") or []
            if isinstance(tags, list):
                tag_list = [str(t) for t in tags]
            else:
                tag_list = []

            haystack = f"{title} {description} {' '.join(tag_list)}"
            if query and not _matches_query(haystack, query):
                continue

            loc = item.get("location", "") or "Remote"
            if location and location.lower() not in loc.lower() and "remote" not in loc.lower():
                continue

            remote_flag = item.get("remote")
            if remote_flag is True:
                remote_type = "remote"
            elif remote_flag in (False, None):
                remote_type = ""
            else:
                remote_type = str(remote_flag)

            jobs.append(
                {
                    "title": title,
                    "company": item.get("company_name", ""),
                    "location": loc,
                    "salary": "",
                    "experience_required": "",
                    "skills": tag_list,
                    "description": description,
                    "apply_url": item.get("url", ""),
                    "application_type": "external",
                    "easy_apply": False,
                    "remote_type": remote_type,
                    "visa_required": False,
                    "source": self.source_name,
                }
            )
            if len(jobs) >= limit:
                break

        logger.info("Arbeitnow kept %d jobs for query=%r", len(jobs), query or "(all)")
        return jobs


class GreenhouseBoardScraper(BaseJobScraper):
    source_name = "greenhouse"

    def __init__(self, board_token: str) -> None:
        self.board_token = board_token

    async def fetch_jobs(self, query: str = "", location: str = "", limit: int = 50) -> list[dict]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.board_token}/jobs"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()

        jobs: list[dict] = []
        for item in payload.get("jobs", [])[:limit]:
            title = item.get("title", "")
            if query and not _matches_query(title, query):
                continue
            loc = item.get("location", {}).get("name", "")
            if location and location.lower() not in loc.lower():
                continue
            jobs.append(
                {
                    "title": title,
                    "company": self.board_token,
                    "location": loc,
                    "salary": "",
                    "experience_required": "",
                    "skills": [],
                    "description": "",
                    "apply_url": item.get("absolute_url", ""),
                    "application_type": "greenhouse",
                    "easy_apply": False,
                    "remote_type": "",
                    "visa_required": False,
                    "source": self.source_name,
                }
            )
        return jobs
