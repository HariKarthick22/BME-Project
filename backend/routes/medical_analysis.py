"""Medical analysis API endpoints."""
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

from ..services.medical_nlp import MedicalNLPPipeline
from ..services.medical_assistant import MedicalAssistant
from ..utils.sanitizer import MedicalAnalysisRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/medical", tags=["medical-analysis"])

# Initialize services
nlp_pipeline = MedicalNLPPipeline()
assistant = MedicalAssistant()


# ============================================================================
# Request/Response Models
# ============================================================================


class EntityExtractionRequest(BaseModel):
    """Request for medical entity extraction."""

    text: str = Field(..., min_length=1, max_length=5000)

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Patient with knee pain and difficulty walking. History of arthritis."
            }
        }


class EntityExtractionResponse(BaseModel):
    """Response with extracted medical entities."""

    status: str
    text: str
    entities: dict
    message: Optional[str] = None


class MedicalAnalysisResponse(BaseModel):
    """Response from medical analysis."""

    status: str
    analysis: Optional[dict] = None
    message: Optional[str] = None


class IntentExtractionResponse(BaseModel):
    """Response from intent extraction."""

    status: str
    intent: str
    entities: list
    condition: Optional[str] = None
    error: Optional[str] = None


class AssistantResponse(BaseModel):
    """Response from medical assistant."""

    status: str
    response: str
    session_id: Optional[str] = None
    message: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/extract-entities", response_model=EntityExtractionResponse)
async def extract_entities(request: EntityExtractionRequest):
    """
    Extract medical entities from text.

    Uses Hugging Face biomedical NER model to identify:
    - Conditions and diseases
    - Medications
    - Procedures
    - Anatomical locations
    - And more...
    """
    try:
        result = nlp_pipeline.extract_entities(request.text)

        if result["status"] != "success":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"],
            )

        return EntityExtractionResponse(
            status="success",
            text=request.text,
            entities=result["entities"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Entity extraction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/analyze-medical-text", response_model=MedicalAnalysisResponse)
async def analyze_medical_text(request: MedicalAnalysisRequest):
    """
    Analyze medical text for conditions, symptoms, medications.

    Combines NLP entity extraction with medical categorization to provide
    structured analysis of medical documents.
    """
    try:
        result = nlp_pipeline.analyze_medical_text(request.text)

        if result["status"] != "success":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"],
            )

        return MedicalAnalysisResponse(
            status="success",
            analysis=result["analysis"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Medical analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/extract-intent", response_model=IntentExtractionResponse)
async def extract_intent(request: EntityExtractionRequest):
    """
    Extract intent from user message.

    Determines if user is asking for:
    - Hospital recommendation
    - Cost comparison
    - Procedure inquiry
    - Symptom analysis
    - General information
    """
    try:
        result = assistant.extract_intent(request.text)

        return IntentExtractionResponse(
            status=result.get("status"),
            intent=result.get("intent"),
            entities=result.get("entities", []),
            condition=result.get("condition"),
            error=result.get("error"),
        )
    except Exception as e:
        logger.error(f"Intent extraction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/analyze-condition", response_model=AssistantResponse)
async def analyze_condition(
    condition: str = Query(..., min_length=1, description="Medical condition to analyze"),
    age: Optional[int] = Query(None, ge=0, le=150, description="Patient age (optional)"),
    budget: Optional[float] = Query(None, ge=0, description="Budget in INR (optional)"),
):
    """
    Analyze medical condition using Anthropic Claude.

    Query Parameters:
    - condition: Medical condition to analyze (required)
    - age: Patient age (optional)
    - budget: Budget in INR (optional)

    Provides:
    - Condition overview
    - Available treatments in Tamil Nadu
    - Cost estimates
    - Recovery information
    - Hospital recommendations
    """
    try:
        result = assistant.analyze_medical_condition(
            condition=condition,
            age=age,
            budget=budget,
        )

        if result["status"] != "success":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"],
            )

        return AssistantResponse(
            status="success",
            response=result["analysis"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Condition analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/recommend-hospitals", response_model=AssistantResponse)
async def recommend_hospitals(
    condition: str = Query(..., min_length=1, description="Medical condition"),
    location: str = Query("Tamil Nadu", description="Location for recommendations"),
):
    """
    Recommend hospitals for specific condition.

    Query Parameters:
    - condition: Medical condition (required)
    - location: Location for recommendations (default: Tamil Nadu)

    Returns hospital recommendations based on:
    - Condition specialization
    - Location
    - Cost estimates
    - Accreditations
    """
    try:
        result = assistant.recommend_hospitals(
            condition=condition,
            location=location,
        )

        if result["status"] != "success":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"],
            )

        return AssistantResponse(
            status="success",
            response=result["recommendations"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hospital recommendation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/chat", response_model=AssistantResponse)
async def chat(
    message: str = Query(..., min_length=1, description="User message"),
    session_id: str = Query(..., min_length=1, description="Conversation session ID"),
    conversation_history: Optional[List] = Query(None, description="Previous messages"),
):
    """
    Chat with medical tourism assistant.

    Query Parameters:
    - message: User message (required)
    - session_id: Conversation session ID (required)
    - conversation_history: Previous messages (optional)

    Maintains conversation context for intelligent responses about:
    - Hospital recommendations
    - Cost information
    - Procedure details
    - Medical tourism guidance
    """
    try:
        result = assistant.process_chat_message(
            message=message,
            session_id=session_id,
            conversation_history=conversation_history or [],
        )

        if result["status"] != "success":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"],
            )

        return AssistantResponse(
            status="success",
            response=result["response"],
            session_id=session_id,
            message=message,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
