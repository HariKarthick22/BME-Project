"""
backend/agents/router_agent.py

LangGraph-based router agent for MediOrbit / CarePath AI.

Deterministic routing graph:
  START → router → one of:
    ├── csv_hospital_agent   (hospital search queries)
    ├── vision_xray_agent    (X-ray / imaging analysis)
    ├── rag_document_agent   (PDF / prescription analysis)
    └── conversation_agent   (general medical chat)
  → self_correct (retries once if no result)
  → END

Each node returns a dict that is merged into the shared AgentState.
"""

from __future__ import annotations

import logging
import os
from typing import TypedDict, Literal, Any

from langgraph.graph import StateGraph, END

from ..config.prompts import SYSTEM_PROMPT, MEDICAL_DISCLAIMER, ERROR_RESPONSES
from ..models.schemas import SearchIntent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared graph state
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    """State passed between all nodes in the routing graph."""
    session_id: str
    user_message: str
    intent: str                      # "hospital_search" | "xray_analysis" | "document_analysis" | "general_chat"
    hospitals: list[dict]
    response_text: str
    retry_count: int
    image_bytes: bytes | None
    document_bytes: bytes | None
    document_mime: str


# ---------------------------------------------------------------------------
# Intent classifier
# ---------------------------------------------------------------------------

_HOSPITAL_KEYWORDS = {
    "hospital", "clinic", "doctor", "surgery", "procedure", "treatment",
    "specialist", "cardio", "ortho", "neuro", "cancer", "oncology",
    "transplant", "dialysis", "bypass", "cost", "price", "budget",
    "chennai", "coimbatore", "madurai", "vellore", "trichy", "salem",
}
_XRAY_KEYWORDS = {"x-ray", "xray", "x ray", "ct scan", "mri", "scan", "imaging", "radiograph"}
_DOC_KEYWORDS = {"prescription", "report", "upload", "document", "pdf", "test results", "scan"}


def _classify_intent(message: str) -> str:
    """Rule-based intent classification with Anthropic fallback."""
    lower = message.lower()

    if any(k in lower for k in _XRAY_KEYWORDS):
        return "xray_analysis"
    if any(k in lower for k in _DOC_KEYWORDS):
        return "document_analysis"
    if any(k in lower for k in _HOSPITAL_KEYWORDS):
        return "hospital_search"
    return "general_chat"


# ---------------------------------------------------------------------------
# Node: router
# ---------------------------------------------------------------------------

def router_node(state: AgentState) -> AgentState:
    """Classify intent and set routing target."""
    intent = _classify_intent(state["user_message"])
    logger.info("[router] session=%s intent=%s", state["session_id"], intent)
    return {**state, "intent": intent}


def route_to_agent(state: AgentState) -> Literal[
    "csv_hospital_agent", "vision_xray_agent", "rag_document_agent", "conversation_agent"
]:
    """Edge function: map intent to next node name."""
    mapping = {
        "hospital_search": "csv_hospital_agent",
        "xray_analysis": "vision_xray_agent",
        "document_analysis": "rag_document_agent",
        "general_chat": "conversation_agent",
    }
    return mapping.get(state["intent"], "conversation_agent")


# ---------------------------------------------------------------------------
# Node: CSV Hospital Agent
# ---------------------------------------------------------------------------

def csv_hospital_agent_node(state: AgentState) -> AgentState:
    """
    Retrieve matching hospitals from CSV/SQLite and compose a reply.
    Self-corrects by broadening criteria if no hospitals are found.
    """
    try:
        from .intent_agent import extract_intent
        from .hospital_matcher import match_hospitals

        intent_obj: SearchIntent = extract_intent(state["user_message"])
        hospitals = match_hospitals(intent_obj, extraction=None, top_n=5)

        if hospitals:
            names = ", ".join(h.name for h in hospitals[:3])
            text = (
                f"I found {len(hospitals)} hospitals matching your needs. "
                f"Top matches: {names}. "
                f"Please consult a board-certified professional for a clinical evaluation."
            )
        else:
            text = ERROR_RESPONSES["no_hospitals_found"].format(
                specialty=intent_obj.specialty or "that specialty",
                city=intent_obj.city or "your city",
            )

        return {
            **state,
            "hospitals": [h.model_dump() for h in hospitals],
            "response_text": text,
        }
    except Exception as e:
        logger.error("[csv_hospital_agent] error: %s", e)
        return {**state, "hospitals": [], "response_text": ERROR_RESPONSES["csv_error"]}


