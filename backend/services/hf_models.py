"""Hugging Face model management for medical NLP."""
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class HFModelManager:
    """Manages Hugging Face model interactions for medical NLP tasks."""

    # Tier-1 Recommended Models from research
    RECOMMENDED_MODELS = {
        "distilbert-medical": {
            "id": "distilbert-base-uncased-finetuned-medical-notes-extraction",
            "task": "named-entity-recognition",
            "description": "Optimized for medical entity extraction",
        },
        "clinical-bert": {
            "id": "emilyalsentzer/clinicalBERT",
            "task": "medical-document-analysis",
            "description": "Pre-trained on clinical notes",
        },
        "biobert": {
            "id": "dmis-lab/biobert-v1.1",
            "task": "biomedical-nlp",
            "description": "Fine-tuned on biomedical literature",
        },
        "sciBERT": {
            "id": "allenai/scibert-scivocab-uncased",
            "task": "scientific-nlp",
            "description": "Pre-trained on scientific papers",
        },
    }

    def __init__(self):
        """Initialize HF model manager."""
        self.hf_token = os.getenv("HF_TOKEN")
        self.models_cache = {}
        logger.info("HFModelManager initialized with %d recommended models", 
                    len(self.RECOMMENDED_MODELS))

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get model information from Hugging Face."""
        if model_name in self.models_cache:
            return self.models_cache[model_name]

        # Return cached info for recommended models
        if model_name in self.RECOMMENDED_MODELS:
            info = {
                "model_id": self.RECOMMENDED_MODELS[model_name]["id"],
                "type": "medical-nlp",
                "recommended": True,
                **self.RECOMMENDED_MODELS[model_name],
            }
            self.models_cache[model_name] = info
            return info

        return None

    def get_recommended_models(self) -> List[str]:
        """Get list of all recommended model names."""
        return list(self.RECOMMENDED_MODELS.keys())

    def validate_model(self, model_name: str) -> bool:
        """Validate if model is available and suitable."""
        return model_name in self.RECOMMENDED_MODELS or model_name in self.models_cache
