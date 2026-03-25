"""Hugging Face transformers pipeline for medical NLP tasks."""
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MedicalNLPPipeline:
    """Manages medical NLP tasks using Hugging Face transformers."""

    def __init__(self):
        """Initialize NLP pipeline with lazy loading."""
        self.hf_token = os.getenv("HF_TOKEN")
        self.pipelines = {}
        self.cache = {}
        logger.info("MedicalNLPPipeline initialized (lazy loading enabled)")

    def _load_pipeline(self, task: str, model_id: str):
        """Lazy load a pipeline only when needed."""
        try:
            from transformers import pipeline as hf_pipeline

            if task not in self.pipelines:
                logger.info(f"Loading Hugging Face model: {model_id}")
                pipeline = hf_pipeline(
                    task,
                    model=model_id,
                    token=self.hf_token,
                    device=0 if self._has_cuda() else -1,  # GPU if available
                )
                self.pipelines[task] = pipeline
                logger.info(f"Pipeline '{task}' loaded successfully")
            return self.pipelines[task]
        except Exception as e:
            logger.error(f"Failed to load pipeline {task}: {e}")
            return None

    def _has_cuda(self) -> bool:
        """Check if CUDA is available."""
        try:
            import torch

            return torch.cuda.is_available()
        except:
            return False

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract medical entities from text using NER."""
        try:
            # Load NER pipeline
            pipeline = self._load_pipeline(
                "ner", "d4data/biomedical-ner-all"
            )
            if not pipeline:
                return {
                    "status": "error",
                    "message": "NER pipeline unavailable",
                    "entities": [],
                }

            # Run NER
            entities = pipeline(text)

            # Group entities by type
            grouped = self._group_entities(entities)

            return {
                "status": "success",
                "text": text,
                "entities": grouped,
                "raw_entities": entities,
            }
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "entities": [],
            }

    def analyze_medical_text(self, text: str) -> Dict[str, Any]:
        """Analyze medical text for conditions, symptoms, medications."""
        try:
            # Extract entities
            entity_results = self.extract_entities(text)

            if entity_results["status"] != "success":
                return entity_results

            # Categorize entities
            categorized = self._categorize_medical_entities(
                entity_results["raw_entities"]
            )

            return {
                "status": "success",
                "text": text,
                "analysis": categorized,
                "entities": entity_results["entities"],
            }
        except Exception as e:
            logger.error(f"Medical analysis failed: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    def _group_entities(self, entities: List[Dict]) -> Dict[str, List[str]]:
        """Group NER entities by entity type."""
        grouped = {}
        for entity in entities:
            entity_type = entity.get("entity", "UNKNOWN")
            # Remove B- and I- prefixes from entity type
            entity_type = entity_type.replace("B-", "").replace("I-", "")
            word = entity.get("word", "").strip()

            if entity_type not in grouped:
                grouped[entity_type] = []

            if word and word not in grouped[entity_type]:
                grouped[entity_type].append(word)

        return grouped

    def _categorize_medical_entities(
        self, entities: List[Dict]
    ) -> Dict[str, List[str]]:
        """Categorize extracted entities into medical categories."""
        categories = {
            "conditions": [],
            "procedures": [],
            "medications": [],
            "symptoms": [],
            "anatomy": [],
            "other": [],
        }

        # Simple rule-based categorization
        condition_keywords = [
            "disease",
            "disorder",
            "syndrome",
            "cancer",
            "diabetes",
            "hypertension",
            "arthritis",
        ]
        procedure_keywords = [
            "surgery",
            "operation",
            "biopsy",
            "scan",
            "test",
            "transplant",
            "bypass",
        ]
        medication_keywords = [
            "drug",
            "medication",
            "medicine",
            "antibiotic",
            "steroid",
            "aspirin",
        ]
        symptom_keywords = ["pain", "fever", "cough", "weakness", "fatigue"]
        anatomy_keywords = [
            "heart",
            "brain",
            "kidney",
            "liver",
            "lung",
            "bone",
            "muscle",
            "nerve",
        ]

        for entity in entities:
            entity_type = entity.get("entity", "").lower()
            word = entity.get("word", "").lower()

            # Check entity type first
            if "disease" in entity_type or "condition" in entity_type:
                categories["conditions"].append(word)
            elif "procedure" in entity_type or "operation" in entity_type:
                categories["procedures"].append(word)
            elif "medication" in entity_type or "drug" in entity_type:
                categories["medications"].append(word)
            elif "symptom" in entity_type:
                categories["symptoms"].append(word)
            elif "anatomy" in entity_type:
                categories["anatomy"].append(word)
            # Check keywords as fallback
            elif any(kw in word for kw in procedure_keywords):
                categories["procedures"].append(word)
            elif any(kw in word for kw in medication_keywords):
                categories["medications"].append(word)
            elif any(kw in word for kw in symptom_keywords):
                categories["symptoms"].append(word)
            elif any(kw in word for kw in anatomy_keywords):
                categories["anatomy"].append(word)
            else:
                categories["other"].append(word)

        # Remove empty categories and duplicates
        return {k: list(set(v)) for k, v in categories.items() if v}

    def summarize_medical_text(self, text: str, max_length: int = 150) -> str:
        """Summarize medical text (if available)."""
        try:
            pipeline = self._load_pipeline(
                "summarization", "facebook/bart-large-cnn"
            )
            if not pipeline:
                return text[:max_length]

            summary = pipeline(text, max_length=max_length, min_length=30)
            return summary[0]["summary_text"]
        except Exception as e:
            logger.warning(f"Summarization failed, returning original: {e}")
            return text[:max_length]

    def clear_cache(self):
        """Clear pipeline cache."""
        self.pipelines.clear()
        self.cache.clear()
        logger.info("Cache cleared")
