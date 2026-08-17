from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "FreightForge API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://freightforge:freightforge@db:5432/freightforge"
    cors_origins: str = "http://localhost:5173"
    default_markup_pct: float = 15.0
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
