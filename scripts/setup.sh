#!/bin/bash
# BME Project - Complete Setup & File Migration Script
# Run this script to automatically migrate files and clean up legacy code

set -e  # Exit on error

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 BME Project File Migration Script"
echo "===================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# STEP 1: Verify directories exist
echo "Step 1: Verifying new directory structure..."
if [ ! -d "frontend/src/ui/pages" ]; then
    print_error "ui/pages directory not found!"
    exit 1
fi
print_status "New structure verified"
echo ""

# STEP 2: Backup existing files
echo "Step 2: Creating backup of existing files..."
if [ ! -d "frontend/src/BACKUP" ]; then
    mkdir -p frontend/src/BACKUP
    cp -r frontend/src/pages/* frontend/src/BACKUP/ 2>/dev/null || true
    cp -r frontend/src/components/* frontend/src/BACKUP/ 2>/dev/null || true
    print_status "Backup created in frontend/src/BACKUP"
else
    print_warning "Backup folder already exists"
fi
echo ""

# STEP 3: Copy files to new locations
echo "Step 3: Migrating files to new structure..."

# Copy pages
if [ -f "frontend/src/pages/HomePage.jsx" ]; then
    cp frontend/src/pages/HomePage.jsx frontend/src/ui/pages/
    print_status "HomePage.jsx"
fi

if [ -f "frontend/src/pages/HospitalDetailPage.jsx" ]; then
    cp frontend/src/pages/HospitalDetailPage.jsx frontend/src/ui/pages/
    print_status "HospitalDetailPage.jsx"
fi

# Copy components
COMPONENTS=(
    "HospitalCard.jsx"
    "HospitalFilters.jsx"
    "ChatPanel.jsx"
    "ChatWidget.jsx"
    "ScoreRing.jsx"
    "Navbar.jsx"
    "Footer.jsx"
    "PrescriptionUpload.jsx"
)

for component in "${COMPONENTS[@]}"; do
    if [ -f "frontend/src/components/$component" ]; then
        cp "frontend/src/components/$component" frontend/src/ui/components/
        print_status "$component"
    fi
done

# Copy CSS files
find frontend/src/components -name "*.css" -exec cp {} frontend/src/ui/components/ \; 2>/dev/null || true
find frontend/src/pages -name "*.css" -exec cp {} frontend/src/ui/styles/ \; 2>/dev/null || true
find frontend/src/styles -name "*.css" -exec cp {} frontend/src/ui/styles/ \; 2>/dev/null || true

print_status "All CSS files migrated"
echo ""

# STEP 4: Delete legacy files
echo "Step 4: Cleaning up legacy files..."

# Delete old folders
find agents -type f -name "*.py" 2>/dev/null && rm -rf agents/ && print_status "Deleted agents/" || true
[ -d "static" ] && rm -rf static && print_status "Deleted static/" || true
[ -f "server_fastapi.py" ] && rm server_fastapi.py && print_status "Deleted server_fastapi.py" || true
[ -f "frontend/src/data/hospitals.js" ] && rm frontend/src/data/hospitals.js && print_status "Deleted hardcoded hospital data" || true

echo ""

# STEP 5: Configure environment
echo "Step 5: Environment Configuration..."
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# Hugging Face token - for authenticated HF downloads
# Get yours at: https://huggingface.co/settings/tokens
HF_TOKEN=your_hf_token_here

# Anthropic API key - required for Claude calls
# Get yours at: https://console.anthropic.com/api-keys
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Claude model ID for conversation and intent extraction
CLAUDE_MODEL_ID=claude-3-5-haiku-20241022
EOF
    print_status ".env file created"
    print_warning "⚠️  IMPORTANT: Update .env with your actual API keys!"
else
    print_warning ".env file already exists"
fi
echo ""

# STEP 6: Install dependencies
echo "Step 6: Installing dependencies..."
if [ -f "requirements.txt" ]; then
    print_status "requirements.txt found"
    print_warning "Run: source .venv/bin/activate && pip install -r requirements.txt"
fi

if [ -f "frontend/package.json" ]; then
    print_status "package.json found"
    print_warning "Run: cd frontend && npm install"
fi
echo ""

# STEP 7: Verify setup
echo "Step 7: Verification..."
print_status "Structure verification complete"
echo ""

echo "📋 REMAINING MANUAL STEPS:"
echo "=============================="
echo ""
echo "1. UPDATE API KEYS in .env file:"
echo "   nano .env"
echo "   # Replace placeholders with real values"
echo ""
echo "2. UPDATE IMPORTS in App.jsx and other files:"
echo "   OLD: import HomePage from './pages/HomePage'"
echo "   NEW: import HomePage from './ui/pages/HomePage'"
echo ""
echo "3. START BACKEND:"
echo "   cd backend"
echo "   python -m uvicorn main:app --reload"
echo ""
echo "4. START FRONTEND:"
echo "   cd frontend"
echo "   npm install"
echo "   npm run dev"
echo ""
echo "5. OPEN BROWSER:"
echo "   http://localhost:5173"
echo ""
echo "${GREEN}✅ File migration complete!${NC}"
echo ""
