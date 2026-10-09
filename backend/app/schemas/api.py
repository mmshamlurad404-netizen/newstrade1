from typing import Literal

from pydantic import BaseModel, Field


class KillSwitchUpdate(BaseModel):
    enabled: bool


class DeviceRegister(BaseModel):
    token: str = Field(min_length=8, max_length=4096)
    platform: Literal["android", "windows", "web"] = "android"
    label: str | None = Field(default=None, max_length=200)


class FeedCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=8, max_length=2048)
    credibility: float = Field(default=0.6, ge=0.0, le=1.0)
    poll_interval_seconds: int = Field(default=300, ge=30, le=86400)


class ActiveUpdate(BaseModel):
    active: bool
