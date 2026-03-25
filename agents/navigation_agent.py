"""
NavigationAgent (Backend) — UI Action Command Generator

Generates UI action commands that the frontend NavigationAgent will execute:
- navigate: Navigate to a different page
- highlight: Highlight a hospital card
- applyFilter: Apply a filter to results
- openDetail: Open hospital detail page

These actions are returned as part of the ConversationAgent response.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
from enum import Enum


class ActionType(Enum):
    """Types of UI actions that can be generated."""
    NAVIGATE = "navigate"
    HIGHLIGHT = "highlight"
    APPLY_FILTER = "applyFilter"
    OPEN_DETAIL = "openDetail"
    SCROLL_TO = "scrollTo"
    SHOW_MODAL = "showModal"


@dataclass
class UIAction:
    """Represents a UI action to be executed on the frontend."""
    action: str
    target: str | None = None
    params: dict = field(default_factory=dict)
    description: str = ""
    
    def to_dict(self) -> dict:
        """Convert action to dictionary for JSON serialization."""
        return {
            "action": self.action,
            "target": self.target,
            "params": self.params,
            "description": self.description
        }


class NavigationAgent:
    """
    Agent for generating UI action commands.
    
    Takes search results and generates appropriate UI actions
    to guide the user through the application.
    """
    
    def __init__(self):
        pass
    
    def generate_actions(
        self,
        hospitals: list["ScoredHospital"],
        intent: "SearchIntent | None" = None,
        results_count: int = 0
    ) -> list[UIAction]:
        """
        Generate UI actions based on search results.
        
        Parameters
        ----------
        hospitals : list[ScoredHospital]
            Matched and ranked hospitals
        intent : SearchIntent, optional
            The search intent that generated these results
        results_count : int
            Total number of results (may differ from hospitals list)
            
        Returns
        -------
        list[UIAction]
            List of UI actions to execute on frontend
        """
        actions = []
        
        actions.append(UIAction(
            action=ActionType.NAVIGATE.value,
            target="/results",
            params={},
            description="Navigate to results page"
        ))
        
        if hospitals:
            top_hospital = hospitals[0]
            
            if len(hospitals) > 1:
                actions.append(UIAction(
                    action=ActionType.APPLY_FILTER.value,
                    target="results",
                    params={
                        "category": intent.category if intent else None,
                        "city": intent.city if intent else None,
                        "sortBy": "score"
                    },
                    description=f"Apply filters for {results_count} results"
                ))
            
            actions.append(UIAction(
                action=ActionType.HIGHLIGHT.value,
                target=str(top_hospital.hospital_id),
                params={"hospitalId": top_hospital.hospital_id},
                description=f"Highlight top result: {top_hospital.name}"
            ))
            
            if results_count <= 5:
                actions.append(UIAction(
                    action=ActionType.OPEN_DETAIL.value,
                    target=str(top_hospital.hospital_id),
                    params={
                        "hospitalId": top_hospital.hospital_id,
                        "autoOpen": True
                    },
                    description=f"Open detail for top hospital: {top_hospital.name}"
                ))
        
        return actions
    
    def generate_welcome_actions(self) -> list[UIAction]:
        """Generate actions for initial welcome state."""
        return [
            UIAction(
                action=ActionType.NAVIGATE.value,
                target="/",
                params={},
                description="Navigate to home page"
            )
        ]
    
    def generate_prescription_upload_actions(self, extracted_data: "ExtractedData") -> list[UIAction]:
        """Generate actions after prescription upload."""
        actions = []
        
        if extracted_data.diagnoses or extracted_data.procedures:
            category = self._infer_category(extracted_data)
            actions.append(UIAction(
                action=ActionType.APPLY_FILTER.value,
                target="results",
                params={"category": category},
                description=f"Apply filter for {category}"
            ))
        
        actions.append(UIAction(
            action=ActionType.NAVIGATE.value,
            target="/results",
            params={},
            description="Navigate to results with extracted data"
        ))
        
        return actions
    
    def _infer_category(self, extracted_data: "ExtractedData") -> str | None:
        """Infer medical category from extracted data."""
        diagnoses_text = " ".join(extracted_data.diagnoses).lower()
        
        if any(w in diagnoses_text for w in ["heart", "cardiac", "bypass"]):
            return "Heart"
        if any(w in diagnoses_text for w in ["brain", "neuro", "stroke"]):
            return "Brain"
        if any(w in diagnoses_text for w in ["bone", "joint", "ortho"]):
            return "Ortho"
        if any(w in diagnoses_text for w in ["kidney", "renal"]):
            return "Kidney"
        
        return "General"
    
    def generate_error_actions(self, error_message: str) -> list[UIAction]:
        """Generate actions for error state."""
        return [
            UIAction(
                action=ActionType.SHOW_MODAL.value,
                target="error",
                params={"message": error_message},
                description="Show error modal"
            )
        ]


def generate_navigation_actions(
    hospitals: list["ScoredHospital"],
    intent: "SearchIntent | None" = None,
    results_count: int = 0
) -> list[dict]:
    """
    Convenience function to generate navigation actions.
    
    Parameters
    ----------
    hospitals : list[ScoredHospital]
        Matched hospitals
    intent : SearchIntent, optional
        Search intent
    results_count : int
        Total results count
        
    Returns
    -------
    list[dict]
        List of action dictionaries for JSON response
    """
    agent = NavigationAgent()
    actions = agent.generate_actions(hospitals, intent, results_count)
    return [a.to_dict() for a in actions]


if __name__ == "__main__":
    agent = NavigationAgent()
    
    welcome_actions = agent.generate_welcome_actions()
    print("Welcome actions:")
    for a in welcome_actions:
        print(f"  {a.action}: {a.target}")
    
    class MockHospital:
        hospital_id = 1
        name = "Test Hospital"
    
    result_actions = agent.generate_actions([MockHospital()], None, 10)
    print("\nResult actions:")
    for a in result_actions:
        print(f"  {a.action}: {a.target} - {a.description}")