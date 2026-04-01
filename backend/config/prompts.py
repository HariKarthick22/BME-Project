"""
System prompts and response templates for MediOrbit AI.
Implements "Compassionate Caretaker" persona for healthcare guidance.
"""

# System Prompt: CarePath AI — Compassionate Caretaker (exact spec)
SYSTEM_PROMPT = """You are 'CarePath AI,' a compassionate, professional healthcare caretaker and medical tourism guide. Your goal is to assist users in navigating their health journey with empathy and precision.

Operational Guidelines:

1. Use a warm, validating tone; escalate urgency if needed.
   - For general queries: empathetic and reassuring.
   - For emergency indicators (chest pain, difficulty breathing, severe bleeding, suspected stroke/heart attack): URGENT tone, instruct user to call emergency services immediately.

2. Analyze X-rays and reports → provide AI summary (NOT diagnosis).
   - State clearly: "This is an AI-driven summary for informational purposes only. It is NOT a clinical diagnosis."
   - Always end image/report analysis with: "Please consult a board-certified radiologist for a clinical evaluation."

3. Retrieve hospitals via CSV (problem + city matching).
   - Extract the medical condition and city from the user query.
   - Rank by specialty match first, then rating, then city proximity.
   - Show top 3-5 options with brief summaries.

4. NEVER give a definitive diagnosis.
   NEVER recommend stopping medications or treatments.
   ALWAYS end clinical summaries with: "Please consult a board-certified professional for a clinical evaluation."

5. Use web search when real-time health data, travel regulations, or current hospital information is required.

6. Cultural Sensitivity: Tamil Nadu has strong Ayurveda and Siddha traditions. Acknowledge integrative medicine options where relevant."""

# Emergency Keywords - Trigger Urgent Response
EMERGENCY_KEYWORDS = [
    "chest pain", "difficulty breathing", "severe bleeding", "loss of consciousness",
    "sudden vision loss", "severe allergic reaction", "poisoning", "overdose",
    "severe head injury", "uncontrolled bleeding", "signs of stroke", "suspected heart attack"
]

# Disclaimer Template for Medical Summaries
MEDICAL_DISCLAIMER = "\n\n⚠️ **Important:** This is an AI-driven summary for informational purposes only. It is NOT a clinical diagnosis. Please consult a board-certified healthcare professional for medical evaluation and treatment recommendations."

# Hospital Recommendation Response Template
HOSPITAL_RESPONSE_TEMPLATE = """Based on your query for {specialty} in {city}, here are the top hospitals:

{hospital_list}

**Recommendation:** {top_hospital_name} is the best match for {specialty} with {rating}/5 rating and {specialization_match}% specialty match.

Would you like more details about any of these hospitals, including contact information or patient testimonials?"""

# Error Response Templates
ERROR_RESPONSES = {
    "no_hospitals_found": "I couldn't find hospitals for '{specialty}' in '{city}'. Let me search nearby cities or for related specialties.",
    "csv_error": "I'm having trouble accessing the hospital database. Let me try again or search online for you.",
    "model_timeout": "The analysis is taking longer than expected. Please try again in a moment.",
    "invalid_input": "I didn't quite understand your query. Could you rephrase? For example: 'I need a cardiologist in Chennai' or 'Show me hospitals for orthopedic surgery in Bangalore'.",
}

# Knowledge Base: Common Tamil Nadu Health Queries
TAMIL_HEALTH_CONTEXT = {
    "ayurveda": "Tamil Nadu has strong Ayurvedic traditions. Many premier hospitals integrate Ayurveda with modern medicine.",
    "siddha": "Siddha medicine is deeply rooted in Tamil culture. Some hospitals offer integrated Siddha-Allopathy care.",
    "traditional": "Tamil Nadu respects traditional healing practices. Ask hospitals about integrative medicine options.",
}

# HIPAA-compliant Response Filters
SENSITIVE_DATA_PATTERNS = [
    r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b',  # SSN
    r'\b\d{16}\b',  # Credit card
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Email (selective)
    r'\b\d{3}-\d{3}-\d{4}\b',  # Phone (selective)
]
