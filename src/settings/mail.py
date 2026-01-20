from pydantic_settings import BaseSettings
from pydantic import Field


class MailSettings(BaseSettings):
    smtp_host: str = Field(...)
    smtp_port: int = Field(...)
    smtp_user: str = Field(...)
    smtp_password: str = Field(...)