#!/bin/bash

# SQLAI Local LLM Setup Script
# This script installs and configures Ollama with required models

echo "================================================"
echo "SQLAI Local LLM Setup"
echo "================================================"

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check operating system
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
else
    print_error "Unsupported operating system: $OSTYPE"
    exit 1
fi

echo "Detected OS: $OS"
echo ""

# Step 1: Check if Ollama is installed
echo "Step 1: Checking Ollama installation..."
if command -v ollama &> /dev/null; then
    print_success "Ollama is already installed"
    ollama --version
else
    print_warning "Ollama not found. Installing..."
    
    if [[ "$OS" == "macos" ]]; then
        # Install using Homebrew
        if command -v brew &> /dev/null; then
            brew install ollama
            if [ $? -eq 0 ]; then
                print_success "Ollama installed successfully"
            else
                print_error "Failed to install Ollama"
                exit 1
            fi
        else
            print_error "Homebrew not found. Please install Homebrew first:"
            echo "       /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            exit 1
        fi
    else
        # Linux installation
        curl -fsSL https://ollama.ai/install.sh | sh
        if [ $? -eq 0 ]; then
            print_success "Ollama installed successfully"
        else
            print_error "Failed to install Ollama"
            exit 1
        fi
    fi
fi

echo ""

# Step 2: Start Ollama service
echo "Step 2: Starting Ollama service..."
if pgrep -x "ollama" > /dev/null; then
    print_success "Ollama service is already running"
else
    print_warning "Starting Ollama service..."
    ollama serve &> /dev/null &
    sleep 3
    
    if pgrep -x "ollama" > /dev/null; then
        print_success "Ollama service started"
    else
        print_error "Failed to start Ollama service"
        print_warning "Please start it manually with: ollama serve"
    fi
fi

echo ""

# Step 3: Download required models
echo "Step 3: Downloading required models..."
echo "This may take some time depending on your internet connection..."
echo ""

# Download Mistral model for Turkish understanding
MODEL_MISTRAL="mistral:7b-instruct-q4_K_M"
echo "Downloading Mistral model for Turkish language understanding..."
echo "Model: $MODEL_MISTRAL (~4GB)"

if ollama list | grep -q "$MODEL_MISTRAL"; then
    print_success "Mistral model already downloaded"
else
    ollama pull $MODEL_MISTRAL
    if [ $? -eq 0 ]; then
        print_success "Mistral model downloaded successfully"
    else
        print_error "Failed to download Mistral model"
        exit 1
    fi
fi

echo ""

# Download SQLCoder model for SQL generation
MODEL_SQLCODER="sqlcoder"
echo "Downloading SQLCoder model for SQL generation..."
echo "Model: $MODEL_SQLCODER (~6GB)"

if ollama list | grep -q "$MODEL_SQLCODER"; then
    print_success "SQLCoder model already downloaded"
else
    ollama pull $MODEL_SQLCODER
    if [ $? -eq 0 ]; then
        print_success "SQLCoder model downloaded successfully"
    else
        print_error "Failed to download SQLCoder model"
        print_warning "SQLCoder might not be available. Trying alternative..."
        
        # Try alternative SQL model
        ALT_MODEL="codellama:7b-instruct-q4_K_M"
        echo "Trying alternative model: $ALT_MODEL"
        ollama pull $ALT_MODEL
        
        if [ $? -eq 0 ]; then
            print_warning "Using alternative model: $ALT_MODEL"
            print_warning "Update your .env file: SQLCODER_MODEL=$ALT_MODEL"
        else
            print_error "Failed to download alternative model"
        fi
    fi
fi

echo ""

# Step 4: Verify models
echo "Step 4: Verifying installed models..."
ollama list

echo ""

# Step 5: Test LLM integration
echo "Step 5: Testing LLM integration..."
python3 << EOF
import sys
try:
    import ollama
    client = ollama.Client()
    models = client.list()
    print("✓ Python ollama library is working")
    print(f"✓ Found {len(models.get('models', []))} models")
    sys.exit(0)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    print_success "LLM integration test passed"
