# MediOrbit API Documentation

## Overview

MediOrbit is a medical tourism assistant API for Tamil Nadu, India. It helps patients find the best hospitals for their medical needs using AI-powered recommendations.

**Base URL**: `http://localhost:8000`

## Authentication

Currently, no authentication is required. All endpoints are publicly accessible.

## Endpoints

### Health Check

#### GET `/`

Health check endpoint to verify the API is running.

**Response:**
```json
{
  "status": "MediOrbit API is running",
  "version": "1.0.0"
}
```

### Chat Interface

#### POST `/api/chat`

Handle a chat message from a user. The API orchestrates intent extraction, hospital matching, and AI responses.

**Request Body:**
```json
{
  "session_id": "session-1234567890",
  "message": "I need knee surgery in Chennai with a budget of 5 lakhs",
  "prescription_data": null
}
```

**Response:**
```json
{
  "session_id": "session-1234567890",
  "text": "I found 3 hospitals in Chennai that offer knee surgery within your budget. The top match is...",
  "actions": [
    {
      "action_type": "navigate_to_results",
      "data": {
        "query": "knee surgery in Chennai"
      }
    }
  ],
  "hospitals": [
    {
      "id": "ganga-01",
      "name": "Ganga Hospital",
      "city": "Coimbatore",
      "ai_score": 8.5,
      ...
    }
  ]
}
```

**Parameters:**
- `session_id` (string, required): Unique conversation session identifier
- `message` (string, required): User's message text
- `prescription_data` (object, optional): Prescription extraction data

### Prescription Upload

#### POST `/api/parse-prescription`

Parse a prescription image or PDF using OCR and medical NER.

**Request:**
- Form data with file upload
- Form field `session_id`: The session identifier

**Response:**
```json
{
  "session_id": "session-1234567890",
  "extraction": {
    "diagnosis": ["Type 2 Diabetes", "Hypertension"],
    "procedure": ["Cardiac Catheterization"],
    "medications": ["Metformin", "Lisinopril"],
    "patient": {
      "age": 45,
      "gender": "M"
    }
  },
  "summary": "Extracted: Diagnosis: Type 2 Diabetes, Hypertension | Procedure: Cardiac Catheterization | Medications: 2 found"
}
```

**Parameters:**
- `file` (file, required): Prescription image (JPG/PNG) or PDF
- `session_id` (string, required): The chat session identifier

**Status Codes:**
- `200`: Success
- `500`: Processing error

### Hospital Listing

#### GET `/api/hospitals`

Retrieve a filtered list of hospitals from the database.

**Query Parameters:**
- `city` (string, optional): Filter by city name (case-insensitive exact match)
- `specialty` (string, optional): Filter by specialty (case-insensitive substring match)
- `min_price` (integer, optional): Minimum price in INR
- `max_price` (integer, optional): Maximum price in INR
- `limit` (integer, default=20): Maximum number of results to return

**Example Request:**
```
GET /api/hospitals?city=Chennai&specialty=Cardiology&max_price=500000&limit=10
```

**Response:**
```json
[
  {
    "id": "ganga-01",
    "name": "Ganga Hospital",
    "city": "Coimbatore",
    "state": "Tamil Nadu",
    "country": "India",
    "zip": "641009",
    "address": "313 Mettupalayam Road, Coimbatore",
    "phone": "+91-422-2393993",
    "email": "info@gangahospital.com",
    "website": "https://www.gangahospital.com",
    "specialties": ["Orthopedics", "Trauma", "Spine Surgery"],
    "procedures": ["Total Knee Replacement", "Hip Replacement"],
    "min_price": 300000,
    "max_price": 800000,
    "ai_score": 8.5,
    "success_rate": 92.5,
    "insurance": ["AYUSH", "Mediclaim"],
    "doctor_count": 25,
    "stars": 4.5,
    "reviews_count": 156,
    "match_score": 0.85,
    "match_reasons": ["Matches your procedure: Total Knee Replacement", "Within your budget"]
  }
]
```

### Hospital Detail

#### GET `/api/hospitals/{hospital_id}`

Retrieve detailed information about a specific hospital.

**Path Parameters:**
- `hospital_id` (string): The hospital's primary key (e.g., "ganga-01")

**Example Request:**
```
GET /api/hospitals/ganga-01
```

**Response:**
Same structure as hospital listing endpoint, but for a single hospital.

**Status Codes:**
- `200`: Success
- `404`: Hospital not found

## Data Models

### Hospital Schema

```python
{
  "id": str,                  # Unique identifier
  "name": str,                # Hospital name
  "city": str,                # City location
  "state": str,               # State (usually Tamil Nadu)
  "country": str,             # Country (India)
  "zip": str,                 # Zip code
  "address": str,             # Full address
  "phone": str,               # Contact phone
  "email": str,               # Email address
  "website": str,             # Website URL
  "specialties": list[str],   # List of medical specialties
  "procedures": list[str],    # List of procedures offered
  "min_price": int,           # Minimum treatment cost in INR
  "max_price": int,           # Maximum treatment cost in INR
  "ai_score": float,          # AI quality rating (0-10)
  "success_rate": float,      # Treatment success rate (0-100)
  "insurance": list[str],     # Accepted insurance schemes
  "doctor_count": int,        # Number of doctors
  "stars": float,             # Star rating (0-5)
  "reviews_count": int,       # Number of published reviews
  "match_score": float,       # Score for current search (0-1)
  "match_reasons": list[str]  # Reasons for matching
}
```

### Search Intent Schema

```python
{
  "specialty": str,           # Medical specialty needed
  "procedure": str,           # Specific procedure
  "city": str,                # Target city
  "budget_max": int,          # Maximum budget in INR
  "insurance_type": str,      # Insurance scheme
  "confidence": float         # Confidence score (0-1)
}
```

### ChatRequest Schema

```python
{
  "session_id": str,          # Unique session identifier
  "message": str,             # User message
  "prescription_data": dict   # Optional prescription extraction
}
```

### ChatResponse Schema

```python
{
  "session_id": str,          # Session identifier
  "text": str,                # AI assistant response
  "actions": list[dict],      # UI actions for frontend
  "hospitals": list[dict]     # Matched hospitals
}
```

### UIAction Schema

```python
{
  "action_type": str,         # Type of action (navigate_to_results, etc.)
  "data": dict                # Action-specific data
}
```

## Error Handling

### Error Response Format

```json
{
  "detail": "Description of the error"
}
```

### Common HTTP Status Codes

- `200 OK`: Successful request
- `400 Bad Request`: Invalid parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server-side error

## Rate Limiting

Currently, no rate limiting is implemented. This will be added in future versions.

## Examples

### Find Hospitals for a Specific Procedure

```bash
curl -X GET "http://localhost:8000/api/hospitals?specialty=Cardiology&city=Chennai&limit=5"
```

### Send a Chat Message

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user-123",
    "message": "I need heart surgery in Chennai with budget of 10 lakhs"
  }'
```

### Upload and Parse a Prescription

```bash
curl -X POST "http://localhost:8000/api/parse-prescription" \
  -F "file=@prescription.jpg" \
  -F "session_id=user-123"
```

## Response Time SLAs

- Hospital listing: < 200ms
- Hospital detail: < 100ms
- Chat endpoint: < 2000ms (includes AI processing)
- Prescription parsing: < 5000ms (includes OCR and NER)

## Version History

- **v1.0.0** (Current): Initial release with core functionality
  - Hospital search and filtering
  - AI-powered chat assistant
  - Prescription OCR and medical NER
  - Multi-language support (English + Tamil Nadu focus)

## Support

For API support, contact: api-support@mediorbital.com
