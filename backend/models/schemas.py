"""
Pydantic schemas for MediOrbit backend.

All request/response models, domain models, and data transfer objects
used across agents and API endpoints.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

class DoctorProfile(BaseModel):
    """A doctor associated with a hospital."""
    name: str
    specialty: str
    experience_years: int
    qualification: str


class PatientReview(BaseModel):
    """A patient review for a hospital."""
    patient_name: str
    condition: str
    outcome: str
    rating: float
    date: str


class CostBreakdown(BaseModel):
    """Itemised cost breakdown for a procedure at a hospital."""
    item: str
    cost: int


class Hospital(BaseModel):
    """Full hospital record as stored in SQLite and returned by the API."""
    model_config = ConfigDict(extra='ignore')

    id: str
    name: str
    city: str
    state: str = "Tamil Nadu"
    specialties: list[str] = []
    procedures: list[str] = []
    min_price: int = 0
    max_price: int = 0
    ai_score: float = 0.0
    match_score: float | None = None          # set by HospitalMatchingAgent
    match_reasons: list[str] = []             # set by HospitalMatchingAgent
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


# ---------------------------------------------------------------------------
# Agent input/output models
# ---------------------------------------------------------------------------

class SearchIntent(BaseModel):
    """Structured intent extracted from a natural language query by IntentAgent."""
    procedure: str | None = None
    specialty: str | None = None
    city: str | None = None
    budget_max: int | None = None          # in INR
    insurance_type: str | None = None
    raw_query: str = ""


class PatientInfo(BaseModel):
    """Demographic data extracted from a prescription."""
    age: int | None = None
    gender: str | None = None             # "male" | "female" | "other"


class ExtractionResult(BaseModel):
    """Structured medical data extracted from a prescription by PrescriptionParserAgent."""
    diagnosis: list[str] = []
    procedure: list[str] = []
    medications: list[str] = []
    patient: PatientInfo = Field(default_factory=PatientInfo)
    raw_text: str = ""                    # OCR'd text before NER


# ---------------------------------------------------------------------------
# UI action models (sent to frontend NavigationAgent)
# ---------------------------------------------------------------------------

UIActionType = Literal[
    "navigate",
    "highlight",
    "apply_filter",
    "open_detail",
    "show_comparison",
    "clear_highlight",
]


class UIAction(BaseModel):
    """
    A command the frontend NavigationAgent should execute.

    Examples:
        {"type": "navigate", "payload": {"url": "/results?session=abc"}}
        {"type": "highlight", "payload": {"hospital_id": "ganga-01"}}
        {"type": "apply_filter", "payload": {"key": "city", "value": "Chennai"}}
        {"type": "open_detail", "payload": {"hospital_id": "cmc-01"}}
    """
    type: UIActionType
    payload: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# API request/response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Request body for POST /api/chat."""
    session_id: str
    message: str
    prescription_data: ExtractionResult | None = None


class ChatResponse(BaseModel):
    """Response body for POST /api/chat."""
    session_id: str
    text: str
    actions: list[UIAction] = []
    hospitals: list[Hospital] = []


class PrescriptionParseResponse(BaseModel):
    """Response body for POST /api/parse-prescription."""
    session_id: str
    extraction: ExtractionResult
    summary: str                          # human-readable summary for chat display
