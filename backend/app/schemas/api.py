from pydantic import BaseModel


class KillSwitchUpdate(BaseModel):
    enabled: bool
