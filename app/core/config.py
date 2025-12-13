from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    """SafeX API Configuration Settings"""

    # Application
    APP_NAME: str = "SafeX API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database (Supabase PostgreSQL)
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost/dbname"
    SYNC_DATABASE_URL: str = "postgresql://user:pass@localhost/dbname"

    # Redis (WebSocket pub/sub)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security & Authentication
    SECRET_KEY: str = "development_secret_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30


    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert comma-separated origins to list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    
    # Cloudinary (Optional)
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    
    @property
    def cloudinary_enabled(self) -> bool:
        """Check if Cloudinary is configured"""
        return bool(self.CLOUDINARY_CLOUD_NAME and self.CLOUDINARY_API_KEY and self.CLOUDINARY_API_SECRET)

    # Twilio (SMS & Calls)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    @property
    def twilio_enabled(self) -> bool:
        """Check if Twilio is configured"""
        return bool(self.TWILIO_ACCOUNT_SID and self.TWILIO_AUTH_TOKEN and self.TWILIO_PHONE_NUMBER)


    # Agent Authentication
    AGENT_API_KEYS: str = ""

    @property
    def agent_api_keys_list(self) -> List[str]:
        """Convert comma-separated API keys to list"""
        if not self.AGENT_API_KEYS:
            return []
        return [key.strip() for key in self.AGENT_API_KEYS.split(",")]

    # Monitoring
    LOG_LEVEL: str = "INFO"

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @property
    def _computed_sync_url(self) -> str:
        """Ensure we have a sync URL for Alembic"""
        url = self.SYNC_DATABASE_URL or self.DATABASE_URL
        if url and url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://")
        return url

    def model_post_init(self, __context):
        """Fix database URLs after initialization"""
        # Ensure DATABASE_URL is async for the app
        if self.DATABASE_URL and self.DATABASE_URL.startswith("postgresql://"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        
        # Ensure SYNC_DATABASE_URL is sync for Alembic
        # If SYNC_DATABASE_URL was not explicitly set (is default), derive from DATABASE_URL
        if self.SYNC_DATABASE_URL == "postgresql://user:pass@localhost/dbname" and self.DATABASE_URL:
             # Use the raw DATABASE_URL but make it sync
             base_url = self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
             self.SYNC_DATABASE_URL = base_url
        elif self.SYNC_DATABASE_URL and self.SYNC_DATABASE_URL.startswith("postgresql+asyncpg://"):
            self.SYNC_DATABASE_URL = self.SYNC_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


settings = Settings()




