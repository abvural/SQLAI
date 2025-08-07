# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend Development
```bash
# Start development server
cd backend && uvicorn app.main:app --reload --port 8000

# Install dependencies
cd backend && pip install -r requirements.txt

# Run individual test files
cd backend && python test_final_simple.py
cd backend && python test_phase1_complete.py
cd backend && python test_phase3_ai_engine.py
cd backend && python test_phase4_query_processing.py

# Run all tests with pytest (if configured)
cd backend && pytest

# Code quality checks
cd backend && black . && flake8 . && isort .
```

### Frontend Development
```bash
# Start development server
cd frontend && npm run dev

# Build for production
cd frontend && npm run build

# Install dependencies
cd frontend && npm install

# Run linting
cd frontend && npm run lint

# Format code
cd frontend && npm run format
```

### Database Testing
```bash
# Test PostgreSQL connection
python3 -c "import psycopg2; conn = psycopg2.connect(host='172.17.12.76', user='myuser', password='myuser01', database='postgres'); print('Connected'); conn.close()"
```

### LLM Setup (Ollama)
```bash
# Install Ollama on macOS
brew install ollama

# Start Ollama service
ollama serve

# Download required models
ollama pull mistral:7b-instruct-q4_K_M  # Turkish understanding (~4GB)
ollama pull sqlcoder                     # SQL generation (~6GB)

# Verify models are installed
ollama list

# Test LLM integration
cd backend && python -c "from app.services.llm_service import LocalLLMService; llm = LocalLLMService(); print('LLM Ready:', llm.test_connection())"
```

## High-Level Architecture

### Project Overview
SQLAI is an intelligent PostgreSQL database analysis and query assistant that can:
- Analyze 20 PostgreSQL databases with ~1000 tables simultaneously
- Convert natural language queries to SQL using local AI
- Support Turkish language for table/column names and queries
- Provide real-time schema visualization and relationship mapping

### Technology Stack
- **Backend**: Python 3.8+ with FastAPI framework, SQLAlchemy ORM, psycopg2 for PostgreSQL
- **Frontend**: React 18+ with TypeScript, Ant Design UI, Vite build tool
- **Databases**: SQLite for local cache/metadata, PostgreSQL as data sources
- **AI Engine**: Hybrid approach using rule-based patterns, sentence-transformers for NLP, NetworkX for graph analysis

### AI Model Architecture (Enhanced with Local LLM)
1. **Local LLM Integration**: 
   - **Mistral 7B** (Turkish Understanding): Natural language comprehension with native Turkish support
   - **SQLCoder** (SQL Generation): Specialized model for accurate SQL query generation
   - **Ollama Runtime**: Local model hosting with Metal acceleration on M3 Mac
   
2. **Vector Database (ChromaDB)**:
   - Schema embeddings for context-aware retrieval
   - Query pattern learning and similarity matching
   - Persistent storage of successful query patterns
   
3. **Hybrid Processing Pipeline**:
   - Primary: LLM-based generation (when USE_LOCAL_LLM=true)
   - Fallback: Pattern-based system with spaCy and TF-IDF
   - Schema Context: Dynamic context retrieval based on query relevance
   
4. **Continuous Learning**:
   - Schema Learner Service tracks successful queries
   - Turkish term mapping improvements over time
   - Relationship discovery from query patterns

### Critical Implementation Points

#### Security & Connection Management
- **Connection Pooling**: Efficient handling of 20 simultaneous database connections using SQLAlchemy pooling
- **Credential Encryption**: AES-256 encryption for database credentials stored locally
- **SQL Injection Prevention**: Parametrized queries and input validation for all user inputs

#### Performance Optimization
- **Stream Processing**: Chunk-based processing for large datasets to prevent memory issues
- **Incremental Analysis**: Only re-analyze changed schema elements instead of full scans
- **Async Processing**: Background job queue for long-running queries with cancellation support

#### Turkish Language Support
- Special handling for Turkish characters (ğ, ü, ş, ı, ç, ö)
- Turkish keyword mapping ("en çok" → MAX, "toplam" → SUM)
- Text normalization for table/column names

## Development Phases

### Current Status
- **Active Phase**: Multi-phase development in progress
- **Backend Status**: Core infrastructure, API routes, AI engine, and services implemented
- **Frontend Status**: React app with routing, pages, and API integration complete
- **Test Coverage**: Phase 1-4 testing files available with real database integration

### Phase Structure (Total: ~21 days)
1. **Phase 1**: Foundation & Infrastructure (3-4 days) - Project setup, security, connections
2. **Phase 2**: Database Integration & Schema Analysis (3-4 days) - Introspection, caching, patterns
3. **Phase 3**: AI Engine Development (4-5 days) - NLP, query generation, confidence scoring
4. **Phase 4**: Query Processing & User Interface (4-5 days) - Async processing, web UI, exports
5. **Phase 5**: Testing & Production Ready (3-4 days) - Comprehensive testing, monitoring

## Test Database Configuration
```
Host: 172.17.12.76
User: myuser
Password: myuser01
Database: postgres
PostgreSQL Version: 14.18
```

