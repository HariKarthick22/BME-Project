"""
ConversationAgent — Master Orchestrator with Claude

Routes requests to appropriate sub-agents:
- IntentAgent for natural language queries
- PrescriptionParserAgent for prescription uploads

Coordinates HospitalMatchingAgent and NavigationAgent.
Maintains session state.
Formats final response with text and UI actions.
"""

from __future__ import annotations
import os
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class ChatMessage:
    """A chat message in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=lambda: __import__("time").time())


@dataclass
class ConversationResponse:
    """Response from the conversation agent."""
    text: str
    actions: list[dict]
    session_id: str
    results_count: int = 0
    hospitals: list[dict] = field(default_factory=list)


class ConversationAgent:
    """
    Master orchestrator for the MediOrbit system.
    
    Uses Claude API to:
    1. Understand user intent from natural language
    2. Route to appropriate sub-agents
    3. Coordinate hospital matching
    4. Generate UI actions
    5. Format friendly responses
    """
    
    SYSTEM_PROMPT = """You are MediOrbit, a helpful medical hospital recommendation assistant.

Your role:
- Help users find suitable hospitals based on their medical needs
- Understand symptoms, procedures, and medical requirements
- Provide personalized recommendations with explanations
- Guide users through the application with clear next steps

When responding:
- Be conversational and friendly
- Explain your recommendations
- Mention specific hospitals, costs, and key features
- Suggest clear next actions
- If you don't have enough information, ask clarifying questions

You have access to these tools:
- Intent parsing: Understand what the user is looking for
- Hospital matching: Find and rank hospitals based on criteria
- Prescription parser: Extract medical information from uploaded prescriptions

