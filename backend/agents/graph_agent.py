"""
backend/agents/graph_agent.py
LangGraph-based CarePath AI orchestrator — routes each user message through
specialised nodes: hospital search, X-ray analysis, prescription parsing, or
general conversation.

Replaces the old Anthropic-based ConversationAgent with a fully local,
zero-cloud-dependency pipeline powered by Ollama + MedGemma 1.5 4B.
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional, TypedDict

from langgraph.graph import StateGraph, END

from ..config.settings import settings
from ..services.ollama_service import OllamaService
from ..models.schemas import ChatResponse, ExtractionResult, UIAction
from ..models.database import (
    get_conversation_history,
    save_conversation_turn,
    get_latest_extraction,
)
from .intent_agent import extract_intent
from .hospital_matcher import match_hospitals
from .navigation_agent import generate_actions

logger = logging.getLogger(__name__)

_ollama = OllamaService(
    base_url=settings.OLLAMA_BASE_URL,
    model=settings.OLLAMA_MODEL,
    timeout=settings.LLM_TIMEOUT,
)


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    session_id: str
    message: str
    history: list[dict]
    intent: str
    condition: Optional[str]
    city: Optional[str]
    hospitals: list
    ui_actions: list
    image_bytes: Optional[bytes]
    extraction: Optional[ExtractionResult]
    response_text: str


# ---------------------------------------------------------------------------
# Node helpers
# ---------------------------------------------------------------------------

def _history_to_messages(history: list[dict]) -> list[dict]:
    """Convert DB conversation history to Ollama message format."""
    messages = []
    for turn in history[-10:]:  # last 10 turns for context window efficiency
        messages.append({"role": "user", "content": turn.get("user", "")})
        if turn.get("assistant"):
            messages.append({"role": "assistant", "content": turn["assistant"]})
    return messages


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def router_node(state: AgentState) -> AgentState:
    """Classify the user's intent to route to the right node."""
    try:
        result = extract_intent(state["message"])
        state["intent"] = result.get("intent", "general")
        state["condition"] = result.get("condition")
        state["city"] = result.get("city")
    except Exception as e:
        logger.warning("Intent extraction failed, defaulting to general: %s", e)
        state["intent"] = "general"
    return state


def hospital_node(state: AgentState) -> AgentState:
    """Match hospitals from the local CSV/DB based on condition and city."""
    try:
        hospitals = match_hospitals(
            condition=state.get("condition") or state["message"],
            city=state.get("city"),
        )
        state["hospitals"] = hospitals[:5]  # top 5 results

        if hospitals:
            names = ", ".join(h.get("name", "") for h in hospitals[:3])
            state["response_text"] = (
                f"I found {len(hospitals)} hospitals matching your needs in Tamil Nadu. "
                f"Top matches: {names}. "
                f"Please consult a board-certified professional for a clinical evaluation."
            )
        else:
            state["response_text"] = (
                "I couldn't find hospitals matching that specific criteria. "
                "Please try broadening your search or contact a medical tourism coordinator. "
                "Please consult a board-certified professional for a clinical evaluation."
            )

        state["ui_actions"] = generate_actions(
            intent=state["intent"],
            hospitals=state["hospitals"],
        )
    except Exception as e:
        logger.error("Hospital matching error: %s", e, exc_info=True)
        state["response_text"] = (
            "I'm having trouble searching our hospital database right now. "
            "Please try again in a moment."
        )
    return state


async def xray_node_async(state: AgentState) -> AgentState:
    """Analyse an X-ray or medical image using MedGemma multimodal capability."""
    image_bytes = state.get("image_bytes")
    if not image_bytes:
        state["response_text"] = (
            "I don't see an image attached. Please upload your X-ray or medical scan."
        )
        return state

    prompt = (
        f"Please analyse this medical image. {state['message']}\n\n"
        "Provide: 1) Key findings, 2) Possible conditions visible, "
        "3) Recommended next steps. "
        "Remember: this is an AI-generated summary, not a clinical diagnosis."
    )

    tokens = []
    async for token in _ollama.generate_with_image(
        text_prompt=prompt,
        image_bytes=image_bytes,
        system_prompt=settings.SYSTEM_PROMPT,
    ):
        tokens.append(token)

    response = "".join(tokens)
    if not response.endswith("."):
        response += "."
    response += (
        "\n\n⚠️ Please consult a board-certified professional for a clinical evaluation."
    )

    state["response_text"] = response
    return state


async def general_node_async(state: AgentState) -> AgentState:
    """Handle general medical questions via CarePath AI (Ollama/MedGemma)."""
    history_msgs = _history_to_messages(state.get("history", []))
    history_msgs.append({"role": "user", "content": state["message"]})

    tokens = []
    async for token in _ollama.generate_stream(
        messages=history_msgs,
        system_prompt=settings.SYSTEM_PROMPT,
    ):
        tokens.append(token)

    state["response_text"] = "".join(tokens)
    return state


