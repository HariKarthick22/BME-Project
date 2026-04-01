#!/usr/bin/env python3
"""
MediOrbit CarePath AI - Unified FastAPI Application

SINGLE-FILE FASTAPI APPLICATION
Production: uvicorn main:app --host 0.0.0.0 --port 8000
Development: uvicorn main:app --reload
All-in-one launcher: python main.py (launches both backend + frontend)

Features:
- Database layer (SQLite with hospitals.csv)
- LLM services (Anthropic Claude, OpenAI, Groq)
- Medical NLP (BioBERT NER, prescription parsing)
- API routes with CORS, rate limiting, security
- Hospital search and matching
- Chat streaming with conversation history
- Clean startup/shutdown flow
"""

from __future__ import annotations

import asyncio
import base64
import csv
import html
import io
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import socket
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from threading import Semaphore
from typing import Any, Dict, List, Literal, Optional, Tuple, AsyncIterator
from urllib.parse import urlparse
from urllib.request import urlopen

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict, field_validator

# Load environment
load_dotenv(Path(__file__).parent / ".env")

# Logging setup
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# DATABASE LAYER

DB_PATH = Path(__file__).parent / "data" / "hospitals.db"
CSV_PATH = Path(__file__).parent / "data" / "hospitals.csv"

def get_db_connection():
    """Get SQLite connection with proper settings"""
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_database() -> None:
    """Initialize database with hospitals table"""
    import sqlite3
    
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()
    
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS hospitals (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                city TEXT,
                state TEXT DEFAULT 'Tamil Nadu',
                specialties TEXT DEFAULT '[]',
                procedures TEXT DEFAULT '[]',
                min_price INTEGER,
                max_price INTEGER,
                ai_score REAL,
                phone TEXT,
                email TEXT,
                image_url TEXT,
                website TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                messages TEXT
            );
            
            CREATE TABLE IF NOT EXISTS analysis_cache (
                id TEXT PRIMARY KEY,
                input_hash TEXT UNIQUE,
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        cursor = conn.execute("SELECT COUNT(*) FROM hospitals")
        if cursor.fetchone()[0] == 0 and CSV_PATH.exists():
            logger.info(f"Loading hospitals from {CSV_PATH}")
            with open(CSV_PATH, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        conn.execute("""
                            INSERT INTO hospitals (id, name, city, state, phone, email, image_url, website)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            row.get('id', ''),
                            row.get('name', ''),
                            row.get('city', ''),
                            row.get('state', 'Tamil Nadu'),
                            row.get('phone', ''),
                            row.get('email', ''),
                            row.get('image_url', ''),
                            row.get('website', '')
                        ))
                    except Exception as e:
                        logger.warning(f"Skipping row: {e}")
            
        conn.commit()
        logger.info("Database initialized successfully")
    finally:
        conn.close()


# PYDANTIC MODELS

class ChatMessage(BaseModel):
    """Chat message model"""
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    conversation_id: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class HospitalResponse(BaseModel):
    """Hospital response model"""
    id: str
    name: str
    city: str
    state: str
    phone: Optional[str] = None
    email: Optional[str] = None
    image_url: Optional[str] = None
    website: Optional[str] = None
    ai_score: Optional[float] = 0.0


# LLM SERVICES

class LLMService:
    """LLM service handler"""

    @staticmethod
    def fallback_reply(message: str) -> str:
        """Return a deterministic fallback response when cloud LLMs are unavailable."""
        text = (message or "").strip()
        if not text:
            return "Please describe your symptoms or medical query, and I will help with next steps."

        return (
            "Local MedGemma is currently unavailable. Start Ollama and pull a model: "
            "`ollama serve` and `ollama pull dcarrascosa/medgemma-1.5-4b-it:Q4_K_M`. "
            "Then retry your medical question."
        )
    
    def __init__(self):
        self.anthropic_client = None
        self.openai_client = None
        self.groq_client = None
        self.ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
        self.ollama_medgemma_model = os.getenv("OLLAMA_MEDGEMMA_MODEL", "dcarrascosa/medgemma-1.5-4b-it:Q4_K_M").strip()
        self.ollama_fallback_model = os.getenv("OLLAMA_FALLBACK_MODEL", "llama3.2:3b").strip()
        self.ollama_timeout = int(os.getenv("OLLAMA_TIMEOUT", "120"))
        self.ollama_num_predict = int(os.getenv("OLLAMA_NUM_PREDICT", "80"))
        self.ollama_num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "1024"))
        self.ollama_num_thread = int(os.getenv("OLLAMA_NUM_THREAD", str(max(1, (os.cpu_count() or 4) - 1))))
        self.ollama_temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))
        self.ollama_num_batch = int(os.getenv("OLLAMA_NUM_BATCH", "256"))
        self.ollama_keep_alive = os.getenv("OLLAMA_KEEP_ALIVE", "20m").strip() or "20m"
        self.ollama_models_cache_ttl = int(os.getenv("OLLAMA_MODELS_CACHE_TTL", "30"))
        self.response_max_chars = int(os.getenv("RESPONSE_MAX_CHARS", "420"))
        self.response_max_sentences = int(os.getenv("RESPONSE_MAX_SENTENCES", "3"))
        self._ollama_models_cache: List[str] = []
        self._ollama_models_cache_at = 0.0
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.groq_key = os.getenv("GROQ_API_KEY", "").strip()
        self.default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "local").strip().lower() or "local"
        self.default_anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022").strip()
        self.default_openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        self.default_groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()
        self.init_clients()
    
    def init_clients(self):
        """Initialize LLM clients"""
        if self.anthropic_key:
            try:
                from anthropic import Anthropic
                self.anthropic_client = Anthropic(api_key=self.anthropic_key)
                logger.info("Anthropic Claude client initialized")
            except Exception as e:
                logger.warning(f"Anthropic client init failed: {e}")
        else:
            logger.info("Anthropic API key not set (optional)")

        if self.openai_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.openai_key)
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.warning(f"OpenAI client init failed: {e}")
        else:
            logger.info("OpenAI API key not set (optional)")

        if self.groq_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_key)
                logger.info("Groq client initialized")
            except Exception as e:
                logger.info(f"Groq client not available (optional): {e}")
        else:
            logger.info("Groq API key not set (optional)")

    async def get_model_status(self) -> Dict[str, Any]:
        """Return provider availability and current defaults."""
        ollama_ok, available_models, selected_model = await self._ollama_status_sync()
        return {
            "default_provider": self.default_provider,
            "providers": {
                "local_ollama": {
                    "online": ollama_ok,
                    "selected_model": selected_model,
                    "available_models": available_models,
                    "base_url": self.ollama_base,
                },
                "anthropic": {
                    "key_configured": bool(self.anthropic_key),
                    "online": self.anthropic_client is not None,
                    "model": self.default_anthropic_model,
                },
                "openai": {
                    "key_configured": bool(self.openai_key),
                    "online": self.openai_client is not None,
                    "model": self.default_openai_model,
                },
                "groq": {
                    "key_configured": bool(self.groq_key),
                    "online": self.groq_client is not None,
                    "model": self.default_groq_model,
                },
                "fallback_local": {
                    "online": True,
                    "model": "fallback-local",
                },
            },
        }

    async def _ollama_status_sync(self) -> Tuple[bool, List[str], str]:
        available = await self._available_ollama_models()
        selected = self._pick_ollama_model(available)
        return bool(available), available, selected or "none"

    async def warmup_local_model(self) -> None:
        """Warm up local model so first user request is faster."""
        available = await self._available_ollama_models()
        model_name = self._pick_ollama_model(available)
        if not model_name:
            return

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "Reply briefly."},
                {"role": "user", "content": "ping"},
            ],
            "stream": False,
            "keep_alive": self.ollama_keep_alive,
            "options": {
                "temperature": 0.0,
                "num_predict": 8,
                "num_ctx": 512,
                "num_thread": self.ollama_num_thread,
                "num_batch": self.ollama_num_batch,
            },
        }

        try:
            import httpx

            async with httpx.AsyncClient(timeout=20) as client:
                await client.post(f"{self.ollama_base}/api/chat", json=payload)
                logger.info("Local Ollama model warmup completed")
        except Exception as e:
            logger.info(f"Local Ollama warmup skipped: {e}")

    async def _available_ollama_models(self) -> List[str]:
        now = time.monotonic()
        if self._ollama_models_cache and (now - self._ollama_models_cache_at) < self.ollama_models_cache_ttl:
            return self._ollama_models_cache

        try:
            import httpx

            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.ollama_base}/api/tags")
                response.raise_for_status()
                models = [m.get("name", "") for m in response.json().get("models", []) if m.get("name")]
                self._ollama_models_cache = models
                self._ollama_models_cache_at = now
                return models
        except Exception:
            return []

    def _pick_ollama_model(self, available: List[str]) -> Optional[str]:
        if not available:
            return None
        for candidate in (self.ollama_medgemma_model, self.ollama_fallback_model):
            base = candidate.split(":")[0]
            for name in available:
                if name == candidate or base in name:
                    return name
        return available[0]

    def _system_prompt(self) -> str:
        return (
            "You are a medical assistant. Respond quickly and concisely. "
            "Use at most 3 short sentences, avoid long disclaimers, and focus on practical next steps. "
            "If urgent red-flag symptoms are present, explicitly say to seek immediate care."
        )

    def _constrain_reply(self, reply: str) -> str:
        cleaned = re.sub(r"\s+", " ", (reply or "")).strip()
        if not cleaned:
            return ""

        pieces = re.split(r"(?<=[.!?])\s+", cleaned)
        if len(pieces) > self.response_max_sentences:
            cleaned = " ".join(pieces[: self.response_max_sentences]).strip()

        if len(cleaned) > self.response_max_chars:
            cleaned = cleaned[: self.response_max_chars]
            if " " in cleaned:
                cleaned = cleaned.rsplit(" ", 1)[0]
            cleaned = cleaned.rstrip(" ,;:-") + "."

        return cleaned

    async def _ollama_chat(self, message: str, stream: bool = False) -> AsyncIterator[str] | str | None:
        available = await self._available_ollama_models()
        model_name = self._pick_ollama_model(available)
        if not model_name:
            return None

        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": self._system_prompt(),
                },
                {"role": "user", "content": message},
            ],
            "stream": stream,
            "keep_alive": self.ollama_keep_alive,
            "options": {
                "temperature": self.ollama_temperature,
                "num_predict": self.ollama_num_predict,
                "num_ctx": self.ollama_num_ctx,
                "num_thread": self.ollama_num_thread,
                "num_batch": self.ollama_num_batch,
            },
        }

        if not stream:
            try:
                import httpx

                async with httpx.AsyncClient(timeout=self.ollama_timeout) as client:
                    response = await client.post(f"{self.ollama_base}/api/chat", json=payload)
                    response.raise_for_status()
                    reply = response.json().get("message", {}).get("content", "").strip()
                    return self._constrain_reply(reply)
            except Exception as e:
                logger.warning(f"Ollama non-stream request failed: {e}")
                return None

        async def _generator() -> AsyncIterator[str]:
            emitted_chars = 0
            emitted_sentences = 0
            try:
                import httpx

                async with httpx.AsyncClient(timeout=self.ollama_timeout) as client:
                    async with client.stream("POST", f"{self.ollama_base}/api/chat", json=payload) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            try:
                                chunk = json.loads(line)
                                text = chunk.get("message", {}).get("content", "")
                                if text:
                                    remaining = self.response_max_chars - emitted_chars
                                    if remaining <= 0:
                                        break
                                    piece = text[:remaining]
                                    if piece:
                                        emitted_chars += len(piece)
                                        emitted_sentences += piece.count(".") + piece.count("!") + piece.count("?")
                                        yield piece
                                    if emitted_chars >= self.response_max_chars or emitted_sentences >= self.response_max_sentences:
                                        break
                                if chunk.get("done"):
                                    break
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.warning(f"Ollama stream request failed: {e}")

        return _generator()

    def _get_provider_order(self, provider: Optional[str]) -> List[str]:
        requested = (provider or self.default_provider or "auto").strip().lower()
        if requested in {"local", "local_ollama", "anthropic", "openai", "groq"}:
            if requested in {"local", "local_ollama"}:
                return ["local_ollama"]
            return [requested]
        return ["local_ollama", "anthropic", "openai", "groq"]

    async def generate_message(self, message: str, provider: Optional[str] = None, model: Optional[str] = None) -> Tuple[str, str, str]:
        """Generate non-stream response from available providers with fallback."""
        for candidate in self._get_provider_order(provider):
            if candidate == "local_ollama":
                local_reply = await self._ollama_chat(message=message, stream=False)
                if isinstance(local_reply, str) and local_reply.strip():
                    return self._constrain_reply(local_reply.strip()), self.ollama_medgemma_model, "local_ollama"

            if candidate == "anthropic" and self.anthropic_client:
                try:
                    response = self.anthropic_client.messages.create(
                        model=model or self.default_anthropic_model,
                        max_tokens=1024,
                        messages=[{"role": "user", "content": message}],
                    )
                    text_parts: List[str] = []
                    for block in getattr(response, "content", []) or []:
                        block_text = getattr(block, "text", None)
                        if isinstance(block_text, str) and block_text:
                            text_parts.append(block_text)
                    reply = "\n".join(text_parts).strip()
                    if reply:
                        return self._constrain_reply(reply), model or self.default_anthropic_model, "anthropic"
                except Exception as e:
                    logger.warning(f"Anthropic request failed: {e}")

            if candidate == "openai" and self.openai_client:
                try:
                    response = self.openai_client.chat.completions.create(
                        model=model or self.default_openai_model,
                        messages=[{"role": "user", "content": message}],
                        temperature=0.2,
                    )
                    reply = (response.choices[0].message.content or "").strip()
                    if reply:
                        return self._constrain_reply(reply), model or self.default_openai_model, "openai"
                except Exception as e:
                    logger.warning(f"OpenAI request failed: {e}")

            if candidate == "groq" and self.groq_client:
                try:
                    response = self.groq_client.chat.completions.create(
                        model=model or self.default_groq_model,
                        messages=[{"role": "user", "content": message}],
                        temperature=0.2,
                    )
                    reply = (response.choices[0].message.content or "").strip()
                    if reply:
                        return self._constrain_reply(reply), model or self.default_groq_model, "groq"
                except Exception as e:
                    logger.warning(f"Groq request failed: {e}")

        return self._constrain_reply(self.fallback_reply(message)), "fallback-local", "fallback_local"

    async def chat_stream(self, message: str, provider: Optional[str] = None, model: Optional[str] = None) -> AsyncIterator[str]:
        """Stream chat response"""
        chosen_provider = (provider or self.default_provider or "auto").strip().lower()
        effective_model = model or self.default_anthropic_model

        if chosen_provider in {"auto", "local", "local_ollama"}:
            local_stream = await self._ollama_chat(message=message, stream=True)
            if local_stream is not None:
                if isinstance(local_stream, str):
                    yield local_stream
                    return
                async for chunk in local_stream:
                    yield chunk
                return

        if chosen_provider in {"auto", "anthropic"} and self.anthropic_client:
            try:
                with self.anthropic_client.messages.stream(
                    model=effective_model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": message}],
                    system="You are a helpful medical assistant. Provide accurate medical information."
                ) as stream:
                    for text in stream.text_stream:
                        yield text
                return
            except Exception as e:
                logger.error(f"Chat stream error: {e}")

        reply, _, _ = await self.generate_message(message=message, provider=provider, model=model)
        yield reply


# MEDICAL NLP

class MedicalNLPService:
    """Medical NLP service"""
    
    def __init__(self):
        self.ner_pipeline = None
        self.init_models()
    
    def init_models(self):
        """Initialize NLP models"""
        model_name = os.getenv("MEDICAL_NLP_MODEL", "").strip()
        if not model_name:
            logger.info("Medical NLP model not configured; using lightweight fallback extraction")
            return

        try:
            from transformers import pipeline
            self.ner_pipeline = pipeline(
                "token-classification",
                model=model_name
            )
            logger.info(f"Medical NLP model loaded: {model_name}")
        except Exception as e:
            logger.warning(f"BioBERT NER init failed: {e}")
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract medical entities from text"""
        if not self.ner_pipeline:
            words = re.findall(r"[A-Za-z][A-Za-z0-9-]+", text.lower())
            disease_terms = {"diabetes", "asthma", "fever", "cancer", "hypertension", "infection"}
            symptom_terms = {"pain", "headache", "cough", "nausea", "fatigue", "dizziness"}
            drug_terms = {"aspirin", "paracetamol", "ibuprofen", "metformin", "amoxicillin"}

            diseases = sorted({w for w in words if w in disease_terms})
            symptoms = sorted({w for w in words if w in symptom_terms})
            drugs = sorted({w for w in words if w in drug_terms})

            return {"diseases": diseases, "drugs": drugs, "symptoms": symptoms}
        
        try:
            results = self.ner_pipeline(text[:512])
            entities = {"diseases": [], "drugs": [], "symptoms": []}
            
            for result in results:
                entity_type = result["entity"].lower()
                if "disease" in entity_type:
                    entities["diseases"].append(result["word"])
                elif "drug" in entity_type:
                    entities["drugs"].append(result["word"])
                elif "symptom" in entity_type:
                    entities["symptoms"].append(result["word"])
            
            return entities
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return {"diseases": [], "drugs": [], "symptoms": []}
    
    async def analyze_prescription(self, text: str) -> Dict[str, Any]:
        """Analyze prescription text"""
        entities = self.extract_entities(text)
        
        return {
            "medications": entities.get("drugs", []),
            "conditions": entities.get("diseases", []),
            "symptoms": entities.get("symptoms", []),
            "raw_text": text[:200]
        }


# HOSPITAL SERVICE

class HospitalService:
    """Hospital search and matching service"""
    
    @staticmethod
    def search_hospitals(query: str, city: Optional[str] = None) -> List[HospitalResponse]:
        """Search hospitals by name, city, or specialty"""
        conn = get_db_connection()
        
        try:
            sql = "SELECT * FROM hospitals WHERE 1=1"
            params = []
            
            if query:
                sql += " AND (LOWER(name) LIKE ? OR LOWER(city) LIKE ?)"
                search_term = f"%{query.lower()}%"
                params.extend([search_term, search_term])
            
            if city:
                sql += " AND LOWER(city) = ?"
                params.append(city.lower())
            
            sql += " LIMIT 20"
            
            cursor = conn.execute(sql, params)
            hospitals = []
            
            for row in cursor.fetchall():
                hospitals.append(HospitalResponse(
                    id=row['id'],
                    name=row['name'],
                    city=row['city'],
                    state=row['state'],
                    phone=row['phone'],
                    email=row['email'],
                    image_url=row['image_url'],
                    website=row['website'],
                    ai_score=row['ai_score'] or 0.0
                ))
            
            return hospitals
        finally:
            conn.close()
    
    @staticmethod
    def get_hospital_by_id(hospital_id: str) -> Optional[HospitalResponse]:
        """Get hospital details by ID"""
        conn = get_db_connection()
        
        try:
            cursor = conn.execute("SELECT * FROM hospitals WHERE id = ?", (hospital_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return HospitalResponse(
                id=row['id'],
                name=row['name'],
                city=row['city'],
                state=row['state'],
                phone=row['phone'],
                email=row['email'],
                image_url=row['image_url'],
                website=row['website'],
                ai_score=row['ai_score'] or 0.0
            )
        finally:
            conn.close()


# GLOBAL SERVICES

llm_service = None
nlp_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager"""
    global llm_service, nlp_service
    
    logger.info("Starting up application...")
    init_database()
    llm_service = LLMService()
    await llm_service.warmup_local_model()
    nlp_service = MedicalNLPService()
    logger.info("Application startup complete")
    
    yield
    
    logger.info("Shutting down application...")


# FASTAPI APP

app = FastAPI(
    title="MediOrbit CarePath AI",
    description="Medical assistant with hospital search",
    version="2.0.0",
    lifespan=lifespan
)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API ROUTES

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "application": "MediOrbit CarePath AI",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/api/chat",
            "hospitals": "/api/hospitals",
            "analysis": "/api/analysis",
            "models": "/api/models/status",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "llm": "initialized" if llm_service else "unavailable",
            "nlp": "initialized" if nlp_service else "unavailable",
            "database": "initialized"
        }
    }


@app.get("/api/models/status")
async def models_status():
    """Report online/offline status for configured model providers."""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not available")

    nlp_model = os.getenv("MEDICAL_NLP_MODEL", "").strip()
    return {
        "llm": await llm_service.get_model_status(),
        "nlp": {
            "configured_model": nlp_model or "fallback-extractor",
            "online": bool(getattr(nlp_service, "ner_pipeline", None)),
            "fallback_online": True,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint - streaming response"""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not available")
    service = llm_service
    provider = str(request.model_config.get("provider", "auto"))
    model = request.model_config.get("model")
    
    async def generate():
        async for chunk in service.chat_stream(request.message, provider=provider, model=model):
            if not chunk:
                continue
            # Always emit valid SSE frames so frontend stream parsers can process reliably.
            text = chunk.replace("\r", " ").replace("\n", " ")
            yield f"data: {text}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/chat/stream")
async def chat_stream_alias(request: ChatRequest):
    """Compatibility alias used by frontend"""
    return await chat(request)


@app.post("/api/chat/message")
async def chat_message(request: ChatRequest):
    """Non-streaming chat endpoint"""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not available")
    provider = str(request.model_config.get("provider", "auto"))
    model = request.model_config.get("model")

    response_text, resolved_model, resolved_provider = await llm_service.generate_message(
        message=request.message,
        provider=provider,
        model=model,
    )

    return {
        "response": response_text,
        "model": resolved_model,
        "provider": resolved_provider,
    }


@app.get("/api/hospitals")
async def list_hospitals(
    q: str = Query("", description="Search query"),
    city: str = Query("", description="Filter by city")
):
    """List/search hospitals"""
    hospitals = HospitalService.search_hospitals(q, city or None)
    return {"hospitals": hospitals, "count": len(hospitals)}


@app.get("/api/hospitals/{hospital_id}")
async def get_hospital(hospital_id: str):
    """Get hospital details"""
    hospital = HospitalService.get_hospital_by_id(hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    return hospital


@app.post("/api/analysis/prescription")
async def analyze_prescription(request: ChatRequest):
    """Analyze prescription text"""
    if not nlp_service:
        raise HTTPException(status_code=503, detail="NLP service not available")
    
    try:
        result = await nlp_service.analyze_prescription(request.message)
        return result
    except Exception as e:
        logger.error(f"Prescription analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analysis/symptoms")
async def analyze_symptoms(request: ChatRequest):
    """Analyze symptoms using medical NLP"""
    if not nlp_service:
        raise HTTPException(status_code=503, detail="NLP service not available")
    
    try:
        entities = nlp_service.extract_entities(request.message)
        conditions = entities.get("diseases", [])
        matching_hospitals = []
        
        if conditions:
            search_results = HospitalService.search_hospitals(" ".join(conditions))
            matching_hospitals = [h.dict() for h in search_results]
        
        return {
            "entities": entities,
            "matching_hospitals": matching_hospitals,
            "recommendation": "Please consult a healthcare professional"
        }
    except Exception as e:
        logger.error(f"Symptom analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/parse-prescription")
async def parse_prescription_upload(file: UploadFile = File(...), session_id: str = Form("")):
    """Upload endpoint compatible with frontend document scan flow"""
    if not nlp_service:
        raise HTTPException(status_code=503, detail="NLP service not available")

    try:
        raw = await file.read()
        text = raw.decode("utf-8", errors="ignore").strip()
        if not text:
            text = f"Uploaded document: {file.filename}"

        result = await nlp_service.analyze_prescription(text)
        summary = f"Detected medications: {', '.join(result.get('medications', [])) or 'none'}; conditions: {', '.join(result.get('conditions', [])) or 'none'}."
        return {
            "session_id": session_id,
            "summary": summary,
            "result": result,
        }
    except Exception as e:
        logger.error(f"Prescription upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze-xray")
async def analyze_xray_upload(file: UploadFile = File(...), session_id: str = Form("")):
    """Upload endpoint compatible with frontend X-ray flow"""
    try:
        raw = await file.read()
        size_kb = max(1, len(raw) // 1024)
        findings = f"X-ray file '{file.filename}' received ({size_kb} KB). No automated radiology model is configured; please consult a radiologist for diagnosis."
        return {
            "session_id": session_id,
            "findings": findings,
            "result": "X-ray upload processed",
        }
    except Exception as e:
        logger.error(f"X-ray upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# LAUNCHER

def start_servers():
    """Start backend, frontend, and optional local Ollama server."""
    project_root = Path(__file__).parent
    frontend_dir = project_root / "frontend"

    def _backend_python_executable() -> str:
        venv_python = project_root / ".venv" / "bin" / "python"
        if venv_python.exists():
            return str(venv_python)
        return sys.executable

    def _is_port_in_use(port: int) -> bool:
        targets = [
            (socket.AF_INET, "127.0.0.1"),
            (socket.AF_INET6, "::1"),
        ]
        for family, host in targets:
            try:
                with socket.socket(family, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.3)
                    if sock.connect_ex((host, port)) == 0:
                        return True
            except OSError:
                continue
        return False

    def _wait_for_port(port: int, timeout_seconds: float = 12.0) -> bool:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if _is_port_in_use(port):
                return True
            time.sleep(0.2)
        return _is_port_in_use(port)

    def _http_reachable(url: str, timeout_seconds: float = 2.0) -> bool:
        try:
            with urlopen(url, timeout=timeout_seconds) as response:
                return 200 <= getattr(response, "status", 0) < 500
        except Exception:
            return False
    
    logger.info("=" * 80)
    logger.info("STARTING CAREPATH AI - BACKEND + FRONTEND")
    logger.info("=" * 80)

    ollama_process = None
    provider = os.getenv("DEFAULT_LLM_PROVIDER", "local").strip().lower()
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    parsed = urlparse(ollama_base_url)
    ollama_port = parsed.port or 11434

    if provider in {"local", "auto"}:
        if _is_port_in_use(ollama_port):
            logger.warning("Ollama server is already running. Reusing existing Ollama service.")
        elif shutil.which("ollama"):
            logger.info(f"Starting Ollama Server (Port {ollama_port})...")
            ollama_process = subprocess.Popen(["ollama", "serve"], cwd=str(project_root))
            if _wait_for_port(ollama_port, timeout_seconds=8.0):
                logger.info("Ollama server is online")
            else:
                logger.warning("Ollama server did not become ready in time; continuing without managed Ollama process")
                if ollama_process.poll() is not None:
                    ollama_process = None
        else:
            logger.warning("Ollama CLI not found; local MedGemma may be unavailable")
    
    backend_process = None
    if _is_port_in_use(8000):
        logger.warning("Port 8000 is already in use. Reusing existing backend server.")
    else:
        logger.info("Starting Backend API Server (Port 8000)...")
        backend_cmd = [
            _backend_python_executable(), "-m", "uvicorn",
            "main:app",
            "--reload",
            "--host", "0.0.0.0",
            "--port", "8000"
        ]
        backend_process = subprocess.Popen(
            backend_cmd,
            cwd=str(project_root)
        )
        if not _wait_for_port(8000, timeout_seconds=12.0):
            raise RuntimeError("Backend server failed to bind to port 8000")
    
    if frontend_dir.exists():
        if _is_port_in_use(5173):
            logger.warning("Port 5173 is already in use. Reusing existing frontend server.")
            if _http_reachable("http://127.0.0.1:5173") or _http_reachable("http://localhost:5173"):
                frontend_process = None
            else:
                logger.warning("Port 5173 is occupied but no reachable frontend responded. Continuing with backend-only mode.")
                frontend_process = None
        else:
            logger.info("Starting Frontend Dev Server (Port 5173)...")
            if not shutil.which("npm"):
                logger.warning("npm command not found. Skipping frontend startup and continuing with backend-only mode.")
                frontend_process = None
                return backend_process, frontend_process, ollama_process
            frontend_cmd = ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173", "--strictPort"]
            frontend_process = subprocess.Popen(
                frontend_cmd,
                cwd=str(frontend_dir)
            )
            if not _wait_for_port(5173, timeout_seconds=30.0):
                logger.warning("Frontend server failed to bind to port 5173. Continuing with backend-only mode.")
                frontend_process = None
            elif not (_http_reachable("http://127.0.0.1:5173", timeout_seconds=4.0) or _http_reachable("http://localhost:5173", timeout_seconds=4.0)):
                logger.warning("Frontend on port 5173 did not respond to HTTP checks. Continuing with backend-only mode.")
                frontend_process = None
    else:
        logger.warning("Frontend directory not found")
        frontend_process = None
    
    return backend_process, frontend_process, ollama_process


def manage_servers(backend_proc, frontend_proc, ollama_proc):
    """Manage server processes"""
    logger.info("=" * 80)
    logger.info("SERVICES STARTED!")
    logger.info("=" * 80)
    logger.info("\nFrontend: http://localhost:5173")
    logger.info("Frontend (direct): http://127.0.0.1:5173")
    logger.info("Backend:  http://localhost:8000")
    logger.info("Backend (direct): http://127.0.0.1:8000")
    if os.getenv("DEFAULT_LLM_PROVIDER", "local").strip().lower() in {"local", "auto"}:
        logger.info("Ollama:  http://127.0.0.1:11434")
    logger.info("API Docs: http://localhost:8000/docs\n")
    logger.info("Press Ctrl+C to stop both servers\n")
    logger.info("=" * 80 + "\n")

    backend_reported_stopped = False
    frontend_reported_stopped = False
    ollama_reported_stopped = False
    
    try:
        while True:
            if backend_proc and backend_proc.poll() is not None:
                if not backend_reported_stopped:
                    logger.error("Backend process stopped! Other services will keep running until Ctrl+C.")
                    backend_reported_stopped = True
                backend_proc = None
            
            if frontend_proc and frontend_proc.poll() is not None:
                if not frontend_reported_stopped:
                    logger.error("Frontend process stopped! Other services will keep running until Ctrl+C.")
                    frontend_reported_stopped = True
                frontend_proc = None

            if ollama_proc and ollama_proc.poll() is not None:
                if not ollama_reported_stopped:
                    logger.error("Ollama process stopped! Backend/frontend will keep running until Ctrl+C.")
                    ollama_reported_stopped = True
                ollama_proc = None
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("\nShutting down servers...")
        if backend_proc:
            backend_proc.terminate()
        if frontend_proc:
            frontend_proc.terminate()
        if ollama_proc:
            ollama_proc.terminate()
        
        try:
            if backend_proc:
                backend_proc.wait(timeout=5)
            if frontend_proc:
                frontend_proc.wait(timeout=5)
            if ollama_proc:
                ollama_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            if backend_proc:
                backend_proc.kill()
            if frontend_proc:
                frontend_proc.kill()
            if ollama_proc:
                ollama_proc.kill()
        
        logger.info("Servers stopped")


# MAIN ENTRY POINT

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="MediOrbit CarePath AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                 # Launch both backend + frontend
  python main.py --backend-only  # Launch backend only
  uvicorn main:app --reload     # Run with uvicorn
        """
    )
    
    parser.add_argument(
        "--backend-only",
        action="store_true",
        help="Run backend server only"
    )
    
    args = parser.parse_args()
    
    if args.backend_only:
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    else:
        try:
            backend_proc, frontend_proc, ollama_proc = start_servers()
            manage_servers(backend_proc, frontend_proc, ollama_proc)
        except Exception as e:
            logger.error(f"Failed to start servers: {e}")
            sys.exit(1)
