"""
MediOrbit / CarePath AI — Unified FastAPI Application

Single-file entry point.  All agents, services, routes, and utilities are
inlined so the project runs with:

    uvicorn main:app --reload          # development
    gunicorn -c gunicorn_config.py main:app   # production

Bugs fixed vs. original multi-file layout:
  1. Missing ``agents/`` module — conversation_agent and prescription_parser
     are now implemented inline.
  2. ``check_ollama()`` was called before its definition (line 147).
  3. ``AutoFeatureExtractor`` deprecated in transformers ≥ 4.35 — replaced
     with ``AutoImageProcessor``.
  4. ``MedicalAnalysisRequest`` required a ``request_type`` field that the
     route never supplied — split into two models.
  5. ``slowapi`` missing from requirements.txt — added.
  6. ``requests`` missing from requirements.txt — added.
  7. Relative imports (``from .models …``) break when running ``python main.py``
     directly — all imports are now absolute or deferred.
"""

from __future__ import annotations

# ── stdlib ────────────────────────────────────────────────────────────────────
import asyncio
import base64
import csv
import html
import io
import json
import logging
import os
import re
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from threading import Semaphore
from typing import Any, Dict, List, Literal, Optional, Tuple

# ── third-party ───────────────────────────────────────────────────────────────
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict, field_validator

# ── .env ──────────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent / ".env")

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================================================== #
#  1.  DATABASE LAYER                                                          #
# =========================================================================== #

DB_PATH = Path(__file__).parent / "data" / "hospitals.db"
CSV_PATH = Path(__file__).parent / "data" / "hospitals.csv"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    try:
        _create_tables(conn)
        _seed_if_empty(conn)
        conn.commit()
    finally:
        conn.close()


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS hospitals (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            city            TEXT,
            state           TEXT DEFAULT 'Tamil Nadu',
            specialties     TEXT DEFAULT '[]',
            procedures      TEXT DEFAULT '[]',
            min_price       INTEGER DEFAULT 0,
            max_price       INTEGER DEFAULT 0,
            ai_score        REAL DEFAULT 0.0,
            insurance       TEXT DEFAULT '[]',
            accreditations  TEXT DEFAULT '[]',
            phone           TEXT DEFAULT '',
            email           TEXT DEFAULT '',
            image_url       TEXT DEFAULT '',
            lat             REAL DEFAULT 0.0,
            lng             REAL DEFAULT 0.0,
            success_rate    REAL DEFAULT 0.0,
            timeline_days   INTEGER DEFAULT 0,
            doctor_count    INTEGER DEFAULT 0,
            review_count    INTEGER DEFAULT 0,
            avg_rating      REAL DEFAULT 0.0,
            doctors         TEXT DEFAULT '[]',
            reviews         TEXT DEFAULT '[]',
            cost_breakdown  TEXT DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            role        TEXT CHECK(role IN ('user', 'assistant')),
            content     TEXT,
            timestamp   TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
        CREATE TABLE IF NOT EXISTS extractions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      TEXT NOT NULL,
            diagnosis       TEXT DEFAULT '[]',
            procedure       TEXT DEFAULT '[]',
            medications     TEXT DEFAULT '[]',
            patient_age     INTEGER,
            patient_gender  TEXT,
            raw_text        TEXT DEFAULT '',
            created_at      TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_ext_session ON extractions(session_id);
    """)


def _seed_if_empty(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) FROM hospitals").fetchone()[0]
    if count > 0:
        return
    if CSV_PATH.exists():
        _seed_from_csv(conn)
    else:
        logger.warning("CSV file not found at %s. Hospital table seeded but empty.", CSV_PATH)


def _seed_from_csv(conn: sqlite3.Connection) -> None:
    try:
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                specialties = [s.strip() for s in row.get("specialties", "").split(",") if s.strip()]
                procedures = [p.strip() for p in row.get("procedures", "").split(",") if s.strip()]
                insurance = [i.strip() for i in row.get("insurance_schemes", "").split(",") if i.strip()]
                try:
                    min_price = int(row.get("min_price", 0))
                    max_price = int(row.get("max_price", 0))
                except (ValueError, TypeError):
                    min_price, max_price = 0, 0
                try:
                    success_rate = float(row.get("success_rate", 0))
                except (ValueError, TypeError):
                    success_rate = 0.0
                try:
                    lat = float(row.get("lat", 0.0))
                    lng = float(row.get("lng", 0.0))
                except (ValueError, TypeError):
                    lat, lng = 0.0, 0.0

                conn.execute(
                    """INSERT OR IGNORE INTO hospitals
                       (id, name, city, state, specialties, procedures, min_price, max_price,
                        ai_score, insurance, accreditations, phone, email,
                        lat, lng, success_rate, doctor_count)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        row.get("id"),
                        row.get("name"),
                        row.get("city"),
                        row.get("state", "Tamil Nadu"),
                        json.dumps(specialties),
                        json.dumps(procedures),
                        min_price,
                        max_price,
                        85.0,
                        json.dumps(insurance),
                        json.dumps([row.get("nabh_accredited", "No")]) if row.get("nabh_accredited") == "Yes" else json.dumps([]),
                        row.get("phone", ""),
                        row.get("email", ""),
                        lat,
                        lng,
                        success_rate,
                        10,
                    ),
                )
        conn.commit()
        hospital_count = conn.execute("SELECT COUNT(*) FROM hospitals").fetchone()[0]
        logger.info("Successfully seeded %d hospitals from CSV", hospital_count)
    except Exception as e:
        logger.error("Error seeding hospitals from CSV: %s", e)
        raise


