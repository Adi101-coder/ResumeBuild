from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("app.pipeline")


def step(step_name: str, **details: Any) -> None:
    parts = " | ".join(f"{k}={v}" for k, v in details.items()) if details else ""
    logger.info("▶ STEP %s%s", step_name, f" | {parts}" if parts else "")


def step_done(step_name: str, **details: Any) -> None:
    parts = " | ".join(f"{k}={v}" for k, v in details.items()) if details else ""
    logger.info("✔ DONE %s%s", step_name, f" | {parts}" if parts else "")


def step_fail(step_name: str, error: str) -> None:
    detail = error or "(no message)"
    logger.error("✗ FAIL %s | error=%s", step_name, detail)