### Test Database Evolution Strategy
- **Phase 1**: 2 simple tables for connection testing
- **Phase 2**: 10-15 tables with relationships and Turkish names
- **Phase 3**: Add sample data (1K+ rows) for NLP testing
- **Phase 4**: Generate large datasets (10K+ rows) for performance
- **Phase 5**: 50+ tables for production simulation

## API Endpoint Structure

### Database Management
- `POST /api/databases/connect` - Test database connection
- `GET /api/databases/list` - List registered databases
- `POST /api/databases/analyze` - Start schema analysis
- `GET /api/databases/{db_id}/status` - Analysis status

### AI Query Interface
- `POST /api/query/natural` - Natural language query
- `POST /api/query/execute` - Execute SQL with async support
- `PUT /api/query/cancel/{query_id}` - Cancel running query
- `GET /api/query/progress/{query_id}` - Query execution progress
- `POST /api/query/export` - Export results (CSV, Excel, JSON)

## Performance Targets
- 20 simultaneous database connections
- 1000+ table analysis in <60 seconds
- 90%+ SQL generation accuracy (95%+ with LLM)
- <1 second query response time (2-3 seconds with LLM)
- Memory-efficient processing for large datasets

## LLM Configuration

### Environment Variables (.env)
```env
# Enable Local LLM
USE_LOCAL_LLM=true

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
MISTRAL_MODEL=mistral:7b-instruct-q4_K_M
SQLCODER_MODEL=sqlcoder
LLM_TIMEOUT=30
MAX_CONTEXT_SIZE=8192
LLM_TEMPERATURE=0.1
LLM_TOP_P=0.95

# ChromaDB Configuration
CHROMA_PERSIST_PATH=./chroma_db
CHROMA_COLLECTION_PREFIX=sqlai_

# Learning Service
ENABLE_LEARNING=true
```

### Model Requirements
- **Disk Space**: ~10GB for both models
- **RAM**: 8GB minimum (16GB recommended)
- **CPU**: M1/M2/M3 Mac or modern Intel/AMD processor
- **GPU**: Optional but improves performance (Metal acceleration on Mac)

## Key Files and Locations

### Backend Structure
- **Entry point**: `backend/app/main.py` - FastAPI app with middleware, routers, and lifecycle management
- **Configuration**: `backend/app/config.py` - Pydantic settings with environment variables
- **AI engine**: `backend/app/ai/` - NLP processor, query builder, and templates
- **Services**: `backend/app/services/` - Connection pool, schema analyzer, query executor, cache service
  - `llm_service.py` - Local LLM integration with Mistral and SQLCoder
  - `schema_context_service.py` - ChromaDB vector database for schema embeddings
  - `schema_learner_service.py` - Continuous learning from query patterns
- **API routes**: `backend/app/routers/` - Database, schema, query, analytics, health endpoints
- **Database models**: `backend/app/models/` - SQLAlchemy models for caching and metadata
- **Utilities**: `backend/app/utils/` - Error handlers, security, logging, SQL validation

### Frontend Structure  
- **Entry point**: `frontend/src/App.tsx` - React router with layout and navigation
- **Pages**: `frontend/src/pages/` - DatabasesPage, QueryPage, SchemaPage, AnalyticsPage
- **Services**: `frontend/src/services/api.ts` - API client with axios
- **Components**: `frontend/src/components/` - Reusable UI components
- **Types**: `frontend/src/types/` - TypeScript interfaces

### Testing and Documentation
- **Phase tests**: `backend/test_phase*.py` - Integration tests for each development phase
- **Component tests**: `backend/test_*.py` - Individual service and component tests
- **Planning docs**: `DEVELOPMENT_PHASES.md`, `KRITIK_NOKTALAR.md`, `TEST_STRATEGY.md`

## Architecture Patterns

### Backend Patterns
- **Dependency Injection**: Services are injected through FastAPI's dependency system
- **Repository Pattern**: Database operations abstracted through service layer
- **Connection Pooling**: SQLAlchemy engine pool manages database connections efficiently  
- **Async Processing**: FastAPI async/await for concurrent database operations
- **Middleware Pipeline**: Request ID, logging, CORS, compression, and security middleware
- **Error Handling**: Centralized exception handlers with structured logging

### Frontend Patterns  
- **Component Composition**: Ant Design components with custom wrappers
- **API State Management**: React Query (TanStack Query) for server state caching
- **Client-Side Routing**: React Router with protected routes and navigation guards
- **TypeScript Integration**: Strict typing for API responses and component props

### AI Engine Architecture
- **Hybrid AI Approach**: Rule-based + ML-based query generation for reliability
- **Graph Analysis**: NetworkX for relationship discovery and join path optimization
- **Multilingual NLP**: sentence-transformers with Turkish language support
- **Query Templates**: Reusable SQL patterns for common operations

### Security & Data Flow
- **Credential Encryption**: AES-256 for database credentials in local storage
- **SQL Injection Prevention**: Parametrized queries and input validation
- **Request/Response Logging**: Structured logging with correlation IDs
- **Connection Health**: Periodic health checks for database connections