def save_node(state: AgentState) -> AgentState:
    """Persist the conversation turn to the database."""
    try:
        save_conversation_turn(
            session_id=state["session_id"],
            user_message=state["message"],
            assistant_response=state["response_text"],
        )
    except Exception as e:
        logger.warning("Could not save conversation turn: %s", e)
    return state


# ---------------------------------------------------------------------------
# Routing logic
# ---------------------------------------------------------------------------

def route_intent(state: AgentState) -> str:
    intent = state.get("intent", "general")
    if intent in ("hospital_search", "cost_inquiry", "specialist_search"):
        return "hospital"
    if intent == "xray_analysis":
        return "xray"
    return "general"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def _build_graph():
    graph = StateGraph(AgentState)

    # Sync nodes
    graph.add_node("router", router_node)
    graph.add_node("save", save_node)

    # Async nodes wrapped for LangGraph compatibility
    async def _hospital(state):
        return hospital_node(state)

    async def _xray(state):
        return await xray_node_async(state)

    async def _general(state):
        return await general_node_async(state)

    graph.add_node("hospital", _hospital)
    graph.add_node("xray", _xray)
    graph.add_node("general", _general)

    # Edges
    graph.set_entry_point("router")
    graph.add_conditional_edges("router", route_intent, {
        "hospital": "hospital",
        "xray": "xray",
        "general": "general",
    })
    graph.add_edge("hospital", "save")
    graph.add_edge("xray", "save")
    graph.add_edge("general", "save")
    graph.add_edge("save", END)

    return graph.compile()


_graph = _build_graph()


# ---------------------------------------------------------------------------
# Public API — called from main.py
# ---------------------------------------------------------------------------

def process_message(
    session_id: str,
    message: str,
    extraction: Optional[ExtractionResult] = None,
    image_bytes: Optional[bytes] = None,
) -> ChatResponse:
    """
    Synchronous wrapper — runs the LangGraph pipeline and returns ChatResponse.
    Called by the non-streaming POST /api/chat endpoint.
    """
    try:
        history = get_conversation_history(session_id)
    except Exception:
        history = []

    initial_state: AgentState = {
        "session_id": session_id,
        "message": message,
        "history": history,
        "intent": "general",
        "condition": None,
        "city": None,
        "hospitals": [],
        "ui_actions": [],
        "image_bytes": image_bytes,
        "extraction": extraction,
        "response_text": "",
    }

    final_state = asyncio.run(_graph.ainvoke(initial_state))

    return ChatResponse(
        session_id=session_id,
        response=final_state["response_text"],
        ui_actions=final_state.get("ui_actions", []),
        matched_hospitals=final_state.get("hospitals", []),
    )


async def stream_message(
    session_id: str,
    message: str,
    extraction: Optional[ExtractionResult] = None,
    image_bytes: Optional[bytes] = None,
) -> AsyncGenerator[str, None]:
    """
    Async generator — streams tokens for the SSE endpoint POST /api/chat/stream.

    Routes to hospital_node (no streaming needed, fast DB lookup) or directly
    streams from Ollama for general and X-ray nodes.
    """
    try:
        history = get_conversation_history(session_id)
    except Exception:
        history = []

    # Run router synchronously to decide path
    temp_state: AgentState = {
        "session_id": session_id,
        "message": message,
        "history": history,
        "intent": "general",
        "condition": None,
        "city": None,
        "hospitals": [],
        "ui_actions": [],
        "image_bytes": image_bytes,
        "extraction": extraction,
        "response_text": "",
    }
    temp_state = router_node(temp_state)
    intent = temp_state.get("intent", "general")

    if intent in ("hospital_search", "cost_inquiry", "specialist_search"):
        # Hospital results are fast — run full node and yield complete response
        temp_state = hospital_node(temp_state)
        save_node(temp_state)
        yield temp_state["response_text"]

    elif intent == "xray_analysis" and image_bytes:
        # Stream X-ray analysis token-by-token
        prompt = (
            f"Please analyse this medical image. {message}\n\n"
            "Provide: 1) Key findings, 2) Possible conditions visible, "
            "3) Recommended next steps."
        )
        full_response = []
        async for token in _ollama.generate_with_image(
            text_prompt=prompt,
            image_bytes=image_bytes,
            system_prompt=settings.SYSTEM_PROMPT,
        ):
            full_response.append(token)
            yield token

        disclaimer = (
            "\n\n⚠️ Please consult a board-certified professional for a clinical evaluation."
        )
        yield disclaimer
        save_conversation_turn(session_id, message, "".join(full_response) + disclaimer)

    else:
        # Stream general CarePath AI response
        history_msgs = _history_to_messages(history)
        history_msgs.append({"role": "user", "content": message})

        full_response = []
        async for token in _ollama.generate_stream(
            messages=history_msgs,
            system_prompt=settings.SYSTEM_PROMPT,
        ):
            full_response.append(token)
            yield token

        try:
            save_conversation_turn(session_id, message, "".join(full_response))
        except Exception as e:
            logger.warning("Could not save streaming turn: %s", e)
