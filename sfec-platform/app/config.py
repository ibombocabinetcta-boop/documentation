from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    odoo_url: str = ""
    odoo_db: str = ""
    odoo_login: str = ""
    odoo_api_key: str = ""

    # mock | sandbox | production
    sfec_mode: str = "mock"
    sfec_api_key: str = ""
    sfec_timeout: int = 30
    sfec_taxpayer_niu: str = ""
    sfec_transaction_location: str = ""
    # Étiquette de contact Odoo identifiant les clients « administration » (recipient_type=government)
    sfec_government_tag: str = "Administration"
    # Mot-clé identifiant, dans le nom de la taxe Odoo, les centimes additionnels
    sfec_cent_tax_keyword: str = "centime"

    database_url: str = "sqlite:///./sfec.db"
    # Accès au tableau de bord (authentification HTTP Basic) ; obligatoire hors mock
    admin_user: str = "admin"
    admin_password: str = ""
    # Accès machine aux routes /api via l'en-tête X-API-Key (facultatif)
    platform_api_key: str = ""
    # Synchronisation automatique Odoo -> SFEC toutes les N minutes (0 = désactivée)
    sync_interval_minutes: int = 0
    # Ne jamais envoyer au SFEC les factures antérieures à cette date (AAAA-MM-JJ)
    sync_from_date: str = ""
    sync_batch_size: int = 50
    max_attempts: int = 5


settings = Settings()
