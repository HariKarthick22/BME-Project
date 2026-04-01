"""
HospitalMatchingAgent — weighted scoring and ranking engine.

Takes a SearchIntent and/or ExtractionResult, queries SQLite for all hospitals,
scores each one using a weighted multi-factor formula, and returns the top-N
matches sorted by match_score descending.

Scoring weights:
    Specialty/procedure match : 35%
    Budget fit                : 25%
    Location match            : 20%
    Insurance match           : 10%
    Base score (AI + success) : 10%
"""

from __future__ import annotations

import time

from ..models.schemas import Hospital, SearchIntent, ExtractionResult
from ..models.database import get_connection, row_to_dict

# Cache for hospitals — TTL 1 hour
_HOSPITAL_CACHE = {"data": None, "timestamp": 0}
_CACHE_TTL_SECONDS = 3600


# ---------------------------------------------------------------------------
# Procedure → specialty keyword mapping
# ---------------------------------------------------------------------------

PROCEDURE_TO_SPECIALTY: dict[str, str] = {
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
    "radiation therapy": "Oncology",
    "cancer surgery": "Oncology",
    "bone marrow transplant": "Haematology",
    "immunotherapy": "Oncology",
    "liver transplant": "Transplant Surgery",
    "bariatric surgery": "Bariatric Surgery",
    "brain surgery": "Neurosurgery",
    "brain tumour": "Neurosurgery",
    "neurosurgery": "Neurosurgery",
    "stroke": "Neurology",
    "cataract": "Ophthalmology",
    "retinal surgery": "Ophthalmology",
    "prostate surgery": "Urology",
    "turp": "Urology",
    "laparoscopic": "General Surgery",
    "cholecystectomy": "General Surgery",
    "whipple": "Gastroenterology",
    "ercp": "Gastroenterology",
    "diabetes": "Diabetology",
}


# ---------------------------------------------------------------------------
# Internal scoring helpers
# ---------------------------------------------------------------------------

def _get_all_hospitals_cached() -> list[dict]:
    """
    Fetch all hospitals from database with 1-hour caching.
    
    Returns:
        List of hospital dicts from database.
    """
    global _HOSPITAL_CACHE
    now = time.time()
    
    # Return cached data if still valid
    if _HOSPITAL_CACHE["data"] is not None and (now - _HOSPITAL_CACHE["timestamp"]) < _CACHE_TTL_SECONDS:
        return _HOSPITAL_CACHE["data"]
    
    # Fetch fresh data from database
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM hospitals").fetchall()
        hospitals = [row_to_dict(row) for row in rows]
        _HOSPITAL_CACHE["data"] = hospitals
        _HOSPITAL_CACHE["timestamp"] = now
        return hospitals
    finally:
        conn.close()


def _score_specialty(
    hospital: dict,
    target_specialty: str | None,
    target_procedure: str | None,
) -> float:
    """
    Score how well a hospital matches the requested specialty or procedure.

    Checks for an exact (case-insensitive) specialty name match first, then
    falls back to a substring search across the hospital's procedure list.

    Args:
        hospital:          Raw hospital dict from the database.
        target_specialty:  The resolved specialty keyword (may be None).
        target_procedure:  The procedure string from intent/extraction (may be None).

    Returns:
        1.0 — exact specialty match or exact procedure match
        0.7 — procedure found as substring in any hospital procedure
        0.0 — no match at all or both targets are None
    """
    if target_specialty is None and target_procedure is None:
        return 0.5

    specialties: list[str] = hospital.get("specialties") or []
    procedures: list[str] = hospital.get("procedures") or []

    specialties_lower = [s.lower() for s in specialties]
    procedures_lower = [p.lower() for p in procedures]

    # Exact specialty match
    if target_specialty and target_specialty.lower() in specialties_lower:
        return 1.0

    # Exact procedure match
    if target_procedure:
        proc_lower = target_procedure.lower()
        if proc_lower in procedures_lower:
            return 1.0
        # Substring match — procedure keyword appears inside any listed procedure
        for p in procedures_lower:
            if proc_lower in p:
                return 0.7

    # Specialty substring match (e.g. "Cardiac" inside "Cardiac Surgery")
    if target_specialty:
        spec_lower = target_specialty.lower()
        for s in specialties_lower:
            if spec_lower in s or s in spec_lower:
                return 0.7

    return 0.0


