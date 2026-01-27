from pydantic_settings import BaseSettings
from pydantic import Field


class AiSettings(BaseSettings):

    ai_provider: str = Field(default="groq")
    groq_api_key: str
    groq_base_url: str

    ai_model: str = Field(default="openai/gpt-oss-120b")  