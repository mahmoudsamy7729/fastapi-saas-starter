from openai import AsyncOpenAI
from src.config import settings
from src.admin.ai_vars import AI_TOOLS, SYSTEM_MESSAGE


def get_ai_client():
    if settings.ai_provider == "groq":
        client = AsyncOpenAI(base_url=settings.groq_base_url, api_key=settings.groq_api_key)
        return client

    raise ValueError(f"Unsupported provider: {settings.ai_provider}")

ai_model = settings.ai_model
ai_tools = AI_TOOLS
system = SYSTEM_MESSAGE


