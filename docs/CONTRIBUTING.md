# Contributing to MediOrbit

Thank you for your interest in contributing to MediOrbit! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

- Be respectful and inclusive to all contributors
- Focus on constructive feedback
- Report issues respectfully
- Welcome diversity in backgrounds and experience
- Help create a welcoming community

## How Can I Contribute?

### 1. Report Bugs

**Found a bug?** Please report it by creating a GitHub issue:

**Include**:
- Clear bug title
- Detailed description
- Steps to reproduce
- Expected vs actual behavior
- Screenshots/logs if applicable
- Environment (OS, browser, etc)

**Example**:
```
Title: Chat widget crashes when message is too long

Steps:
1. Open chat widget
2. Type message with >500 characters
3. Click send

Expected: Message sends successfully
Actual: Chat widget closes unexpectedly

Environment: Chrome 120, macOS 13
```

### 2. Suggest Features

**Have an idea?** Suggest it as a GitHub discussion:

**Include**:
- Feature title
- Use case / problem it solves
- Proposed solution
- Alternative approaches
- Examples/mockups if applicable

**Example**:
```
Title: Support for multi-language search

Use Case: Many patients speak Tamil as first language

Proposal: Add Tamil language option for:
- Chat interface
- Search queries
- Hospital information display

Would improve accessibility for local patients.
```

### 3. Submit Code Changes

**Want to code?** Follow these steps:

#### Step 1: Fork and Clone

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/your-username/mediorbital.git
cd mediorbital

# Add upstream remote
git remote add upstream https://github.com/EvoAgentX/EvoAgentX.git
```

#### Step 2: Create a Branch

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Or for bugfixes
git checkout -b fix/bug-description
```

**Branch naming**:
- `feature/add-user-accounts`
- `fix/chat-widget-crash`
- `docs/update-setup-guide`
- `test/add-prescription-parser-tests`

#### Step 3: Make Changes

1. **Code Style**: Follow existing patterns
2. **Commit Messages**: Clear and descriptive
   ```bash
   git commit -m "feat: Add multi-language chat support"
   git commit -m "fix: Correct hospital ranking algorithm"
   git commit -m "docs: Update API documentation"
   ```

3. **Comments & Documentation**: Add docstrings
   ```python
   def calculate_hospital_score(hospital, intent):
       """
       Calculate weighted match score for a hospital.
       
       Scores hospital across 5 dimensions:
       - Specialty match (35%)
       - Budget fit (25%)
       - Location (20%)
       - Insurance (10%)
       - Quality (10%)
       
       Args:
           hospital: Hospital object from database
           intent: SearchIntent from IntentAgent
           
       Returns:
           float: Weighted score between 0 and 1
       """
   ```

4. **Tests**: Add test cases for new code
   ```python
   def test_calculate_hospital_score_specialty_match():
       hospital = {"specialties": ["Cardiology"]}
       intent = SearchIntent(specialty="Cardiology")
       score = calculate_hospital_score(hospital, intent)
       assert score > 0.8
   ```

#### Step 4: Test Locally

**Backend**:
```bash
cd backend
python3 -m pytest tests/
python3 main.py  # Manual testing
```

**Frontend**:
```bash
cd frontend
npm run lint
npm run build
npm run preview
```

#### Step 5: Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
# Include:
# - What changes were made
# - Why the changes are needed
# - How to test the changes
# - Screenshots/logs for UI changes
```

## Development Setup

### Backend Development

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install pytest pytest-cov black isort

# Run tests
pytest

# Format code
black backend/
isort backend/

# Run linter
flake8 backend/
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev

# Run linter
npm run lint

# Build
npm run build

# Test build
npm run preview
```

## Code Standards

### Python (Backend)

**Style Guide**: PEP 8

**Format Code Automatically**:
```bash
pip install black
black backend/agents/ backend/models/ backend/main.py
```

**Import Sorting**:
```bash
pip install isort
isort backend/
```

**Lines**: Max 88 characters (Black default)

**Docstring Style**: Google Style
```python
def function_name(arg1: str, arg2: int) -> bool:
    """
    Brief description of function.
    
    Longer description explaining what it does, edge cases,
    and important behavior.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2
        
    Returns:
        bool: Description of return value
        
    Raises:
        ValueError: When arg2 is negative
    """
```

**Type Hints**: Use typing for all functions
```python
from typing import Optional, List, Dict

def search_hospitals(
    city: str,
    specialty: Optional[str] = None,
    limit: int = 20
) -> List[Hospital]:
    pass
```

### JavaScript/React (Frontend)

**Style Guide**: Airbnb JavaScript Style Guide

**Format Code**:
```bash
npm install -D prettier
npx prettier --write src/
```

**Components**:
```jsx
/**
 * FeatureName component
 * 
 * Brief description of what this component does.
 * 
 * Props:
 *   - propName (type): Description
 *   - another (type): Description
 */
export default function ComponentName({ propName, another }) {
  // Implementation
}
```

**Comments**: Use JSDoc style
```jsx
// Single line comment for brief notes

/*
  Multi-line comment for detailed explanations
  Explain the why, not just the what
*/
```

## Database Changes

### Adding New Fields

1. **Migration**:
   - Create migration script in `backend/migrations/`
   - Version: `001_add_field_name.sql`
   - Include both UP and DOWN migrations

