"""Browser automation adapters for Indeed, ZipRecruiter, LinkedIn, and Glassdoor."""

from abc import ABC, abstractmethod


class ApplicationAdapter(ABC):
    platform: str = "base"

    @abstractmethod
    async def can_handle(self, url: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def apply(self, url: str, profile: dict, resume_path: str, cover_letter_path: str | None) -> dict:
        raise NotImplementedError


class IndeedAdapter(ApplicationAdapter):
    platform = "indeed"

    async def can_handle(self, url: str) -> bool:
        return "indeed.com" in url

    async def apply(self, url: str, profile: dict, resume_path: str, cover_letter_path: str | None) -> dict:
        return {
            "status": "manual_required",
            "message": "Indeed auto-apply requires Playwright session — adapter not wired yet.",
            "url": url,
        }


class ZipRecruiterAdapter(ApplicationAdapter):
    platform = "ziprecruiter"

    async def can_handle(self, url: str) -> bool:
        return "ziprecruiter.com" in url

    async def apply(self, url: str, profile: dict, resume_path: str, cover_letter_path: str | None) -> dict:
        return {
            "status": "manual_required",
            "message": "ZipRecruiter auto-apply requires Playwright session — adapter not wired yet.",
            "url": url,
        }


class LinkedInEasyApplyAdapter(ApplicationAdapter):
    platform = "linkedin"

    async def can_handle(self, url: str) -> bool:
        return "linkedin.com" in url

    async def apply(self, url: str, profile: dict, resume_path: str, cover_letter_path: str | None) -> dict:
        return {
            "status": "manual_required",
            "message": "LinkedIn Easy Apply requires authenticated Playwright session.",
            "url": url,
        }


class GlassdoorAdapter(ApplicationAdapter):
    platform = "glassdoor"

    async def can_handle(self, url: str) -> bool:
        return "glassdoor.com" in url

    async def apply(self, url: str, profile: dict, resume_path: str, cover_letter_path: str | None) -> dict:
        return {
            "status": "manual_required",
            "message": "Glassdoor auto-apply requires Playwright session — adapter not wired yet.",
            "url": url,
        }


ADAPTERS: list[ApplicationAdapter] = [
    IndeedAdapter(),
    ZipRecruiterAdapter(),
    LinkedInEasyApplyAdapter(),
    GlassdoorAdapter(),
]


async def get_adapter(url: str) -> ApplicationAdapter | None:
    for adapter in ADAPTERS:
        if await adapter.can_handle(url):
            return adapter
    return None
