from pydantic_settings import BaseSettings
from pydantic import Field


class AuthSettings(BaseSettings):
    #JWT
    algorithm: str = Field(...) 
    access_secret_key: str = Field(...)
    access_token_expire: int = Field(...)
    refresh_secret_key: str = Field(...)
    refresh_token_expire: int = Field(...)
    validation_secret_key: str = Field(...)
    validation_token_expire: int = Field(...)

    #SOCIAL_LOGIN
    google_client_id: str = Field(...)
    google_client_secret: str = Field(...)
    google_redirect_uri: str = Field(...)
    google_auth_url: str = Field(...)
    google_token_url: str = Field(...)
    google_userinfo_url: str = Field(...)

    github_client_id: str = Field(...)
    github_client_secret: str = Field(...)
    github_redirect_uri: str = Field(...)
    github_authorize_url: str = Field(...)
    github_token_url: str = Field(...)
    github_user_api: str = Field(...)
    github_emails: str = Field(...)