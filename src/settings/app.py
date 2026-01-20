from pydantic_settings import BaseSettings
from pydantic import Field


class AppSettings(BaseSettings):
    app_name: str = "FastAPI Auth System"
    app_env: str = "development"
    app_debug: bool = True
    app_url: str