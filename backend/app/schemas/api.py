from typing import Literal

from pydantic import BaseModel, Field


class KillSwitchUpdate(BaseModel):
    enabled: bool


class DeviceRegister(BaseModel):
    token: str = Field(min_length=8, max_length=4096)
    platform: Literal["android", "windows", "web"] = "android"
    label: str | None = Field(default=None, max_length=200)
