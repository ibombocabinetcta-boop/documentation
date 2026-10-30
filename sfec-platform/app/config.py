from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    odoo_url: str = ""
    odoo_db: str = ""
    odoo_login: str = ""
    odoo_api_key: str = ""

    sfec_mode: str = "mock"
    sfec_base_url: str = ""
    sfec_api_token: str = ""
    sfec_timeout: int = 30

    database_url: str = "sqlite:///./sfec.db"
    platform_api_key: str = ""
    sync_batch_size: int = 50
    max_attempts: int = 5


settings = Settings()
