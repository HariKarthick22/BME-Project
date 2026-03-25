"""
HospitalMatchingAgent — Weighted Scoring and Ranking Engine

Scores hospitals based on multiple criteria:
- Specialty match
- Procedure match
- Budget compatibility
- Location proximity
- Insurance acceptance
- Rating/accreditation
- Cost efficiency

Returns ranked list with scores and explanations.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import logging

from database import query

logger = logging.getLogger(__name__)


@dataclass
class ScoredHospital:
    """Hospital with scoring details."""
    hospital_id: int
    name: str
    city: str
    type: str
    accreditation: str | None
    rating: float | None
    procedure_id: int
    procedure_name: str
    category: str
    cost_min_inr: int
    cost_max_inr: int
    cost_avg_inr: int
    success_rate_pct: float | None
    insurance_schemes: str | None
    hospital_stay_days: str | None
    recovery_weeks: str | None
    availability: str
    total_score: float
    score_breakdown: dict = field(default_factory=dict)
    match_reasons: list[str] = field(default_factory=list)


class HospitalMatchingAgent:
    """
    Agent for scoring and ranking hospitals based on search intent.
    
    Uses weighted scoring algorithm with configurable weights.
    """
    
    DEFAULT_WEIGHTS = {
        "specialty_match": 25.0,
        "budget_match": 25.0,
        "location_match": 15.0,
        "insurance_match": 15.0,
        "rating": 10.0,
        "cost_efficiency": 10.0,
    }
    
    CATEGORY_KEYWORDS = {
        "Heart": ["heart", "cardiac", "bypass", "angio", "stent", "valve", "cardiology"],
        "Brain": ["brain", "neuro", "stroke", "neuro", "spine", "neuro surgery"],
        "Ortho": ["ortho", "bone", "joint", "knee", "hip", "fracture", "replacement", "arthroscopy"],
        "Kidney": ["kidney", "renal", "dialysis", "transplant", "urology"],
        "General": ["general", "surgery", "medicine", "fever", "checkup"],
    }
    
    def __init__(self, weights: dict | None = None):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
    
    def match(
        self,
        intent: "SearchIntent",
        limit: int = 20
    ) -> list[ScoredHospital]:
        """
        Match and rank hospitals based on search intent.
        
        Parameters
        ----------
        intent : SearchIntent
            Parsed search intent from IntentAgent
        limit : int
            Maximum number of results to return
            
        Returns
        -------
        list[ScoredHospital]
            Ranked list of matching hospitals with scores
        """
        if not intent:
            return self._get_all_hospitals(limit)
        
        candidates = self._fetch_candidates(intent)
        
        if not candidates:
            return []
        
        scored = []
        for candidate in candidates:
            score_data = self._score_hospital(candidate, intent)
            scored.append(score_data)
        
        scored.sort(key=lambda x: x.total_score, reverse=True)
        
        for i, h in enumerate(scored, 1):
            h.match_reasons.insert(0, f"Rank #{i}")
        
        return scored[:limit]
    
    def _fetch_candidates(self, intent: "SearchIntent") -> list[dict]:
        """Fetch candidate hospitals based on category/city filters."""
        conditions = []
        params = []
        
        if intent.category:
            conditions.append("p.category = ?")
            params.append(intent.category)
        
        if intent.city:
            conditions.append("LOWER(h.city) = LOWER(?)")
            params.append(intent.city)
        
        if intent.hospital_type:
            conditions.append("h.type = ?")
            params.append(intent.hospital_type)
        
        if intent.procedure:
            conditions.append("p.procedure_name LIKE ?")
            params.append(f"%{intent.procedure}%")
        
        if intent.insurance:
            conditions.append("p.insurance_schemes LIKE ?")
            params.append(f"%{intent.insurance}%")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
            SELECT
                h.id AS hospital_id,
                h.name,
                h.city,
                h.type,
                h.accreditation,
                h.rating,
                p.id AS procedure_id,
                p.procedure_name,
                p.category,
                p.cost_min_inr,
                p.cost_max_inr,
                p.cost_avg_inr,
                p.success_rate_pct,
                p.insurance_schemes,
                p.hospital_stay_days,
                p.recovery_weeks,
                p.availability,
                (SELECT COUNT(*) FROM hospitals h2 WHERE h2.city = h.city) as city_hospital_count
            FROM hospital_procedures p
            JOIN hospitals h ON h.id = p.hospital_id
            WHERE {where_clause}
              AND p.availability != 'unavailable'
            ORDER BY 
                CASE h.type
                    WHEN 'Government' THEN 1
                    WHEN 'Private (Mission)' THEN 2
                    WHEN 'Private (Trust)' THEN 3
                    ELSE 4
                END,
                p.cost_avg_inr ASC NULLS LAST
            LIMIT 100
        """
        
        try:
            return query(sql, tuple(params))
        except Exception as e:
            logger.error(f"Failed to fetch candidates: {e}")
            return []
    
    def _score_hospital(self, candidate: dict, intent: "SearchIntent") -> ScoredHospital:
        """Calculate weighted score for a hospital."""
        breakdown = {}
        
        specialty_score = self._score_specialty(candidate, intent)
        breakdown["specialty_match"] = specialty_score
        
        budget_score = self._score_budget(candidate, intent)
        breakdown["budget_match"] = budget_score
        
        location_score = self._score_location(candidate, intent)
        breakdown["location_match"] = location_score
        
        insurance_score = self._score_insurance(candidate, intent)
        breakdown["insurance_match"] = insurance_score
        
        rating_score = self._score_rating(candidate)
        breakdown["rating"] = rating_score
        
        cost_efficiency = self._score_cost_efficiency(candidate)
        breakdown["cost_efficiency"] = cost_efficiency
        
        total = sum(
            breakdown[key] * self.weights.get(key, 0) / 100
            for key in self.weights
        )
        
        reasons = self._generate_reasons(breakdown, candidate, intent)
        
        return ScoredHospital(
            hospital_id=candidate["hospital_id"],
            name=candidate["name"],
            city=candidate["city"],
            type=candidate["type"],
            accreditation=candidate["accreditation"],
            rating=candidate["rating"],
            procedure_id=candidate["procedure_id"],
            procedure_name=candidate["procedure_name"],
            category=candidate["category"],
            cost_min_inr=candidate["cost_min_inr"],
            cost_max_inr=candidate["cost_max_inr"],
            cost_avg_inr=candidate["cost_avg_inr"],
            success_rate_pct=candidate["success_rate_pct"],
            insurance_schemes=candidate["insurance_schemes"],
            hospital_stay_days=candidate["hospital_stay_days"],
            recovery_weeks=candidate["recovery_weeks"],
            availability=candidate["availability"],
            total_score=round(total, 2),
            score_breakdown=breakdown,
            match_reasons=reasons
        )
    
    def _score_specialty(self, candidate: dict, intent: "SearchIntent") -> float:
        """Score based on specialty/category match."""
        if not intent.category and not intent.procedure:
            return 50.0
        
        category = candidate.get("category", "").lower()
        procedure = candidate.get("procedure_name", "").lower()
        query = (intent.category or "").lower() + " " + (intent.procedure or "").lower()
        
        if intent.category and category == intent.category.lower():
            return 100.0
        
        if intent.procedure:
            if intent.procedure.lower() in procedure:
                return 90.0
            for keyword in self.CATEGORY_KEYWORDS.get(category.title(), []):
                if keyword in query:
                    return 85.0
        
        return 40.0
    
    def _score_budget(self, candidate: dict, intent: "SearchIntent") -> float:
        """Score based on budget compatibility."""
        cost_avg = candidate.get("cost_avg_inr", 0) or 0
        budget_max = intent.budget_max
        
        if not budget_max:
            return 60.0
        
        if cost_avg <= budget_max:
            if cost_avg <= budget_max * 0.7:
                return 100.0
            elif cost_avg <= budget_max * 0.9:
                return 85.0
            else:
                return 70.0
        else:
            excess_pct = (cost_avg - budget_max) / budget_max
            if excess_pct <= 0.1:
                return 50.0
            elif excess_pct <= 0.25:
                return 30.0
            else:
                return 10.0
    
    def _score_location(self, candidate: dict, intent: "SearchIntent") -> float:
        """Score based on location match."""
        if not intent.city:
            return 50.0
        
        candidate_city = candidate.get("city", "").lower()
        intent_city = intent.city.lower()
        
        if candidate_city == intent_city:
            return 100.0
        
        common_cities = {
            "chennai": ["coimbatore", "madurai", "trichy", "salem"],
            "delhi": ["noida", "gurgaon", "faridabad"],
            "mumbai": ["pune", "navi mumbai", "thane"],
            "bangalore": ["mysore", "hubli"],
        }
        
        nearby = common_cities.get(intent_city, [])
        if candidate_city in nearby:
            return 75.0
        
        return 30.0
    
    def _score_insurance(self, candidate: dict, intent: "SearchIntent") -> float:
        """Score based on insurance acceptance."""
        if not intent.insurance:
            return 50.0
        
        schemes = candidate.get("insurance_schemes", "") or ""
        
        if intent.insurance.lower() == "any":
            if schemes and schemes.lower() != "none":
                return 80.0
            return 30.0
        
        if intent.insurance.lower() in schemes.lower():
            return 100.0
        
        if schemes and schemes.lower() not in ["", "none", "na"]:
            return 60.0
        
        return 20.0
    
    def _score_rating(self, candidate: dict) -> float:
        """Score based on hospital rating and accreditation."""
        rating = candidate.get("rating")
        accreditation = candidate.get("accreditation")
        
        score = 50.0
        
        if rating:
            score += (rating / 5.0) * 30
        
        if accreditation == "NABH":
            score += 20
        elif accreditation == "NABL":
            score += 15
        
        return min(score, 100.0)
    
    def _score_cost_efficiency(self, candidate: dict) -> float:
        """Score based on cost relative to average."""
        cost_avg = candidate.get("cost_avg_inr", 0) or 0
        hospital_type = candidate.get("type", "")
        
        if not cost_avg:
            return 50.0
        
        base_score = 50.0
        
        if hospital_type == "Government":
            base_score += 30
        elif "Trust" in hospital_type:
            base_score += 15
        
        if cost_avg < 50000:
            base_score += 10
        elif cost_avg > 200000:
            base_score -= 10
        
        return min(max(base_score, 0), 100)
    
    def _generate_reasons(self, breakdown: dict, candidate: dict, intent: "SearchIntent") -> list[str]:
        """Generate human-readable match reasons."""
        reasons = []
        
        if breakdown["specialty_match"] >= 85:
            reasons.append(f"Matches {candidate.get('category')} specialty")
        
        if breakdown["budget_match"] >= 70:
            if intent.budget_max:
                reasons.append(f"Fits within budget of ₹{intent.budget_max:,}")
            else:
                reasons.append("Cost-effective option")
        
        if breakdown["location_match"] >= 75 and intent.city:
            reasons.append(f"Located in {candidate.get('city')}")
        
        if breakdown["insurance_match"] >= 60 and intent.insurance:
            reasons.append("Accepts insurance")
        
        if breakdown["rating"] >= 70:
            if candidate.get("accreditation"):
                reasons.append(f"{candidate['accreditation']} accredited")
            if candidate.get("rating"):
                reasons.append(f"Rating: {candidate['rating']}/5")
        
        if candidate.get("type"):
            reasons.append(f"{candidate['type']} hospital")
        
        if not reasons:
            reasons.append("Matches search criteria")
        
        return reasons
    
    def _get_all_hospitals(self, limit: int) -> list[ScoredHospital]:
        """Get all available hospitals when no intent specified."""
        sql = """
            SELECT
                h.id AS hospital_id, h.name, h.city, h.type,
                h.accreditation, h.rating, p.id AS procedure_id,
                p.procedure_name, p.category, p.cost_min_inr,
                p.cost_max_inr, p.cost_avg_inr, p.success_rate_pct,
                p.insurance_schemes, p.hospital_stay_days,
                p.recovery_weeks, p.availability
            FROM hospital_procedures p
            JOIN hospitals h ON h.id = p.hospital_id
            WHERE p.availability != 'unavailable'
            ORDER BY p.cost_avg_inr ASC
            LIMIT ?
        """
        
        try:
            rows = query(sql, (limit,))
            return [
                ScoredHospital(
                    hospital_id=r["hospital_id"],
                    name=r["name"],
                    city=r["city"],
                    type=r["type"],
                    accreditation=r["accreditation"],
                    rating=r["rating"],
                    procedure_id=r["procedure_id"],
                    procedure_name=r["procedure_name"],
                    category=r["category"],
                    cost_min_inr=r["cost_min_inr"],
                    cost_max_inr=r["cost_max_inr"],
                    cost_avg_inr=r["cost_avg_inr"],
                    success_rate_pct=r["success_rate_pct"],
                    insurance_schemes=r["insurance_schemes"],
                    hospital_stay_days=r["hospital_stay_days"],
                    recovery_weeks=r["recovery_weeks"],
                    availability=r["availability"],
                    total_score=50.0,
                    match_reasons=["Available"]
                )
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to fetch all hospitals: {e}")
            return []


def match_hospitals(intent: "SearchIntent", limit: int = 20) -> list[ScoredHospital]:
    """
    Convenience function to match hospitals.
    
    Parameters
    ----------
    intent : SearchIntent
        Parsed search intent
    limit : int
        Maximum results to return
        
    Returns
    -------
    list[ScoredHospital]
        Ranked list of matching hospitals
    """
    agent = HospitalMatchingAgent()
    return agent.match(intent, limit)


if __name__ == "__main__":
    from intent_agent import parse_intent
    
    test_queries = [
        "knee replacement under ₹5L Chennai",
        "heart bypass surgery in Delhi with insurance",
        "best orthopedic hospital for hip replacement",
    ]
    
    agent = HospitalMatchingAgent()
    
    for q in test_queries:
        intent = parse_intent(q)
        results = agent.match(intent, limit=5)
        
        print(f"\n{'='*60}")
        print(f"Query: {q}")
        print(f"Results: {len(results)}")
        print(f"{'='*60}")
        
        for h in results:
            print(f"\n{h.name} ({h.city}) - Score: {h.total_score}")
            print(f"  Procedure: {h.procedure_name} - ₹{h.cost_avg_inr:,}")
            print(f"  Reasons: {', '.join(h.match_reasons)}")