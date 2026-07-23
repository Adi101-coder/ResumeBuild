from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("app.pipeline")


def step(name: str, **details: Any) -> None:
    parts = " | ".join(f"{k}={v}" for k, v in details.items()) if details else ""
    logger.info("▶ STEP %s%s", name, f" | {parts}" if parts else "")


def step_done(name: str, **details: Any) -> None:
    parts = " | ".join(f"{k}={v}" for k, v in details.items()) if details else ""
    logger.info("✔ DONE %s%s", name, f" | {parts}" if parts else "")


def step_fail(name: str, error: str) -> None:
    logger.error("✗ FAIL %s | error=%s", name, error)
