"""Browser automation adapters — prototype stubs for ATS-specific handlers."""

from abc import ABC, abstractmethod


class ApplicationAdapter(ABC):
    platform: str = "base"

    @abstractmethod
    async def can_handle(self, url: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def apply(self, url: str, profile: dict, resume_path: str, cover_letter_path: str | None) -> dict:
        raise NotImplementedError


class GreenhouseAdapter(ApplicationAdapter):
    platform = "greenhouse"

    async def can_handle(self, url: str) -> bool:
        return "greenhouse.io" in url

    async def apply(self, url: str, profile: dict, resume_path: str, cover_letter_path: str | None) -> dict:
        return {
            "status": "manual_required",
            "message": "Greenhouse adapter stub — Playwright handler not wired in prototype.",
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


ADAPTERS: list[ApplicationAdapter] = [
    GreenhouseAdapter(),
    LinkedInEasyApplyAdapter(),
]


async def get_adapter(url: str) -> ApplicationAdapter | None:
    for adapter in ADAPTERS:
        if await adapter.can_handle(url):
            return adapter
    return None
