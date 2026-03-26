"""
backend/config/settings.py
Application configuration — pure Ollama/MedGemma, no cloud API keys.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env from project root
ENV_FILE = Path(__file__).parent.parent.parent / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
    logger.info("Loaded environment from %s", ENV_FILE)
else:
    logger.warning("No .env file found at %s — using defaults", ENV_FILE)


class Settings:
    """Application settings — zero cloud dependencies."""

    # API
    API_TITLE: str = "MediOrbit API"
    API_VERSION: str = "2.0.0"
    API_DESCRIPTION: str = "CarePath AI — Medical Tourism Assistant (Tamil Nadu)"

    # Ollama / MedGemma (local, no API key required)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "medgemma:4b")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "300"))  # 300s for X-ray processing

    # CarePath AI system prompt
    SYSTEM_PROMPT: str = (
        "You are 'CarePath AI,' a compassionate, professional healthcare caretaker "
        "and medical tourism guide. Your goal is to assist users in navigating their "
        "health journey with empathy and precision.\n\n"
        "Operational Guidelines:\n"
        "1. Persona: Use a warm, validating tone (e.g., 'I understand you're feeling "
        "anxious about your symptoms'). Transition to a direct, urgent tone if symptoms "
        "indicate a medical emergency.\n"
        "2. Multimodal Analysis: When an X-ray or medical report is provided, analyze "
        "the visuals using your medical knowledge. Provide an AI-driven summary but "
        "explicitly state this is not a final diagnosis.\n"
        "3. Hospital Retrieval: If a user asks for hospitals, extract the 'Problem' and "
        "'City' from their query. Rank hospitals by specialty match first, then by city.\n"
        "4. Safety & Professionalism: NEVER provide a definitive diagnosis. Always end "
        "clinical summaries with: 'Please consult a board-certified professional for a "
        "clinical evaluation.'\n"
        "5. Focus: You cover Tamil Nadu, India. Provide culturally sensitive, "
        "accurate information about local hospitals, costs (INR), and procedures."
    )

    # Streaming
    STREAM_RESPONSES: bool = os.getenv("STREAM_RESPONSES", "true").lower() == "true"

    # CORS
    CORS_ORIGINS: list = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")

    # Data
    HOSPITALS_CSV: Path = Path(__file__).parent.parent / "data" / "hospitals.csv"

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Feature flags
    ENABLE_OCR: bool = True
    ENABLE_NER: bool = True
    ENABLE_XRAY: bool = True

    @classmethod
    def validate(cls) -> bool:
        errors = []
        if not cls.HOSPITALS_CSV.exists():
            errors.append(f"Hospitals CSV not found at {cls.HOSPITALS_CSV}")
        for err in errors:
            logger.error(err)
        return len(errors) == 0

    @classmethod
    def log_summary(cls):
        logger.info("=" * 50)
        logger.info("MEDIOORBIT CONFIGURATION")
        logger.info("Model:   %s @ %s", cls.OLLAMA_MODEL, cls.OLLAMA_BASE_URL)
        logger.info("Server:  %s:%s", cls.HOST, cls.PORT)
        logger.info("Timeout: %ss", cls.LLM_TIMEOUT)
        logger.info("=" * 50)


settings = Settings()
