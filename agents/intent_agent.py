"""
IntentAgent — Natural Language Query Understanding

Parses natural language queries into structured SearchIntent using Claude.
Handles queries like:
- "knee replacement under ₹5L Chennai"
- "heart bypass surgery in Delhi"
- "best orthopedic hospital for hip replacement"
"""

from __future__ import annotations
import os
import json
import re
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class SearchIntent:
    """Structured search intent parsed from natural language."""
    procedure: str | None
    category: str | None
    budget_min: int | None
    budget_max: int | None
    city: str | None
    specialty: str | None
    insurance: str | None
    hospital_type: str | None
    rating_min: float | None
    raw_query: str


class IntentAgent:
    """
    Agent for parsing natural language queries into structured SearchIntent.
    
    Uses Claude API for intelligent parsing with fallback to regex-based extraction.
    """
    
    SYSTEM_PROMPT = """You are a medical hospital search intent parser. 
Parse the user's natural language query into a structured search intent.

Extract:
- procedure: the medical procedure or treatment (e.g., "knee replacement", "bypass surgery")
- category: medical category if known (Heart, Brain, Ortho, Kidney, General)
- budget_min: minimum budget in INR (numeric)
- budget_max: maximum budget in INR (numeric) 
- city: city name
- specialty: medical specialty
- insurance: insurance provider/scheme
- hospital_type: type (Private, Government, Trust, etc.)

Return JSON with these fields. Use null for unknown fields.

Example:
Input: "knee replacement under ₹5L Chennai"
Output: {"procedure": "knee replacement", "category": "Ortho", "budget_min": null, "budget_max": 500000, "city": "Chennai", "specialty": null, "insurance": null, "hospital_type": null, "rating_min": null}

Input: "heart surgery in Delhi with insurance"
Output: {"procedure": "heart surgery", "category": "Heart", "budget_min": null, "budget_max": null, "city": "Delhi", "specialty": null, "insurance": "any", "hospital_type": null, "rating_min": null}"""

    def __init__(self, api_key: str | None = None):
        self._client = None
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        
        if ANTHROPIC_AVAILABLE and self._api_key:
            self._client = anthropic.Anthropic(api_key=self._api_key)
    
    def parse(self, query: str) -> SearchIntent:
        """
        Parse natural language query into structured SearchIntent.
        
        Parameters
        ----------
        query : str
            Natural language query (e.g., "knee replacement under ₹5L Chennai")
            
        Returns
        -------
        SearchIntent
            Structured search intent
        """
        if not query or not query.strip():
            return SearchIntent(
                procedure=None, category=None, budget_min=None, budget_max=None,
                city=None, specialty=None, insurance=None, hospital_type=None,
                rating_min=None, raw_query=""
            )
        
        if self._client:
            return self._parse_with_claude(query)
        else:
            return self._parse_fallback(query)
    
    def _parse_with_claude(self, query: str) -> SearchIntent:
        """Parse using Claude API."""
        try:
            message = self._client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": query}]
            )
            
            response_text = message.content[0].text.strip()
            
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                return SearchIntent(
                    procedure=data.get("procedure"),
                    category=data.get("category"),
                    budget_min=data.get("budget_min"),
                    budget_max=data.get("budget_max"),
                    city=data.get("city"),
                    specialty=data.get("specialty"),
                    insurance=data.get("insurance"),
                    hospital_type=data.get("hospital_type"),
                    rating_min=data.get("rating_min"),
                    raw_query=query
                )
            
            logger.warning(f"Could not parse Claude response: {response_text}")
            return self._parse_fallback(query)
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return self._parse_fallback(query)
    
    def _parse_fallback(self, query: str) -> SearchIntent:
        """Fallback regex-based parsing when Claude is not available."""
        query_lower = query.lower()
        
        budget_max = None
        budget_patterns = [
            (r'under\s*₹?(\d+)\s*(l|lakh)', lambda m: int(m.group(1)) * 100000),
            (r'below\s*₹?(\d+)\s*(l|lakh)', lambda m: int(m.group(1)) * 100000),
            (r'less\s*than\s*₹?(\d+)\s*(l|lakh)', lambda m: int(m.group(1)) * 100000),
            (r'₹?(\d+)\s*l', lambda m: int(m.group(1)) * 100000),
            (r'under\s*₹?(\d+)', lambda m: int(m.group(1))),
            (r'below\s*₹?(\d+)', lambda m: int(m.group(1))),
        ]
        
        for pattern, converter in budget_patterns:
            match = re.search(pattern, query_lower)
            if match:
                budget_max = converter(match)
                break
        
        category = None
        category_map = {
            "heart": "Heart", "cardiac": "Heart", "bypass": "Heart",
            "brain": "Brain", "neuro": "Brain", "neurology": "Brain",
            "ortho": "Ortho", "orthopedic": "Ortho", "bone": "Ortho", "joint": "Ortho", "knee": "Ortho", "hip": "Ortho",
            "kidney": "Kidney", "renal": "Kidney", "dialysis": "Kidney",
            "cancer": "Oncology", "tumor": "Oncology",
            "general": "General", "fever": "General", "cold": "General",
        }
        
        for keyword, cat in category_map.items():
            if keyword in query_lower:
                category = cat
                break
        
        city = None
        major_cities = [
            "chennai", "delhi", "mumbai", "bangalore", "hyderabad",
            "kolkata", "pune", "coimbatore", "madurai", "trichy"
        ]
        for city_name in major_cities:
            if city_name in query_lower:
                city = city_name.title()
                break
        
        hospital_type = None
        if "government" in query_lower or "govt" in query_lower:
            hospital_type = "Government"
        elif "private" in query_lower:
            hospital_type = "Private"
        elif "trust" in query_lower:
            hospital_type = "Private (Trust)"
        
        insurance = None
        if "insurance" in query_lower or "insured" in query_lower:
            insurance = "any"
        
        procedure = query
        for remove_word in ["under", "in", "with", "for", "near", "best", "cheap", "affordable"]:
            procedure = re.sub(rf'\b{remove_word}\b', '', procedure, flags=re.IGNORECASE)
        procedure = procedure.strip()
        
        if len(procedure) < 3 or procedure.lower() in ["search", "find", "show", "list"]:
            procedure = None
        
        return SearchIntent(
            procedure=procedure,
            category=category,
            budget_min=None,
            budget_max=budget_max,
            city=city,
            specialty=None,
            insurance=insurance,
            hospital_type=hospital_type,
            rating_min=None,
            raw_query=query
        )


def parse_intent(query: str) -> SearchIntent:
    """
    Convenience function to parse query into SearchIntent.
    
    Parameters
    ----------
    query : str
        Natural language query
        
    Returns
    -------
    SearchIntent
        Structured search intent
    """
    agent = IntentAgent()
    return agent.parse(query)


if __name__ == "__main__":
    test_queries = [
        "knee replacement under ₹5L Chennai",
        "heart bypass surgery in Delhi with insurance",
        "best orthopedic hospital for hip replacement",
        "kidney dialysis in Coimbatore under ₹3 lakh",
    ]
    
    agent = IntentAgent()
    for q in test_queries:
        intent = agent.parse(q)
        print(f"\nQuery: {q}")
        print(f"  Procedure: {intent.procedure}")
        print(f"  Category: {intent.category}")
        print(f"  Budget: {intent.budget_min} - {intent.budget_max}")
        print(f"  City: {intent.city}")
        print(f"  Type: {intent.hospital_type}")