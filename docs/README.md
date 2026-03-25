# MediOrbit Documentation

## Overview
MediOrbit is a comprehensive medical hospital recommendation system that helps users find and evaluate hospitals for medical procedures. The system combines AI-powered analysis with user-friendly interfaces to provide personalized hospital recommendations.

## System Architecture

### Backend Components
- **FastAPI Server** (`server_fastapi.py`) - Main API server
- **Agents** (`/agents/`) - Specialized AI agents:
  - `prescription_parser.py` - OCR and medical NER for prescriptions
  - `intent_agent.py` - Natural language query understanding
  - `hospital_matcher_v2.py` - Weighted scoring and ranking engine
  - `navigation_agent.py` - UI action command generator
  - `conversation_agent.py` - Master orchestrator with Claude

### Frontend Components
- **React 19** (`frontend/`) - Modern frontend application
- **Chat Interface** - Floating chat widget with conversation capabilities
- **Navigation Context** - State management for UI actions
- **Prescription Upload** - Drag-and-drop prescription processing

## API Endpoints

### Hospitals
- `GET /api/hospitals` - List all hospitals with filtering and sorting
- `GET /api/hospitals/{id}` - Get detailed hospital information
- `POST /api/hospitals/search` - Search hospitals with advanced filters

### Prescriptions
- `POST /api/prescription` - Upload and process prescription images
- `GET /api/prescription/{id}` - Get prescription processing results

### Agents
- `POST /api/agents/intent` - Process natural language queries
- `POST /api/agents/match` - Get hospital recommendations
- `POST /api/agents/navigate` - Generate UI navigation actions

## Installation

### Backend
```bash
pip install -r requirements.txt
python server_fastapi.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Configuration

### Database
- SQLite database: `covaicare.db`
- Schema: `schema.sql`
- Connection: `database.py`

### Development Proxy
- Vite proxy config: `/Users/harikarthick/Desktop/BME Project/frontend/vite.config.js`
- Proxies `/api` requests to `localhost:8000`

## Usage

### Basic Workflow
1. Upload prescription (optional)
2. Use chat interface to search for hospitals
3. View results with filtering and sorting
4. Click on hospital for detailed information
5. Use navigation commands for UI actions

### Chat Commands
- "Find hospitals for [procedure]"
- "Compare costs for [procedure]"
- "Show hospitals near me"
- "Navigate to results page"
- "Help me with [medical condition]"

## Development

### Backend Development
```bash
# Run FastAPI server
python server_fastapi.py

# Test API endpoints
curl http://localhost:8000/api/hospitals
```

### Frontend Development
```bash
# Start Vite dev server
cd frontend
npm run dev

# Build for production
npm run build
```

## File Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ChatWidget.jsx
│   │   ├── ChatPanel.jsx
│   │   ├── PrescriptionUpload.jsx
│   │   ├── HospitalCard.jsx
│   │   └── ScoreRing.jsx
│   ├── context/
│   │   └── NavigationAgent.js
│   ├── pages/
│   │   ├── HomePage.jsx
│   │   ├── ResultsPage.jsx
│   │   └── HospitalDetailPage.jsx
│   ├── App.jsx
│   └── vite.config.js
├── agents/
│   ├── prescription_parser.py
│   ├── intent_agent.py
│   ├── hospital_matcher_v2.py
│   ├── navigation_agent.py
│   └── conversation_agent.py
├── server_fastapi.py
├── database.py
├── schema.sql
├── covaicare.db
├── requirements.txt
└── docs/
    └── README.md
```

## API Reference

### Hospital Matching
```python
# Example usage
from agents.hospital_matcher_v2 import HospitalMatcher
matcher = HospitalMatcher()
results = matcher.match_hospitals(procedure="cardiac surgery", budget=500000)
```

### Intent Processing
```python
# Example usage
from agents.intent_agent import IntentAgent
agent = IntentAgent()
intent = agent.process_query("I need a hospital for knee replacement")
```

## Testing

### Backend Tests
```bash
# Run FastAPI tests
python -m pytest tests/

# Test individual agents
python -m agents.prescription_parser.py
python -m agents.intent_agent.py
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Deployment

### Production Setup
1. Build frontend: `npm run build`
2. Configure production database
3. Set up reverse proxy (nginx/Apache)
4. Configure SSL certificates
5. Set up monitoring and logging

## Troubleshooting

### Common Issues
- **CORS errors**: Check Vite proxy configuration
- **Database connection**: Verify SQLite file permissions
- **API not responding**: Check FastAPI server logs
- **Frontend build errors**: Check package.json dependencies

### Debug Mode
```bash
# Backend debug
export DEBUG=True
python server_fastapi.py

# Frontend debug
npm run dev -- --debug
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions:
- Create an issue in the repository
- Check the FAQ in docs/FAQ.md
- Review the troubleshooting guide