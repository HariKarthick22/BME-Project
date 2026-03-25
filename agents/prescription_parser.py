"""
PrescriptionParserAgent — OCR + HuggingFace Medical NER

Extracts structured medical data from prescription images using:
- OCR (pytesseract) for text extraction
- HuggingFace biomedical-ner-all for NER

Returns ExtractedData with diagnosis, procedures, medications, demographics.
"""

from __future__ import annotations
import os
from typing import Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("pytesseract or PIL not available. Install pytesseract separately.")

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    logger.warning("transformers not available. Install with: pip install transformers")


@dataclass
class ExtractedData:
    """Structured data extracted from prescription."""
    diagnoses: list[str]
    procedures: list[str]
    medications: list[str]
    demographics: dict
    raw_text: str
    confidence: float


class PrescriptionParserAgent:
    """
    Agent for parsing prescription images and extracting medical entities.
    
    Uses HuggingFace d4data/biomedical-ner-all model for biomedical NER.
    Falls back to basic extraction if OCR/NER not available.
    """
    
    MODEL_NAME = "d4data/biomedical-ner-all"
    
    def __init__(self):
        self._ner_pipeline = None
        self._initialized = False
    
    def _init_ner(self):
        """Lazy initialization of NER pipeline."""
        if self._initialized:
            return
            
        if HF_AVAILABLE:
            try:
                logger.info(f"Loading NER model: {self.MODEL_NAME}")
                self._ner_pipeline = pipeline(
                    "ner",
                    model=self.MODEL_NAME,
                    aggregation_strategy="simple",
                    device=-1  # CPU
                )
                self._initialized = True
                logger.info("NER model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load NER model: {e}")
                self._initialized = False
        else:
            logger.warning("HuggingFace not available. Using basic extraction.")
            self._initialized = True
    
    def extract_from_image(self, image_path: str) -> ExtractedData:
        """
        Extract medical data from prescription image.
        
        Parameters
        ----------
        image_path : str
            Path to prescription image file (JPG, PNG, etc.)
            
        Returns
        -------
        ExtractedData
            Structured extraction results
        """
        self._init_ner()
        
        if not OCR_AVAILABLE:
            return ExtractedData(
                diagnoses=[],
                procedures=[],
                medications=[],
                demographics={},
                raw_text="OCR not available. Please install pytesseract.",
                confidence=0.0
            )
        
        try:
            image = Image.open(image_path)
            raw_text = pytesseract.image_to_string(image)
        except Exception as e:
            logger.error(f"Failed to read image: {e}")
            return ExtractedData(
                diagnoses=[],
                procedures=[],
                medications=[],
                demographics={},
                raw_text=f"Error reading image: {str(e)}",
                confidence=0.0
            )
        
        return self._extract_entities(raw_text)
    
    def extract_from_text(self, text: str) -> ExtractedData:
        """
        Extract medical data from raw text.
        
        Parameters
        ----------
        text : str
            Raw prescription text
            
        Returns
        -------
        ExtractedData
            Structured extraction results
        """
        self._init_ner()
        return self._extract_entities(text)
    
    def _extract_entities(self, raw_text: str) -> ExtractedData:
        """Perform NER on raw text and extract structured data."""
        diagnoses = []
        procedures = []
        medications = []
        demographics = {}
        confidence = 0.0
        
        if not raw_text.strip():
            return ExtractedData(
                diagnoses=[],
                procedures=[],
                medications=[],
                demographics={},
                raw_text="",
                confidence=0.0
            )
        
        if self._ner_pipeline is not None:
            try:
                ner_results = self._ner_pipeline(raw_text)
                confidence = 0.8
                
                entity_map = {
                    "DISEASE": diagnoses,
                    "DISORDER": diagnoses,
                    "PROCEDURE": procedures,
                    "TREATMENT": procedures,
                    "DRUG": medications,
                    "MEDICATION": medications,
                    "CHEMICAL": medications,
                    "PERSON": demographics.setdefault("persons", []),
                    "AGE": demographics.setdefault("age", []),
                    "DATE": demographics.setdefault("dates", []),
                }
                
                for entity in ner_results:
                    label = entity.get("entity_group", "")
                    word = entity.get("word", "").strip()
                    
                    if word and label in entity_map:
                        if word not in entity_map[label]:
                            entity_map[label].append(word)
                            
            except Exception as e:
                logger.error(f"NER pipeline failed: {e}")
                confidence = 0.3
        else:
            confidence = 0.2
            diagnoses, procedures, medications = self._basic_extraction(raw_text)
        
        return ExtractedData(
            diagnoses=diagnoses,
            procedures=procedures,
            medications=medications,
            demographics=demographics,
            raw_text=raw_text,
            confidence=confidence
        )
    
    def _basic_extraction(self, text: str) -> tuple[list, list, list]:
        """
        Fallback basic extraction when NER is not available.
        Uses simple keyword matching.
        """
        text_lower = text.lower()
        
        disease_keywords = [
            "diabetes", "hypertension", "heart", "cancer", "asthma",
            "arthritis", "thyroid", "kidney", "liver", "infection"
        ]
        procedure_keywords = [
            "surgery", "mri", "ct scan", "x-ray", "biopsy",
            "dialysis", "chemotherapy", "radiation", "angioplasty"
        ]
        medication_keywords = [
            "aspirin", "metformin", "insulin", "amoxicillin",
            "paracetamol", "omeprazole", "atorvastatin", "losartan"
        ]
        
        diagnoses = [kw for kw in disease_keywords if kw in text_lower]
        procedures = [kw for kw in procedure_keywords if kw in text_lower]
        medications = [kw for kw in medication_keywords if kw in text_lower]
        
        return diagnoses, procedures, medications


def parse_prescription(image_path: str | None = None, text: str | None = None) -> ExtractedData:
    """
    Convenience function to parse prescription.
    
    Parameters
    ----------
    image_path : str, optional
        Path to prescription image
    text : str, optional
        Raw prescription text
        
    Returns
    -------
    ExtractedData
        Structured extraction results
    """
    agent = PrescriptionParserAgent()
    
    if image_path:
        return agent.extract_from_image(image_path)
    elif text:
        return agent.extract_from_text(text)
    else:
        raise ValueError("Either image_path or text must be provided")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python prescription_parser.py <image_path>")
        print("   or: python prescription_parser.py --text '<prescription text>'")
        sys.exit(1)
    
    if sys.argv[1] == "--text":
        result = parse_prescription(text=" ".join(sys.argv[2:]))
    else:
        result = parse_prescription(image_path=sys.argv[1])
    
    print(f"Diagnoses: {result.diagnoses}")
    print(f"Procedures: {result.procedures}")
    print(f"Medications: {result.medications}")
    print(f"Demographics: {result.demographics}")
    print(f"Confidence: {result.confidence:.2f}")