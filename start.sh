#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# MediOrbit — single startup script
# Starts Ollama, the FastAPI backend, and the Vite frontend.
#
# Prerequisites:
#   • Ollama installed  → https://ollama.ai
#   • Model pulled      → ollama pull medgemma:4b
#   • Python venv ready → python -m venv .venv && pip install -r requirements.txt
#   • Node deps ready   → cd medioorbit && npm install
#
# Usage:
#   chmod +x start.sh
#   ./start.sh
# ─────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Colour helpers ──────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}[MediOrbit]${NC} $*"; }
warn()    { echo -e "${YELLOW}[MediOrbit]${NC} $*"; }
error()   { echo -e "${RED}[MediOrbit]${NC} $*" >&2; }

# ── Cleanup on exit ─────────────────────────────────────────────
PIDS=()
cleanup() {
  info "Shutting down…"
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

# ── 1. Check .env exists ────────────────────────────────────────
if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
  warn ".env not found — copying from .env.example"
  warn "Edit .env and set JWT_SECRET_KEY before production use!"
  cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
fi

# Generate a JWT secret if the placeholder is still empty
if grep -q "^JWT_SECRET_KEY=$" "$SCRIPT_DIR/.env"; then
  JWT=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  sed -i.bak "s/^JWT_SECRET_KEY=$/JWT_SECRET_KEY=${JWT}/" "$SCRIPT_DIR/.env"
  rm -f "$SCRIPT_DIR/.env.bak"
  info "Auto-generated JWT_SECRET_KEY and saved to .env"
fi

# ── 2. Start Ollama ─────────────────────────────────────────────
if command -v ollama &>/dev/null; then
  if ! curl -sf http://localhost:11434/api/tags &>/dev/null; then
    info "Starting Ollama…"
    ollama serve &>/dev/null &
    PIDS+=($!)
    sleep 2
    info "Ollama started (PID ${PIDS[-1]})"
  else
    info "Ollama already running ✓"
  fi

  # Pull MedGemma if not already downloaded
  if ! ollama list 2>/dev/null | grep -q "medgemma:4b"; then
    warn "MedGemma model not found — pulling medgemma:4b (~3 GB, one-time download)…"
    ollama pull medgemma:4b
  fi
else
  warn "Ollama not found — AI features will be unavailable."
  warn "Install from https://ollama.ai then run: ollama pull medgemma:4b"
fi

# ── 3. Activate Python venv ─────────────────────────────────────
VENV="$SCRIPT_DIR/.venv"
if [[ -d "$VENV" ]]; then
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  info "Python venv activated ✓"
else
  warn ".venv not found — using system Python (run: python -m venv .venv && pip install -r requirements.txt)"
fi

# ── 4. Start FastAPI backend ────────────────────────────────────
info "Starting FastAPI backend on http://localhost:8000 …"
cd "$SCRIPT_DIR/backend"
uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --timeout-keep-alive 300 \
  --log-level info &
BACKEND_PID=$!
PIDS+=($BACKEND_PID)
cd "$SCRIPT_DIR"

# Wait for backend to be healthy
info "Waiting for backend…"
for i in {1..15}; do
  if curl -sf http://localhost:8000/api/health &>/dev/null; then
    info "Backend healthy ✓"
    break
  fi
  sleep 1
done

# ── 5. Start Vite frontend ──────────────────────────────────────
info "Starting Vite frontend on http://localhost:5173 …"
cd "$SCRIPT_DIR/medioorbit"
npm run dev &
FRONTEND_PID=$!
PIDS+=($FRONTEND_PID)
cd "$SCRIPT_DIR"

# ── Done ────────────────────────────────────────────────────────
echo ""
info "────────────────────────────────────────────"
info "  MediOrbit is running!"
info "  Frontend  →  http://localhost:5173"
info "  Backend   →  http://localhost:8000"
info "  API docs  →  http://localhost:8000/docs"
info "────────────────────────────────────────────"
info "Press Ctrl+C to stop all services."
echo ""

# Keep script alive until Ctrl+C
wait
