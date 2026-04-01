#!/bin/bash

# ============================================
# Run Frontend Only
# ============================================

echo "=========================================="
echo "🟡 Starting Frontend Development Server"
echo "=========================================="

cd "$(dirname "$0")"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

echo -e "\n✅ Starting dev server..."
npm run dev

echo -e "\n🌐 Frontend running at http://localhost:5173"
