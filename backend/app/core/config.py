from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:5173"

    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # Groq (primary LLM)
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    groq_url: str = "https://api.groq.com/openai/v1/chat/completions"

    # Google Gemini (fallback LLM)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # Alpha Vantage
    alpha_vantage_api_key: str = ""

    # Pipeline
    nse_data_start_year: int = 2019

    class Config:
        env_file = str(_ENV_FILE) if _ENV_FILE.exists() else None
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
