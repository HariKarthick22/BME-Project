# MediOrbit API Reference

## Overview
MediOrbit provides a comprehensive REST API for hospital recommendations, prescription processing, and AI-powered medical assistance.

## Base URL
```
http://localhost:8000/api
```

## Authentication
All endpoints are currently open access. For production deployment, implement JWT authentication.

## Error Handling
All endpoints return JSON responses with the following structure:

```json
{
  "success": true,
  "data": {},
  "message": "Operation successful",
  "error": null
}
```

On error:
```json
{
  "success": false,
  "data": null,
  "message": "Error description",
  "error": "ERROR_CODE"
}
```

## Endpoints

### Hospitals

#### GET /api/hospitals
List all hospitals with optional filtering and sorting.

**Query Parameters:**
- `procedure` (string) - Filter by procedure name
- `min_rating` (number) - Minimum hospital rating
- `max_distance` (number) - Maximum distance in km
- `sort` (string) - Sort field: 'rating', 'distance', 'cost'
- `limit` (number) - Maximum results to return

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Apollo Hospitals",
      "rating": 4.5,
      "address": "123 Main St",
      "city": "Mumbai",
      "state": "Maharashtra",
      "zip": "400001",
      "phone": "+91-22-12345678",
      "email": "info@apollohospitals.com",
      "specialties": ["cardiac surgery", "orthopedics"],
      "pricing": {
        "minCost": 150000,
        "maxCost": 350000,
        "avgCost": 250000,
        "insuranceAccepted": true
      },
      "stats": {
        "successRate": 92,
        "distance": 5.2,
        "travelTime": "15 mins"
      },
      "facilities": ["ICU", "Emergency", "Pharmacy"],
      "reviews": [
        {
          "patientName": "John Doe",
          "rating": 5,
          "comment": "Excellent care",
          "date": "2024-01-15"
        }
      ],
      "aiScore": 4.7
    }
  ],
  "message": "Hospitals retrieved successfully",
  "error": null
}
```

#### GET /api/hospitals/{id}
Get detailed information for a specific hospital.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Apollo Hospitals",
    "rating": 4.5,
    "address": "123 Main St",
    "city": "Mumbai",
    "state": "Maharashtra",
    "zip": "400001",
    "phone": "+91-22-12345678",
    "email": "info@apollohospitals.com",
    "specialties": ["cardiac surgery", "orthopedics"],
    "pricing": {
      "minCost": 150000,
      "maxCost": 350000,
      "avgCost": 250000,
      "insuranceAccepted": true
    },
    "stats": {
      "successRate": 92,
      "distance": 5.2,
      "travelTime": "15 mins",
      "beds": 300,
      "doctors": 50
    },
    "facilities": ["ICU", "Emergency", "Pharmacy", "Blood Bank"],
    "reviews": [
      {
        "patientName": "John Doe",
        "rating": 5,
        "comment": "Excellent care",
        "date": "2024-01-15"
      }
    ],
    "aiScore": 4.7,
    "heroImage": "https://example.com/hospital.jpg",
    "googleMapsUrl": "https://maps.google.com/?q=Apollo+Hospitals+Mumbai"
  },
  "message": "Hospital retrieved successfully",
  "error": null
}
```

#### POST /api/hospitals/search
Advanced hospital search with complex filters.

**Request Body:**
```json
{
  "procedures": ["cardiac surgery", "angioplasty"],
  "budget_min": 100000,
  "budget_max": 500000,
  "min_rating": 4.0,
  "max_distance": 50,
  "insurance": true,
  "sort_by": "ai_score",
  "page": 1,
  "limit": 10
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "hospitals": [...],
    "total": 25,
    "page": 1,
    "limit": 10,
    "total_pages": 3
  },
  "message": "Search results retrieved successfully",
  "error": null
}
```

### Prescriptions

#### POST /api/prescription
Upload and process prescription images.

**Request:**
- Content-Type: multipart/form-data
- File: prescription image (JPG, PNG, PDF)

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "prescription_123",
    "patientName": "John Doe",
    "age": 45,
    "gender": "male",
    "procedure": "cardiac surgery",
    "medications": ["aspirin", "beta-blocker"],
    "extractedText": "Prescription text content",
    "confidence": 0.92
  },
  "message": "Prescription processed successfully",
  "error": null
}
```

#### GET /api/prescription/{id}
Get prescription processing results.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "prescription_123",
    "patientName": "John Doe",
    "age": 45,
    "gender": "male",
    "procedure": "cardiac surgery",
    "medications": ["aspirin", "beta-blocker"],
    "extractedText": "Prescription text content",
    "confidence": 0.92,
    "processedAt": "2024-01-15T10:30:00Z"
  },
  "message": "Prescription data retrieved successfully",
  "error": null
}
```

### Agents