else
    print_error "LLM integration test failed"
    print_warning "Make sure you have installed Python dependencies:"
    echo "       pip install -r requirements.txt"
fi

echo ""

# Step 6: Create/Update .env file
echo "Step 6: Configuring environment variables..."
ENV_FILE=".env"

if [ -f "$ENV_FILE" ]; then
    print_warning ".env file already exists"
    
    # Check if LLM settings are already configured
    if grep -q "USE_LOCAL_LLM" "$ENV_FILE"; then
        print_success "LLM settings already configured in .env"
    else
        print_warning "Adding LLM settings to .env..."
        cat >> "$ENV_FILE" << EOL

# LLM Configuration (added by setup script)
USE_LOCAL_LLM=true
OLLAMA_HOST=http://localhost:11434
MISTRAL_MODEL=$MODEL_MISTRAL
SQLCODER_MODEL=$MODEL_SQLCODER
LLM_TIMEOUT=30
MAX_CONTEXT_SIZE=8192
LLM_TEMPERATURE=0.1
LLM_TOP_P=0.95

# ChromaDB Configuration
CHROMA_PERSIST_PATH=./chroma_db
CHROMA_COLLECTION_PREFIX=sqlai_

# Learning Service
ENABLE_LEARNING=true
EOL
        print_success "LLM settings added to .env"
    fi
else
    print_warning "Creating .env file with LLM settings..."
    cat > "$ENV_FILE" << EOL
# SQLAI Environment Configuration

# Application Settings
APP_NAME=SQLAI
APP_VERSION=1.0.0
DEBUG=True
LOG_LEVEL=INFO

# API Settings
API_HOST=localhost
API_PORT=8000
API_PREFIX=/api

# Database Cache (SQLite)
CACHE_DATABASE_URL=sqlite:///./cache.db

# Security
SECRET_KEY=your-secret-key-here-change-in-production
SQLAI_MASTER_KEY=sqlai-fixed-master-key-2024-v1
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# LLM Configuration
USE_LOCAL_LLM=true
OLLAMA_HOST=http://localhost:11434
MISTRAL_MODEL=$MODEL_MISTRAL
SQLCODER_MODEL=$MODEL_SQLCODER
LLM_TIMEOUT=30
MAX_CONTEXT_SIZE=8192
LLM_TEMPERATURE=0.1
LLM_TOP_P=0.95

# ChromaDB Configuration
CHROMA_PERSIST_PATH=./chroma_db
CHROMA_COLLECTION_PREFIX=sqlai_

# Learning Service
ENABLE_LEARNING=true

# Connection Pool Settings
POOL_SIZE=5
MAX_OVERFLOW=10
POOL_TIMEOUT=30

# Performance Settings
CHUNK_SIZE=10000
MAX_RESULT_SIZE=100000
EOL
    print_success ".env file created with LLM settings"
fi

echo ""

# Step 7: Final verification
echo "Step 7: Final verification..."
echo ""
echo "Checking system requirements:"

# Check disk space
DISK_USAGE=$(df -h . | awk 'NR==2 {print $4}')
echo "  Available disk space: $DISK_USAGE"

# Check memory
if [[ "$OS" == "macos" ]]; then
    MEMORY=$(sysctl -n hw.memsize | awk '{print $1/1024/1024/1024 "GB"}')
else
    MEMORY=$(free -h | awk 'NR==2 {print $2}')
fi
echo "  Total memory: $MEMORY"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "  Python version: $PYTHON_VERSION"

echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Make sure Ollama service is running:"
echo "   ollama serve"
echo ""
echo "2. Install Python dependencies:"
echo "   pip install -r requirements.txt"
echo ""
echo "3. Start the backend server:"
echo "   uvicorn app.main:app --reload --port 8000"
echo ""
echo "4. Test the LLM integration:"
echo "   python -c \"from app.services.llm_service import LocalLLMService; llm = LocalLLMService(); print('LLM Ready:', llm.test_connection())\""
echo ""
print_success "SQLAI Local LLM setup completed successfully!"