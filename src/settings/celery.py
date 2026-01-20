from pydantic_settings import BaseSettings 
from pydantic import Field


class CelerySettings(BaseSettings):
    celery_worker_url: str = Field(...)
    celery_beat_url: str = Field(...)