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
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2

    analysis_prompt_version: str = "analysis-v1"
    analysis_relevance_min: float = 0.3
    fast_path_enabled: bool = True

    typesafe_api_key: str = ""
    typesafe_base_url: str = "https://api.typesafe.ai"
    typesafe_model: str = "jev-latest"
    typesafe_timeout_seconds: float = 20.0
    jev_gate_enabled: bool = True
    jev_usefulness_min: float = 0.5

    trading_mode: str = "paper"
    default_exchange: str = "binance"
    paper_equity: float = 10000.0
    confidence_min: int = 60
    max_daily_loss_pct: float = 3.0
    max_leverage: int = 5
    kill_switch: bool = False

    api_token: str = "change-me"
    cors_origins: str = "*"

    notifications_enabled: bool = True
    fcm_project_id: str = ""
    fcm_credentials_path: str = ""

    feed_request_timeout: float = 20.0
    feed_user_agent: str = "newstrade1-feedbot/0.1"
    feed_max_entries: int = 40
    feed_max_age_hours: int = 72

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
