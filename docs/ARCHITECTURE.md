# MediOrbit System Architecture

## Overview

MediOrbit is a medical tourism recommendation system for Tamil Nadu, India. It uses AI-powered agents to understand patient needs, match them with suitable hospitals, and guide them through the medical travel process.

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER (React)                             │
├─────────────────────┬──────────────────────┬──────────────────────────────┤
│   HomePage.jsx      │  ResultsPage.jsx     │  HospitalDetailPage.jsx      │
│  (AI Chat & Steps)  │  (Filterable Grid)   │  (Full Hospital Details)     │
└─────────────────────┴──────────────────────┴──────────────────────────────┘
         ▲                   ▲                       ▲
         │                   │                       │
         │ HTTP/JSON REST    │                       │
         │                   │                       │
┌────────▼───────────────────────────────────────────────────────────────────┐
│                    CHAT & NAVIGATION LAYER (React)                         │
├─────────────────────┬──────────────────────┬──────────────────────────────┤
│  ChatWidget.jsx     │ ChatPanel.jsx        │  NavigationAgent Context     │
│  (Floating Bubble)  │ (Message Display)    │  (State Management)          │
└─────────────────────┴──────────────────────┴──────────────────────────────┘
         ▲                   ▲                       ▲
         │                   │                       │
         │              API Calls                    │
         │              to /api/*                    │
         │                                           │
┌────────▼─────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY (FastAPI)                               │
├──────────────────────────────────────────────────────────────────────────────┤
│  POST /api/chat              GET /api/hospitals        GET /api/hospitals/{id}
│  POST /api/parse-prescription (with CORS middleware)                         │
└────────▲──────────────────────────────────────────────────────────────────────┘
         │
         │ Function Calls
         │
┌────────▼──────────────────────────────────────────────────────────────────────┐
│                      AGENT ORCHESTRATION LAYER                               │
├──────────────────┬────────────────────┬─────────────────┬───────────────────┤
│  ConversationAgent│ IntentAgent        │ HospitalMatcher │  NavigationAgent  │
│  (Master Orch.)  │ (Parse Query)       │ (Scoring Engine)│ (UI Actions)      │
│                  │ Claude API +        │                 │                   │
│                  │ Local Fallback      │ Weighted        │ Rule-based        │
│                  │                     │ Multi-factor    │ Action Generator  │
└──────────────────┴────────────────────┴─────────────────┴───────────────────┘
         ▲                ▲                    ▲
         │                │                    │
         │ Python Calls   │                    │
         │                │                    │
┌────────▼────────────────▼────────────────────▼──────────────────────────────┐
│              PRESCRIPTION PARSER AGENT                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│  File Extraction       │  OCR Processing    │  Medical NER                  │
│  - PDF text extract    │  - pytesseract     │  - HuggingFace d4data model  │
│  - Image bytes read    │  - Image to text   │  - Entity extraction        │
│                        │                    │  - Diagnosis/Proc/Med labels  │
└────────▲───────────────▲────────────────────▲──────────────────────────────┘
         │               │                    │
         │               │ Model Loaded       │
         │               │ at Startup         │
         │               │                    │
┌────────▼───────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                         │
├──────────────────────┬──────────────────────┬──────────────────────────────┤
│  SQLite Database     │  HuggingFace Models │  Anthropic Claude API        │
│  - hospitals table   │  - Biomedical NER   │  - chat completion          │
│  - extractions table │  - model weights    │  - system prompts           │
│  - conv_history      │  - embedding models │  - max tokens: 512          │
│  (WAL mode)          │  (downloaded at init)│  (gpt-3.5-turbo compatible)│
└──────────────────────┴──────────────────────┴──────────────────────────────┘
```

## Component Details

### Frontend Layer (React)

#### Core Pages
- **HomePage.jsx**: Initial landing page with AI chat search interface
  - Animated steps showing the medical travel process
  - Chip-based quick search suggestions
  - Integration with FloatingChatWidget

- **ResultsPage.jsx**: Hospital search results with filters
  - Real-time filtering by specialty, city, price range
  - Sortable results (rating, cost, distance)
  - Grid layout with HospitalCard components
  - Server-side pagination (limit=20)

- **HospitalDetailPage.jsx**: Detailed hospital information
  - Full hospital profile with specialties and procedures
  - Pricing breakdown (min/max/average)
  - Patient reviews and ratings
  - Insurance accepted, doctor count, facilities
  - Links to Google Maps and hospital website

#### Components
- **ChatWidget.jsx**: Floating chat bubble
  - Toggleable chat panel
  - Sends messages to `/api/chat` endpoint
  - Handles typing indicators
  - Processes UI actions from backend

- **ChatPanel.jsx**: Message display area
  - Shows conversation history
  - Message bubbles with timestamps
  - Typing indicator animation
  - Input field with send button

- **PrescriptionUpload.jsx**: File upload component
  - Drag-and-drop prescription upload
  - Calls `/api/parse-prescription` endpoint
  - Displays extracted medical information
  - Navigation to results based on procedure

- **HospitalFilters.jsx**: Filter UI for results page
  - Expandable sections for each filter
  - Specialty selection with search
  - City filter with search
  - Rating and sort controls

### API Gateway Layer (FastAPI)

**Framework**: FastAPI 0.115.0 with Uvicorn

**Features**:
- CORS middleware for localhost development
- Lifespan context manager for startup/shutdown
- Request validation with Pydantic
- Automatic OpenAPI/Swagger documentation
- Async request handling

**Endpoints**:
- `GET /`: Health check
- `POST /api/chat`: Main chat interface
- `POST /api/parse-prescription`: Prescription upload
- `GET /api/hospitals`: Hospital search/filter
- `GET /api/hospitals/{id}`: Hospital detail

### Agent Orchestration Layer

#### ConversationAgent (conversation_agent.py)
**Responsibility**: Master orchestrator for chat sessions

**Process**:
1. Load conversation history from database
2. Save incoming user message
3. Retrieve any prior prescription extraction
4. Run IntentAgent to extract search intent
5. Match hospitals if intent detected
6. Generate system prompt with context
7. Call Anthropic Claude API
8. Generate UI actions via NavigationAgent
9. Save assistant response
10. Return ChatResponse with text + actions + hospitals

**Config**:
- Model: claude-3-5-haiku-20241022
- Max tokens: 512
- System prompt: Medical tourism assistant for Tamil Nadu

#### IntentAgent (intent_agent.py)
**Responsibility**: Extract structured search intent from natural language

**Process**:
1. Try Claude API with few-shot examples
2. Fallback to regex-based parsing for:
   - Tamil Nadu city names (Chennai, Coimbatore, etc.)
   - Medical specialties (Cardiology, Orthopedics, etc.)
   - Budget extraction from text
   - Insurance scheme names

**Outputs**: SearchIntent object with specialty, procedure, city, budget_max, insurance_type

#### HospitalMatchingAgent (hospital_matcher.py)
**Responsibility**: Score and rank hospitals against patient needs

**Scoring Formula** (weighted):
- Specialty/Procedure Match: 35%
- Budget Fit: 25%
- Location Match: 20%
- Insurance Match: 10%
- Base Quality Score: 10%

**Scoring Logic**:
- Specialty score: 1.0 (exact match), 0.7 (substring), 0.0 (no match)
- Budget score: 1.0 (within budget), 0.5 (partial fit), 0.0 (unaffordable)
- Location score: 1.0 (same city), 0.6 (same state), 0.3 (different)
- Insurance score: 1.0 (accepted), 0.0 (not accepted)
- Base score: (ai_score/100 × 0.5) + (success_rate/100 × 0.5)

**Output**: Top N hospitals (default 5) with match_score and match_reasons

#### NavigationAgent (navigation_agent.py)
**Responsibility**: Generate UI action commands for frontend

**Actions**:
- `navigate_to_results`: Show filtered hospital list
- `navigate_to_hospital_detail`: Show specific hospital
- `highlight_hospital`: Highlight in current view
- `clear_highlight`: Remove highlight

**Detection Logic**:
- Looks for city mentions (detection via IntentAgent)
- Detects price/budget filters
- Suggests hospital comparisons
- Triggers results page navigation

#### PrescriptionParserAgent (prescription_parser.py)
**Responsibility**: OCR + Medical NER pipeline for prescription images

**Process**:
1. Receive file bytes from multipart upload
2. Determine file type (image vs PDF)
3. Extract text via:
   - OCR: pytesseract for image files
   - Text extraction: pypdf for PDF files
4. Run HuggingFace medical NER model
5. Extract entities:
   - DISO (disorder/diagnosis)
   - CHEM (chemical/medication)
   - PROC (procedure)
6. Normalize whitespace and title-case
7. Deduplicate extracted entities
8. Return ExtractionResult

**NER Model**: d4data/biomedical-ner-all (aggregation_strategy="simple")

### Data Layer

#### SQLite Database (hospitals.db)

**Tables**:

**hospitals**
```sql
CREATE TABLE hospitals (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  city TEXT,
  state TEXT,
  country TEXT,
  zip TEXT,
  address TEXT,
  phone TEXT,
  email TEXT,
  website TEXT,
  specialties JSON,        -- Array of specialty strings
  procedures JSON,         -- Array of procedure strings
  min_price INTEGER,
  max_price INTEGER,
  ai_score REAL,
  success_rate REAL,
  insurance JSON,          -- Array of insurance scheme names
  doctor_count INTEGER,
  stars REAL,
  reviews_count INTEGER,
  latitude REAL,
  longitude REAL
)
```

**extractions**
```sql
CREATE TABLE extractions (
  id TEXT PRIMARY KEY,
  session_id TEXT,
  diagnosis JSON,
  procedure JSON,
  medications JSON,
  patient_age INTEGER,
  patient_gender TEXT,
  raw_text TEXT,
  created_at TIMESTAMP
)
```

**conversation_history**
```sql
CREATE TABLE conversation_history (
  id TEXT PRIMARY KEY,
  session_id TEXT,
  role TEXT,        -- "user" or "assistant"
  content TEXT,
  created_at TIMESTAMP
)
```

**Features**:
- WAL (Write-Ahead Logging) mode for concurrent access
- JSON columns for flexible array storage
- per-request connection handling
- Seed data with ~50 Tamil Nadu hospitals

#### External APIs

**Anthropic Claude** (conversation_agent.py)
- Model: claude-3-5-haiku-20241022
- API Key: ANTHROPIC_API_KEY environment variable
- Purpose: Natural language understanding and response generation
- Fallback: Rule-based response if API unavailable

**HuggingFace** (prescription_parser.py)
- Model: d4data/biomedical-ner-all
- API Token: HF_TOKEN environment variable (optional)
- Purpose: Medical entity recognition from OCR text
- Download: Automatic at application startup (lifespan)

## Data Flow Examples

### Patient Search Flow
```
User Message
    ↓
Chat API (/api/chat)
    ↓
ConversationAgent.process_message()
    ├─ IntentAgent: "I need cardiac surgery in Chennai"
    │  → SearchIntent(specialty="Cardiac Surgery", city="Chennai")
    │
    ├─ HospitalMatcher: Query hospitals + score
    │  → [Hospital1(score=0.89), Hospital2(score=0.78), ...]
    │
    ├─ Claude API: Generate natural response
    │  → "I found 5 cardiac surgery hospitals in Chennai..."
    │
    ├─ NavigationAgent: Generate actions
    │  → UIAction(navigate_to_results, data={query: "cardiac surgery in Chennai"})
    │
    └─ Save to conversation_history
        ↓
        ChatResponse (text + actions + hospitals)
            ↓
        Frontend receives → Navigate + Display Results
```

### Prescription Upload Flow
```
Prescription File
    ↓
Upload API (/api/parse-prescription)
    ↓
PrescriptionParser.parse_prescription()
    ├─ OCR: Extract text from image
    │  → "Patient: John Doe, Age: 45, Diagnosis: Type 2 Diabetes..."
    │
    ├─ Medical NER: Extract entities
    │  → diagnosis=["Type 2 Diabetes"], procedure=["Cardiac Catheterization"], ...
    │
    └─ Save to extractions table
        ↓
        PrescriptionParseResponse (extraction + summary)
            ↓
        Frontend:
        ├─ Show extraction results
        ├─ Pass to next chat message
        └─ Navigate to results if procedure found
```

## Technology Stack

### Backend
- **Framework**: FastAPI 0.115.0
- **Server**: Uvicorn 0.30.6
- **Database**: SQLite3 with WAL
- **AI/ML**: 
  - Anthropic Python SDK 0.34.2 (Claude API)
  - Transformers 4.44.2 (HuggingFace models)
  - PyTorch 2.4.1 (inference backend)
- **OCR**: pytesseract 0.3.10 + Tesseract
- **Image**: Pillow 10.2.0

### Frontend
- **Framework**: React 19.2.4 with Vite 8
- **Routing**: react-router-dom 7.13.1
- **CSS**: Tailwind CSS (via globals.css)
- **Build**: Vite with dev server proxy

### Development
- **Python**: 3.12+
- **Node.js**: 16+ (for npm/Vite)
- **Package Managers**: pip + npm

## Performance Characteristics

| Operation | Expected Duration | Notes |
|-----------|------------------|-------|
| Hospital Search | < 200ms | SQLite query + filtering |
| Hospital Detail | < 100ms | Direct DB lookup |
| Chat Message | 1-3s | Includes Claude API call |
| Prescription Parse | 3-5s | OCR + NER inference |
| App Startup | 5-10s | HF model download if needed |

## Security Considerations

### Current Implementation
- CORS restricted to localhost (development)
- No authentication/authorization
- API keys stored in `.env` files (local development)
- SQLite default file permissions

### Recommended for Production
- Use HTTPS/TLS for all endpoints
- Implement API key authentication
- Add rate limiting per client
- Use environment variable vaults for secrets
- SQL injection prevention (Pydantic validation + parameterized queries)
- File upload size limits (currently unlimited)
- Input sanitization for OCR text

## Deployment Considerations

### Backend Deployment
- Use production ASGI server (e.g., Gunicorn + Uvicorn workers)
- Configure database backups and WAL checkpoints
- Set up monitoring for API latency and error rates
- Cache HuggingFace models to avoid download delays
- Consider containerization (Docker) for consistency

### Frontend Deployment
- Build with `npm run build` for production bundle
- Deploy to CDN or static hosting (Vercel, Netlify)
- Configure API base URL for prod environment
- Enable gzip compression for assets

## Future Enhancements

1. **Multi-language Support**: Tamil language chat + OCR
2. **User Accounts**: Session persistence across devices
3. **Insurance Integration**: Real-time verification of insurance coverage
4. **Appointment Booking**: Direct scheduling with hospitals
5. **Payment Gateway**: In-app pricing and payment handling
6. **Video Consultations**: Telemedicine integration
7. **Travel Planning**: Visa, accommodation, transport suggestions
8. **Analytics Dashboard**: Hospital performance metrics
