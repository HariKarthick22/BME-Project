"""
LangGraph-based agentic router for MediOrbit.
Routes queries to appropriate handlers: CSV Agent, Vision Model, PDF RAG, etc.
Implements self-correction and fallback mechanisms.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Types of queries the system can handle"""
    HOSPITAL_SEARCH = "hospital_search"      # CSV lookup: specialty + city
    SYMPTOM_ANALYSIS = "symptom_analysis"    # Conversational medical guidance
    IMAGE_ANALYSIS = "image_analysis"        # X-ray/medical image analysis
    DOCUMENT_ANALYSIS = "document_analysis"  # PDF/medical report RAG
    TRAVEL_INFO = "travel_info"              # Medical tourism travel info
    PRESCRIPTION = "prescription_parsing"    # Parse prescription images
    EMERGENCY = "emergency"                  # Emergency triage
    UNKNOWN = "unknown"                      # Fallback

class QueryRouter:
    """
    Routes user queries to appropriate handlers based on intent detection.
    Implements fallback mechanisms for improved reliability.
    """
    
    def __init__(self):
        self.hospital_keywords = ['hospital', 'doctor', 'specialist', 'clinic', 'surgery', 'treatment', 'center']
        self.symptom_keywords = ['pain', 'fever', 'symptom', 'feel', 'suffer', 'sick', 'illness', 'disease']
        self.image_keywords = ['x-ray', 'xray', 'scan', 'mri', 'ct', 'image', 'radiograph', 'upload']
        self.document_keywords = ['report', 'record', 'pdf', 'document', 'lab', 'pathology', 'diagnosis']
        self.emergency_keywords = ['emergency', 'urgent', 'severe', 'critical', 'accident', '911', 'ambulance']
        self.travel_keywords = ['flight', 'visa', 'accommodation', 'tourism', 'travel', 'hotel', 'airport']
        
    def classify_query(self, user_input: str, has_attachment: bool = False, 
                      attachment_type: Optional[str] = None) -> QueryType:
        """
        Classify user query to determine appropriate handler.
        
        Args:
            user_input: User's text query
            has_attachment: Whether query includes file attachment
            attachment_type: Type of attachment (image, pdf, etc.)
            
        Returns:
            QueryType enum indicating query classification
        """
        
        user_input_lower = user_input.lower()
        
        # Check for emergency first
        if any(keyword in user_input_lower for keyword in self.emergency_keywords):
            return QueryType.EMERGENCY
        
        # Check for image/visual queries
        if has_attachment and attachment_type in ['image', 'xray', 'scan']:
            return QueryType.IMAGE_ANALYSIS
        
        if any(keyword in user_input_lower for keyword in self.image_keywords):
            return QueryType.IMAGE_ANALYSIS
        
        # Check for document analysis
        if has_attachment and attachment_type == 'pdf':
            return QueryType.DOCUMENT_ANALYSIS
        
        if any(keyword in user_input_lower for keyword in self.document_keywords):
            return QueryType.DOCUMENT_ANALYSIS
        
        # Check for hospital/specialist search
        # Match patterns like: "hospital in City for Specialty" or "doctor for condition in City"
        if any(keyword in user_input_lower for keyword in self.hospital_keywords):
            if any(city_word in user_input_lower for city_word in ['chennai', 'bangalore', 'delhi', 'mumbai', 'city', 'town']):
                return QueryType.HOSPITAL_SEARCH
        
        # Check for symptom analysis
        if any(keyword in user_input_lower for keyword in self.symptom_keywords):
            return QueryType.SYMPTOM_ANALYSIS
        
        # Check for travel info
        if any(keyword in user_input_lower for keyword in self.travel_keywords):
            return QueryType.TRAVEL_INFO
        
        # Check for prescription parsing
        if 'prescription' in user_input_lower and has_attachment:
            return QueryType.PRESCRIPTION
        
        return QueryType.UNKNOWN
    
    def extract_hospital_params(self, user_input: str) -> Dict[str, Optional[str]]:
        """
        Extract hospital search parameters from query.
        Implements fallback search if city not found.
        
        Returns:
            Dict with keys: specialty, city, additional_filters
        """
        import re
        
        result = {
            'specialty': None,
            'city': None,
            'additional_filters': {}
        }
        
        user_input_lower = user_input.lower()
        
        # List of common specialties
        specialties = [
            'cardiology', 'orthopedic', 'neurology', 'gastroenterology',
            'oncology', 'urology', 'nephrology', 'pediatrics',
            'gynecology', 'psychiatry', 'dermatology', 'pulmonology',
            'surgery', 'general', 'ent', 'ophthalmology', 'kidney'
        ]
        
        # List of major Tamil Nadu cities
        cities = [
            'chennai', 'bangalore', 'delhi', 'mumbai', 'hyderabad',
            'coimbatore', 'madurai', 'salem', 'trichy', 'kochi',
            'pune', 'kolkata', 'ahmedabad'
        ]
        
        # Extract specialty
        for specialty in specialties:
            if specialty in user_input_lower:
                result['specialty'] = specialty
                break
        
        # Extract city
        for city in cities:
            if city in user_input_lower:
                result['city'] = city
                break
        
        # If no specialty found, try to extract from pattern "doctor for X"
        if not result['specialty']:
            match = re.search(r'(?:doctor|specialist|hospital)\s+(?:for|in)\s+(\w+)', user_input_lower)
            if match:
                result['specialty'] = match.group(1)
        
        # Self-correction: If city not found, use default or request clarification
        if not result['city']:
            result['city'] = 'chennai'  # Default to Chennai
            result['additional_filters']['city_assumed'] = True
        
        return result
    
    def should_fallback(self, query_type: QueryType, handler_response: Optional[Dict]) -> bool:
        """
        Determine if we should fallback to alternative handler
        (e.g., CSV returned no results, fallback to nearby cities)
        """
        if handler_response is None:
            return True
        
        # If CSV returned empty results, fallback
        if isinstance(handler_response, dict):
            if handler_response.get('count', 0) == 0:
                return True
        
        if isinstance(handler_response, list) and len(handler_response) == 0:
            return True
        
        return False

