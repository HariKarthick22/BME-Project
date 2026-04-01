"""
MedGemma Medical AI Service
Integrated medical text analysis using Google's MedGemma model
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class MedGemmaService:
    """Medical AI analysis using MedGemma model"""
    
    def __init__(self, model_path: Optional[str] = None, tokenizer_path: Optional[str] = None):
        """
        Initialize MedGemma service
        
        Args:
            model_path: Path to saved MedGemma model (default: ./models/medgemma/model)
            tokenizer_path: Path to saved tokenizer (default: ./models/medgemma/tokenizer)
        """
        self.model_path = model_path or os.getenv("MEDGEMMA_MODEL_PATH", "./models/medgemma/model")
        self.tokenizer_path = tokenizer_path or os.getenv("MEDGEMMA_TOKENIZER_PATH", "./models/medgemma/tokenizer")
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self._load_model()
    
    def _load_model(self):
        """Load MedGemma model and tokenizer"""
        try:
            if os.path.exists(self.tokenizer_path):
                logger.info("Loading MedGemma tokenizer from cache...")
                self.tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_path)
            else:
                logger.info("Downloading MedGemma tokenizer...")
                self.tokenizer = AutoTokenizer.from_pretrained("google/medgemma-2b")
                self.tokenizer.save_pretrained(self.tokenizer_path)
            
            if os.path.exists(self.model_path):
                logger.info("Loading MedGemma model from cache...")
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_path,
                    torch_dtype="auto",
                    device_map="auto"
                )
            else:
                logger.info("Downloading MedGemma model (this may take a few minutes)...")
                self.model = AutoModelForCausalLM.from_pretrained(
                    "google/medgemma-2b",
                    torch_dtype="auto",
                    device_map="auto"
                )
                self.model.save_pretrained(self.model_path)
            
            logger.info(f"MedGemma model loaded successfully on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load MedGemma model: {e}")
            raise
    
    def analyze(
        self,
        text: str,
        max_length: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> dict:
        """
        Analyze medical text using MedGemma
        
        Args:
            text: Medical text to analyze
            max_length: Maximum output length
            temperature: Sampling temperature (0.0-1.0)
            top_p: Nucleus sampling parameter
        
        Returns:
            dict with analysis results
        """
        if not self.model or not self.tokenizer:
            return {"error": "Model not loaded"}
        
        try:
            # Prepare prompt
            prompt = f"""You are a medical AI assistant. Analyze the following medical text and provide insights:

Medical Text: {text}

Analysis:"""
            
            # Tokenize input
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            
            # Generate response
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode response
            response_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract only the analysis part (remove input prompt)
            analysis = response_text.split("Analysis:")[-1].strip()
            
            return {
                "status": "success",
                "analysis": analysis,
                "model": "MedGemma-2B",
                "device": self.device
            }
        
        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            return {
                "status": "error",
                "error": str(e),
                "model": "MedGemma-2B"
            }
    
    def extract_medical_entities(self, text: str) -> dict:
        """
        Extract medical entities (symptoms, medications, conditions, etc.)
        
        Args:
            text: Medical text to analyze
        
        Returns:
            dict with extracted entities
        """
        if not self.model or not self.tokenizer:
            return {"error": "Model not loaded"}
        
        try:
            prompt = f"""Extract medical entities from this text. List them as:
- Symptoms:
- Medications:
- Diagnoses:
- Procedures:

Text: {text}

Entities:"""
            
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=256,
                    temperature=0.5,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            response_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            entities_section = response_text.split("Entities:")[-1].strip()
            
            return {
                "status": "success",
                "entities": entities_section,
                "model": "MedGemma-2B"
            }
        
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        return {
            "model_name": "MedGemma-2B",
            "model_path": self.model_path,
            "tokenizer_path": self.tokenizer_path,
            "device": self.device,
            "torch_dtype": str(self.model.dtype) if self.model else "unknown",
            "model_loaded": self.model is not None
        }
