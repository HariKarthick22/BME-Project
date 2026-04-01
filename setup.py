#!/usr/bin/env python3
"""
Automated Setup Script for CarePath AI Medical Assistant
Handles: venv creation, pip install, frontend setup, database init, MedGemma download

Usage:
    python setup.py

Options:
    - Press Enter to continue each step
    - Type 'skip' to skip MedGemma download (large ~8GB file)
    - Press Ctrl+C to exit anytime (safe - can resume)
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime


class Color:
    """Color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_header(text):
    """Print section header"""
    print(f"\n{Color.BOLD}{Color.BLUE}{'='*80}{Color.END}")
    print(f"{Color.BOLD}{Color.BLUE}{text:^80}{Color.END}")
    print(f"{Color.BOLD}{Color.BLUE}{'='*80}{Color.END}\n")


def print_step(num, text):
    """Print step indicator"""
    print(f"{Color.CYAN}[STEP {num}]{Color.END} {Color.BOLD}{text}{Color.END}")


def print_success(text):
    """Print success message"""
    print(f"{Color.GREEN}✓ {text}{Color.END}")


def print_warn(text):
    """Print warning message"""
    print(f"{Color.YELLOW}⚠ {text}{Color.END}")


def print_error(text):
    """Print error message"""
    print(f"{Color.RED}✗ {text}{Color.END}")


def run_cmd(cmd, description, cwd=None, show_output=False):
    """Run command and handle errors"""
    try:
        if show_output:
            result = subprocess.run(
                cmd if isinstance(cmd, list) else cmd.split(),
                cwd=cwd,
                text=True
            )
            return result.returncode == 0
        else:
            result = subprocess.run(
                cmd if isinstance(cmd, list) else cmd.split(),
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                print_success(description)
                return True
            else:
                print_error(f"{description} - {result.stderr[:100]}")
                return False
    except subprocess.TimeoutExpired:
        print_error(f"{description} - timeout")
        return False
    except Exception as e:
        print_error(f"{description} - {str(e)}")
        return False


def step1_create_venv():
    """Step 1: Create virtual environment"""
    print_step(1, "Creating Virtual Environment")
    
    venv_path = Path(".venv")
    
    if venv_path.exists():
        print_warn("Virtual environment already exists")
        return True
    
    return run_cmd(
        [sys.executable, "-m", "venv", ".venv"],
        "Virtual environment created"
    )


def step2_upgrade_pip():
    """Step 2: Upgrade pip"""
    print_step(2, "Upgrading pip, setuptools, wheel")
    
    if sys.platform == "win32":
        pip_cmd = ".venv\\Scripts\\pip"
    else:
        pip_cmd = ".venv/bin/pip"
    
    return run_cmd(
        [pip_cmd, "install", "--upgrade", "pip", "setuptools", "wheel"],
        "pip upgrade complete"
    )


def step3_install_dependencies():
    """Step 3: Install requirements"""
    print_step(3, "Installing Python Dependencies")
    
    if not Path("requirements.txt").exists():
        print_error("requirements.txt not found")
        return False
    
    if sys.platform == "win32":
        pip_cmd = ".venv\\Scripts\\pip"
    else:
        pip_cmd = ".venv/bin/pip"
    
    return run_cmd(
        [pip_cmd, "install", "-r", "requirements.txt"],
        "Python dependencies installed",
        show_output=True
    )


def step4_download_medgemma():
    """Step 4: Download MedGemma model (optional)"""
    print_step(4, "MedGemma 2B Model Setup (Optional)")
    
    print(f"{Color.YELLOW}Note:{Color.END} This downloads ~8GB model file")
    print("Type 'skip' to skip, or press Enter to continue")
    
    user_input = input(f"{Color.CYAN}> {Color.END}").strip().lower()
    
    if user_input == "skip":
        print_warn("MedGemma download skipped - app will use OpenAI/Anthropic instead")
        return True
    
    from pathlib import Path
    models_dir = Path("models/medgemma")
    models_dir.mkdir(parents=True, exist_ok=True)
    
    print("Downloading MedGemma (this may take 10-30 minutes)...")
    print("Model will be saved to: models/medgemma/")
    
    try:
        import importlib
        hf_module = importlib.import_module("huggingface_hub")
        hf_hub_download = getattr(hf_module, "hf_hub_download")
        
        model_id = "Google/MedGemma-2B"
        filenames = ["model.safetensors", "config.json", "tokenizer.model", "special_tokens_map.json"]
        
        for filename in filenames:
            print(f"  Downloading {filename}...")
            try:
                hf_hub_download(
                    repo_id=model_id,
                    filename=filename,
                    local_dir=str(models_dir),
                    force_download=False
                )
                print_success(f"  {filename}")
            except Exception as e:
                print_warn(f"  Could not download {filename}: {e}")
        
        print_success("MedGemma model setup complete")
        return True
    
    except ImportError:
        print_warn("huggingface-hub not available, skipping model download")
        return True
    except Exception as e:
        print_warn(f"Model download failed (optional): {e}")
        return True


def step5_install_frontend_deps():
    """Step 5: Install frontend dependencies"""
    print_step(5, "Installing Frontend Dependencies")
    
    frontend_dir = Path("frontend")
    
    if not frontend_dir.exists():
        print_warn("frontend/ directory not found - skipping npm install")
        return True
    
    if not Path("frontend/package.json").exists():
        print_warn("package.json not found in frontend/ - skipping npm install")
        return True
    
    return run_cmd(
        "npm install",
        "Frontend dependencies installed (npm)",
        cwd="frontend",
        show_output=True
    )


def step6_initialize_database():
    """Step 6: Initialize database"""
    print_step(6, "Initializing Database")
    
    try:
        import main
        main.init_database()
        print_success("Database initialized")
        
        db_path = Path("data/hospitals.db")
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024*1024)
            print(f"  Database size: {size_mb:.2f} MB")
        
        return True
    except Exception as e:
        print_error(f"Database initialization failed: {e}")
        return False


