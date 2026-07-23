from pydantic import BaseModel, Field

from fastapi import APIRouter

import logging

logger = logging.getLogger("app.ui")

router = APIRouter(prefix="/events", tags=["events"])


class ClientEvent(BaseModel):
    action: str
    page: str = ""
    detail: str = ""
    meta: dict = Field(default_factory=dict)


@router.post("/client")
def log_client_event(event: ClientEvent) -> dict:
    meta = " | ".join(f"{k}={v}" for k, v in event.meta.items()) if event.meta else ""
    logger.info(
        "UI CLICK | action=%s page=%s detail=%s%s",
        event.action,
        event.page or "-",
        event.detail or "-",
        f" | {meta}" if meta else "",
    )
    return {"logged": True}
