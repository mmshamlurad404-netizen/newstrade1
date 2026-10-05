import os

os.environ["API_TOKEN"] = "test-token"
os.environ.setdefault("TG_API_ID", "1")
os.environ.setdefault("TG_API_HASH", "test-hash")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/newstrade_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
