# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend Development
```bash
# Start development server
cd backend && uvicorn app.main:app --reload --port 8000

# Install dependencies
cd backend && pip install -r requirements.txt

# Run tests
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

### AI Model Architecture (3-Layer Hybrid)
1. **Schema Intelligence Engine**: Rule-based pattern recognition from table/column names, foreign key relationships, data types
2. **Natural Language Processor**: sentence-transformers for converting prompts to SQL intents with Turkish language support
3. **Query Builder**: Graph-based join path discovery and query optimization using NetworkX

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
- **Active Phase**: Phase 1 - Foundation & Infrastructure
- **Progress**: 0/11 tasks completed
- **Next Task**: P1.1 - Create project folder structure

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
- 90%+ SQL generation accuracy
- <1 second query response time
- Memory-efficient processing for large datasets

## Key Files and Locations
- **Backend entry point**: `backend/app/main.py`
- **AI engine components**: `backend/app/ai/` (schema_analyzer, nlp_processor, query_builder)
- **Frontend entry point**: `frontend/src/App.tsx`
- **Database models**: `backend/app/models/`
- **API routes**: `backend/app/routers/`
- **Test specifications**: `TEST_STRATEGY.md`
- **Development phases**: `DEVELOPMENT_PHASES.md`
- **Critical points**: `KRITIK_NOKTALAR.md`