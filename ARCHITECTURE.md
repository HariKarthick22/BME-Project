# BME Project - Optimized Architecture & Implementation Guide

## 📋 Overview

This document outlines the completely restructured, production-ready architecture for the MediOrbit hospital recommendation system.

---

## 🏗️ NEW PROJECT STRUCTURE

```
/Users/harikarthick/Desktop/BME Project/
│
├── backend/                           # FastAPI backend service
│   ├── main.py                        # FastAPI application entry point
│   ├── models/
│   │   ├── database.py                # SQLite operations
│   │   └── schemas.py                 # Pydantic models
│   ├── agents/                        # AI/ML agents
│   │   ├── intent_agent.py
│   │   ├── hospital_matcher.py
│   │   ├── conversation_agent.py
│   │   ├── navigation_agent.py
│   │   └── prescription_parser.py
│   └── data/
│       ├── hospitals.csv              # Hospital data source (23 hospitals)
│       └── hospitals.db               # SQLite database
│
├── medioorbit/                        # React 19 + Vite frontend
│   ├── src/
│   │   ├── ui/                        # ✅ NEW - All UI components unified
│   │   │   ├── pages/
│   │   │   │   ├── ResultsPage.jsx    # ✅ UPDATED - Top 5 hospitals, dynamic data
│   │   │   │   ├── HomePage.jsx       # Move here from /pages
│   │   │   │   ├── HospitalDetailPage.jsx
│   │   │   │   └── ResultsPage.css
│   │   │   │
│   │   │   ├── components/
│   │   │   │   ├── HospitalCard.jsx   # Move from /components
│   │   │   │   ├── HospitalCard.css
│   │   │   │   ├── HospitalFilters.jsx
│   │   │   │   ├── MedicalDocScanner.jsx  # ✅ NEW - Medical document upload & OCR
│   │   │   │   ├── MedicalDocScanner.css
│   │   │   │   ├── ChatPanel.jsx
│   │   │   │   ├── ChatWidget.jsx
│   │   │   │   ├── Navbar.jsx
│   │   │   │   ├── Navbar.css
│   │   │   │   ├── Footer.jsx
│   │   │   │   └── Footer.css
│   │   │   │
│   │   │   └── styles/
│   │   │       ├── ResultsPage.css
│   │   │       ├── global.css
│   │   │       └── theme.css
│   │   │
│   │   ├── services/                  # ✅ NEW - API integration layer
│   │   │   └── hospitalService.js     # Centralized API calls
│   │   │
│   │   ├── utils/                     # ✅ NEW - Helper functions
│   │   │   ├── normalizeData.js       # Data transformation & formatting
│   │   │   └── medicalCoding.js       # ICD-10 codes, medical terminology
│   │   │
│   │   ├── hooks/                     # ✅ NEW - Custom React hooks
│   │   │   └── useHospitals.js        # Hospital data fetching hook
│   │   │
│   │   ├── context/
│   │   │   └── NavigationAgent.jsx    # Global navigation state
│   │   │
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── public/
│   │
│   ├── package.json
│   ├── vite.config.js
│   └── dist/
│
├── .env                               # ✅ REQUIRED - Environment variables
├── requirements.txt                   # Python dependencies
├── ARCHITECTURE.md                    # This file
│
└── [DELETED FILES]
    ├── ❌ agents/ (old/deprecated)
    ├── ❌ static/ (unused HTML)
    ├── ❌ server_fastapi.py
    └── ❌ medioorbit/src/data/hospitals.js (hardcoded data)
```

---

## ✨ KEY IMPROVEMENTS

### 1. **Data Management**
✅ **Removed hardcoded hospital data** from frontend
✅ **Implemented genuine top 5 system**: Hospitals ranked by AI score, always fresh from backend
✅ **Unified data normalization**: Single `normalizeData.js` handles all format conversions
✅ **SessionStorage caching**: Smart cache for chat results with fallback to full API

### 2. **Frontend Architecture**
✅ **UI Folder Consolidation**: All UI components in `/ui` (pages, components, styles)
✅ **Service Layer**: Centralized API calls in `hospitalService.js`
✅ **Utility Functions**: Separation of concerns - formatting, filtering, sorting
✅ **Medical Coding Module**: ICD-10 support, diagnosis extraction
✅ **Document Scanner**: Medical document upload with OCR integration

### 3. **Features Implemented**
✅ **Medical Document Scanner** (MedicalDocScanner.jsx)
  - Upload prescription/medical documents (JPG, PNG, PDF)
  - Automatic OCR processing
  - Extract diagnoses, medications, procedures
  - Display medical coding results

✅ **Medical Coding & ICD-10**
  - Pre-mapped procedure codes (CABG, knee replacement, etc.)
  - Automatic diagnosis extraction from text
  - Cost estimation based on procedure
  - Specialty mapping

✅ **Dynamic Hospital Ranking**
  - Top 5 hospitals by AI score + success rate
  - Real-time filtering by specialty, city, price
  - Dynamic sorting options
  - Live statistics (avg rating, avg cost)

