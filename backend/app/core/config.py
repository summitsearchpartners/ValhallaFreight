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
    document_storage_path: str = "/app/storage"
    max_compliance_document_mb: int = 15
    dayton_api_base_url: str = "https://api.daytonfreight.com"
    dayton_api_username: str = ""
    dayton_api_password: str = ""
    dayton_api_account: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
