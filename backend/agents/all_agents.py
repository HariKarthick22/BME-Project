"""
backend/agents/all_agents.py
Complete ML agent pipeline for BME Medical Tourism Project
Optimized for Mac M2 + HP Laptop (Ollama local LLM)
Real data only - no synthetic responses
"""

import os
import io
import json
import csv
import logging
from pathlib import Path
from typing import Optional, List, Dict
from PIL import Image
import torch
from openai import OpenAI

logger = logging.getLogger(__name__)

# Load hospitals from CSV file
def load_hospitals_from_csv():
    """Load real hospital data from CSV file."""
    hospitals = []
    csv_path = Path(__file__).parent.parent / "data" / "hospitals.csv"
    
    if csv_path.exists():
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                hospitals.append({
                    "id": row['id'],
                    "name": row['name'],
                    "city": row['city'],
                    "state": row['state'],
                    "category": row['category'],
                    "specialties": [s.strip() for s in row['specialties'].split(',')],
                    "procedures": [p.strip() for p in row['procedures'].split(',')],
                    "cost_range": [int(row['min_price']), int(row['max_price'])],
                    "score": int(float(row['success_rate'])),
                    "accreditation": row['nabh_accredited'],
                    "insurance_schemes": [s.strip() for s in row['insurance_schemes'].split(',')],
                    "lead_doctors": row['lead_doctors'],
                    "phone": row['phone'],
                    "email": row['email'],
                    "latitude": float(row['lat']),
                    "longitude": float(row['lng']),
                })
        logger.info(f"✅ Loaded {len(hospitals)} hospitals from CSV")
    else:
        logger.warning(f"⚠️ CSV not found at {csv_path}")
    
    return hospitals

# ─────────────────────────────────────────────
# 1. MEDICAL NER AGENT
# Model: d4data/biomedical-ner-all (420MB)
# ─────────────────────────────────────────────
class MedicalNERAgent:
    """Extract medical entities from text."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def _load(self):
        if self._loaded:
            return
        from transformers import pipeline
        print("⏳ Loading Medical NER…")
        self.ner = pipeline(
            "ner",
            model="d4data/biomedical-ner-all",
            tokenizer="d4data/biomedical-ner-all",
            aggregation_strategy="max",
            device=-1,
        )
        self._loaded = True
        print("✅ Medical NER loaded")

    def extract(self, text: str) -> dict:
        """Extract medical entities - REAL data only."""
        self._load()
        if not text or len(text.strip()) < 3:
            return {"diseases": [], "medications": [], "procedures": [], "anatomy": [], "symptoms": []}
        
        raw = self.ner(text[:512])

        result = {
            "diseases": [],
            "medications": [],
            "procedures": [],
            "anatomy": [],
            "symptoms": []
        }
        
        mapping = {
            "Disease_disorder": "diseases",
            "Medication": "medications",
            "Therapeutic_procedure": "procedures",
            "Anatomical_structure": "anatomy",
            "Sign_symptom": "symptoms",
        }

        seen = set()
        for ent in raw:
            cat = mapping.get(ent.get("entity_group", ""))
            word = ent["word"].strip()
            if cat and word not in seen and len(word) > 2:
                seen.add(word)
                result[cat].append({
                    "text": word,
                    "confidence": round(ent["score"], 3)
                })

        return result


# ─────────────────────────────────────────────
# 2. DOCUMENT OCR AGENT
# ─────────────────────────────────────────────
class DocumentOCRAgent:
    """Process medical documents via OCR."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def _load(self):
        if self._loaded:
            return
        try:
            import easyocr
            print("⏳ Loading EasyOCR…")
            self.reader = easyocr.Reader(["en"], gpu=False, verbose=False)
            self._loaded = True
            print("✅ OCR loaded")
        except ImportError:
            print("⚠️ EasyOCR not installed")
            self._loaded = False

    def process_bytes(self, data: bytes, mime: str) -> str:
        """Process image/PDF and extract text."""
        self._load()
        if not self._loaded:
            return "[OCR not available]"

        try:
            if mime == "application/pdf":
                return self._process_pdf(data)
            
            img = Image.open(io.BytesIO(data)).convert("RGB")
            results = self.reader.readtext(img, detail=0, paragraph=True)
            text = " ".join(results)
            return text if text.strip() else "[No text in image]"
        except Exception as e:
            return f"[OCR Error: {str(e)}]"

    def _process_pdf(self, data: bytes) -> str:
        """Extract text from PDF."""
        try:
            import pdf2image
            images = pdf2image.convert_from_bytes(data, dpi=200, first_page=1, last_page=3)
            parts = []
            for img in images:
                res = self.reader.readtext(img, detail=0, paragraph=True)
                parts.extend(res)
            text = " ".join(parts)
            return text if text.strip() else "[No text in PDF]"
        except ImportError:
            return "[PDF requires: pip install pdf2image]"


