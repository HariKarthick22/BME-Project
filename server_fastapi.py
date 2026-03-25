"""
MediOrbit FastAPI Backend

API Endpoints:
- POST /api/chat - Main chat endpoint
- POST /api/upload-prescription - Prescription upload handler  
- GET /api/hospitals/{id} - Hospital detail endpoint
- GET /api/hospitals - List hospitals with filters
- GET /api/health - Health check

Run: uvicorn server:app --reload --port 8000
"""

from __future__ import annotations
import os
import uuid
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MediOrbit API",
    description="Medical Hospital Recommendation System API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    session_id: Optional[str] = "default"
    prescription_data: Optional[dict] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    text: str
    actions: list[dict]
    session_id: str
    results_count: int
    hospitals: list[dict]


class HospitalResponse(BaseModel):
    """Response model for hospital detail."""
    id: int
    name: str
    city: str
    type: str
    accreditation: str | None
    rating: float | None
    procedures: list[dict]


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "MediOrbit API"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.
    
    Processes user message and returns:
    - text: friendly response message
    - actions: UI actions to execute
    - hospitals: matched hospital results
    - session_id: session identifier
    """
    try:
        from agents.conversation_agent import ConversationAgent
        
        agent = ConversationAgent()
        response = agent.chat(
            message=request.message,
            session_id=request.session_id,
            prescription_data=request.prescription_data
        )
        
        return ChatResponse(
            text=response.text,
            actions=response.actions,
            session_id=response.session_id,
            results_count=response.results_count,
            hospitals=response.hospitals
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload-prescription")
async def upload_prescription(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form("default")
):
    """
    Upload and parse a prescription image.
    
    Parameters
    ----------
    file : UploadFile
        Prescription image (JPG, PNG, PDF)
    session_id : str
        Session identifier
        
    Returns
    -------
    dict
        Extracted data and parsed intent
    """
    try:
        from agents.prescription_parser import PrescriptionParserAgent
        
        temp_path = f"/tmp/prescription_{uuid.uuid4()}.{file.filename.split('.')[-1]}"
        
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        parser = PrescriptionParserAgent()
        result = parser.extract_from_image(temp_path)
        
        os.remove(temp_path)
        
        return {
            "success": True,
            "session_id": session_id,
            "extracted": {
                "diagnoses": result.diagnoses,
                "procedures": result.procedures,
                "medications": result.medications,
                "demographics": result.demographics,
                "confidence": result.confidence,
                "raw_text": result.raw_text[:500]
            }
        }
        
    except Exception as e:
        logger.error(f"Prescription upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/hospitals/{hospital_id}", response_model=HospitalResponse)
async def get_hospital_detail(hospital_id: int):
    """
    Get detailed information about a hospital.
    
    Parameters
    ----------
    hospital_id : int
        Hospital ID
        
    Returns
    -------
    HospitalResponse
        Detailed hospital information
    """
    try:
        hospital_rows = query(
            "SELECT * FROM hospitals WHERE id = ?",
            (hospital_id,)
        )
        
        if not hospital_rows:
            raise HTTPException(status_code=404, detail="Hospital not found")
        
        hospital = hospital_rows[0]
        
        procedure_rows = query(
            """
            SELECT * FROM hospital_procedures 
            WHERE hospital_id = ?
            ORDER BY cost_avg_inr ASC
            """,
            (hospital_id,)
        )
        
        return HospitalResponse(
            id=hospital["id"],
            name=hospital["name"],
            city=hospital["city"],
            type=hospital["type"],
            accreditation=hospital["accreditation"],
            rating=hospital["rating"],
            procedures=[
                {
                    "id": p["id"],
                    "category": p["category"],
                    "procedure_name": p["procedure_name"],
                    "lead_doctors": p["lead_doctors"],
                    "cost_min_inr": p["cost_min_inr"],
                    "cost_max_inr": p["cost_max_inr"],
                    "cost_avg_inr": p["cost_avg_inr"],
                    "hospital_stay_days": p["hospital_stay_days"],
                    "recovery_weeks": p["recovery_weeks"],
                    "success_rate_pct": p["success_rate_pct"],
                    "insurance_schemes": p["insurance_schemes"],
                    "availability": p["availability"]
                }
                for p in procedure_rows
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hospital detail error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/hospitals")
async def list_hospitals(
    category: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    procedure: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0)
):
    """
    List hospitals with optional filters.
    
    Parameters
    ----------
    category : str, optional
        Filter by medical category
    city : str, optional
        Filter by city
    procedure : str, optional
        Filter by procedure name
    limit : int
        Maximum results (default 50)
    offset : int
        Results offset
        
    Returns
    -------
    dict
        List of hospitals with pagination info
    """
    try:
        conditions = []
        params = []
        
        if category:
            conditions.append("p.category = ?")
            params.append(category)
        
        if city:
            conditions.append("LOWER(h.city) = LOWER(?)")
            params.append(city)
        
        if procedure:
            conditions.append("p.procedure_name LIKE ?")
            params.append(f"%{procedure}%")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        count_sql = f"""
            SELECT COUNT(DISTINCT h.id) as total
            FROM hospitals h
            JOIN hospital_procedures p ON h.id = p.hospital_id
            WHERE {where_clause}
        """
        count_result = query(count_sql, tuple(params))
        total = count_result[0]["total"] if count_result else 0
        
        sql = f"""
            SELECT DISTINCT
                h.id, h.name, h.city, h.type, 
                h.accreditation, h.rating,
                MIN(p.cost_min_inr) as min_cost,
                MAX(p.cost_max_inr) as max_cost,
                AVG(p.cost_avg_inr) as avg_cost,
                COUNT(p.id) as procedure_count
            FROM hospitals h
            JOIN hospital_procedures p ON h.id = p.hospital_id
            WHERE {where_clause}
            GROUP BY h.id
            ORDER BY h.name ASC
            LIMIT ? OFFSET ?
        """
        
        params_with_pagination = params + [limit, offset]
        rows = query(sql, tuple(params_with_pagination))
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "hospitals": [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "city": r["city"],
                    "type": r["type"],
                    "accreditation": r["accreditation"],
                    "rating": r["rating"],
                    "min_cost": r["min_cost"],
                    "max_cost": r["max_cost"],
                    "avg_cost": r["avg_cost"],
                    "procedure_count": r["procedure_count"]
                }
                for r in rows
            ]
        }
        
    except Exception as e:
        logger.error(f"List hospitals error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/categories")
async def list_categories():
    """Get list of available medical categories."""
    try:
        rows = query("SELECT DISTINCT category FROM hospital_procedures ORDER BY category")
        return {"categories": [r["category"] for r in rows]}
    except Exception as e:
        logger.error(f"List categories error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cities")
async def list_cities():
    """Get list of available cities."""
    try:
        rows = query("SELECT DISTINCT city FROM hospitals ORDER BY city")
        return {"cities": [r["city"] for r in rows]}
    except Exception as e:
        logger.error(f"List cities error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)