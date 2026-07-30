from __future__ import annotations

from abc import ABC, abstractmethod

import logging

logger = logging.getLogger("app.scraper")


def _matches_query(text: str, query: str) -> bool:
    if not query:
        return True
    return query.lower() in text.lower()


class BaseJobScraper(ABC):
    source_name: str = "base"

    @abstractmethod
    async def fetch_jobs(self, query: str = "", location: str = "", limit: int = 50) -> list[dict]:
        raise NotImplementedError
