"""
IntentAgent — extract structured SearchIntent from natural language queries.

Uses Anthropic Claude to parse free-text medical queries into a structured
SearchIntent object. Falls back to regex for common patterns (budget in INR,
city names, procedure keywords) when Claude is unavailable.
"""

import json
import os
import re

import anthropic

from models.schemas import SearchIntent
from models.database import get_available_cities


# Cache for available cities — fetched from database on first use
_AVAILABLE_CITIES_CACHE = None


def _get_available_cities_cached() -> set[str]:
    """
    Fetch available cities from database, caching the result.
    
    Fallback to empty set if database is unavailable.
    """
    global _AVAILABLE_CITIES_CACHE
    if _AVAILABLE_CITIES_CACHE is None:
        try:
            cities = get_available_cities()
            _AVAILABLE_CITIES_CACHE = {city.lower() for city in cities if city}
        except Exception:
            # Database unavailable; use empty set (Claude will handle city parsing)
            _AVAILABLE_CITIES_CACHE = set()
    return _AVAILABLE_CITIES_CACHE

# Common specialty keywords mapped to canonical specialty names
_SPECIALTY_KEYWORDS: dict[str, str] = {
    "heart": "Cardiac Surgery",
    "cardiac": "Cardiac Surgery",
    "cardio": "Cardiac Surgery",
    "bypass": "Cardiac Surgery",
    "knee": "Orthopaedics",
    "hip": "Orthopaedics",
    "spine": "Orthopaedics",
    "ortho": "Orthopaedics",
    "bone": "Orthopaedics",
    "brain": "Neurosurgery",
    "neuro": "Neurosurgery",
    "stroke": "Neurology",
    "cancer": "Oncology",
    "tumour": "Oncology",
    "tumor": "Oncology",
    "chemo": "Oncology",
    "kidney": "Nephrology",
    "renal": "Nephrology",
    "dialysis": "Nephrology",
    "liver": "Hepatology",
    "transplant": "Transplant Surgery",
    "eye": "Ophthalmology",
    "cataract": "Ophthalmology",
    "diabetes": "Diabetology",
    "gastro": "Gastroenterology",
    "bariatric": "Bariatric Surgery",
    "obesity": "Bariatric Surgery",
}

# Procedure to specialty inference mapping
_PROCEDURE_TO_SPECIALTY: dict[str, str] = {
    "knee replacement": "Orthopaedics",
    "total knee replacement": "Orthopaedics",
    "hip replacement": "Orthopaedics",
    "hip fracture": "Orthopaedics",
    "spine fusion": "Spine Surgery",
    "spine surgery": "Spine Surgery",
    "fracture fixation": "Orthopaedics",
    "bypass": "Cardiac Surgery",
    "bypass surgery": "Cardiac Surgery",
    "cabg": "Cardiac Surgery",
    "angioplasty": "Cardiac Surgery",
    "heart valve": "Cardiac Surgery",
    "valve replacement": "Cardiac Surgery",
    "coronary angioplasty": "Cardiac Surgery",
    "dialysis": "Nephrology",
    "kidney transplant": "Nephrology",
    "renal": "Nephrology",
    "chemotherapy": "Oncology",
    "chemo": "Oncology",
    "radiation": "Oncology",
    "radiotherapy": "Oncology",
    "tumor removal": "Oncology",
    "cancer treatment": "Oncology",
    "cataract surgery": "Ophthalmology",
    "lasik": "Ophthalmology",
    "eye surgery": "Ophthalmology",
    "glaucoma": "Ophthalmology",
    "bariatric surgery": "Bariatric Surgery",
    "gastric bypass": "Bariatric Surgery",
    "weight loss surgery": "Bariatric Surgery",
    "appendectomy": "General Surgery",
    "hernia repair": "General Surgery",
    "gallbladder surgery": "General Surgery",
    "c section": "Obstetrics",
    "cesarean": "Obstetrics",
    "delivery": "Obstetrics",
}


def _extract_budget_regex(text: str) -> int | None:
    """
    Extract a budget ceiling from text using regex patterns.

    Handles formats like: 5L, 5 lakhs, ₹5L, Rs 5 lakh, 500000, 5,00,000.

    Args:
        text: Raw query text.

    Returns:
        Budget in INR as int, or None if not found.
    """
    text_lower = text.lower().replace(",", "")

    # Match "5l", "5 l", "5 lakh", "5 lakhs", "5.5 lakh"
    m = re.search(r"(?:rs\.?|₹|inr)?\s*(\d+(?:\.\d+)?)\s*(?:l\b|lakh|lakhs|lac\b|lacs\b)", text_lower)
    if m:
        return int(float(m.group(1)) * 100_000)

    # Match plain numbers >= 10000 as direct INR amounts
    m = re.search(r"(?:under|below|within|budget|upto|up to|less than)\s*(?:rs\.?|₹|inr)?\s*(\d{5,})", text_lower)
    if m:
        return int(m.group(1))

    return None


