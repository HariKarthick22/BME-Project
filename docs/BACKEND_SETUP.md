# MediOrbit Backend Setup Guide

## Prerequisites

- Python 3.12 or higher
- pip package manager
- Virtual environment (recommended)
- Tesseract OCR (for prescription parsing)
- Anthropic API key (optional, for chat without fallback)
- HuggingFace token (optional, for medical NER)

## Installation Steps

### 1. Create Virtual Environment

```bash
cd /path/to/BME\ Project
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Note on specific packages:**
- `numpy`, `scipy`, `scikit-learn` come with Transformers
- `torch` is a large download (~2GB) - ensure good internet connection
- `anthropic` SDK requires Python 3.7+
- Windows users may need to install PyTorch separately from pytorch.org

### 3. Install Tesseract OCR

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**Windows:**
- Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
- Add to PATH: `C:\Program Files\Tesseract-OCR`

**Verify installation:**
```bash
tesseract --version
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Anthropic API (for Claude chat)
ANTHROPIC_API_KEY=sk-ant-...your-key-here...

# HuggingFace API (for medical NER model)
HF_TOKEN=hf_...your-hf-token...

# Optional database settings
DATABASE_URL=sqlite:///backend/data/hospitals.db
LOG_LEVEL=INFO
```

**Obtaining Keys:**
- **Anthropic API**: https://console.anthropic.com/ (create account, generate key)
- **HuggingFace Token**: https://huggingface.co/settings/tokens (account required)

### 5. Initialize Database

The database will be auto-initialized on first app run, but you can manually init:

```bash
cd backend
python3 -c "from models.database import init_db; init_db()"
```

This creates:
- `backend/data/hospitals.db` (SQLite database)
- Tables: hospitals, extractions, conversation_history
- Seed data: ~50 Tamil Nadu hospitals

## Running the Backend

### Development Server

```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
INFO:     HuggingFace NER pipeline loaded successfully.
```

Access the API:
- **Health check**: http://localhost:8000/
- **OpenAPI docs**: http://localhost:8000/docs
- **ReDoc docs**: http://localhost:8000/redoc

### Production Server

```bash
cd backend
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

Or with Uvicorn directly (with multiple workers):

```bash
cd backend
python3 -m uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000
```

## Project Structure

```
backend/
├── main.py                     # FastAPI application + endpoints
├── requirements.txt            # Python dependencies
├── agents/
│   ├── __init__.py
│   ├── conversation_agent.py   # Chat orchestrator
│   ├── intent_agent.py         # Intent extraction
│   ├── hospital_matcher.py     # Hospital scoring/ranking
│   ├── navigation_agent.py     # UI action generation
│   └── prescription_parser.py  # OCR + medical NER
├── models/
│   ├── __init__.py
│   ├── schemas.py              # Pydantic data models
│   └── database.py             # SQLite operations
└── data/
    └── hospitals.db            # SQLite database (created on init)
```

## API Testing

### Using curl

**Health Check:**
```bash
curl http://localhost:8000/
```

**List Hospitals:**
```bash
curl "http://localhost:8000/api/hospitals?city=Chennai&limit=5"
```

**Get Hospital Details:**
```bash
curl "http://localhost:8000/api/hospitals/ganga-01"
```

**Send Chat Message:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "message": "I need cardiac surgery in Chennai"
  }'
```

**Upload Prescription:**
```bash
curl -X POST http://localhost:8000/api/parse-prescription \
  -F "file=@prescription.jpg" \
  -F "session_id=test-123"
```

### Using Python Requests

```python
import requests
import json

# Health check
response = requests.get('http://localhost:8000/')
print(response.json())

# Search hospitals
params = {
    'city': 'Chennai',
    'specialty': 'Cardiology',
    'max_price': 500000,
    'limit': 10
}
response = requests.get('http://localhost:8000/api/hospitals', params=params)
hospitals = response.json()

# Chat
payload = {
    'session_id': 'user-123',
    'message': 'I need knee surgery'
}
response = requests.post('http://localhost:8000/api/chat', json=payload)
chat_response = response.json()
print(chat_response['text'])
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named X"

**Solution**: Ensure virtual environment is activated and dependencies installed:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Issue: "HuggingFace NER model could not be loaded"

This is non-fatal. App continues with degraded NER functionality.

