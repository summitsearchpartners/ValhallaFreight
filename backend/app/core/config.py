from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Valhalla Freight API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://valhalla_freight:valhalla_freight@db:5432/valhalla_freight"
    cors_origins: str = "http://localhost:5173"
    default_markup_pct: float = 15.0
    jwt_secret_key: str = "change-this-local-development-secret"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 720
    default_admin_email: str = "admin@valhallafreight.local"
    default_admin_password: str = "Valhalla123!"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