# ─────────────────────────────────────────────
# 3. X-RAY ANALYSIS AGENT
# ─────────────────────────────────────────────
class XRayAgent:
    """Analyze medical X-ray images."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def _load(self):
        if self._loaded:
            return
        try:
            from transformers import AutoFeatureExtractor, AutoModelForImageClassification
            print("⏳ Loading X-Ray model…")
            model_id = "nickmuchi/vit-finetuned-chest-xray-pneumonia"
            self.extractor = AutoFeatureExtractor.from_pretrained(model_id)
            self.model = AutoModelForImageClassification.from_pretrained(model_id)
            self.model.eval()
            self._loaded = True
            print("✅ X-Ray model loaded")
        except Exception as e:
            print(f"⚠️ X-Ray load failed: {e}")
            self._loaded = False

    def analyze(self, image_bytes: bytes) -> dict:
        """Analyze X-ray image."""
        self._load()
        if not self._loaded:
            return {"error": "X-Ray unavailable"}
        
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            inputs = self.extractor(images=image, return_tensors="pt")

            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.nn.functional.softmax(outputs.logits, dim=-1)[0]

            predicted_idx = probs.argmax().item()
            label = self.model.config.id2label[predicted_idx]
            confidence = probs[predicted_idx].item()

            return {
                "primary_finding": label,
                "confidence_pct": round(confidence * 100, 1),
                "recommendation": self._recommend(label, confidence),
                "specialist": self._specialist(label),
            }
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

    def _recommend(self, label: str, conf: float) -> str:
        label_up = label.upper()
        if "PNEUMONIA" in label_up and conf > 0.7:
            return "URGENT: Pulmonology consultation. Possible pneumonia detected."
        elif "NORMAL" in label_up and conf > 0.75:
            return "Normal. Continue routine monitoring."
        elif conf < 0.55:
            return "Inconclusive. Consult radiologist for detailed review."
        return f"Possible finding: {label}. Specialist consultation recommended."

    def _specialist(self, label: str) -> str:
        label_up = label.upper()
        if any(x in label_up for x in ["PNEUMONIA", "EFFUSION"]):
            return "Pulmonologist"
        elif "CARDIOMEGALY" in label_up:
            return "Cardiologist"
        elif "NODULE" in label_up or "MASS" in label_up:
            return "Oncologist"
        return "General Physician"


# ─────────────────────────────────────────────
# 4. CONVERSATION AGENT (OpenAI GPT-3.5)
# ─────────────────────────────────────────────
MEDICAL_SYSTEM_PROMPT = """You are MediOrbit AI, an expert medical tourism assistant for Tamil Nadu.

YOUR ROLE:
- Help patients find best hospitals for their medical needs
- Extract and understand medical conditions
- Recommend hospitals based on specialty, location, budget
- Explain medical info in simple language
- NEVER attempt diagnosis - suggest specialists only

HOSPITALS (Real database):
- Apollo Hospitals, Chennai - Cardiology, Oncology, Neurology - ₹3-15L - 96%
- GKNM Hospital, Coimbatore - Orthopedics, Cardiac - ₹2-8L - 94%
- KMCH, Coimbatore - Cardiac, Neuro, Ortho - ₹2-9L - 93%
- PSG Hospitals, Coimbatore - Multi-specialty - ₹1.5-10L - 91%
- CMC Vellore - All specialties - ₹1-20L - 98% (top)
- Aravind Eye, Madurai - Ophthalmology - ₹20K-2L - 97%