✅ **Enhanced UI/UX**
  - Rank badges (#1-5) on cards
  - Hospital detail modal view
  - Responsive grid layout (mobile → desktop)
  - Loading states & error handling
  - Summary statistics display

### 4. **Code Organization**
✅ **Services**: API integration layer (`hospitalService.js`)
✅ **Utils**: Reusable functions (`normalizeData.js`, `medicalCoding.js`)
✅ **Hooks**: React custom hooks (ready for `useHospitals.js`)
✅ **Styles**: Organized CSS in `/ui/styles/`

---

## 🔧 SETUP INSTRUCTIONS

### Step 1: Configure Environment Variables

Edit `.env` file in project root:

```env
# Hugging Face - Required for medical document NER
HF_TOKEN=your_huggingface_token_here

# Anthropic Claude - Required for intent extraction & responses
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Claude model version
CLAUDE_MODEL_ID=claude-3-5-haiku-20241022
```

**How to get tokens:**
- **HF_TOKEN**: https://huggingface.co/settings/tokens
- **ANTHROPIC_API_KEY**: https://console.anthropic.com/api-keys

### Step 2: Install Python Dependencies

```bash
cd "/Users/harikarthick/Desktop/BME Project"
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Start Backend

```bash
cd "/Users/harikarthick/Desktop/BME Project/backend"
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs on: **http://localhost:8000**

### Step 4: Start Frontend

```bash
cd "/Users/harikarthick/Desktop/BME Project/medioorbit"
npm install
npm run dev
```

Frontend runs on: **http://localhost:5173**

### Step 5: Verify Setup

1. Open http://localhost:5173 in browser
2. Search for hospitals using chat interface
3. Results page should show **top 5 hospitals** by score
4. Upload medical document using scanner
5. Verify OCR extraction works

---

## 📡 API ENDPOINTS

### Chat Interface
```
POST /api/chat
Body: {
  "session_id": "user-123",
  "message": "knee replacement in coimbatore under 5 lakh",
  "prescription_data": {...}
}
Response: {
  "text": "I found 3 hospitals...",
  "hospitals": [...],
  "actions": [...]
}
```

### Hospital Listing
```
GET /api/hospitals?limit=5&city=Coimbatore&specialty=Orthopedics
Response: [{id, name, ai_score, successtrate, pricing, ...}]
```

### Single Hospital
```
GET /api/hospitals/{hospital_id}
Response: {Hospital object with full details}
```

### Document Processing
```
POST /api/parse-prescription
Body: FormData with file
Response: {
  "extraction": {
    "diagnosis": [...],
    "medications": [...],
    "procedure": [...]
  },
  "summary": "..."
}
```

---

## 🎨 COMPONENT HIERARCHY

```
App.jsx
├── HomePage.jsx
│   ├── ChatWidget.jsx
│   │   ├── ChatPanel.jsx
│   │   └── MedicalDocScanner.jsx ✨ NEW
│   └── HeroSection
│
├── ResultsPage.jsx ✨ UPDATED
│   ├── HospitalFilters.jsx
│   └── HospitalCard.jsx (x5)
│       └── ScoreRing.jsx
│
└── HospitalDetailPage.jsx
```

---

## 🚀 DATA FLOW (Updated)

```
User Input (Chat/Document)
    ↓
/api/chat endpoint
    ↓
IntentAgent (Extract intent) + HospitalMatchingAgent
    ↓
[AI Scoring + Ranking]
    ↓
Top 5 Hospitals (by ai_score + success_rate)
    ↓
sessionStorage.setItem('lastSearchResults', hospitals)
    ↓
Frontend: ResultsPage.jsx
    ↓
normalizeHospitals() → getTopHospitals(5)
    ↓
Display with Rank Badges (#1-5)
```

---

## 📊 Database Structure

### Hospitals Table
```
Columns:
- id (TEXT PRIMARY KEY)
- name (TEXT)
- city (TEXT)
- specialties (JSON)
- procedures (JSON)
- min_price, max_price (INTEGER)
- ai_score (REAL)
- success_rate (REAL)
- lead_doctors (TEXT)
- phone, email (TEXT)
- address, lat, lng (TEXT)
- insurance (JSON)
```

**Total Records**: 23 hospitals (all in Tamil Nadu/Coimbatore)

---

## 🎯 NEXT STEPS (Future Enhancements)

1. **Hospital System Integration**
   - Add hospital login system
   - Create doctor profiles
   - Implement appointment booking

2. **Advanced Features**
   - Multi-language support (Tamil, English, Hindi)
   - Payment gateway integration
   - Insurance verification
   - Patient reviews & ratings

3. **Analytics**
   - User search analytics
   - Hospital performance metrics
   - Cost trend analysis

4. **Mobile App**
   - React Native app
   - Offline mode support
   - Push notifications

---

## ⚙️ TROUBLESHOOTING

### "No hospitals found"
**Solution**: Check that backend is running, database is initialized, and API is accessible

### "OCR not working"
**Solution**: Verify HF_TOKEN is set correctly and model has downloaded (~300MB)

### "Claude API errors"
**Solution**: Check ANTHROPIC_API_KEY is valid and has remaining credits

### "Port already in use"
**Solution**: Change port in backend (`--port 9000`) or frontend (`vite.config.js`)

---

## 📝 File Manifest

| File | Purpose | Status |
|------|---------|--------|
| `hospitalService.js` | API integration | ✅ NEW |
| `normalizeData.js` | Data formatting | ✅ NEW |
| `medicalCoding.js` | ICD-10 codes | ✅ NEW |
| `MedicalDocScanner.jsx` | Document upload | ✅ NEW |
| `ResultsPage.jsx` | Top 5 display | ✅ UPDATED |
| `HospitalCard.jsx` | Card component | ✅ INHERITED |
| `.env` | Environment config | ✅ REQUIRED |

---

## 🔐 Security Best Practices

✅ API keys in `.env` (not in code)
✅ CORS configured for local testing
✅ Input validation on file uploads (10MB max)
✅ Sanitized medical data handling
✅ Session storage for user privacy

---

**Version**: 2.0.0 (Restructured)
**Last Updated**: March 2025
**Maintenance**: Regular updates for hospital data & features
