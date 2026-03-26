"""
MediOrbit FastAPI application entry point.

Wires together all four API endpoints:
  - POST /api/chat
  - POST /api/parse-prescription
  - GET  /api/hospitals
  - GET  /api/hospitals/{hospital_id}

Also provides a root health-check at GET /.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware

from .models.schemas import (
    ChatRequest,
    ChatResponse,
    Hospital,
    PrescriptionParseResponse,
    ExtractionResult,
)
from .models.database import init_db, get_connection, row_to_dict, save_extraction
from .middleware.security import setup_security
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
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.

    On startup:
        1. Initialise the SQLite database (create tables, seed data).
        2. Attempt to load the HuggingFace biomedical NER pipeline.
           If loading fails, ``app.state.ner_pipeline`` is set to ``None``
           and a warning is logged; the application continues without NER.

    On shutdown:
        Nothing additional is needed (SQLite connections are per-request).
    """
    # Initialise DB
    init_db()

    # Load HuggingFace NER model
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
    description="Medical tourism assistant API for Tamil Nadu, India.",
    version="1.0.0",
    lifespan=lifespan,
)

# Security configuration (CORS, rate limiting, security headers)
setup_security(app)

# Include medical analysis routes
app.include_router(medical_router)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _build_parse_summary(extraction: ExtractionResult) -> str:
    """
    Build a human-readable one-line summary of a prescription extraction.

    Args:
        extraction: The structured data returned by ``parse_prescription``.

    Returns:
        A string in the format:
        "Extracted: Diagnosis: <items or 'none'> | Procedure: <items or 'none'> | Medications: <N> found"
    """
    diagnosis_str = ", ".join(extraction.diagnosis) if extraction.diagnosis else "none"
    procedure_str = ", ".join(extraction.procedure) if extraction.procedure else "none"
    med_count = len(extraction.medications)
    return (
        f"Extracted: Diagnosis: {diagnosis_str} | "
        f"Procedure: {procedure_str} | "
        f"Medications: {med_count} found"
    )


# ---------------------------------------------------------------------------
# Root health check
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    """Return a simple health-check payload confirming the API is running."""
    return {"status": "MediOrbit API is running", "version": "1.0.0"}

@app.get("/api/health")
def health():
    """Health check endpoint for monitoring."""
    return {
        "status": "running", 
        "version": "1.0.0",
        "ollama": check_ollama()
    }

def check_ollama() -> bool:
    """Check if Ollama is available."""
    try:
        import requests
        requests.get("http://localhost:11434/api/tags", timeout=2)
        return True
    except:
        return False


# ---------------------------------------------------------------------------
# POST /api/chat
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    """
    Handle a chat message for a given session.

    Delegates to ``ConversationAgent.process_message``, which orchestrates
    intent extraction, hospital matching, Anthropic LLM calls, and UI action
    generation.

    Args:
        body: ``ChatRequest`` containing ``session_id``, ``message``, and an
              optional ``prescription_data`` (``ExtractionResult``).

    Returns:
        ``ChatResponse`` with the assistant reply text, UI actions, and matched
        hospitals.

    Raises:
        HTTPException: 400 if input validation fails.
        HTTPException: 500 if an unexpected error occurs during processing.
    """
    try:
        from agents.conversation_agent import process_message

        response = process_message(
            session_id=body.session_id,
            message=body.message,
            extraction=body.prescription_data,
        )
        return response
    except ValueError as e:
        # Input validation error — return 400 Bad Request
        logger.warning("Input validation error in /api/chat: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error in /api/chat: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# POST /api/parse-prescription
# ---------------------------------------------------------------------------

@app.post("/api/parse-prescription", response_model=PrescriptionParseResponse)
async def parse_prescription_endpoint(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    """
    Parse an uploaded prescription file and return structured extraction data.

    Reads the uploaded file bytes, runs the HuggingFace biomedical NER pipeline
    (loaded at startup and stored on ``app.state``), persists the result to the
    database, and returns a ``PrescriptionParseResponse``.

    Args:
        request: The raw FastAPI ``Request`` object, used to access
                 ``app.state.ner_pipeline``.
        file: The multipart-uploaded prescription file (image or PDF).
        session_id: The chat session identifier, supplied as a form field.

    Returns:
        ``PrescriptionParseResponse`` containing the ``session_id``, structured
        ``ExtractionResult``, and a human-readable ``summary`` string.

    Raises:
        HTTPException: 500 if an unexpected error occurs during parsing.
    """
    try:
        file_bytes = await file.read()
        ner_pipeline = request.app.state.ner_pipeline

        from agents.prescription_parser import parse_prescription

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
    except Exception as e:
        logger.error("Error in /api/parse-prescription: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /api/hospitals
# ---------------------------------------------------------------------------

@app.get("/api/hospitals", response_model=list[Hospital])
def list_hospitals(
    city: str | None = None,
    specialty: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    limit: int = 20,
):
    """
    Return a filtered list of hospitals from the SQLite database.

    All query parameters are optional; when omitted the corresponding filter is
    not applied.  Results are limited to ``limit`` rows (default 20).

    Args:
        city: Filter by city name (case-insensitive exact match).
        specialty: Filter by specialty substring (case-insensitive LIKE match).
        min_price: Return only hospitals whose ``min_price`` is at or above this
                   value (in INR).
        max_price: Return only hospitals whose ``max_price`` is at or below this
                   value (in INR).
        limit: Maximum number of hospitals to return (default 20).

    Returns:
        List of ``Hospital`` objects matching the supplied filters.
    """
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
def get_hospital(hospital_id: str):
    """
    Return a single hospital by its unique identifier.

    Args:
        hospital_id: The hospital's primary-key string (e.g. ``"ganga-01"``).

    Returns:
        The ``Hospital`` record if found.

    Raises:
        HTTPException: 404 if no hospital with the given ``hospital_id`` exists.
    """
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
