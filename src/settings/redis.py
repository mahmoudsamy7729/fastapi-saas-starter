from pydantic_settings import BaseSettings
from pydantic import Field


class RedisSettings(BaseSettings):
    redis_url: str = Field(...)