def _extract_city_regex(text: str) -> str | None:
    """
    Extract a city from the query text by matching against available database cities.

    Args:
        text: Raw query text.

    Returns:
        Canonical city name (title-cased), or None.
    """
    text_lower = text.lower()
    available_cities = _get_available_cities_cached()
    
    # If database is unavailable, Claude will handle city extraction
    if not available_cities:
        return None
    
    for city in available_cities:
        if re.search(r"\b" + city + r"\b", text_lower):
            return city.title()
    return None


def _extract_specialty_regex(text: str) -> str | None:
    """
    Map keyword mentions to canonical specialty names.

    Args:
        text: Raw query text.

    Returns:
        Canonical specialty string, or None.
    """
    text_lower = text.lower()
    for keyword, specialty in _SPECIALTY_KEYWORDS.items():
        if keyword in text_lower:
            return specialty
    return None


def _extract_procedure_regex(text: str) -> str | None:
    """
    Extract a procedure mentioned in the query text.
    
    Matches against the procedure-to-specialty mapping keys (sorted by length
    descending, so longer phrases match first to avoid partial matches).

    Args:
        text: Raw query text.

    Returns:
        Procedure string if found, otherwise None.
    """
    text_lower = text.lower().replace(",", " ").replace(".", " ")
    
    # Sort procedures by length (desc) to match longer phrases first
    sorted_procedures = sorted(_PROCEDURE_TO_SPECIALTY.keys(), key=len, reverse=True)
    for procedure in sorted_procedures:
        if re.search(r"\b" + re.escape(procedure) + r"\b", text_lower):
            return procedure
    return None


def _infer_specialty_from_procedure(procedure: str) -> str | None:
    """
    Infer specialty from a procedure name.

    Args:
        procedure: The procedure name (e.g., "knee replacement").

    Returns:
        Canonical specialty string, or None.
    """
    return _PROCEDURE_TO_SPECIALTY.get(procedure.lower())


def extract_intent(query: str) -> SearchIntent:
    """
    Parse a natural language medical query into a structured SearchIntent.

    First attempts Anthropic Claude for nuanced extraction. Falls back to
    regex-based extraction if the API call fails.

    Args:
        query: Natural language string, e.g. "knee replacement under 5L in Chennai".

    Returns:
        SearchIntent with procedure, specialty, city, budget_max, and insurance_type populated
        wherever possible.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            return _extract_with_claude(query, api_key)
        except Exception:
            pass  # Silently fall through to regex

    return _extract_with_regex(query)


def _extract_with_claude(query: str, api_key: str) -> SearchIntent:
    """
    Use Claude to extract structured intent from the query.

    Args:
        query: The user's natural language query.
        api_key: Anthropic API key.

    Returns:
        SearchIntent populated by Claude's response.

    Raises:
        Exception: Any Anthropic API error, so caller can fall back to regex.
    """
    client = anthropic.Anthropic(api_key=api_key)

    system = """You are a medical query parser for a hospital recommendation system in Tamil Nadu, India.

Extract the following fields from the user's query and respond ONLY with valid JSON:
{
  "procedure": "<specific medical procedure or null>",
  "specialty": "<medical specialty or null>",
  "city": "<Tamil Nadu city or null>",
  "budget_max": <integer in INR or null>,
  "insurance_type": "<insurance type mentioned or null>"
}

Rules:
- budget_max: convert to INR integers (5 lakhs = 500000, 5L = 500000)
- specialty: use standard names like "Cardiac Surgery", "Orthopaedics", "Neurosurgery", "Oncology", "Nephrology"
- If the user mentions a procedure (knee replacement), infer the specialty (Orthopaedics)
- Return null for any field that is not mentioned"""

    message = client.messages.create(
        model=os.getenv("CLAUDE_MODEL_ID", "claude-3-5-haiku-20241022"),
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": query}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    data = json.loads(raw)
    return SearchIntent(
        procedure=data.get("procedure"),
        specialty=data.get("specialty"),
        city=data.get("city"),
        budget_max=data.get("budget_max"),
        insurance_type=data.get("insurance_type"),
        raw_query=query,
    )


def _extract_with_regex(query: str) -> SearchIntent:
    """
    Fallback intent extraction using regex and keyword matching.

    When a procedure is extracted but no specialty is found, infers the specialty
    from the procedure-to-specialty mapping.

    Args:
        query: The user's natural language query.

    Returns:
        SearchIntent with fields populated where regex matches.
    """
    procedure = _extract_procedure_regex(query)
    specialty = _extract_specialty_regex(query)
    
    # If no explicit specialty but procedure exists, infer specialty from procedure
    if not specialty and procedure:
        specialty = _infer_specialty_from_procedure(procedure)
    
    return SearchIntent(
        procedure=procedure,
        specialty=specialty,
        city=_extract_city_regex(query),
        budget_max=_extract_budget_regex(query),
        insurance_type=None,
        raw_query=query,
    )