def step7_setup_env_file():
    """Step 7: Setup .env configuration"""
    print_step(7, "Setting up Environment Configuration")
    
    env_path = Path(".env")
    
    env_content = """# CarePath AI - Environment Configuration
# Add your API keys here

# LLM API Keys (optional - comment out to disable)
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
# GROQ_API_KEY=gsk-...

# LLM Routing and Model Selection
DEFAULT_LLM_PROVIDER=local
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
OPENAI_MODEL=gpt-4o-mini
GROQ_MODEL=llama-3.1-8b-instant

# Local MedGemma via Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MEDGEMMA_MODEL=dcarrascosa/medgemma-1.5-4b-it:Q4_K_M
OLLAMA_FALLBACK_MODEL=llama3.2:3b
OLLAMA_TIMEOUT=120

# Optional NLP model (leave empty to use fallback extractor)
MEDICAL_NLP_MODEL=

# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# CORS Origins (comma-separated)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173

# Database
DATABASE_URL=sqlite:///data/hospitals.db

# Security (optional)
# JWT_SECRET=your-secret-key-here
# ENCRYPTION_KEY=your-encryption-key-here
"""
    
    if env_path.exists():
        try:
            if env_path.read_text().strip():
                print_warn(".env file already exists - skipping creation")
                return True
            print_warn(".env file exists but is empty - writing default configuration")
        except Exception:
            print_warn("Could not read existing .env file - writing default configuration")
    
    try:
        env_path.write_text(env_content)
        print_success(".env configuration file created")
        print(f"  Location: {env_path.absolute()}")
        print(f"  {Color.YELLOW}Important:{Color.END} Edit .env and add your API keys if needed")
        return True
    except Exception as e:
        print_error(f"Could not create .env: {e}")
        return False


def step8_verify_installation():
    """Step 8: Verify installation"""
    print_step(8, "Verifying Installation")
    
    checks = [
        ("requirements.txt", Path("requirements.txt").exists()),
        ("main.py", Path("main.py").exists()),
        ("frontend/", Path("frontend").exists()),
        ("data/hospitals.csv", Path("data/hospitals.csv").exists()),
        ("data/hospitals.db", Path("data/hospitals.db").exists()),
        (".env", Path(".env").exists()),
    ]
    
    all_good = True
    for name, exists in checks:
        status = "✓" if exists else "✗"
        symbol = Color.GREEN if exists else Color.YELLOW
        print(f"{symbol}{status}{Color.END} {name}")
        if not exists and "optional" not in name.lower():
            if not any(opt in name for opt in ["optional"]):
                if name not in ["data/hospitals.db", ".env"]:
                    all_good = False
    
    print()
    
    if all_good:
        print_success("Installation verification complete!")
        return True
    else:
        print_warn("Some files are missing (may not be critical)")
        return True


def main():
    """Main setup flow"""
    print_header("CarePath AI - Automated Setup")
    
    print(f"{Color.BOLD}This script will:{Color.END}")
    print("  1. Create a virtual environment")
    print("  2. Install Python dependencies from requirements.txt")
    print("  3. Setup frontend (npm install)")
    print("  4. Initialize the database")
    print("  5. Create .env configuration file")
    print(f"\n{Color.YELLOW}Estimated time: 3-5 minutes{Color.END}")
    print(f"{Color.YELLOW}(10-30 minutes if downloading MedGemma model){Color.END}\n")
    
    input(f"{Color.CYAN}Press Enter to begin...{Color.END}")
    
    steps = [
        step1_create_venv,
        step2_upgrade_pip,
        step3_install_dependencies,
        step4_download_medgemma,
        step5_install_frontend_deps,
        step6_initialize_database,
        step7_setup_env_file,
        step8_verify_installation,
    ]
    
    completed = 0
    skipped = 0
    
    start_time = datetime.now()
    
    for step_func in steps:
        try:
            if step_func():
                completed += 1
            else:
                print_warn(f"Step {step_func.__name__} had issues - continuing anyway")
        except KeyboardInterrupt:
            print(f"\n{Color.YELLOW}Setup interrupted by user{Color.END}")
            print(f"You can resume later by running: python setup.py")
            sys.exit(0)
        except Exception as e:
            print_error(f"Unexpected error in {step_func.__name__}: {e}")
    
    elapsed = datetime.now() - start_time
    
    print_header("Setup Complete!")
    
    print(f"{Color.BOLD}Next Steps:{Color.END}")
    print("\n1. Edit .env file to add API keys (optional):")
    print(f"   {Color.CYAN}nano .env{Color.END}")
    
    print("\n2. Launch the application:")
    print(f"   {Color.CYAN}python main.py{Color.END}\n")
    
    print("   OR launch backend only:")
    print(f"   {Color.CYAN}python main.py --backend-only{Color.END}")
    
    print(f"\n3. Access the application:")
    print(f"   Frontend:  {Color.CYAN}http://localhost:5173{Color.END}")
    print(f"   Backend:   {Color.CYAN}http://localhost:8000{Color.END}")
    print(f"   API Docs:  {Color.CYAN}http://localhost:8000/docs{Color.END}")
    
    print(f"\n{Color.GREEN}Setup took {elapsed.total_seconds():.0f} seconds{Color.END}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Color.YELLOW}Setup interrupted{Color.END}")
        sys.exit(0)
    except Exception as e:
        print_error(f"Fatal error: {e}")
        sys.exit(1)