RULES:
1. Ask clarifying questions about symptoms
2. Confirm understanding before recommending
3. Match hospital specialty to condition
4. Mention costs and accreditation honestly
5. Never diagnose - use "may indicate", "could suggest"
6. Recommend 3-5 hospitals max
7. Be warm and empathetic"""

class ConversationAgent:
    """Chat with OpenAI or Groq - FAST & RELIABLE."""
    
    def __init__(self, api_key: Optional[str] = None, use_groq: bool = False):
        self.use_groq = use_groq or bool(os.getenv("GROQ_API_KEY"))
        self.history: List[Dict] = []
        
        if self.use_groq:
            # Use Groq (free, super fast)
            try:
                from groq import Groq
                self.api_key = os.getenv("GROQ_API_KEY")
                if not self.api_key:
                    raise ValueError("❌ GROQ_API_KEY not set. Export it: export GROQ_API_KEY='gsk-...'")
                self.client = Groq(api_key=self.api_key)
                self.model = "mixtral-8x7b-32768"
                self.provider = "Groq"
            except ImportError:
                raise ImportError("Groq not installed. Install: pip install groq")
        else:
            # Use OpenAI (default)
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("❌ OPENAI_API_KEY not set. Export it: export OPENAI_API_KEY='sk-...'")
            self.client = OpenAI(api_key=self.api_key)
            self.model = "gpt-3.5-turbo"
            self.provider = "OpenAI"

    def chat(self, user_message: str, medical_context: Optional[dict] = None) -> str:
        """Chat with OpenAI or Groq - INSTANT responses."""
        augmented_message = user_message
        if medical_context and any(medical_context.values()):
            ctx_parts = []
            if medical_context.get("diseases"):
                ctx_parts.append(f"Conditions: {[d['text'] for d in medical_context['diseases']]}")
            if medical_context.get("medications"):
                ctx_parts.append(f"Meds: {[m['text'] for m in medical_context['medications']]}")
            if medical_context.get("symptoms"):
                ctx_parts.append(f"Symptoms: {[s['text'] for s in medical_context['symptoms']]}")
            
            if ctx_parts:
                augmented_message = f"{user_message}\n\n[Context: {' | '.join(ctx_parts)}]"

        self.history.append({"role": "user", "content": augmented_message})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": MEDICAL_SYSTEM_PROMPT},
                    *self.history[-5:]  # Keep last 5 messages for context
                ],
                temperature=0.3,
                max_tokens=256,
                timeout=10 if not self.use_groq else 30
            )

            reply = response.choices[0].message.content
            self.history.append({"role": "assistant", "content": reply})
            return reply

        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "authentication" in error_msg.lower():
                key_var = "GROQ_API_KEY" if self.use_groq else "OPENAI_API_KEY"
                return f"❌ Invalid {self.provider} API key. Set {key_var} environment variable."
            elif "rate_limit" in error_msg.lower():
                return f"⚠️ {self.provider} rate limit. Please wait and try again."
            elif "timeout" in error_msg.lower():
                return "⚠️ Request timeout. Please try again."
            else:
                return f"⚠️ {self.provider} Error: {error_msg}"

    def reset(self):
        self.history = []


# ─────────────────────────────────────────────
# 5. HOSPITAL MATCHER AGENT
# ─────────────────────────────────────────────
class HospitalMatcherAgent:
    """Match hospitals based on conditions using real CSV data."""
    
    def __init__(self):
        self.hospitals = load_hospitals_from_csv()

    def match(self, conditions: List[str], specialty: Optional[str] = None, city: Optional[str] = None, 
              max_budget: Optional[float] = None, limit: int = 5) -> List[dict]:
        """Find matching hospitals."""
        candidates = self.hospitals

        if city:
            candidates = [h for h in candidates if city.lower() in h["city"].lower()]

        if max_budget:
            candidates = [h for h in candidates if h["cost_range"][0] <= max_budget]

        scored = []
        for hospital in candidates:
            score = hospital["score"]
            
            if specialty:
                if any(specialty.lower() in s.lower() for s in hospital["specialties"]):
                    score += 5
            
            if conditions:
                for cond in conditions:
                    if any(cond.lower() in s.lower() for s in hospital["specialties"]):
                        score += 3

            scored.append({**hospital, "match_score": min(score, 100)})

        scored.sort(key=lambda x: x["match_score"], reverse=True)
        return scored[:limit]