class RoutingAgent:
    """
    Main routing agent that orchestrates query routing and handler selection.
    Implements stateful routing with conversation context.
    """
    
    def __init__(self, conversation_history: Optional[List[Dict]] = None):
        self.router = QueryRouter()
        self.conversation_history = conversation_history or []
        
    async def route_query(self, user_input: str, attachment_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main routing function. Analyzes query and returns routing decision.
        
        Returns:
            {
                'query_type': QueryType,
                'handler': 'handler_name',
                'params': {...},
                'confidence': 0.0-1.0,
                'fallback_options': [...]
            }
        """
        
        attachment_info = attachment_info or {}
        
        # Classify query
        query_type = self.router.classify_query(
            user_input,
            has_attachment=attachment_info.get('present', False),
            attachment_type=attachment_info.get('type')
        )
        
        routing_decision = {
            'query_type': query_type,
            'confidence': 0.85,  # Base confidence
            'params': {}
        }
        
        # Route to appropriate handler
        if query_type == QueryType.HOSPITAL_SEARCH:
            routing_decision['handler'] = 'csv_agent'
            routing_decision['params'] = self.router.extract_hospital_params(user_input)
            routing_decision['fallback_options'] = ['semantic_search', 'web_search']
            
        elif query_type == QueryType.SYMPTOM_ANALYSIS:
            routing_decision['handler'] = 'conversation_agent'
            routing_decision['fallback_options'] = ['web_search']
            
        elif query_type == QueryType.IMAGE_ANALYSIS:
            routing_decision['handler'] = 'vision_model'
            routing_decision['fallback_options'] = ['conversation_agent']
            
        elif query_type == QueryType.DOCUMENT_ANALYSIS:
            routing_decision['handler'] = 'pdf_rag'
            routing_decision['fallback_options'] = ['conversation_agent']
            
        elif query_type == QueryType.EMERGENCY:
            routing_decision['handler'] = 'emergency_protocol'
            routing_decision['confidence'] = 1.0
            
        else:  # UNKNOWN or others
            routing_decision['handler'] = 'conversation_agent'
            routing_decision['fallback_options'] = ['semantic_search']
        
        # Store in conversation history
        self.conversation_history.append({
            'user_input': user_input,
            'routing_decision': routing_decision
        })
        
        return routing_decision

# Global router instance
query_router = QueryRouter()
routing_agent = None  # Initialize in main.py
