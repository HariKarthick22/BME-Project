"""
backend/config/settings.py
Production-ready configuration management with proper env loading
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env from project root
ENV_FILE = Path(__file__).parent.parent.parent / '.env'
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
    logger.info(f"✅ Loaded environment from {ENV_FILE}")
else:
    logger.warning(f"⚠️ No .env file found at {ENV_FILE}")


class Settings:
    """Application settings - production-ready."""
    
    # API Configuration
    API_TITLE: str = "MediOrbit API"
    API_VERSION: str = "3.0"
    API_DESCRIPTION: str = "Medical Tourism Assistant - Production Ready"
    
    # CORS Configuration
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]
    
    # LLM Configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Default to Groq if available, else OpenAI
    LLM_PROVIDER: str = "groq" if GROQ_API_KEY else ("openai" if OPENAI_API_KEY else None)
    
    # Model Configuration
    GROQ_MODEL: str = "mixtral-8x7b-32768"
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    
    # LLM Parameters
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 256
    LLM_TIMEOUT: int = 30
    
    # Data Configuration
    HOSPITALS_CSV: Path = Path(__file__).parent.parent / "data" / "hospitals.csv"
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Server Configuration
    RELOAD: bool = os.getenv("RELOAD", "False").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Feature Flags
    ENABLE_OCR: bool = True
    ENABLE_NER: bool = True
    ENABLE_XRAY: bool = True
    ENABLE_MATCHING: bool = True
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration settings."""
        errors = []
        
        # Check LLM configuration
        if not cls.GROQ_API_KEY and not cls.OPENAI_API_KEY:
            errors.append("❌ Neither GROQ_API_KEY nor OPENAI_API_KEY is set")
        
        # Check if hospitals CSV exists
        if not cls.HOSPITALS_CSV.exists():
            errors.append(f"❌ Hospitals CSV not found at {cls.HOSPITALS_CSV}")
        
        if errors:
            for error in errors:
                logger.error(error)
            return False
        
        logger.info("✅ All configuration settings validated")
        return True
    
    @classmethod
    def get_active_provider(cls) -> str:
        """Get the active LLM provider."""
        if cls.LLM_PROVIDER == "groq":
            return "Groq (FREE)"
        elif cls.LLM_PROVIDER == "openai":
            return "OpenAI (GPT-3.5)"
        return "None (LLM disabled)"
    
    @classmethod
    def log_summary(cls):
        """Log configuration summary."""
        logger.info("=" * 60)
        logger.info("CONFIGURATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"API Version: {cls.API_VERSION}")
        logger.info(f"LLM Provider: {cls.get_active_provider()}")
        logger.info(f"Hospitals CSV: {cls.HOSPITALS_CSV}")
        logger.info(f"Server: {cls.HOST}:{cls.PORT}")
        logger.info(f"Log Level: {cls.LOG_LEVEL}")
        logger.info("=" * 60)


# Create settings instance
settings = Settings()
