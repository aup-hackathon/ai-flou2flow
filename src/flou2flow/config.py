"""Configuration management for Flou2Flow."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
EXAMPLES_DIR = BASE_DIR / "examples"


class Settings:
    """Application settings loaded from environment variables."""

    # LLM Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")  # Default to ollama
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen2:1.5b")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # LLM Parameters
    TEMPERATURE: float = 0.3  # Low temperature for structured output
    MAX_TOKENS: int = 4096
    VISION_MODEL: str = os.getenv("VISION_MODEL", "llava")

    @property
    def api_url(self) -> str:
        """Get the appropriate API URL based on provider."""
        if self.LLM_PROVIDER == "ollama":
            return f"{self.OLLAMA_BASE_URL}/api/chat"
        return self.MISTRAL_API_URL


settings = Settings()