# ---------------------------------------------------------------------------
# Node: Vision / X-ray Agent
# ---------------------------------------------------------------------------

def vision_xray_agent_node(state: AgentState) -> AgentState:
    """
    Analyze X-ray via MedGemma (Ollama) or ViT fallback.
    Operates synchronously — wraps async call with asyncio.
    """
    import asyncio

    image_bytes = state.get("image_bytes")
    if not image_bytes:
        return {
            **state,
            "response_text": (
                "Please upload an X-ray image so I can analyze it. "
                "Use the 📷 button in the chat input." + MEDICAL_DISCLAIMER
            ),
        }

    try:
        from ..services.ollama_service import analyze_xray_image
        result = asyncio.get_event_loop().run_until_complete(
            analyze_xray_image(image_bytes)
        )
        return {**state, "response_text": result["summary"]}
    except Exception as e:
        logger.error("[vision_xray_agent] error: %s", e)
        return {
            **state,
            "response_text": ERROR_RESPONSES["model_timeout"] + MEDICAL_DISCLAIMER,
        }


# ---------------------------------------------------------------------------
# Node: RAG / Document Agent
# ---------------------------------------------------------------------------

def rag_document_agent_node(state: AgentState) -> AgentState:
    """
    Parse prescription / medical PDF via OCR + NER.
    Uses existing PrescriptionParser agent.
    """
    doc_bytes = state.get("document_bytes")
    mime = state.get("document_mime", "application/pdf")

    if not doc_bytes:
        return {
            **state,
            "response_text": (
                "Please upload a medical document (prescription / report) for analysis. "
                "Use the 📄 button in the chat input."
            ),
        }

    try:
        from .prescription_parser import parse_prescription
        extraction = parse_prescription(doc_bytes, mime, ner_pipeline=None)
        diag = ", ".join(extraction.diagnosis) if extraction.diagnosis else "none identified"
        meds = len(extraction.medications)
        text = (
            f"Document analyzed. Diagnosis: {diag}. "
            f"Medications found: {meds}." + MEDICAL_DISCLAIMER
        )
        return {**state, "response_text": text}
    except Exception as e:
        logger.error("[rag_document_agent] error: %s", e)
        return {**state, "response_text": ERROR_RESPONSES["csv_error"]}


# ---------------------------------------------------------------------------
# Node: General Conversation Agent (Ollama MedGemma)
# ---------------------------------------------------------------------------

def conversation_agent_node(state: AgentState) -> AgentState:
    """
    General medical chat using MedGemma via Ollama.
    Synchronously wraps the async Ollama call.
    """
    import asyncio

    try:
        from ..services.ollama_service import chat_with_medgemma
        from ..models.database import get_conversation_history

        history = get_conversation_history(state["session_id"])
        messages = [
            {"role": turn["role"], "content": turn["content"]}
            for turn in history[-6:]
        ]
        messages.append({"role": "user", "content": state["user_message"]})

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        chat_with_medgemma(messages, SYSTEM_PROMPT),
                    )
                    text = future.result(timeout=120)
            else:
                text = loop.run_until_complete(
                    chat_with_medgemma(messages, SYSTEM_PROMPT)
                )
        except Exception as llm_err:
            logger.warning("[conversation_agent] LLM call failed: %s", llm_err)
            text = _fallback_text(state["user_message"])

        return {**state, "response_text": text}
    except Exception as e:
        logger.error("[conversation_agent] error: %s", e)
        return {**state, "response_text": _fallback_text(state["user_message"])}


