"""Anthropic Claude integration for medical analysis and recommendations."""
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MedicalAssistant:
    """Anthropic Claude-powered medical tourism assistant."""

    SYSTEM_PROMPT = """You are an expert medical tourism consultant specializing in hospitals and healthcare in Tamil Nadu, India. 
Your role is to:
1. Understand patient's medical needs, conditions, and budget
2. Recommend appropriate hospitals based on their requirements
3. Explain procedures, success rates, and costs clearly
4. Provide compassionate, professional medical tourism guidance
5. Always emphasize consulting with physicians for medical decisions

Key guidelines:
- Be empathetic and professional
- Provide evidence-based recommendations
- Consider cost, quality, and convenience
- Never provide medical diagnosis or treatment advice
- Always recommend verified medical professionals
- Maintain patient privacy and confidentiality"""

    def __init__(self):
        """Initialize Anthropic Claude client."""
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model_id = os.getenv("CLAUDE_MODEL_ID", "claude-3-5-haiku-20241022")
        self.client = None
        self._initialize_client()
        logger.info(f"MedicalAssistant initialized with model: {self.model_id}")

    def _initialize_client(self):
        """Initialize Anthropic client with error handling."""
        try:
            from anthropic import Anthropic

            self.client = Anthropic(api_key=self.api_key)
            logger.info("Anthropic client initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize Anthropic client: {e}")
            self.client = None

    def analyze_medical_condition(
        self, condition: str, age: Optional[int] = None, budget: Optional[float] = None
    ) -> Dict[str, Any]:
        """Analyze medical condition and provide recommendations."""
        if not self.client:
            return {
                "status": "error",
                "message": "Anthropic client not available",
            }

        try:
            prompt = self._build_analysis_prompt(condition, age, budget)

            response = self.client.messages.create(
                model=self.model_id,
                max_tokens=1000,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            analysis = response.content[0].text

            return {
                "status": "success",
                "analysis": analysis,
                "condition": condition,
                "metadata": {
                    "model": self.model_id,
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    },
                },
            }
        except Exception as e:
            logger.error(f"Medical analysis failed: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    def recommend_hospitals(
        self, condition: str, location: str = "Tamil Nadu"
    ) -> Dict[str, Any]:
        """Recommend hospitals based on condition and location."""
        if not self.client:
            return {
                "status": "error",
                "message": "Anthropic client not available",
            }

        try:
            prompt = f"""Based on the following medical condition, provide hospital recommendations in {location}:
            
Condition: {condition}

Please recommend 3-5 hospitals in {location} that are well-suited for treating this condition. Include:
1. Hospital name
2. Specialization relevant to the condition
3. Estimated cost range (in INR)
4. Key strengths/accreditations
5. Why it's recommended for this condition

Format as a structured list."""

            response = self.client.messages.create(
                model=self.model_id,
                max_tokens=1500,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            recommendations = response.content[0].text

            return {
                "status": "success",
                "recommendations": recommendations,
                "condition": condition,
                "location": location,
            }
        except Exception as e:
            logger.error(f"Hospital recommendation failed: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    def process_chat_message(
        self,
        message: str,
        session_id: str,
        conversation_history: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Process chat message and provide response."""
        if not self.client:
            return {
                "status": "error",
                "message": "Anthropic client not available",
            }

        try:
            # Build message history
            messages = []
            if conversation_history:
                messages.extend(conversation_history)

            # Add current message
            messages.append({"role": "user", "content": message})

            # Get Claude response
            response = self.client.messages.create(
                model=self.model_id,
                max_tokens=800,
                system=self.SYSTEM_PROMPT,
                messages=messages,
            )

            assistant_response = response.content[0].text

            return {
                "status": "success",
                "response": assistant_response,
                "session_id": session_id,
                "message": message,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            }
        except Exception as e:
            logger.error(f"Chat processing failed: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    def extract_intent(self, message: str) -> Dict[str, Any]:
        """Extract intent from user message (diagnosis, recommendation, comparison, etc)."""
        if not self.client:
            return {
                "status": "error",
                "intent": "unknown",
            }

        try:
            intent_prompt = f"""Analyze the following user message and determine their primary intent. 
Return ONLY the intent type and key entities in JSON format.

User message: "{message}"

Intent types: diagnosis_request, hospital_recommendation, cost_comparison, procedure_inquiry, symptom_description, general_inquiry

Return as JSON:
{{"intent": "intent_type", "entities": ["entity1", "entity2"], "condition": "if applicable"}}"""

            response = self.client.messages.create(
                model=self.model_id,
                max_tokens=200,
                system="You are a medical intent classifier. Always respond in valid JSON format.",
                messages=[{"role": "user", "content": intent_prompt}],
            )

            import json

            response_text = response.content[0].text
            try:
                intent_data = json.loads(response_text)
            except json.JSONDecodeError:
                intent_data = {
                    "intent": "general_inquiry",
                    "entities": [],
                }

            return {
                "status": "success",
                "intent": intent_data.get("intent", "unknown"),
                "entities": intent_data.get("entities", []),
                "condition": intent_data.get("condition"),
            }
        except Exception as e:
            logger.error(f"Intent extraction failed: {e}")
            return {
                "status": "error",
                "intent": "unknown",
                "error": str(e),
            }

    def _build_analysis_prompt(
        self, condition: str, age: Optional[int], budget: Optional[float]
    ) -> str:
        """Build prompt for medical condition analysis."""
        prompt = f"I need information about {condition}"

        if age:
            prompt += f" for a {age}-year-old patient"

        if budget:
            prompt += f" with a budget of ₹{budget:.0f}"

        prompt += (
            """. Please provide:
1. Overview of the condition
2. Treatment options available in Tamil Nadu
3. Expected cost range
4. Recovery timeline
5. Recommended hospitals/specializations

Keep response professional but easy to understand."""
        )

        return prompt
