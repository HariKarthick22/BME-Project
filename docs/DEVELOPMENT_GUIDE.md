# MediOrbit Development Guide

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- SQLite
- FastAPI
- React 19

### Installation

#### Backend
```bash
# Clone the repository
git clone https://github.com/your-org/mediorbit.git
cd mediorbit

# Install Python dependencies
pip install -r requirements.txt

# Set up database
python -c "from database import init_db; init_db()"
```

#### Frontend
```bash
cd medioorbit
npm install
```

## Running the Application

### Development Mode
```bash
# Terminal 1: Start FastAPI backend
cd mediorbit
python server_fastapi.py

# Terminal 2: Start React frontend
cd medioorbit
npm run dev
```

### Production Mode
```bash
# Build frontend
cd medioorbit
npm run build

# Start production server
cd mediorbit
uvicorn server_fastapi:app --host 0.0.0.0 --port 8000
```

## Project Structure

```
mediorbit/
├── src/
│   ├── components/          # React components
│   ├── context/            # React context providers
│   ├── pages/              # Page components
│   ├── App.jsx             # Main app component
│   └── vite.config.js      # Vite configuration
├── agents/                 # Python AI agents
│   ├── prescription_parser.py
│   ├── intent_agent.py
│   ├── hospital_matcher_v2.py
│   ├── navigation_agent.py
│   └── conversation_agent.py
├── server_fastapi.py       # FastAPI server
├── database.py            # Database utilities
├── schema.sql             # Database schema
├── covaicare.db           # SQLite database
├── requirements.txt       # Python dependencies
└── docs/                  # Documentation
```

## Backend Development

### Adding New Endpoints
1. Open `server_fastapi.py`
2. Add new route using FastAPI decorators
3. Implement the endpoint logic
4. Add error handling
5. Update API documentation

### Creating New Agents
1. Create new file in `agents/` directory
2. Implement agent class with required methods
3. Add to `__init__.py` if needed
4. Test with unit tests

### Database Operations
```python
# Using database utilities
from database import get_db, init_db

# Get database connection
db = get_db()

# Query hospitals
hospitals = db.execute("SELECT * FROM hospitals").fetchall()
```

## Frontend Development

### Adding New Components
1. Create component in `src/components/`
2. Import and use in pages
3. Add styling in CSS files
4. Test with Storybook (if available)

### Navigation
```javascript
// Using React Router
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();
navigate('/results');
```

### State Management
```javascript
// Using NavigationContext
import { useNavigation } from '../context/NavigationAgent';

const { navigateToResults, highlightHospital } = useNavigation();
navigateToResults('cardiac surgery');
```

## Testing

### Backend Tests
```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_agents.py

# Run with coverage
python -m pytest tests/ --cov=agents
```

### Frontend Tests
```bash
cd medioorbit
npm test

# Run with coverage
npm run test:coverage
```

## API Development

### Adding New Endpoints
1. Define route in `server_fastapi.py`
2. Create Pydantic models for request/response
3. Add to OpenAPI documentation
4. Implement validation
5. Add error handling

### Request Validation
```python
from fastapi import HTTPException
from pydantic import BaseModel

class SearchRequest(BaseModel):
    procedure: str
    location: str = None
    budget: float = None

@app.post("/api/hospitals/search")
def search_hospitals(request: SearchRequest):
    if not request.procedure:
        raise HTTPException(status_code=400, detail="Procedure is required")
    # Process request
```

## Deployment

### Docker Deployment
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "server_fastapi:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables
```bash
# Backend
export DATABASE_URL="sqlite:///covaicare.db"
export DEBUG="True"
export PORT=8000

# Frontend
export VITE_API_URL="http://localhost:8000/api"
```

## Debugging

### Backend Debugging
```bash
# Run with debug
python server_fastapi.py --debug

# Enable debug mode
export DEBUG=True
python server_fastapi.py

# Check logs
tail -f logs/api.log
```

### Frontend Debugging
```bash
# Run with debug
npm run dev -- --debug

# Check browser console
# Use React DevTools
# Use Redux DevTools if applicable
```

## Performance Optimization

### Backend
- Use database indexes
- Implement caching
- Use async/await for I/O operations
- Optimize database queries

### Frontend
- Code splitting
- Lazy loading
- Image optimization
- Bundle analysis

## Security

### Best Practices
- Validate all inputs
- Use HTTPS in production
- Implement rate limiting
- Sanitize user inputs
- Use secure headers

### Common Vulnerabilities
- SQL injection prevention
- XSS protection
- CSRF protection
- File upload validation

## Monitoring

### Application Metrics
- Response times
- Error rates
- Database queries
- Memory usage

### Logging
- Structured logging
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Log rotation
- Error tracking

## Contributing

### Code Style
- Follow PEP 8 for Python
- Use Prettier for JavaScript/TypeScript
- Add type hints where applicable
- Write meaningful commit messages

### Pull Request Process
1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Update documentation
6. Submit pull request

## Troubleshooting

### Common Issues

#### Backend
- **Port already in use**: Check for running processes
- **Database connection failed**: Check SQLite file permissions
- **Import errors**: Verify Python path

#### Frontend
- **Module not found**: Check import paths
- **Build errors**: Check package.json dependencies
- **Runtime errors**: Check browser console

### Debug Commands
```bash
# Check Python version
python --version

# Check npm version
npm --version

# Check if port is in use
lsof -i :8000

# Check logs
tail -f logs/api.log
```

## Support

### Getting Help
- Check the documentation
- Search existing issues
- Ask in community forums
- Contact maintainers

### Reporting Issues
- Provide detailed error messages
- Include environment information
- Share code snippets
- Describe steps to reproduce

## Version History

### v1.0.0
- Initial release
- Basic hospital recommendation
- Chat interface
- Prescription upload

### v1.1.0
- Added advanced filtering
- Improved AI matching
- Performance optimizations
- Bug fixes

## License

This project is licensed under the MIT License.

## Acknowledgments

- FastAPI team for the excellent framework
- React team for the UI library
- Hugging Face for the NLP models
- All contributors and supporters