"""
NavigationAgent — UI action command generator.

Pure-function module that takes conversation context and matched hospitals,
then returns a list of UIAction objects for the frontend NavigationAgent.js
to execute. No external API calls or database access.
"""

import re

from ..models.schemas import Hospital, UIAction
from ..models.database import get_available_cities


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
            # Database unavailable; fallback to minimal set for graceful degradation
            _AVAILABLE_CITIES_CACHE = set()
    return _AVAILABLE_CITIES_CACHE

# Keywords that indicate a price/budget filter is desired
_PRICE_KEYWORDS = {"under", "below", "budget", "affordable", "cheapest"}

# Keywords that indicate the user wants a side-by-side comparison
_COMPARISON_KEYWORDS = {"compare", "vs", "versus", "difference between"}


def _detect_city(message: str) -> str | None:
    """
    Scan the message for any available city name from the database.

    Uses whole-word matching so "Salem" inside "Jerusalem" is not a false
    positive.

    Args:
        message: Raw user message text.

    Returns:
        Title-cased city name if found, otherwise None.
    """
    text_lower = message.lower()
    available_cities = _get_available_cities_cached()
    
    # If no cities available from database, return None
    if not available_cities:
        return None
    
    for city in available_cities:
        if re.search(r"\b" + re.escape(city) + r"\b", text_lower):
            return city.title()
    return None


def _detect_hospital_name_match(message: str, hospitals: list[Hospital]) -> Hospital | None:
    """
    Check whether the message contains the full name of exactly one hospital
    from the provided list (case-insensitive whole-name match).

    Args:
        message: Raw user message text.
        hospitals: Candidate Hospital objects to check against.

    Returns:
        The matching Hospital if exactly one name is found in the message,
        otherwise None.
    """
    message_lower = message.lower()
    matches = [h for h in hospitals if re.search(r'\b' + re.escape(h.name.lower()) + r'\b', message_lower)]
    return matches[0] if len(matches) == 1 else None


def _has_price_keyword(message: str) -> bool:
    """
    Return True if the message contains any price/budget-related keyword.

    Args:
        message: Raw user message text.

    Returns:
        True if a price keyword is present, False otherwise.
    """
    text_lower = message.lower()
    return any(kw in text_lower for kw in _PRICE_KEYWORDS)


def _has_comparison_keyword(message: str) -> bool:
    """
    Return True if the message contains any comparison-related keyword.

    Args:
        message: Raw user message text.

    Returns:
        True if a comparison keyword is present, False otherwise.
    """
    text_lower = message.lower()
    return any(kw in text_lower for kw in _COMPARISON_KEYWORDS)


def _deduplicate(actions: list[UIAction]) -> list[UIAction]:
    """
    Remove duplicate UIAction entries where both type and payload are identical.

    Preserves original ordering, keeping the first occurrence of each
    type+payload combination.

    Args:
        actions: Possibly-redundant list of UIAction objects.

    Returns:
        New list with duplicate actions removed.
    """
    seen: set[tuple] = set()
    result: list[UIAction] = []
    for action in actions:
        # Convert payload dict to a frozenset of items for hashability
        try:
            key = (action.type, frozenset(
                (k, tuple(v) if isinstance(v, list) else v)
                for k, v in action.payload.items()
            ))
        except TypeError:
            key = (action.type, str(action.payload.items()))
        if key not in seen:
            seen.add(key)
            result.append(action)
    return result


def generate_actions(
    session_id: str,
    matched_hospitals: list[Hospital],
    intent_detected: bool,
    message: str,
    conversation_turn: int,
) -> list[UIAction]:
    """
    Generate a list of UIAction commands for the frontend NavigationAgent.

    Rules are applied in order; multiple actions can be produced per call.
    Duplicate type+payload combinations are removed before returning.

    Args:
        session_id: Active session identifier used to construct result URLs.
        matched_hospitals: Hospitals returned by the HospitalMatchingAgent,
            ordered by relevance (best match first).
        intent_detected: True when the IntentAgent found a recognisable
            medical query; False for greetings or unrecognised input.
        message: The raw user message text.
        conversation_turn: 1-based index of the current turn in the session.

    Returns:
        Ordered, deduplicated list of UIAction objects. Returns an empty list
        when no navigation is appropriate (first-turn generic message, or
        intent detected but no hospitals matched).
    """
    # Early exit: Rule 6 — first turn with no recognised intent — nothing to navigate to
    if not intent_detected and conversation_turn == 1:
        return []

    # Early exit: Rule 7 — intent was clear but the matcher found nothing — no results page
    if intent_detected and not matched_hospitals:
        return []

    # Rules 1-5: generate actions
    actions: list[UIAction] = []

    # Rule 1: navigate to results page and highlight the top hospital
    if matched_hospitals and intent_detected:
        actions.append(UIAction(
            type="navigate",
            payload={"url": f"/results?session={session_id}"},
        ))
        actions.append(UIAction(
            type="highlight",
            payload={"hospital_id": matched_hospitals[0].id},
        ))

    # Rule 2: open detail panel when the message names exactly one hospital
    matched_hospital = _detect_hospital_name_match(message, matched_hospitals)
    if matched_hospital is not None:
        actions.append(UIAction(
            type="open_detail",
            payload={"hospital_id": matched_hospital.id},
        ))

    # Rule 3: apply city filter when a known TN city is mentioned
    city = _detect_city(message)
    if city is not None:
        actions.append(UIAction(
            type="apply_filter",
            payload={"key": "city", "value": city},
        ))

    # Rule 4: sort by price when budget keywords appear
    if _has_price_keyword(message):
        actions.append(UIAction(
            type="apply_filter",
            payload={"key": "sort", "value": "price_asc"},
        ))

    # Rule 5: show comparison when comparison keywords + enough hospitals
    if _has_comparison_keyword(message) and len(matched_hospitals) >= 2:
        actions.append(UIAction(
            type="show_comparison",
            payload={"hospital_ids": [h.id for h in matched_hospitals[:3]]},
        ))

    return _deduplicate(actions)