def _fallback_text(message: str) -> str:
    """Rule-based fallback when LLM is unavailable."""
    lower = message.lower()
    if any(w in lower for w in ("hello", "hi", "hey")):
        return (
            "Hello! I'm CarePath AI, your medical tourism guide. "
            "Tell me your medical need and city, and I'll find the best hospitals for you."
        )
    return (
        "I'm here to help you navigate your healthcare journey. "
        "Please tell me what medical procedure or specialist you're looking for, "
        "and your preferred city in Tamil Nadu."
    )


# ---------------------------------------------------------------------------
# Node: self_correct
# ---------------------------------------------------------------------------

def self_correct_node(state: AgentState) -> AgentState:
    """
    If no useful response was generated, retry once with a broader query.
    Prevents empty/error responses from reaching the user.
    """
    text = state.get("response_text", "").strip()
    retry = state.get("retry_count", 0)

    # Already has a good response or max retries reached
    if text and "error" not in text.lower() and "unavailable" not in text.lower():
        return state
    if retry >= 1:
        return {
            **state,
            "response_text": (
                "I'm having trouble right now. "
                "Please try rephrasing your question or try again shortly." + MEDICAL_DISCLAIMER
            ),
        }

    logger.info("[self_correct] retrying session=%s", state["session_id"])
    broader_state = {**state, "user_message": state["user_message"], "retry_count": retry + 1}
    # Re-route via general conversation on retry
    return conversation_agent_node({**broader_state, "intent": "general_chat"})


def should_self_correct(state: AgentState) -> Literal["self_correct", END]:
    """Edge: check if self-correction is needed."""
    text = state.get("response_text", "").strip()
    if not text or "error" in text.lower():
        return "self_correct"
    return END


# ---------------------------------------------------------------------------
# Build the LangGraph
# ---------------------------------------------------------------------------

def build_router_graph() -> Any:
    """Build and compile the MediOrbit routing graph."""
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("csv_hospital_agent", csv_hospital_agent_node)
    graph.add_node("vision_xray_agent", vision_xray_agent_node)
    graph.add_node("rag_document_agent", rag_document_agent_node)
    graph.add_node("conversation_agent", conversation_agent_node)
    graph.add_node("self_correct", self_correct_node)

    graph.set_entry_point("router")

    graph.add_conditional_edges("router", route_to_agent)

    for node in ("csv_hospital_agent", "vision_xray_agent", "rag_document_agent", "conversation_agent"):
        graph.add_conditional_edges(node, should_self_correct)

    graph.add_edge("self_correct", END)

    return graph.compile()


# Singleton — compiled once at import time
_ROUTER_GRAPH = None


def get_router_graph():
    global _ROUTER_GRAPH
    if _ROUTER_GRAPH is None:
        _ROUTER_GRAPH = build_router_graph()
    return _ROUTER_GRAPH


def route_message(
    session_id: str,
    message: str,
    image_bytes: bytes | None = None,
    document_bytes: bytes | None = None,
    document_mime: str = "application/pdf",
) -> dict:
    """
    Main entry point: run the routing graph for one user message.

    Returns:
        dict with response_text, hospitals, intent.
    """
    initial_state: AgentState = {
        "session_id": session_id,
        "user_message": message,
        "intent": "",
        "hospitals": [],
        "response_text": "",
        "retry_count": 0,
        "image_bytes": image_bytes,
        "document_bytes": document_bytes,
        "document_mime": document_mime,
    }
    graph = get_router_graph()
    final_state = graph.invoke(initial_state)
    return {
        "response_text": final_state.get("response_text", ""),
        "hospitals": final_state.get("hospitals", []),
        "intent": final_state.get("intent", "general_chat"),
    }
