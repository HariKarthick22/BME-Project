"""Medical analysis API endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status, Query
from pydantic import BaseModel, Field

from ..services.medical_nlp import MedicalNLPPipeline
from ..services.medical_assistant import MedicalAssistant
from ..utils.sanitizer import MedicalAnalysisRequest
from ..middleware.security import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/medical", tags=["medical-analysis"])

nlp_pipeline = MedicalNLPPipeline()
assistant = MedicalAssistant()


# ============================================================================
# Request/Response Models
# ============================================================================


class EntityExtractionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Patient with knee pain and difficulty walking. History of arthritis."
            }
        }


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


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/extract-entities", response_model=EntityExtractionResponse)
@limiter.limit("30/minute")
async def extract_entities(request: Request, req: EntityExtractionRequest):
    """Extract medical entities from text using biomedical NER."""
    try:
        result = nlp_pipeline.extract_entities(req.text)

        if result["status"] != "success":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Entity extraction failed. Please try again.",
            )

        return EntityExtractionResponse(
            status="success",
            text=req.text,
            entities=result["entities"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Entity extraction error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred. Please try again.",
        )


@router.post("/analyze-medical-text", response_model=MedicalAnalysisResponse)
@limiter.limit("30/minute")
async def analyze_medical_text(request: Request, req: MedicalAnalysisRequest):
    """Analyze medical text for conditions, symptoms, medications."""
    try:
        result = nlp_pipeline.analyze_medical_text(req.text)

        if result["status"] != "success":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Medical analysis failed. Please try again.",
            )

        return MedicalAnalysisResponse(
            status="success",
            analysis=result["analysis"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Medical analysis error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred. Please try again.",
        )


@router.post("/extract-intent", response_model=IntentExtractionResponse)
@limiter.limit("30/minute")
async def extract_intent(request: Request, req: EntityExtractionRequest):
    """Extract intent from user message."""
    try:
        result = assistant.extract_intent(req.text)

        return IntentExtractionResponse(
            status=result.get("status"),
            intent=result.get("intent"),
            entities=result.get("entities", []),
            condition=result.get("condition"),
            error=result.get("error"),
        )
    except Exception as e:
        logger.error("Intent extraction error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred. Please try again.",
        )


@router.post("/analyze-condition", response_model=AssistantResponse)
@limiter.limit("30/minute")
async def analyze_condition(
    request: Request,
    condition: str = Query(..., min_length=1, max_length=500),
    age: Optional[int] = Query(None, ge=0, le=150),
    budget: Optional[float] = Query(None, ge=0),
):
    """Analyze medical condition using CarePath AI."""
    try:
        result = assistant.analyze_medical_condition(
            condition=condition,
            age=age,
            budget=budget,
        )

        if result["status"] != "success":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Condition analysis failed. Please try again.",
            )

        return AssistantResponse(
            status="success",
            response=result["analysis"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Condition analysis error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred. Please try again.",
        )


@router.post("/recommend-hospitals", response_model=AssistantResponse)
@limiter.limit("30/minute")
async def recommend_hospitals(
    request: Request,
    condition: str = Query(..., min_length=1, max_length=500),
    location: str = Query("Tamil Nadu", max_length=100),
):
    """Recommend hospitals for a specific condition."""
    try:
        result = assistant.recommend_hospitals(
            condition=condition,
            location=location,
        )

        if result["status"] != "success":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Hospital recommendation failed. Please try again.",
            )

        return AssistantResponse(
            status="success",
            response=result["recommendations"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Hospital recommendation error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred. Please try again.",
        )


@router.post("/chat", response_model=AssistantResponse)
@limiter.limit("20/minute")
async def medical_chat(
    request: Request,
    message: str = Query(..., min_length=1, max_length=2000),
    session_id: str = Query(..., min_length=1, max_length=100),
):
    """Chat with CarePath AI medical tourism assistant."""
    try:
        result = assistant.process_chat_message(
            message=message,
            session_id=session_id,
            conversation_history=[],
        )

        if result["status"] != "success":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Chat processing failed. Please try again.",
            )

        return AssistantResponse(
            status="success",
            response=result["response"],
            session_id=session_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Medical chat error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred. Please try again.",
        )
