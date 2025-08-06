# SQLAI - Intelligent PostgreSQL Database Analysis Assistant

An intelligent database assistant that can analyze 20 PostgreSQL databases with ~1000 tables simultaneously, convert natural language queries to SQL using local AI, and provide real-time schema visualization.

## Features

- 🔗 **Multi-Database Support**: Connect and manage up to 20 PostgreSQL databases simultaneously
- 🤖 **Natural Language to SQL**: Convert natural language queries to SQL using local AI models
- 🇹🇷 **Turkish Language Support**: Full support for Turkish table/column names and queries
- 📊 **Schema Visualization**: Interactive graph visualization of database relationships
- ⚡ **Real-time Analysis**: Fast schema analysis with incremental updates
- 🔒 **Secure**: AES-256 encryption for credentials, SQL injection prevention
- 📈 **Analytics**: Query performance tracking and usage analytics

## Tech Stack

- **Backend**: Python 3.8+, FastAPI, SQLAlchemy, psycopg2
- **Frontend**: React 18+, TypeScript, Ant Design, Vite
- **AI**: sentence-transformers, NetworkX for graph analysis
- **Database**: PostgreSQL (source), SQLite (cache)

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL database for testing

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The application will be available at http://localhost:3000

## Test Database

For testing, you can use the following PostgreSQL connection:
- Host: 172.17.12.76
- User: myuser
- Password: myuser01
- Database: postgres

## Development Status

Currently in Phase 1 of development (Foundation & Infrastructure). See `DEVELOPMENT_PHASES.md` for detailed roadmap.

## Documentation

- `SQLAI_PROJECT_SPEC.md` - Complete project specifications
- `DEVELOPMENT_PHASES.md` - 5-phase development plan
- `TEST_STRATEGY.md` - Testing approach and scenarios
- `KRITIK_NOKTALAR.md` - Critical implementation points

## License

Private project for personal use.