def _score_budget(hospital: dict, budget_max: int | None) -> float:
    """
    Score how well the hospital's pricing fits the patient's budget.

    Args:
        hospital:   Raw hospital dict from the database.
        budget_max: The patient's maximum budget in INR (may be None).

    Returns:
        0.5 — neutral when budget_max is not specified
        1.0 — hospital's min_price is within budget
        0.5 — hospital's max_price is within 120% of budget (partial fit)
        0.0 — hospital is clearly unaffordable
    """
    if budget_max is None:
        return 0.5

    min_price: int = hospital.get("min_price") or 0
    max_price: int = hospital.get("max_price") or 0

    if min_price == 0 and max_price == 0:
        return 0.5

    if min_price <= budget_max:
        return 1.0
    if max_price <= budget_max * 1.2:
        return 0.5
    return 0.0


def _score_location(hospital: dict, target_city: str | None) -> float:
    """
    Score geographic proximity between the hospital and the patient's city.

    Args:
        hospital:    Raw hospital dict from the database.
        target_city: The city from the search intent (may be None).

    Returns:
        0.5 — neutral when no city is specified
        1.0 — exact city match (case-insensitive)
        0.6 — same state (Tamil Nadu assumed for all seeded hospitals)
        0.3 — different state / no match
    """
    if target_city is None:
        return 0.5

    hospital_city: str = (hospital.get("city") or "").lower()
    hospital_state: str = (hospital.get("state") or "").lower()
    city_lower = target_city.lower()

    if hospital_city == city_lower:
        return 1.0

    # Infer the state of the target city (all seeded cities are in Tamil Nadu)
    # For now compare hospital state against a constant; extend if multi-state data grows.
    SAME_STATE = "tamil nadu"
    if hospital_state == SAME_STATE:
        # Both are in Tamil Nadu but different cities
        return 0.6

    return 0.3


def _score_insurance(hospital: dict, insurance_type: str | None) -> float:
    """
    Score whether the hospital accepts the patient's insurance.

    Args:
        hospital:       Raw hospital dict from the database.
        insurance_type: The insurance scheme name from intent (may be None).

    Returns:
        0.5 — neutral when insurance type is not specified
        1.0 — insurance name found (case-insensitive) in hospital's insurance list
        0.0 — insurance not accepted
    """
    if insurance_type is None:
        return 0.5

    insurance_list: list[str] = hospital.get("insurance") or []
    insurance_lower = [i.lower() for i in insurance_list]
    target_lower = insurance_type.lower()

    for item in insurance_lower:
        if target_lower in item or item in target_lower:
            return 1.0

    return 0.0


def _score_base(hospital: dict) -> float:
    """
    Compute a normalised base quality score from ai_score and success_rate.

    Formula: (ai_score / 100) * 0.5 + (success_rate / 100) * 0.5, clamped to [0, 1].

    Args:
        hospital: Raw hospital dict from the database.

    Returns:
        Float in [0.0, 1.0] representing intrinsic hospital quality.
    """
    ai_score: float = float(hospital.get("ai_score") or 0.0)
    success_rate: float = float(hospital.get("success_rate") or 0.0)
    raw = (ai_score / 100.0) * 0.5 + (success_rate / 100.0) * 0.5
    return max(0.0, min(1.0, raw))


# ---------------------------------------------------------------------------
# Reason builders
# ---------------------------------------------------------------------------