#### POST /api/agents/intent
Process natural language queries.

**Request Body:**
```json
{
  "query": "I need a hospital for heart surgery in Mumbai",
  "context": {
    "budget": 300000,
    "location": "Mumbai",
    "urgency": "medium"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "intent": "SEARCH_HOSPITALS",
    "procedure": "heart surgery",
    "location": "Mumbai",
    "budget": 300000,
    "urgency": "medium",
    "entities": [
      {"type": "procedure", "value": "heart surgery"},
      {"type": "location", "value": "Mumbai"}
    ],
    "confidence": 0.95
  },
  "message": "Intent processed successfully",
  "error": null
}
```

#### POST /api/agents/match
Get hospital recommendations.

**Request Body:**
```json
{
  "intent": "SEARCH_HOSPITALS",
  "procedure": "heart surgery",
  "budget": 300000,
  "location": "Mumbai",
  "preferences": {
    "insurance": true,
    "distance": 20
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "hospitals": [
      {
        "id": 1,
        "name": "Apollo Hospitals",
        "score": 4.8,
        "reasons": ["Excellent success rate", "Accepts insurance", "Close to location"]
      }
    ],
    "summary": "Found 5 hospitals matching your criteria",
    "total_count": 5
  },
  "message": "Hospital matching completed",
  "error": null
}
```

#### POST /api/agents/navigate
Generate UI navigation actions.

**Request Body:**
```json
{
  "action": "navigate_to_results",
  "data": {
    "procedure": "heart surgery",
    "location": "Mumbai"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "action": "navigate_to_results",
    "url": "/results?procedure=heart%20surgery&location=Mumbai",
    "description": "Navigate to hospital results page",
    "parameters": {
      "procedure": "heart surgery",
      "location": "Mumbai"
    }
  },
  "message": "Navigation action generated",
  "error": null
}
```

#### POST /api/agents/conversation
Master conversation orchestrator.

**Request Body:**
```json
{
  "message": "Find me the best hospital for knee replacement",
  "context": {
    "user_id": "user_123",
    "session_id": "session_456",
    "previous_intent": "SEARCH_HOSPITALS"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "response": "I found 8 hospitals for knee replacement in your area. Would you like to see the top recommendations?",
    "suggested_actions": [
      {"type": "show_results", "data": {"count": 8}},
      {"type": "ask_for_budget", "data": {"default": 200000}}
    ],
    "next_intent": "CONFIRM_RESULTS",
    "confidence": 0.92
  },
  "message": "Conversation processed successfully",
  "error": null
}
```

## Models

### Hospital Model
```json
{
  "id": "integer",
  "name": "string",
  "rating": "number",
  "address": "string",
  "city": "string",
  "state": "string",
  "zip": "string",
  "phone": "string",
  "email": "string",
  "specialties": ["string"],
  "pricing": {
    "minCost": "number",
    "maxCost": "number",
    "avgCost": "number",
    "insuranceAccepted": "boolean"
  },
  "stats": {
    "successRate": "number",
    "distance": "number",
    "travelTime": "string",
    "beds": "number",
    "doctors": "number"
  },
  "facilities": ["string"],
  "reviews": [{
    "patientName": "string",
    "rating": "number",
    "comment": "string",
    "date": "date"
  }],
  "aiScore": "number",
  "heroImage": "string",
  "googleMapsUrl": "string"
}
```

### Prescription Model
```json
{
  "id": "string",
  "patientName": "string",
  "age": "number",
  "gender": "string",
  "procedure": "string",
  "medications": ["string"],
  "extractedText": "string",
  "confidence": "number",
  "processedAt": "date"
}
```

### Intent Model
```json
{
  "intent": "string",
  "procedure": "string",
  "location": "string",
  "budget": "number",
  "urgency": "string",
  "entities": [{
    "type": "string",
    "value": "string"
  }],
  "confidence": "number"
}
```

## Status Codes

- `200 OK` - Successful request
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation failed
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service temporarily unavailable

## Rate Limiting
- Default: 100 requests per minute per IP
- Burst: 10 requests per second
- Adjust limits in production based on usage patterns

## CORS
- Allowed origins: `*` (development)
- Methods: `GET, POST, PUT, DELETE, OPTIONS`
- Headers: `Content-Type, Authorization, X-Requested-With`

## Security
- All endpoints use HTTPS in production
- Input validation for all parameters
- Rate limiting to prevent abuse
- SQL injection prevention in database queries
- File upload validation for prescriptions

## Maintenance

### Health Check
```
GET /api/health
```
Returns system status and uptime.

### Metrics
```
GET /api/metrics
```
Returns API usage statistics and performance metrics.

## Support

For API issues and questions:
- Check the error messages in responses
- Review the logs in `/logs/api.log`
- Contact support at support@mediorbit.com