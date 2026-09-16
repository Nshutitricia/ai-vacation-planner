from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ANTHROPIC_API_KEY:str
    LLM_PROVIDER: str = "anthropic"
    DEBUG: bool = False
    EMBEDDING_DIMENSIONS: int = 1024
    VOYAGE_API_KEY: str
    EMBEDDING_MODEL: str = "voyage-3.5-lite"

settings = Settings()