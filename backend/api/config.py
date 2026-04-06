from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://pt_user:changeme@localhost:5432/pricetracker"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = "changeme"

    # LLM
    LLM_PROVIDER: str = "ollama"  # ollama | openai | anthropic
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Proxy
    PROXY_PROVIDER: str = "none"  # webshare | static_file | none
    WEBSHARE_API_KEY: str = ""
    PROXY_STATIC_FILE_PATH: str = "/app/proxies.txt"

    # Auth
    JWT_SECRET_KEY: str = "changeme_use_a_real_secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days

    # App
    API_BASE_URL: str = "http://localhost:8000"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Scraping concurrency limits
    SCRAPE_CONCURRENCY_AMAZON: int = 2
    SCRAPE_CONCURRENCY_FLIPKART: int = 3
    SCRAPE_CONCURRENCY_MYNTRA: int = 3

    # AI extraction
    ENABLE_LLM_FALLBACK: bool = True
    ENABLE_VISION_FALLBACK: bool = False
    LLM_CONFIDENCE_THRESHOLD: float = 0.75


settings = Settings()