**Solutions**:
- Check internet connection (first run downloads ~500MB model)
- Verify HF_TOKEN is set in .env
- Check disk space for model cache (~2GB)
- Pre-download model: `python3 -c "from transformers import pipeline; pipeline('ner', model='d4data/biomedical-ner-all')"`

### Issue: "OSError: [Errno 2] No such file or directory: 'tesseract'"

**Solution**: Tesseract not installed or not in PATH. Install it:

**macOS:**
```bash
brew install tesseract
```

**Ubuntu:**
```bash
sudo apt-get install tesseract-ocr
```

**Windows**: Add to PATH in System Environment Variables

### Issue: "ANTHROPIC_API_KEY not present in environment"

**Solution**: Set API key in `.env`:
```env
ANTHROPIC_API_KEY=sk-ant-...your-actual-key...
```

App will fall back to rule-based responses if key is missing (non-fatal).

### Issue: SQLite database locked

**Solution**: This is usually temporary with WAL mode. Wait a moment and retry. In production, ensure single writer.

### Issue: Slow chat responses

**Diagnosis**:
- First run: HF model loading (one-time, ~30s)
- Claude API: Network latency or model processing
- Database: Hospital query overhead (unlikely with <100 records)

**Solutions**:
- Pre-load models at startup
- Cache hospital data in memory
- Use smaller Claude model (currently using Haiku - already optimized)

## Database Management

### Inspect Database

```bash
cd backend
sqlite3 data/hospitals.db

# List tables
.tables

# View hospital count
SELECT COUNT(*) FROM hospitals;

# View a hospital record
SELECT * FROM hospitals LIMIT 1;

# Query specific city
SELECT id, name, city, ai_score FROM hospitals WHERE city='Chennai';
```

### Backup Database

```bash
cp backend/data/hospitals.db backend/data/hospitals.db.backup
```

### Reset Database

```bash
rm backend/data/hospitals.db*
python3 -c "from models.database import init_db; init_db()"
```

## Performance Tuning

### Database Indexing

```sql
-- Add indexes for common queries
CREATE INDEX idx_city ON hospitals(city);
CREATE INDEX idx_specialty ON hospitals(specialties);
CREATE INDEX idx_price ON hospitals(min_price, max_price);
```

### Caching

Consider adding Redis for session caching:

```python
# Pseudo-code for future enhancement
import redis
cache = redis.Redis(host='localhost', port=6379, db=0)

# In conversation_agent.py
conversation_key = f"conv:{session_id}"
history = cache.get(conversation_key)
```

### Connection Pooling

For production, use SQLAlchemy with connection pooling:

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    'sqlite:///hospitals.db',
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20
)
```

## Monitoring and Logging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Monitor Request Performance

```bash
# Install apache-bench
ab -n 100 -c 10 http://localhost:8000/api/hospitals

# Or use locust
pip install locust
locust -f locustfile.py --host=http://localhost:8000
```

### Track API Metrics

Current logging covers:
- API errors (500, exceptions)
- NER model loading status
- Database operations

For production monitoring, integrate:
- Prometheus + Grafana for metrics
- ELK stack for logging
- Sentry for error tracking

## API Documentation

Once backend is running, access docs at:
- **OpenAPI/Swagger UI**: http://localhost:8000/docs
- **ReDoc Alternative**: http://localhost:8000/redoc

Auto-generated documentation includes:
- All endpoints with descriptions
- Request/response schemas
- Try-it-out functionality
- Status codes and error messages

## Next Steps

1. ✅ Backend is running locally
2. → Set up Frontend (see FRONTEND_SETUP.md)
3. → Configure browser API proxy in vite.config.js
4. → Start frontend dev server
5. → Test end-to-end workflow

## Support

For backend issues:
- Check logs: Look for `INFO`, `WARNING`, `ERROR` messages
- Enable debug logging for detailed traces
- Test endpoints directly with curl
- Verify database with sqlite3 CLI

**Common Endpoints Reference:**
- `GET http://localhost:8000/` → Health
- `GET http://localhost:8000/docs` → API docs
- `GET http://localhost:8000/api/hospitals` → Search
- `POST http://localhost:8000/api/chat` → Chat
- `POST http://localhost:8000/api/parse-prescription` → Upload
