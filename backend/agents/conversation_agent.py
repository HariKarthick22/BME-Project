"""
ConversationAgent — master orchestrator for MediOrbit chat sessions.

Called on every POST /api/chat request. Loads session history, delegates to
IntentAgent and HospitalMatchingAgent, calls the Anthropic API for a natural
language response, and composes the final ChatResponse including UI actions.
"""

import logging
import os

import anthropic

from models.schemas import ChatResponse, ExtractionResult, PatientInfo, UIAction
from models.database import (
    get_conversation_history,
    save_conversation_turn,
    get_latest_extraction,
)
from agents.intent_agent import extract_intent
from agents.hospital_matcher import match_hospitals
from agents.navigation_agent import generate_actions

logger = logging.getLogger(__name__)


def _build_hospital_summary(hospitals: list) -> str:
    """
    Build a concise text summary of the top matched hospitals.

    Args:
        hospitals: List of Hospital objects returned by HospitalMatchingAgent.

    Returns:
        Pipe-separated string of the top 3 hospitals with name, city, and
        AI score, or "None yet" when the list is empty.
    """
    if not hospitals:
        return "None yet"
    parts = [
        f"{h.name} ({h.city}, score {h.ai_score})"
        for h in hospitals[:3]
    ]
    return " | ".join(parts)


def _build_extraction_summary(extraction: ExtractionResult | None) -> str:
    """
    Build a concise text summary of the patient's prescription extraction.

    Args:
        extraction: ExtractionResult from PrescriptionParserAgent, or None.

    Returns:
        Human-readable string with diagnosis, procedure, and medication count,
        or "None" when no extraction is available.
    """
    if extraction is None:
        return "None"
    return (
        f"Diagnosis: {extraction.diagnosis}, "
        f"Procedure: {extraction.procedure}, "
        f"Medications: {len(extraction.medications)} items"
    )


def _fallback_response(hospitals: list, intent_detected: bool) -> str:
    """
    Generate a rule-based response when the Anthropic API is unavailable.

    Args:
        hospitals: List of Hospital objects matched for this session.
        intent_detected: True when IntentAgent found a recognisable query.

    Returns:
        A plain-text fallback response string.
    """
    if hospitals:
        top = hospitals[0]
        return (
            f"I found {len(hospitals)} hospitals matching your needs. "
            f"The top match is {top.name} in {top.city} "
            f"with an AI score of {top.ai_score}."
        )
    if intent_detected:
        return (
            "I couldn't find hospitals matching exactly that criteria. "
            "Try broadening your search."
        )
    return (
        "Hello! I'm MediOrbit's AI assistant. Tell me what medical procedure "
        "you need, your city, and your budget, and I'll find the best hospitals "
        "for you."
    )


