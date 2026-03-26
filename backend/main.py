"""
MediOrbit FastAPI application entry point.

Endpoints:
  - POST /api/chat          — CarePath AI chat (non-streaming)
  - POST /api/chat/stream   — CarePath AI chat (SSE streaming)
  - POST /api/parse-prescription — Upload & parse prescription files
  - GET  /api/hospitals     — List/filter hospitals
  - GET  /api/hospitals/{id} — Single hospital detail
  - GET  /api/health        — Health check
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse

from .models.schemas import (
    ChatRequest,
    ChatResponse,
    Hospital,
    PrescriptionParseResponse,
    ExtractionResult,
)
from .models.database import init_db, get_connection, row_to_dict, save_extraction
from .middleware.security import setup_security, limiter
from .routes.medical_analysis import router as medical_router

# ---------------------------------------------------------------------------
# Load .env from project root (parent of backend/)
# ---------------------------------------------------------------------------

load_dotenv(Path(__file__).parent.parent / ".env")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# File upload constants
# ---------------------------------------------------------------------------

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    On startup: initialise DB and attempt to load HuggingFace NER pipeline.
    On shutdown: nothing (SQLite connections are per-request).
    """
    init_db()

    hf_token = os.getenv("HF_TOKEN")
    try:
        from transformers import pipeline as hf_pipeline

        app.state.ner_pipeline = hf_pipeline(
            "ner",
            model="d4data/biomedical-ner-all",
            aggregation_strategy="simple",
            token=hf_token,
        )
        logger.info("HuggingFace NER pipeline loaded successfully.")
    except Exception as e:
        logger.warning("HuggingFace NER model could not be loaded: %s", e)
        app.state.ner_pipeline = None

    yield


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="MediOrbit API",
    description="CarePath AI — Medical tourism assistant for Tamil Nadu, India.",
    version="2.0.0",
    lifespan=lifespan,
)

setup_security(app)
app.include_router(medical_router)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _build_parse_summary(extraction: ExtractionResult) -> str:
    diagnosis_str = ", ".join(extraction.diagnosis) if extraction.diagnosis else "none"
    procedure_str = ", ".join(extraction.procedure) if extraction.procedure else "none"
    med_count = len(extraction.medications)
    return (
        f"Extracted: Diagnosis: {diagnosis_str} | "
        f"Procedure: {procedure_str} | "
        f"Medications: {med_count} found"
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"status": "MediOrbit API is running", "version": "2.0.0"}


@app.get("/api/health")
def health():
    return {
        "status": "running",
        "version": "2.0.0",
        "ollama": _check_ollama(),
    }


def _check_ollama() -> bool:
    try:
        import httpx
        httpx.get("http://localhost:11434/api/tags", timeout=2)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# POST /api/chat
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
def chat(request: Request, body: ChatRequest):
    """Handle a chat message and return a structured response."""
    try:
        from .agents.graph_agent import process_message

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
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


# ---------------------------------------------------------------------------
# POST /api/chat/stream  (SSE streaming)
# ---------------------------------------------------------------------------

@app.post("/api/chat/stream")
@limiter.limit("20/minute")
async def chat_stream(request: Request, body: ChatRequest):
    """Stream CarePath AI response as Server-Sent Events."""
    async def event_generator():
        try:
            from .agents.graph_agent import stream_message

            async for token in stream_message(
                session_id=body.session_id,
                message=body.message,
                extraction=body.prescription_data,
            ):
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            logger.error("Error in /api/chat/stream: %s", e, exc_info=True)
            yield f"data: {json.dumps({'error': 'Stream interrupted. Please retry.'})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# POST /api/parse-prescription
# ---------------------------------------------------------------------------

@app.post("/api/parse-prescription", response_model=PrescriptionParseResponse)
@limiter.limit("10/minute")
async def parse_prescription_endpoint(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    """Parse an uploaded prescription (image or PDF) and return structured data."""
    try:
        # Validate file type before reading
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{file.content_type}'. "
                       f"Allowed: JPEG, PNG, WebP, PDF.",
            )

        file_bytes = await file.read()

        # Validate file size after reading
        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="File too large. Maximum allowed size is 10 MB.",
            )

        ner_pipeline = request.app.state.ner_pipeline

        from .agents.prescription_parser import parse_prescription

        extraction = parse_prescription(
            file_bytes,
            file.content_type or "",
            ner_pipeline,
        )
        save_extraction(session_id, extraction.model_dump())
        summary = _build_parse_summary(extraction)
        return PrescriptionParseResponse(
            session_id=session_id,
            extraction=extraction,
            summary=summary,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in /api/parse-prescription: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


# ---------------------------------------------------------------------------
# GET /api/hospitals
# ---------------------------------------------------------------------------

@app.get("/api/hospitals", response_model=list[Hospital])
@limiter.limit("60/minute")
def list_hospitals(
    request: Request,
    city: str | None = None,
    specialty: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    limit: int = 20,
):
    """Return a filtered list of hospitals from the database."""
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


# ---------------------------------------------------------------------------
# GET /api/hospitals/{hospital_id}
# ---------------------------------------------------------------------------

@app.get("/api/hospitals/{hospital_id}", response_model=Hospital)
@limiter.limit("60/minute")
def get_hospital(request: Request, hospital_id: str):
    """Return a single hospital by its unique identifier."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM hospitals WHERE id = ?",
            (hospital_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Hospital not found")

    return Hospital(**row_to_dict(row))
