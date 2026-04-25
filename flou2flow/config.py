"""Configuration management for Flou2Flow."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
EXAMPLES_DIR = BASE_DIR / "examples"


class Settings:
    """Application settings loaded from environment variables."""

    # LLM Configuration (Local Only)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # Pro Hybrid Model Routing
    LLM_MODEL: str = os.getenv("LLM_MODEL", "phi3")  # Primary Reasoning
    VISION_MODEL: str = os.getenv("VISION_MODEL", "moondream")  # Vision/OCR
    CLEANING_MODEL: str = os.getenv("CLEANING_MODEL", "qwen2:1.5b")  # Aggregation/Cleaning
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")  # Voice Transcription

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8001")) # Sync with common port used in tests

    # NATS
    NATS_URL: str = os.getenv("NATS_URL", "nats://localhost:4222")

    # LLM Parameters
    TEMPERATURE: float = 0.3
    MAX_TOKENS: int = 4096

    @property
    def api_url(self) -> str:
        return f"{self.OLLAMA_BASE_URL}/api/chat"


settings = Settings()
