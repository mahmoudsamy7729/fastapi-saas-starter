from pydantic_settings import SettingsConfigDict
from pathlib import Path
from src.settings.app import AppSettings
from src.settings.database import DatabaseSettings
from src.settings.mail import MailSettings
from src.settings.redis import RedisSettings
from src.settings.celery import CelerySettings
from src.auth.config import AuthSettings
from src.settings.stripe import StripeSettings



BASE_DIR = Path(__file__).parent.parent


class Settings(AppSettings,DatabaseSettings,MailSettings,RedisSettings,
    CelerySettings,AuthSettings, StripeSettings):

    model_config = SettingsConfigDict(env_file=".env",env_file_encoding="utf-8",
    extra="ignore",)



settings = Settings()