2. **Schema Update**:
   - Update `models/database.py` CREATE TABLE
   - Update `models/schemas.py` Pydantic models

3. **Testing**:
   - Test migration on fresh database
   - Test with existing data

### Adding New Tables

Follow same pattern as adding fields.

## Testing

### Backend Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_hospital_matcher.py

# Run with coverage
pytest --cov=agents --cov=models

# Run specific test
pytest tests/test_hospital_matcher.py::test_calculate_score
```

**Test Structure**:
```python
import pytest
from agents.hospital_matcher import calculate_score

def test_calculate_score_with_specialty_match():
    """Test that matching specialty increases score."""
    hospital = {"specialties": ["Cardiology"]}
    intent = SearchIntent(specialty="Cardiology")
    
    score = calculate_score(hospital, intent)
    
    assert score > 0.7
    
def test_calculate_score_without_match():
    """Test score when no attributes match."""
    hospital = {"specialties": ["Cardiology"]}
    intent = SearchIntent(specialty="Orthopedics")
    
    score = calculate_score(hospital, intent)
    
    assert score < 0.5
```

### Frontend Tests

```bash
# Run tests (when set up)
npm test

# Run with coverage
npm test -- --coverage

# Run in watch mode
npm test -- --watch
```

## API Endpoint Changes

### Adding New Endpoint

1. **In `main.py`**:
```python
@app.post("/api/new-endpoint")
def new_endpoint(body: NewRequest) -> NewResponse:
    """
    Brief description of endpoint.
    
    Args:
        body: Request payload
        
    Returns:
        NewResponse with data
    """
    try:
        result = process_request(body)
        return NewResponse(data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

2. **In `models/schemas.py`**:
```python
class NewRequest(BaseModel):
    field1: str
    field2: int
    
class NewResponse(BaseModel):
    data: dict
    status: str = "success"
```

3. **Documentation**: Update `docs/API_DOCUMENTATION.md`

4. **Test**: Use curl or Python to verify

## Documentation Updates

### Update Existing Docs

1. Navigate to `/docs` folder
2. Edit the `.md` file
3. Use clear, concise language
4. Include code examples
5. Keep in sync with code changes

### Examples to Document

```
- New API endpoints
- Algorithm changes
- Database schema changes
- Configuration options
- Known limitations
- Troubleshooting guides
```

## Release Process

### Version Numbering

Uses Semantic Versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes (1.0.0)
- MINOR: New features, backwards compatible (1.1.0)
- PATCH: Bug fixes (1.1.1)

### Release Checklist

- [ ] Update version in `package.json` and `main.py`
- [ ] Update `CHANGELOG.md`
- [ ] Run all tests
- [ ] Build both frontend and backend
- [ ] Create release notes
- [ ] Tag release: `git tag v1.0.0`
- [ ] Push to GitHub: `git push --tags`

## Performance Considerations

### Backend

- ✅ Query optimization for databases
- ✅ Caching frequently accessed data
- ✅ Async/await for I/O operations
- ✅ Error handling without blocking
- ❌ Avoid N+1 queries
- ❌ Avoid synchronous calls in async context

### Frontend

- ✅ Code splitting for pages
- ✅ Lazy loading of images
- ✅ Memoization of expensive computations
- ✅ Debounce search/filter inputs
- ❌ Avoid unnecessary re-renders
- ❌ Avoid large bundles

## Security Best Practices

### Backend

- ✅ Validate all inputs (Pydantic)
- ✅ Sanitize database queries (parameterized)
- ✅ Use HTTPS in production
- ✅ Secure API keys (environment variables)
- ❌ Don't log sensitive data
- ❌ Don't expose internal errors to users

### Frontend

- ✅ Use HTTPS for API calls
- ✅ Sanitize user input before display
- ✅ Validate file uploads
- ❌ Don't store sensitive data in localStorage
- ❌ Don't expose API keys in frontend code

## Pull Request Review

Expect reviewers to check for:

1. **Functionality**: Does it work? Are edge cases handled?
2. **Code Quality**: Is it readable? Does it follow standards?
3. **Tests**: Is it adequately tested?
4. **Documentation**: Is it documented?
5. **Performance**: Any impact on speed?
6. **Security**: Any vulnerabilities?

## Getting Help

- **Documentation**: Check `/docs` folder
- **Issues**: Search existing GitHub issues
- **Discussions**: Use GitHub discussions for questions
- **Code Comments**: Ask in PR discussions

## Commit Message Conventions

```
type(scope): subject

body

footer
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation update
- `style`: Code style (no logic change)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Dependency update, build config, etc

**Examples**:
```
feat(chat): Add support for Tamil language

Adds Tamil language support to chat interface and hospital search.
Implements language detection and translation via Claude API.

Closes #123

---

fix(hospital-matcher): Correct specialty matching algorithm

The substring match was incorrectly matching partial words.
Now uses word boundary matching for accuracy.

---

docs(setup): Add troubleshooting section

Adds common issues and solutions to BACKEND_SETUP.md.
```

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Given credit in commit history

## Questions?

- Create a GitHub discussion
- Ask in PR comments
- Email: dev@mediorbital.com

---

**Thank you for contributing to MediOrbit!** 🎉

Together, we're making medical tourism accessible to everyone. ❤️
