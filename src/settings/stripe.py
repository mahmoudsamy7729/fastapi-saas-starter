from pydantic_settings import BaseSettings
from pydantic import Field



class StripeSettings(BaseSettings):
    stripe_webhook_secret: str = Field(...)
    stripe_public_key: str = Field(...)
    stripe_secret_key: str = Field(...)