Always provide a helpful, informative response that guides the user forward."""

    def __init__(self, api_key: str | None = None):
        self._client = None
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        
        if ANTHROPIC_AVAILABLE and self._api_key:
            self._client = anthropic.Anthropic(api_key=self._api_key)
        
        self._intent_agent = None
        self._matcher = None
        self._navigation_agent = None
        self._prescription_parser = None
        
        self._sessions: dict[str, list[ChatMessage]] = {}
    
    def _lazy_init_agents(self):
        """Lazy initialization of sub-agents."""
        if self._intent_agent is None:
            from agents.intent_agent import IntentAgent
            self._intent_agent = IntentAgent(self._api_key)
        
        if self._matcher is None:
            from agents.hospital_matcher_v2 import HospitalMatchingAgent
            self._matcher = HospitalMatchingAgent()
        
        if self._navigation_agent is None:
            from agents.navigation_agent import NavigationAgent
            self._navigation_agent = NavigationAgent()
    
    def chat(
        self,
        message: str,
        session_id: str = "default",
        prescription_data: dict | None = None
    ) -> ConversationResponse:
        """
        Process a chat message and return a response.
        
        Parameters
        ----------
        message : str
            User's message
        session_id : str
            Session identifier for conversation state
        prescription_data : dict, optional
            Pre-parsed prescription data from upload
            
        Returns
        -------
        ConversationResponse
            Response with text, actions, and hospital results
        """
        self._lazy_init_agents()
        
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        
        session = self._sessions[session_id]
        session.append(ChatMessage(role="user", content=message))
        
        extracted_intent = None
        hospitals = []
        actions = []
        results_count = 0
        
        try:
            if prescription_data:
                extracted_intent = self._process_prescription_data(prescription_data)
            else:
                extracted_intent = self._intent_agent.parse(message)
            
            logger.info(f"Parsed intent: {extracted_intent}")
            
            if extracted_intent and (extracted_intent.procedure or extracted_intent.category or extracted_intent.city):
                hospitals = self._matcher.match(extracted_intent, limit=20)
                results_count = len(hospitals)
                
                logger.info(f"Found {results_count} hospitals")
                
                if hospitals:
                    actions = self._navigation_agent.generate_actions(
                        hospitals, extracted_intent, results_count
                    )
                else:
                    actions = [self._navigation_agent._navigation_agent.generate_error_actions(
                        "No hospitals found matching your criteria. Try adjusting your search."
                    )[0].to_dict()]
            else:
                actions = self._navigation_agent.generate_welcome_actions()
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            actions = self._navigation_agent.generate_error_actions(
                "Sorry, I encountered an error processing your request."
            )
        
        response_text = self._format_response(
            message, extracted_intent, hospitals, results_count
        )
        
        session.append(ChatMessage(role="assistant", content=response_text))
        
        return ConversationResponse(
            text=response_text,
            actions=actions,
            session_id=session_id,
            results_count=results_count,
            hospitals=[
                {
                    "id": h.hospital_id,
                    "name": h.name,
                    "city": h.city,
                    "type": h.type,
                    "accreditation": h.accreditation,
                    "rating": h.rating,
                    "procedure": h.procedure_name,
                    "category": h.category,
                    "cost_avg": h.cost_avg_inr,
                    "cost_min": h.cost_min_inr,
                    "cost_max": h.cost_max_inr,
                    "success_rate": h.success_rate_pct,
                    "insurance": h.insurance_schemes,
                    "availability": h.availability,
                    "score": h.total_score,
                    "reasons": h.match_reasons
                }
                for h in hospitals[:10]
            ]
        )
    
    def _process_prescription_data(self, data: dict) -> "SearchIntent":
        """Process prescription data into search intent."""
        from agents.intent_agent import SearchIntent
        
        diagnoses = data.get("diagnoses", [])
        procedures = data.get("procedures", [])
        
        procedure = procedures[0] if procedures else None
        
        category = None
        if diagnoses:
            category = self._infer_category_from_diagnoses(diagnoses)
        
        return SearchIntent(
            procedure=procedure,
            category=category,
            budget_min=None,
            budget_max=None,
            city=None,
            specialty=None,
            insurance=None,
            hospital_type=None,
            rating_min=None,
            raw_query=f"Prescription: {diagnoses + procedures}"
        )
    
    def _infer_category_from_diagnoses(self, diagnoses: list[str]) -> str | None:
        """Infer medical category from diagnoses."""
        text = " ".join(diagnoses).lower()
        
        if any(w in text for w in ["heart", "cardiac", "bypass", "angio"]):
            return "Heart"
        if any(w in text for w in ["brain", "neuro", "stroke"]):
            return "Brain"
        if any(w in text for w in ["ortho", "bone", "joint", "knee", "hip"]):
            return "Ortho"
        if any(w in text for w in ["kidney", "renal", "dialysis"]):
            return "Kidney"
        
        return "General"
    
    def _format_response(
        self,
        message: str,
        intent: "SearchIntent | None",
        hospitals: list,
        results_count: int
    ) -> str:
        """Format a friendly response message."""
        if not intent or (not intent.procedure and not intent.category and not intent.city):
            return (
                "Welcome to MediOrbit! I'm here to help you find the right hospital "
                "for your medical needs.\n\n"
                "You can:\n"
                "• Tell me what procedure you need (e.g., 'knee replacement')\n"
                "• Mention your budget (e.g., 'under ₹5 lakh')\n"
                "• Specify a city (e.g., 'in Chennai')\n"
                "• Upload a prescription for automatic analysis\n\n"
                "How can I help you today?"
            )
        
        if results_count == 0:
            return (
                f"I couldn't find any hospitals matching your requirements for "
                f"'{intent.procedure or intent.category}'"
                + (f" in {intent.city}" if intent.city else "") + ".\n\n"
                "Try adjusting your search criteria, or let me know if you'd like "
                "me to broaden the search."
            )
        
        top = hospitals[0]
        
        response = f"Great news! I found {results_count} hospitals that match your needs.\n\n"
        
        if intent.procedure:
            response += f"Based on your search for '{intent.procedure}'"
        elif intent.category:
            response += f"Based on your search for {intent.category} treatment"
        
        if intent.city:
            response += f" in {intent.city}"
        
        if intent.budget_max:
            response += f" under ₹{intent.budget_max:,}"
        
        response += ".\n\n"
        
        response += f"🏥 **Top Recommendation: {top.name}**\n"
        response += f"   📍 {top.city} | {top.type}\n"
        if top.accreditation:
            response += f"   ✅ {top.accreditation} Accredited\n"
        if top.rating:
            response += f"   ⭐ Rating: {top.rating}/5\n"
        response += f"   💰 Cost: ₹{top.cost_avg_inr:,} (avg)\n"
        response += f"   🏥 Procedure: {top.procedure_name}\n"
        
        if top.match_reasons:
            response += f"   📝 {top.match_reasons[1] if len(top.match_reasons) > 1 else top.match_reasons[0]}\n"
        
        if results_count > 1:
            response += f"\n...and {results_count - 1} more hospitals found.\n"
        
        response += "\nI've highlighted the top result and navigated to the results page. "
        response += "Click on any hospital to see full details!"
        
        return response
    
    def get_session_history(self, session_id: str) -> list[ChatMessage]:
        """Get conversation history for a session."""
        return self._sessions.get(session_id, [])
    
    def clear_session(self, session_id: str) -> None:
        """Clear a session's history."""
        if session_id in self._sessions:
            del self._sessions[session_id]


def chat_with_user(
    message: str,
    session_id: str = "default",
    prescription_data: dict | None = None
) -> ConversationResponse:
    """
    Convenience function to chat with the agent.
    
    Parameters
    ----------
    message : str
        User message
    session_id : str
        Session ID
    prescription_data : dict, optional
        Prescription data from upload
        
    Returns
    -------
    ConversationResponse
        Agent response
    """
    agent = ConversationAgent()
    return agent.chat(message, session_id, prescription_data)


if __name__ == "__main__":
    agent = ConversationAgent()
    
    test_queries = [
        "knee replacement under ₹5L Chennai",
        "heart bypass surgery in Delhi",
        "best hospital for general checkup",
    ]
    
    for q in test_queries:
        print(f"\n{'='*60}")
        print(f"User: {q}")
        print(f"{'='*60}")
        
        response = agent.chat(q)
        
        print(f"\nResponse:\n{response.text}")
        print(f"\nActions: {len(response.actions)}")
        print(f"Results: {response.results_count}")