from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    tg_api_id: int
    tg_api_hash: str
    tg_session_name: str = "newstrade_ingestor"
    tg_history_limit: int = 2000

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    trading_mode: str = "paper"
    confidence_min: int = 60
    max_daily_loss_pct: float = 3.0
    max_leverage: int = 5
    kill_switch: bool = False

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