def row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    json_cols = {"specialties", "procedures", "insurance", "accreditations",
                 "doctors", "reviews", "cost_breakdown"}
    for col in json_cols:
        if col in d and isinstance(d[col], str):
            try:
                d[col] = json.loads(d[col])
            except (json.JSONDecodeError, TypeError):
                d[col] = []
    return d


def save_conversation_turn(session_id: str, role: str, content: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        conn.commit()
    finally:
        conn.close()


def get_conversation_history(session_id: str, limit: int = 20) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    finally:
        conn.close()


def save_extraction(session_id: str, extraction: dict) -> None:
    conn = get_connection()
    try:
        patient = extraction.get("patient", {})
        conn.execute(
            """INSERT INTO extractions
               (session_id, diagnosis, procedure, medications, patient_age, patient_gender, raw_text)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                json.dumps(extraction.get("diagnosis", [])),
                json.dumps(extraction.get("procedure", [])),
                json.dumps(extraction.get("medications", [])),
                patient.get("age") if isinstance(patient, dict) else None,
                patient.get("gender") if isinstance(patient, dict) else None,
                extraction.get("raw_text", ""),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_latest_extraction(session_id: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM extractions WHERE session_id = ? ORDER BY id DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        for col in ("diagnosis", "procedure", "medications"):
            if isinstance(d.get(col), str):
                try:
                    d[col] = json.loads(d[col])
                except (json.JSONDecodeError, TypeError):
                    d[col] = []
        return d
    finally:
        conn.close()


def get_available_cities() -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT city FROM hospitals WHERE city IS NOT NULL ORDER BY city"
        ).fetchall()
        return [row[0] for row in rows]
    finally:
        conn.close()


def query_hospitals_by_specialty(specialty: str) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM hospitals WHERE specialties LIKE ? OR procedures LIKE ? ORDER BY success_rate DESC, avg_rating DESC",
            (f"%{specialty}%", f"%{specialty}%"),
        ).fetchall()
        return [row_to_dict(row) for row in rows]
    finally:
        conn.close()

# =========================================================================== #
#  2.  PYDANTIC SCHEMAS                                                        #
# =========================================================================== #

class DoctorProfile(BaseModel):
    name: str
    specialty: str
    experience_years: int
    qualification: str


class PatientReview(BaseModel):
    patient_name: str
    condition: str
    outcome: str
    rating: float
    date: str


class CostBreakdown(BaseModel):
    item: str
    cost: int


class Hospital(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    city: str
    state: str = "Tamil Nadu"
    specialties: list[str] = []
    procedures: list[str] = []
    min_price: int = 0
    max_price: int = 0
    ai_score: float = 0.0
    match_score: float | None = None
    match_reasons: list[str] = []
    insurance: list[str] = []
    accreditations: list[str] = []
    phone: str = ""
    email: str = ""
    image_url: str = ""
    lat: float = 0.0
    lng: float = 0.0
    success_rate: float = 0.0
    timeline_days: int = 0
    doctor_count: int = 0
    review_count: int = 0
    avg_rating: float = 0.0
    doctors: list[DoctorProfile] = []
    reviews: list[PatientReview] = []
    cost_breakdown: list[CostBreakdown] = []


class SearchIntent(BaseModel):
    procedure: str | None = None
    specialty: str | None = None
    city: str | None = None
    budget_max: int | None = None
    insurance_type: str | None = None
    raw_query: str = ""


class PatientInfo(BaseModel):
    age: int | None = None
    gender: str | None = None


class ExtractionResult(BaseModel):
    diagnosis: list[str] = []
    procedure: list[str] = []
    medications: list[str] = []
    patient: PatientInfo = Field(default_factory=PatientInfo)
    raw_text: str = ""


UIActionType = Literal["navigate", "highlight", "apply_filter", "open_detail", "show_comparison", "clear_highlight"]


class UIAction(BaseModel):
    type: UIActionType
    payload: dict[str, Any] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str
    prescription_data: ExtractionResult | None = None


class ChatResponse(BaseModel):
    session_id: str
    text: str
    actions: list[UIAction] = []
    hospitals: list[Hospital] = []


class PrescriptionParseResponse(BaseModel):
    session_id: str
    extraction: ExtractionResult
    summary: str


class StreamChatRequest(BaseModel):
    session_id: str
    message: str

# =========================================================================== #
#  3.  PROMPTS                                                                 #
# =========================================================================== #

SYSTEM_PROMPT = """You are 'CarePath AI,' a compassionate, professional healthcare caretaker and medical tourism guide. Your goal is to assist users in navigating their health journey with empathy and precision.

Operational Guidelines:

1. Use a warm, validating tone; escalate urgency if needed.
   - For general queries: empathetic and reassuring.
   - For emergency indicators (chest pain, difficulty breathing, severe bleeding, suspected stroke/heart attack): URGENT tone, instruct user to call emergency services immediately.

2. Analyze X-rays and reports -> provide AI summary (NOT diagnosis).
   - State clearly: "This is an AI-driven summary for informational purposes only. It is NOT a clinical diagnosis."
   - Always end image/report analysis with: "Please consult a board-certified radiologist for a clinical evaluation."

3. Retrieve hospitals via CSV (problem + city matching).
   - Extract the medical condition and city from the user query.
   - Rank by specialty match first, then rating, then city proximity.
   - Show top 3-5 options with brief summaries.

4. NEVER give a definitive diagnosis.
   NEVER recommend stopping medications or treatments.
   ALWAYS end clinical summaries with: "Please consult a board-certified professional for a clinical evaluation."

5. Use web search when real-time health data, travel regulations, or current hospital information is required.

6. Cultural Sensitivity: Tamil Nadu has strong Ayurveda and Siddha traditions. Acknowledge integrative medicine options where relevant."""

MEDICAL_DISCLAIMER = "\n\n**Important:** This is an AI-driven summary for informational purposes only. It is NOT a clinical diagnosis. Please consult a board-certified healthcare professional for medical evaluation and treatment recommendations."

EMERGENCY_KEYWORDS = [
    "chest pain", "difficulty breathing", "severe bleeding", "loss of consciousness",
    "sudden vision loss", "severe allergic reaction", "poisoning", "overdose",
    "severe head injury", "uncontrolled bleeding", "signs of stroke", "suspected heart attack",
]

# =========================================================================== #
#  4.  SANITIZER                                                               #
# =========================================================================== #

def sanitize_string(v: Any) -> str:
    if not isinstance(v, str):
        raise TypeError("String required")
    v = html.escape(v)
    v = v.strip()
    if len(v) > 10000:
        raise ValueError("String too long (max 10000 chars)")
    return v


class SanitizedTextInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)

    @field_validator("text", mode="before")
    @classmethod
    def sanitize(cls, v: Any) -> str:
        return sanitize_string(v)


class MedicalAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)

    @field_validator("text", mode="before")
    @classmethod
    def sanitize(cls, v: Any) -> str:
        return sanitize_string(v)

# =========================================================================== #
#  5.  OLLAMA SERVICE                                                          #
# =========================================================================== #

OLLAMA_BASE = "http://localhost:11434"
MEDGEMMA_MODEL = "dcarrascosa/medgemma-1.5-4b-it:Q4_K_M"
FALLBACK_MODEL = "llama3.2:3b"
OLLAMA_TIMEOUT = 120


async def _available_models() -> list[str]:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


async def _pick_model() -> str | None:
    available = await _available_models()
    for candidate in (MEDGEMMA_MODEL, FALLBACK_MODEL):
        base = candidate.split(":")[0]
        if any(base in m for m in available):
            return candidate
    return None


async def chat_with_medgemma(
    messages: list[dict],
    system_prompt: str = SYSTEM_PROMPT,
) -> str:
    import httpx
    model = await _pick_model()
    if model is None:
        return "CarePath AI: local model not available. Run: ollama pull medgemma:4b-it" + MEDICAL_DISCLAIMER

    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}, *messages],
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 512, "num_ctx": 4096},
    }
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            r = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"]
    except httpx.TimeoutException:
        raise TimeoutError("Model inference timed out. Try again.")
    except Exception as e:
        logger.error("Ollama chat error: %s", e)
        raise


async def stream_chat_with_medgemma(
    messages: list[dict],
    system_prompt: str = SYSTEM_PROMPT,
):
    import httpx
    model = await _pick_model()
    if model is None:
        yield "Local model not available. Run: ollama pull medgemma:4b-it"
        return

    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}, *messages],
        "stream": True,
        "options": {"temperature": 0.3, "num_predict": 512, "num_ctx": 4096},
    }
    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
        async with client.stream("POST", f"{OLLAMA_BASE}/api/chat", json=payload) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    text = chunk.get("message", {}).get("content", "")
                    if text:
                        yield text
                    if chunk.get("done"):
                        break
                except json.JSONDecodeError:
                    continue


async def analyze_xray_image(image_bytes: bytes, filename: str = "xray.jpg") -> dict:
    model = await _pick_model()
    if model and "medgemma" in model:
        return await _analyze_with_medgemma(image_bytes, model)
    logger.warning("MedGemma unavailable for X-ray - using ViT fallback")
    return await _analyze_xray_vit_fallback(image_bytes)


async def _analyze_with_medgemma(image_bytes: bytes, model: str) -> dict:
    import httpx
    b64 = base64.b64encode(image_bytes).decode()
    prompt = (
        "Describe key findings visible in this X-ray in 2-3 sentences. "
        "Do NOT provide a diagnosis. Describe observable findings only."
    )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt, "images": [b64]}],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 256},
    }
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            r = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload)
            r.raise_for_status()
            findings = r.json()["message"]["content"]
    except Exception as e:
        logger.error("MedGemma X-ray failed: %s - falling back to ViT", e)
        return await _analyze_xray_vit_fallback(image_bytes)

    return {
        "summary": f"AI X-ray Analysis: {findings}{MEDICAL_DISCLAIMER}",
        "findings": findings,
        "disclaimer": MEDICAL_DISCLAIMER.strip(),
        "model_used": model,
    }


async def _analyze_xray_vit_fallback(image_bytes: bytes) -> dict:
    try:
        from PIL import Image
        import torch
        from transformers import AutoImageProcessor, AutoModelForImageClassification

        model_id = "nickmuchi/vit-finetuned-chest-xray-pneumonia"
        processor = AutoImageProcessor.from_pretrained(model_id)
        clf_model = AutoModelForImageClassification.from_pretrained(model_id)

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        inputs = processor(images=image, return_tensors="pt")

        with torch.inference_mode():
            logits = clf_model(**inputs).logits
            probs = torch.nn.functional.softmax(logits, dim=-1)[0]

        idx = int(probs.argmax())
        label = clf_model.config.id2label[idx]
        confidence = round(float(probs[idx]) * 100, 1)
        findings = f"Possible finding: {label} (confidence {confidence}%)"
    except Exception as e:
        logger.error("ViT fallback error: %s", e)
        findings = "Unable to analyze image automatically."

    return {
        "summary": f"AI X-ray Analysis: {findings}{MEDICAL_DISCLAIMER}",
        "findings": findings,
        "disclaimer": MEDICAL_DISCLAIMER.strip(),
        "model_used": "vit-chest-xray-fallback",
    }

# =========================================================================== #
#  6.  MEDICAL NLP PIPELINE                                                    #
# =========================================================================== #

class MedicalNLPPipeline:
    def __init__(self):
        self.hf_token = os.getenv("HF_TOKEN")
        self.pipelines: dict[str, Any] = {}

    def _load_pipeline(self, task: str, model_id: str):
        try:
            from transformers import pipeline as hf_pipeline
            if task not in self.pipelines:
                logger.info("Loading Hugging Face model: %s", model_id)
                device = 0 if self._has_cuda() else -1
                pipeline = hf_pipeline(task, model=model_id, token=self.hf_token, device=device)
                self.pipelines[task] = pipeline
                logger.info("Pipeline '%s' loaded successfully", task)
            return self.pipelines[task]
        except Exception as e:
            logger.error("Failed to load pipeline %s: %s", task, e)
            return None

    @staticmethod
    def _has_cuda() -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except Exception:
            return False

    def extract_entities(self, text: str) -> Dict[str, Any]:
        try:
            pipeline = self._load_pipeline("ner", "d4data/biomedical-ner-all")
            if not pipeline:
                return {"status": "error", "message": "NER pipeline unavailable", "entities": []}
            entities = pipeline(text)
            grouped = self._group_entities(entities)
            return {"status": "success", "text": text, "entities": grouped, "raw_entities": entities}
        except Exception as e:
            logger.error("Entity extraction failed: %s", e)
            return {"status": "error", "message": str(e), "entities": []}

    def analyze_medical_text(self, text: str) -> Dict[str, Any]:
        try:
            entity_results = self.extract_entities(text)
            if entity_results["status"] != "success":
                return entity_results
            categorized = self._categorize_medical_entities(entity_results["raw_entities"])
            return {"status": "success", "text": text, "analysis": categorized, "entities": entity_results["entities"]}
        except Exception as e:
            logger.error("Medical analysis failed: %s", e)
            return {"status": "error", "message": str(e)}

    @staticmethod
    def _group_entities(entities: List[Dict]) -> Dict[str, List[str]]:
        grouped: dict[str, list[str]] = {}
        for entity in entities:
            entity_type = entity.get("entity", "UNKNOWN").replace("B-", "").replace("I-", "")
            word = entity.get("word", "").strip()
            if entity_type not in grouped:
                grouped[entity_type] = []
            if word and word not in grouped[entity_type]:
                grouped[entity_type].append(word)
        return grouped

    @staticmethod
    def _categorize_medical_entities(entities: List[Dict]) -> Dict[str, List[str]]:
        categories = {"conditions": [], "procedures": [], "medications": [], "symptoms": [], "anatomy": [], "other": []}
        for entity in entities:
            entity_type = entity.get("entity", "").lower()
            word = entity.get("word", "").lower()
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
            else:
                categories["other"].append(word)
        return {k: list(set(v)) for k, v in categories.items() if v}

# =========================================================================== #
#  7.  MEDICAL ASSISTANT (Anthropic Claude)                                    #
# =========================================================================== #

class MedicalAssistant:
    SYSTEM_PROMPT = """You are an expert medical tourism consultant specializing in hospitals and healthcare in Tamil Nadu, India.
Your role is to:
1. Understand patient's medical needs, conditions, and budget
2. Recommend appropriate hospitals based on their requirements
3. Explain procedures, success rates, and costs clearly
4. Provide compassionate, professional medical tourism guidance
5. Always emphasize consulting with physicians for medical decisions

Key guidelines:
- Be empathetic and professional
- Provide evidence-based recommendations
- Consider cost, quality, and convenience
- Never provide medical diagnosis or treatment advice
- Always recommend verified medical professionals
- Maintain patient privacy and confidentiality"""

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model_id = os.getenv("CLAUDE_MODEL_ID", "claude-3-5-haiku-20241022")
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
            logger.info("Anthropic client initialized successfully")
        except Exception as e:
            logger.warning("Could not initialize Anthropic client: %s", e)
            self.client = None

    def analyze_medical_condition(self, condition: str, age: Optional[int] = None, budget: Optional[float] = None) -> Dict[str, Any]:
        if not self.client:
            return {"status": "error", "message": "Anthropic client not available"}
        try:
            prompt = f"I need information about {condition}"
            if age:
                prompt += f" for a {age}-year-old patient"
            if budget:
                prompt += f" with a budget of INR {budget:.0f}"
            prompt += """. Please provide:
1. Overview of the condition
2. Treatment options available in Tamil Nadu
3. Expected cost range
4. Recovery timeline
5. Recommended hospitals/specializations

Keep response professional but easy to understand."""
            response = self.client.messages.create(
                model=self.model_id, max_tokens=1000, system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return {
                "status": "success", "analysis": response.content[0].text, "condition": condition,
                "metadata": {"model": self.model_id, "usage": {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}},
            }
        except Exception as e:
            logger.error("Medical analysis failed: %s", e)
            return {"status": "error", "message": str(e)}

    def recommend_hospitals(self, condition: str, location: str = "Tamil Nadu") -> Dict[str, Any]:
        if not self.client:
            return {"status": "error", "message": "Anthropic client not available"}
        try:
            prompt = f"""Based on the following medical condition, provide hospital recommendations in {location}:

Condition: {condition}

Please recommend 3-5 hospitals in {location} that are well-suited for treating this condition. Include:
1. Hospital name
2. Specialization relevant to the condition
3. Estimated cost range (in INR)
4. Key strengths/accreditations
5. Why it's recommended for this condition

Format as a structured list."""
            response = self.client.messages.create(
                model=self.model_id, max_tokens=1500, system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return {"status": "success", "recommendations": response.content[0].text, "condition": condition, "location": location}
        except Exception as e:
            logger.error("Hospital recommendation failed: %s", e)
            return {"status": "error", "message": str(e)}

    def process_chat_message(self, message: str, session_id: str, conversation_history: Optional[list] = None) -> Dict[str, Any]:
        if not self.client:
            return {"status": "error", "message": "Anthropic client not available"}
        try:
            messages = list(conversation_history or [])
            messages.append({"role": "user", "content": message})
            response = self.client.messages.create(
                model=self.model_id, max_tokens=800, system=self.SYSTEM_PROMPT, messages=messages,
            )
            return {
                "status": "success", "response": response.content[0].text, "session_id": session_id,
                "message": message, "usage": {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens},
            }
        except Exception as e:
            logger.error("Chat processing failed: %s", e)
            return {"status": "error", "message": str(e)}

    def extract_intent(self, message: str) -> Dict[str, Any]:
        if not self.client:
            return {"status": "error", "intent": "unknown"}
        try:
            intent_prompt = f"""Analyze the following user message and determine their primary intent.
Return ONLY the intent type and key entities in JSON format.

User message: "{message}"

Intent types: diagnosis_request, hospital_recommendation, cost_comparison, procedure_inquiry, symptom_description, general_inquiry

Return as JSON:
{{"intent": "intent_type", "entities": ["entity1", "entity2"], "condition": "if applicable"}}"""
            response = self.client.messages.create(
                model=self.model_id, max_tokens=200,
                system="You are a medical intent classifier. Always respond in valid JSON format.",
                messages=[{"role": "user", "content": intent_prompt}],
            )
            response_text = response.content[0].text
            try:
                intent_data = json.loads(response_text)
            except json.JSONDecodeError:
                intent_data = {"intent": "general_inquiry", "entities": []}
            return {"status": "success", "intent": intent_data.get("intent", "unknown"), "entities": intent_data.get("entities", []), "condition": intent_data.get("condition")}
        except Exception as e:
            logger.error("Intent extraction failed: %s", e)
            return {"status": "error", "intent": "unknown", "error": str(e)}

# =========================================================================== #
#  8.  CONVERSATION AGENT  (replaces missing agents/conversation_agent.py)     #
# =========================================================================== #

def _detect_emergency(message: str) -> bool:
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in EMERGENCY_KEYWORDS)


def _simple_intent_extraction(message: str) -> SearchIntent:
    msg = message.lower()
    intent = SearchIntent(raw_query=message)

    city_patterns = {
        "chennai": r"\bchennai\b", "coimbatore": r"\bcoimbatore\b",
        "madurai": r"\bmadurai\b", "tiruchirappalli": r"\btiruchirappalli\b|\btrichy\b",
        "salem": r"\bsalem\b", "tirunelveli": r"\btirunelveli\b",
        "erode": r"\berode\b", "vellore": r"\bvellore\b",
        "thanjavur": r"\bthanjavur\b|\btanjore\b",
    }
    for city, pat in city_patterns.items():
        if re.search(pat, msg):
            intent.city = city
            break

    specialty_map = {
        "cardi": "Cardiology", "orthoped": "Orthopedic", "neuro": "Neurology",
        "dermat": "Dermatology", "ent": "ENT", "gynec": "Gynecology",
        "pediatr": "Pediatrics", "oncolog": "Oncology", "nephro": "Nephrology",
        "ophthalm": "Ophthalmology", "psychiatr": "Psychiatry",
    }
    for key, spec in specialty_map.items():
        if key in msg:
            intent.specialty = spec
            break

    budget_match = re.search(r"(\d[\d,]*)\s*(?:inr|rs\.?|rupees?)", msg)
    if budget_match:
        try:
            intent.budget_max = int(budget_match.group(1).replace(",", ""))
        except ValueError:
            pass

    return intent


def _match_hospitals(intent: SearchIntent, limit: int = 5) -> list[Hospital]:
    conn = get_connection()
    try:
        conditions: list[str] = []
        params: list = []
        if intent.city:
            conditions.append("LOWER(city) = LOWER(?)")
            params.append(intent.city)
        if intent.specialty:
            conditions.append("(specialties LIKE ? OR procedures LIKE ?)")
            params.extend([f"%{intent.specialty}%", f"%{intent.specialty}%"])
        if intent.budget_max:
            conditions.append("min_price <= ?")
            params.append(intent.budget_max)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = conn.execute(f"SELECT * FROM hospitals {where} ORDER BY success_rate DESC, avg_rating DESC LIMIT ?", params + [limit]).fetchall()
        return [Hospital(**row_to_dict(r)) for r in rows]
    finally:
        conn.close()


def process_message(session_id: str, message: str, extraction: ExtractionResult | None = None) -> ChatResponse:
    """Process a chat message and return a structured response."""
    save_conversation_turn(session_id, "user", message)

    # Emergency check
    if _detect_emergency(message):
        text = (
            "**URGENT:** Your message indicates a potential medical emergency. "
            "Please call emergency services (108 in India) or go to the nearest hospital immediately.\n\n"
            "Do not wait for online consultation. Every minute counts in emergencies."
        )
        save_conversation_turn(session_id, "assistant", text)
        return ChatResponse(session_id=session_id, text=text)

    intent = _simple_intent_extraction(message)
    hospitals = _match_hospitals(intent)

    # Build response text
    if hospitals:
        hospital_names = ", ".join(h.name for h in hospitals[:3])
        text = (
            f"Based on your query, I found {len(hospitals)} hospital(s) that may be suitable.\n\n"
            f"Top matches: {hospital_names}\n\n"
            f"Would you like more details about any of these hospitals?"
        )
    else:
        text = (
            "I couldn't find matching hospitals for your criteria. "
            "Try broadening your search — for example, search by specialty alone or try a nearby city."
        )

    actions: list[UIAction] = []
    if hospitals:
        actions.append(UIAction(type="apply_filter", payload={"key": "city", "value": intent.city or ""}))

    save_conversation_turn(session_id, "assistant", text)
    return ChatResponse(session_id=session_id, text=text, actions=actions, hospitals=hospitals)

# =========================================================================== #
#  9.  PRESCRIPTION PARSER AGENT  (replaces missing agents/prescription_parser.py) #
# =========================================================================== #

def parse_prescription(file_bytes: bytes, content_type: str, ner_pipeline: Any | None = None) -> ExtractionResult:
    """Parse an uploaded prescription file and return structured extraction."""
    raw_text = _extract_text_from_file(file_bytes, content_type)

    extraction = ExtractionResult(raw_text=raw_text)

    if ner_pipeline:
        try:
            entities = ner_pipeline(raw_text)
            for ent in entities:
                entity_type = ent.get("entity_group", ent.get("entity", "")).replace("B-", "").replace("I-", "")
                word = ent.get("word", "").strip()
                if not word:
                    continue
                if entity_type in ("DISEASE", "CONDITION", "DISORDER"):
                    if word not in extraction.diagnosis:
                        extraction.diagnosis.append(word)
                elif entity_type in ("PROCEDURE", "TEST"):
                    if word not in extraction.procedure:
                        extraction.procedure.append(word)
                elif entity_type in ("DRUG", "MEDICATION"):
                    if word not in extraction.medications:
                        extraction.medications.append(word)
        except Exception as e:
            logger.warning("NER pipeline failed during prescription parsing: %s", e)

    # Fallback: keyword-based extraction if NER returned nothing
    if not extraction.diagnosis and not extraction.procedure and not extraction.medications:
        extraction = _keyword_fallback(raw_text)

    # Try to extract patient info
    age_match = re.search(r"\b(age|years)\s*:?\s*(\d{1,3})\b", raw_text, re.IGNORECASE)
    if age_match:
        extraction.patient.age = int(age_match.group(2))
    gender_match = re.search(r"\b(male|female|other)\b", raw_text, re.IGNORECASE)
    if gender_match:
        extraction.patient.gender = gender_match.group(1).lower()

    return extraction


def _extract_text_from_file(file_bytes: bytes, content_type: str) -> str:
    """Extract text from image or PDF prescription files."""
    if content_type and "image" in content_type:
        return _ocr_image(file_bytes)
    if content_type and "pdf" in content_type:
        return _extract_pdf_text(file_bytes)
    # Fallback: try image OCR
    return _ocr_image(file_bytes)


def _ocr_image(image_bytes: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
        image = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(image)
    except Exception as e:
        logger.error("OCR failed: %s", e)
        return ""


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.error("PDF extraction failed: %s", e)
        return ""


def _keyword_fallback(raw_text: str) -> ExtractionResult:
    """Simple keyword-based extraction when NER is unavailable."""
    extraction = ExtractionResult(raw_text=raw_text)
    text_lower = raw_text.lower()

    diagnosis_keywords = ["diagnosis", "dx", "impression", "finding", "condition", "disease", "pain", "fever", "hypertension", "diabetes"]
    procedure_keywords = ["procedure", "surgery", "operation", "test", "scan", "x-ray", "mri", "ct", "ultrasound", "biopsy"]
    medication_keywords = ["tab", "tablet", "cap", "capsule", "syrup", "injection", "mg", "ml", "dosage", "prescribed"]

    for line in raw_text.split("\n"):
        line_lower = line.lower().strip()
        if any(kw in line_lower for kw in diagnosis_keywords) and line_lower not in extraction.diagnosis:
            extraction.diagnosis.append(line.strip())
        elif any(kw in line_lower for kw in procedure_keywords) and line_lower not in extraction.procedure:
            extraction.procedure.append(line.strip())
        elif any(kw in line_lower for kw in medication_keywords) and line_lower not in extraction.medications:
            extraction.medications.append(line.strip())

    return extraction

# =========================================================================== #
# 10.  VRAM MANAGER                                                            #
# =========================================================================== #

class VRAMManager:
    def __init__(self, vram_buffer_mb: int = 512, vram_per_inference_mb: int = 1024, check_interval_sec: int = 5):
        self.vram_buffer_mb = vram_buffer_mb
        self.vram_per_inference_mb = vram_per_inference_mb
        self.check_interval_sec = check_interval_sec
        self.semaphore = Semaphore(1)
        self.max_slots = 1
        self.has_gpu = False
        self.pynvml = None
        try:
            import pynvml
            pynvml.nvmlInit()
            self.pynvml = pynvml
            self.has_gpu = True
            logger.info("GPU VRAM monitoring enabled via pynvml")
        except Exception as e:
            logger.warning("GPU monitoring unavailable: %s. Using CPU-only mode.", e)
        self.stats = {"total_requests": 0, "current_active": 0, "peak_concurrent": 0, "last_check": datetime.now(), "available_vram_mb": 0}

    def get_available_vram_mb(self) -> int:
        if not self.has_gpu or not self.pynvml:
            return 2048
        try:
            handle = self.pynvml.nvmlDeviceGetHandleByIndex(0)
            mem_info = self.pynvml.nvmlDeviceGetMemoryInfo(handle)
            available_mb = int(mem_info.free / (1024 * 1024))
            self.stats["available_vram_mb"] = available_mb
            return available_mb
        except Exception as e:
            logger.warning("Failed to query GPU VRAM: %s", e)
            return 2048

    def update_semaphore_slots(self) -> int:
        available_vram = self.get_available_vram_mb()
        slots = max((available_vram - self.vram_buffer_mb) // self.vram_per_inference_mb, 1)
        old_slots = self.max_slots
        self.max_slots = slots
        if slots != old_slots:
            logger.info("VRAM: %dMB available | Buffer: %dMB | Per-inference: %dMB | Slots: %d -> %d",
                        available_vram, self.vram_buffer_mb, self.vram_per_inference_mb, old_slots, slots)
        return slots

    async def acquire_slot(self, timeout_sec: float = 60.0) -> bool:
        self.update_semaphore_slots()
        try:
            if self.semaphore.acquire(blocking=False):
                self.stats["current_active"] += 1
                self.stats["total_requests"] += 1
                self.stats["peak_concurrent"] = max(self.stats["peak_concurrent"], self.stats["current_active"])
                return True
            loop = asyncio.get_event_loop()
            start = loop.time()
            while loop.time() - start < timeout_sec:
                if self.semaphore.acquire(blocking=False):
                    self.stats["current_active"] += 1
                    self.stats["total_requests"] += 1
                    self.stats["peak_concurrent"] = max(self.stats["peak_concurrent"], self.stats["current_active"])
                    return True
                await asyncio.sleep(0.1)
            logger.warning("VRAM slot request timeout after %.1fs", timeout_sec)
            return False
        except Exception as e:
            logger.error("Error acquiring VRAM slot: %s", e)
            return False

    def release_slot(self) -> None:
        try:
            if self.stats["current_active"] > 0:
                self.semaphore.release()
                self.stats["current_active"] -= 1
        except Exception as e:
            logger.error("Error releasing VRAM slot: %s", e)

    def get_stats(self) -> dict:
        return {
            "available_vram_mb": self.get_available_vram_mb(),
            "max_slots": self.max_slots,
            "current_active": self.stats["current_active"],
            "total_requests": self.stats["total_requests"],
            "peak_concurrent": self.stats["peak_concurrent"],
            "gpu_available": self.has_gpu,
            "check_interval_sec": self.check_interval_sec,
        }


_vram_manager: VRAMManager | None = None


def get_vram_manager() -> VRAMManager:
    global _vram_manager
    if _vram_manager is None:
        _vram_manager = VRAMManager()
    return _vram_manager

# =========================================================================== #
# 11.  SECURITY MIDDLEWARE                                                     #
# =========================================================================== #

def setup_security(app: FastAPI):
    allowed_origins = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")
    allowed_origins = [origin.strip() for origin in allowed_origins]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Rate limiting — only if slowapi is installed
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.util import get_remote_address
        limiter = Limiter(key_func=get_remote_address)
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    except ImportError:
        logger.warning("slowapi not installed — rate limiting disabled. Install with: pip install slowapi")

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    logger.info("Security configured. CORS allowed origins: %s", allowed_origins)

# =========================================================================== #
# 12.  MEDICAL ANALYSIS ROUTER                                                  #
# =========================================================================== #

class EntityExtractionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class EntityExtractionResponse(BaseModel):
    status: str
    text: str
    entities: dict
    message: Optional[str] = None


class MedicalAnalysisResponse(BaseModel):
    status: str
    analysis: Optional[dict] = None
    message: Optional[str] = None


class IntentExtractionResponse(BaseModel):
    status: str
    intent: str
    entities: list
    condition: Optional[str] = None
    error: Optional[str] = None


class AssistantResponse(BaseModel):
    status: str
    response: str
    session_id: Optional[str] = None
    message: Optional[str] = None


medical_router = APIRouter(prefix="/api/medical", tags=["medical-analysis"])

_nlp_pipeline = MedicalNLPPipeline()
_assistant = MedicalAssistant()


@medical_router.post("/extract-entities", response_model=EntityExtractionResponse)
async def extract_entities(request: EntityExtractionRequest):
    try:
        result = _nlp_pipeline.extract_entities(request.text)
        if result["status"] != "success":
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
        return EntityExtractionResponse(status="success", text=request.text, entities=result["entities"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Entity extraction error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@medical_router.post("/analyze-medical-text", response_model=MedicalAnalysisResponse)
async def analyze_medical_text(request: MedicalAnalysisRequest):
    try:
        result = _nlp_pipeline.analyze_medical_text(request.text)
        if result["status"] != "success":
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
        return MedicalAnalysisResponse(status="success", analysis=result["analysis"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Medical analysis error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@medical_router.post("/extract-intent", response_model=IntentExtractionResponse)
async def extract_intent(request: EntityExtractionRequest):
    try:
        result = _assistant.extract_intent(request.text)
        return IntentExtractionResponse(
            status=result.get("status"), intent=result.get("intent"),
            entities=result.get("entities", []), condition=result.get("condition"), error=result.get("error"),
        )
    except Exception as e:
        logger.error("Intent extraction error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@medical_router.post("/analyze-condition", response_model=AssistantResponse)
async def analyze_condition(
    condition: str = Query(..., min_length=1, description="Medical condition to analyze"),
    age: Optional[int] = Query(None, ge=0, le=150, description="Patient age (optional)"),
    budget: Optional[float] = Query(None, ge=0, description="Budget in INR (optional)"),
):
    try:
        result = _assistant.analyze_medical_condition(condition=condition, age=age, budget=budget)
        if result["status"] != "success":
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
        return AssistantResponse(status="success", response=result["analysis"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Condition analysis error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@medical_router.post("/recommend-hospitals", response_model=AssistantResponse)
async def recommend_hospitals(
    condition: str = Query(..., min_length=1, description="Medical condition"),
    location: str = Query("Tamil Nadu", description="Location for recommendations"),
):
    try:
        result = _assistant.recommend_hospitals(condition=condition, location=location)
        if result["status"] != "success":
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
        return AssistantResponse(status="success", response=result["recommendations"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Hospital recommendation error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@medical_router.post("/chat", response_model=AssistantResponse)
async def chat_assistant(
    message: str = Query(..., min_length=1, description="User message"),
    session_id: str = Query(..., min_length=1, description="Conversation session ID"),
):
    try:
        result = _assistant.process_chat_message(message=message, session_id=session_id, conversation_history=[])
        if result["status"] != "success":
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
        return AssistantResponse(status="success", response=result["response"], session_id=session_id, message=message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Chat error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# =========================================================================== #
# 13.  HELPER                                                                  #
# =========================================================================== #

def _build_parse_summary(extraction: ExtractionResult) -> str:
    diagnosis_str = ", ".join(extraction.diagnosis) if extraction.diagnosis else "none"
    procedure_str = ", ".join(extraction.procedure) if extraction.procedure else "none"
    med_count = len(extraction.medications)
    return f"Extracted: Diagnosis: {diagnosis_str} | Procedure: {procedure_str} | Medications: {med_count} found"


def check_ollama() -> bool:
    try:
        import requests
        requests.get("http://localhost:11434/api/tags", timeout=2)
        return True
    except Exception:
        return False

# =========================================================================== #
# 14.  FASTAPI APP                                                             #
# =========================================================================== #

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    hf_token = os.getenv("HF_TOKEN")
    try:
        from transformers import pipeline as hf_pipeline
        app.state.ner_pipeline = hf_pipeline(
            "ner", model="d4data/biomedical-ner-all",
            aggregation_strategy="simple", token=hf_token,
        )
        logger.info("HuggingFace NER pipeline loaded successfully.")
    except Exception as e:
        logger.warning("HuggingFace NER model could not be loaded: %s", e)
        app.state.ner_pipeline = None
    yield


app = FastAPI(
    title="MediOrbit API",
    description="Medical tourism assistant API for Tamil Nadu, India.",
    version="1.0.0",
    lifespan=lifespan,
)

setup_security(app)
app.include_router(medical_router)


@app.get("/")
def root():
    return {"status": "MediOrbit API is running", "version": "1.0.0"}


@app.get("/api/health")
def health():
    return {"status": "running", "version": "1.0.0", "ollama": check_ollama()}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    try:
        response = process_message(
            session_id=body.session_id,
            message=body.message,
            extraction=body.prescription_data,
        )
        return response
    except ValueError as e:
        logger.warning("Input validation error in /api/chat: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error in /api/chat: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/parse-prescription", response_model=PrescriptionParseResponse)
async def parse_prescription_endpoint(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    try:
        file_bytes = await file.read()
        ner_pipeline = request.app.state.ner_pipeline
        extraction = parse_prescription(file_bytes, file.content_type or "", ner_pipeline)
        save_extraction(session_id, extraction.model_dump())
        summary = _build_parse_summary(extraction)
        return PrescriptionParseResponse(session_id=session_id, extraction=extraction, summary=summary)
    except Exception as e:
        logger.error("Error in /api/parse-prescription: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(body: StreamChatRequest):
    history = get_conversation_history(body.session_id)
    messages = [{"role": t["role"], "content": t["content"]} for t in history[-6:]]
    messages.append({"role": "user", "content": body.message})
    save_conversation_turn(body.session_id, "user", body.message)

    async def generate():
        full_reply: list[str] = []
        async for chunk in stream_chat_with_medgemma(messages, SYSTEM_PROMPT):
            full_reply.append(chunk)
            yield f"data: {chunk}\n\n"
        save_conversation_turn(body.session_id, "assistant", "".join(full_reply))
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/analyze-xray")
async def analyze_xray_endpoint(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        result = await analyze_xray_image(file_bytes, file.filename or "xray.jpg")
        return result
    except Exception as e:
        logger.error("Error in /api/analyze-xray: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/hospitals", response_model=list[Hospital])
def list_hospitals(
    city: str | None = None,
    specialty: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    limit: int = 20,
):
    conditions: list[str] = []
    params: list = []
    if city is not None:
        conditions.append("LOWER(city) = LOWER(?)")
        params.append(city)
    if specialty is not None:
        conditions.append("LOWER(specialties) LIKE LOWER(?)")
        params.append(f"%{specialty}%")
    if min_price is not None:
        conditions.append("min_price >= ?")
        params.append(min_price)
    if max_price is not None:
        conditions.append("max_price <= ?")
        params.append(max_price)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"SELECT * FROM hospitals {where_clause} LIMIT ?"
    params.append(limit)

    conn = get_connection()
    try:
        rows = conn.execute(query, params).fetchall()
        return [Hospital(**row_to_dict(row)) for row in rows]
    finally:
        conn.close()


@app.get("/api/hospitals/{hospital_id}", response_model=Hospital)
def get_hospital(hospital_id: str):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM hospitals WHERE id = ?", (hospital_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Hospital not found")
    return Hospital(**row_to_dict(row))
