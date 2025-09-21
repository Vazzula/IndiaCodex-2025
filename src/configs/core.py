from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Aegis: The Autonomous Custodian"
    API_V1_STR: str = "/api/v1"

    # Database configuration
    # These will be loaded from the .env file
    DATABASE_URL: str = "postgresql://user:password@localhost/aegis_db"

    # Blockfrost API Key for Cardano
    BLOCKFROST_API_KEY: Optional[str] = None

    class Config:
        case_sensitive = True
        env_file = ".env"  # Specify the env file to load


settings = Settings()
