from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

# Config loaded from .env file

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "SweatBet"
    APP_VERSION: str = "1.0.0"

    # Username and Password for login
    USER_NAME: str = ''
    PASSWORD: str = ''

    # Strava OAuth settings
    STRAVA_CLIENT_ID: str = ''
    STRAVA_CLIENT_SECRET: str = ''
    STRAVA_REDIRECT_URI: str = ''
    
    # Strava Webhook settings
    STRAVA_WEBHOOK_VERIFY_TOKEN: str = 'SWEATBET_WEBHOOK_TOKEN'
    
    # Telegram Bot settings (for webhook notifications)
    TELEGRAM_BOT_TOKEN: str = ''
    TELEGRAM_CHAT_ID: str = ''
    
    # Session secret key
    SECRET_KEY: str = 'dev-secret-key-change-in-production'
    
    # Activity Scheduler settings
    ACTIVITY_CHECK_INTERVAL_MINUTES: int = 5  # How often to check for new activities
    REMINDER_CHECK_INTERVAL_HOURS: int = 1    # How often to check if reminders are due
    REMINDER_COOLDOWN_HOURS: int = 24         # Minimum hours between reminders
    ACTIVITY_LOOKBACK_HOURS: int = 24         # How far back to look for activities
    SCHEDULER_ENABLED: bool = True            # Enable/disable the background scheduler

    @property
    def DB_URL(self):
        if self.ENV_MODE == "dev":
            return self.DEV_DB_URL
        else:
            if self.DATABASE_URL:
                return self.DATABASE_URL
            else:
                return '{}://{}:{}@{}:{}/{}'.format(
                    self.DB_ENGINE,
                    self.DB_USERNAME,
                    self.DB_PASS,
                    self.DB_HOST,
                    self.DB_PORT,
                    self.DB_NAME
                )

    @property
    def ASYNC_DB_URL(self):
        if self.ENV_MODE == "dev":
            return "sqlite+aiosqlite:///./dev.db"
        else:
            if self.DATABASE_URL:
                URL_split = self.DATABASE_URL.split("://")
                return f"{URL_split[0]}+asyncpg://{URL_split[1]}"
            else:
                return '{}+asyncpg://{}:{}@{}:{}/{}'.format(
                    self.DB_ENGINE,
                    self.DB_USERNAME,
                    self.DB_PASS,
                    self.DB_HOST,
                    self.DB_PORT,
                    self.DB_NAME
                )

    @property
    def API_BASE_URL(self) -> str:
        if self.ENV_MODE == "dev":
            return 'http://localhost:5000/'
        return self.HOST_URL

class DevSettings(Settings):
    # Environment mode: 'dev' or 'prod'
    ENV_MODE: str = 'dev'

    # Database settings for development
    DEV_DB_URL: str = "sqlite:///./dev.db"

    model_config = SettingsConfigDict(env_file=".env", extra='allow')

class ProdSettings(Settings):
    # Environment mode: 'dev' or 'prod'
    ENV_MODE: str = 'prod'

    # Database settings for production
    DB_ENGINE: str = ''
    DB_USERNAME: str = ''
    DB_PASS: str = ''
    DB_HOST: str = ''
    DB_PORT: str = ''
    DB_NAME: str = ''

    # Extra Database settings for deploying on Railway; if you provide DATABASE_URL, the above settings will be ignored
    DATABASE_URL: str = ''

    # Define HOST_URL based on environment mode
    HOST_URL: str = ''

    # Database settings for production
    model_config = SettingsConfigDict(env_file=".env", extra='allow')

    @model_validator(mode='after')
    def validate_prod_settings(self):
        """Ensure critical settings are configured in production."""
        missing = []
        if not self.SECRET_KEY or self.SECRET_KEY == 'dev-secret-key-change-in-production':
            missing.append('SECRET_KEY')
        if not self.DATABASE_URL and not (self.DB_ENGINE and self.DB_HOST):
            missing.append('DATABASE_URL')
        if not self.HOST_URL:
            missing.append('HOST_URL')
        if not self.STRAVA_CLIENT_ID:
            missing.append('STRAVA_CLIENT_ID')
        if not self.STRAVA_CLIENT_SECRET:
            missing.append('STRAVA_CLIENT_SECRET')
        if missing:
            raise ValueError(f"Missing required production settings: {', '.join(missing)}")
        return self

def get_settings(env_mode: str = "dev"):
    if env_mode == "dev":
        return DevSettings()
    return ProdSettings()