def _build_match_reasons(
    hospital: dict,
    target_procedure: str | None,
    target_specialty: str | None,
    target_city: str | None,
    budget_max: int | None,
    insurance_type: str | None,
) -> list[str]:
    """
    Build a list of human-readable strings explaining why the hospital matched.

    Args:
        hospital:          Raw hospital dict.
        target_procedure:  Resolved procedure string.
        target_specialty:  Resolved specialty string.
        target_city:       Target city from intent.
        budget_max:        Maximum budget in INR.
        insurance_type:    Insurance scheme name.

    Returns:
        List of plain-English explanation strings (may be empty).
    """
    reasons: list[str] = []

    specialties: list[str] = hospital.get("specialties") or []
    procedures: list[str] = hospital.get("procedures") or []
    specialties_lower = [s.lower() for s in specialties]
    procedures_lower = [p.lower() for p in procedures]

    # Procedure / specialty reasons
    if target_procedure:
        proc_lower = target_procedure.lower()
        matched_proc = next(
            (p for p in procedures if proc_lower in p.lower() or p.lower() in proc_lower),
            None,
        )
        if matched_proc:
            reasons.append(f"Matches your procedure: {matched_proc}")
        elif target_specialty and target_specialty.lower() in specialties_lower:
            reasons.append(f"Specialises in {target_specialty}")
    elif target_specialty:
        matched_spec = next(
            (s for s in specialties if target_specialty.lower() in s.lower() or s.lower() in target_specialty.lower()),
            None,
        )
        if matched_spec:
            reasons.append(f"Specialises in {matched_spec}")

    # Budget reason
    if budget_max is not None:
        min_price: int = hospital.get("min_price") or 0
        if min_price <= budget_max:
            budget_lakhs = budget_max / 100_000
            reasons.append(f"Within your budget of \u20b9{budget_lakhs:.0f}L")

    # Location reason
    if target_city:
        hospital_city: str = hospital.get("city") or ""
        if hospital_city.lower() == target_city.lower():
            reasons.append(f"Located in {hospital_city}")
        elif (hospital.get("state") or "").lower() == "tamil nadu":
            reasons.append(f"Located in Tamil Nadu ({hospital_city})")

    # Insurance reason
    if insurance_type:
        insurance_list: list[str] = hospital.get("insurance") or []
        matched_ins = next(
            (i for i in insurance_list if insurance_type.lower() in i.lower() or i.lower() in insurance_type.lower()),
            None,
        )
        if matched_ins:
            reasons.append(f"Accepts {matched_ins} insurance")

    # Top-rated reason
    success_rate: float = float(hospital.get("success_rate") or 0.0)
    if success_rate >= 95.0:
        reasons.append(f"Top-rated: {success_rate:.0f}% success rate")

    return reasons


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def match_hospitals(
    intent: SearchIntent | None,
    extraction: ExtractionResult | None,
    top_n: int = 10,
) -> list[Hospital]:
    """
    Score and rank all hospitals against the given search intent and/or extraction.

    Combines fields from both sources to build a unified query target, fetches
    every hospital from SQLite, computes a weighted match_score for each, and
    returns the top_n hospitals in descending score order.

    Scoring weights:
        Specialty/procedure match : 35 %
        Budget fit                : 25 %
        Location match            : 20 %
        Insurance match           : 10 %
        Base quality score        : 10 %

    Args:
        intent:     Structured intent from IntentAgent (may be None).
        extraction: Prescription extraction from PrescriptionParserAgent (may be None).
        top_n:      Maximum number of hospitals to return (default 10).

    Returns:
        List of Hospital objects with match_score and match_reasons populated,
        sorted by match_score descending (best match first).
    """
    # ------------------------------------------------------------------
    # 1. Build combined query target from intent + extraction
    # ------------------------------------------------------------------
    target_procedure: str | None = None
    target_specialty: str | None = None
    target_city: str | None = None
    budget_max: int | None = None
    insurance_type: str | None = None

    if intent is not None:
        target_procedure = intent.procedure or target_procedure
        target_specialty = intent.specialty or target_specialty
        target_city = intent.city
        budget_max = intent.budget_max
        insurance_type = intent.insurance_type

    if extraction is not None and extraction.procedure:
        if target_procedure is None:
            target_procedure = extraction.procedure[0]

    # If we have a procedure but no specialty, map it via the lookup dict
    if target_procedure and not target_specialty:
        proc_lower = target_procedure.lower()
        for keyword, specialty in PROCEDURE_TO_SPECIALTY.items():
            if keyword in proc_lower:
                target_specialty = specialty
                break

    # ------------------------------------------------------------------
    # 2. Fetch all hospitals from SQLite (with caching)
    # ------------------------------------------------------------------
    raw_hospitals: list[dict] = _get_all_hospitals_cached()

    # ------------------------------------------------------------------
    # 3 & 4. Score each hospital and collect match reasons
    # ------------------------------------------------------------------
    WEIGHTS = {
        "specialty": 0.35,
        "budget": 0.25,
        "location": 0.20,
        "insurance": 0.10,
        "base": 0.10,
    }

    scored: list[tuple[float, dict, list[str]]] = []

    for h in raw_hospitals:
        s_specialty = _score_specialty(h, target_specialty, target_procedure)
        s_budget = _score_budget(h, budget_max)
        s_location = _score_location(h, target_city)
        s_insurance = _score_insurance(h, insurance_type)
        s_base = _score_base(h)

        match_score = (
            WEIGHTS["specialty"] * s_specialty
            + WEIGHTS["budget"] * s_budget
            + WEIGHTS["location"] * s_location
            + WEIGHTS["insurance"] * s_insurance
            + WEIGHTS["base"] * s_base
        )

        reasons = _build_match_reasons(
            h,
            target_procedure,
            target_specialty,
            target_city,
            budget_max,
            insurance_type,
        )

        scored.append((match_score, h, reasons))

    # ------------------------------------------------------------------
    # 5. Sort descending by match_score, take top_n
    # ------------------------------------------------------------------
    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:top_n]

    # ------------------------------------------------------------------
    # 6. Construct Hospital objects with match_score and match_reasons set
    # ------------------------------------------------------------------
    results: list[Hospital] = []
    for score, h_dict, reasons in top:
        hospital = Hospital(**h_dict)
        hospital.match_score = round(score, 4)
        hospital.match_reasons = reasons
        results.append(hospital)

    return results