def process_message(
    session_id: str,
    message: str,
    extraction: ExtractionResult | None = None,
) -> ChatResponse:
    """
    Orchestrate all agents and return a ChatResponse for the given user message.

    Steps:
        1. Validate input message (non-empty, max 2000 chars).
        2. Load conversation history for the session from the database.
        3. Persist the incoming user message.
        4. Resolve the active ExtractionResult (param overrides DB value).
        5. Compute the current conversation turn number.
        6. Run IntentAgent to extract structured search intent.
        7. Determine whether a meaningful intent was detected.
        8. Run HospitalMatchingAgent when intent or extraction is present.
        9. Build the system prompt and message list for Claude.
        10. Call the Anthropic API for a natural language response.
        11. Get response_text from API response.
        12. Generate UI actions via NavigationAgent.
        13. Persist the assistant response.
        14. Return the assembled ChatResponse.

    Falls back to a rule-based response if the Anthropic API key is absent or
    the API call raises any exception.

    Args:
        session_id: Unique identifier for the chat session.
        message: The user's latest message text.
        extraction: Optional ExtractionResult from a prior prescription parse;
            overrides any extraction stored in the database for this session.

    Returns:
        ChatResponse containing the assistant text, UI actions, and matched
        hospitals.

    Raises:
        ValueError: If message is empty or exceeds 2000 characters.
    """
    # Step 1: Input validation
    if not message or not message.strip():
        raise ValueError("Message cannot be empty")
    if len(message) > 2000:
        raise ValueError("Message exceeds maximum length of 2000 characters")
    # Step 2: Load conversation history
    history = get_conversation_history(session_id)

    # Step 3: Save the user message
    save_conversation_turn(session_id, "user", message)

    # Step 4: Resolve active extraction — param takes precedence over DB
    if extraction is not None:
        active_extraction = extraction
    else:
        raw = get_latest_extraction(session_id)
        if raw is not None:
            # get_latest_extraction returns a flat dict; reconstruct the model
            patient = PatientInfo(
                age=raw.get("patient_age"),
                gender=raw.get("patient_gender"),
            )
            active_extraction = ExtractionResult(
                diagnosis=raw.get("diagnosis", []),
                procedure=raw.get("procedure", []),
                medications=raw.get("medications", []),
                patient=patient,
                raw_text=raw.get("raw_text", ""),
            )
        else:
            active_extraction = None

    # Step 5: Determine conversation turn (history already saved the user msg)
    conversation_turn = len(history) + 1  # +1 counts the user message just saved above

    # Step 6: Extract structured intent from the message
    intent = extract_intent(message)

    # Step 6b: Enrich intent with extraction data if available
    # Extracted procedures have higher priority for matching
    if active_extraction is not None:
        if active_extraction.procedure and not intent.procedure:
            # Use first extracted procedure as primary search target
            intent.procedure = active_extraction.procedure[0] if isinstance(active_extraction.procedure, list) else active_extraction.procedure

    # Step 7: Decide whether a meaningful intent was found
    intent_detected = bool(
        intent.specialty or intent.procedure or intent.city or intent.budget_max
    )

    # Step 8: Match hospitals when there is intent or prescription data
    if intent_detected or active_extraction is not None:
        hospitals = match_hospitals(intent, active_extraction, top_n=5)
    else:
        hospitals = []

    # Step 9: Build system prompt
    hospital_summary = _build_hospital_summary(hospitals)
    extraction_summary = _build_extraction_summary(active_extraction)

    system_prompt = (
        "You are MediOrbit's medical tourism assistant for Tamil Nadu, India. "
        "You help patients find the best hospitals for their medical needs.\n\n"
        "You are friendly, professional, and concise. Keep responses under 3 sentences.\n\n"
        "When hospitals are found, briefly summarize the top recommendation and invite "
        "the user to ask follow-up questions.\n"
        "When no hospitals are found yet, ask clarifying questions: what procedure do "
        "they need, which city, and their budget.\n"
        "Never make up hospital names or medical facts.\n\n"
        f"Current matched hospitals (if any): {hospital_summary}\n"
        f"Patient extraction data (if any): {extraction_summary}"
    )

    # Build the messages list for Claude (history + current user message)
    claude_messages = [
        {"role": turn["role"], "content": turn["content"]}
        for turn in history
    ]
    claude_messages.append({"role": "user", "content": message})

    # Step 10: Call Anthropic API (with fallback)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    model_id = os.getenv("CLAUDE_MODEL_ID", "claude-3-5-haiku-20241022")
    response_text: str

    if api_key:
        try:
            client = anthropic.Anthropic(api_key=api_key)
            api_response = client.messages.create(
                model=model_id,
                max_tokens=512,
                system=system_prompt,
                messages=claude_messages,
            )
            if api_response.content:
                response_text = api_response.content[0].text
            else:
                response_text = _fallback_response(hospitals, intent_detected)
        except Exception as e:
            logger.warning("Anthropic API call failed: %s", e, exc_info=True)
            response_text = _fallback_response(hospitals, intent_detected)
    else:
        response_text = _fallback_response(hospitals, intent_detected)

    # Step 11: Generate UI actions
    actions = generate_actions(
        session_id,
        hospitals,
        intent_detected,
        message,
        conversation_turn,
    )

    # Step 12: Save the assistant response
    save_conversation_turn(session_id, "assistant", response_text)

    # Step 13: Return the assembled response
    return ChatResponse(
        session_id=session_id,
        text=response_text,
        actions=actions,
        hospitals=hospitals,
    )
