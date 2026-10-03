from datetime import datetime

from pydantic import BaseModel, Field


class RawItem(BaseModel):
    channel_telegram_id: int
    channel_title: str | None = None
    is_private: bool = False
    message_id: int
    posted_at: datetime
    original_text: str | None = None
    normalized_text: str
    links: list[str] = Field(default_factory=list)
    media_type: str | None = None
    views: int | None = None
    forwards: int | None = None
    content_hash: str
