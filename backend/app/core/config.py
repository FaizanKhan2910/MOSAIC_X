import os
from pydantic import BaseModel

class Settings(BaseModel):
    APP_NAME: str = "NEXORA Personal Intelligence Discovery Engine"
    API_PREFIX: str = "/api"
    DEBUG: bool = True
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./backend/nexora.db")
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ]
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

settings = Settings()
