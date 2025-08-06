# SQLAI - AI-Powered PostgreSQL Database Assistant

## 🎯 Project Overview

SQLAI is an intelligent PostgreSQL database analysis and query assistant that converts natural language queries to SQL with Turkish language support. The system can analyze multiple databases simultaneously, provide schema insights, and execute queries with real-time progress tracking.

## ✨ Key Features

### 🤖 AI-Powered Query Generation
- Natural language to SQL conversion
- Turkish and English language support
- 90%+ query accuracy target
- Confidence scoring system
- Ambiguous query handling

### 📊 Multi-Database Support
- Connect to 20+ PostgreSQL databases simultaneously
- Analyze 1000+ tables efficiently
- Real-time schema introspection
- Relationship graph visualization using NetworkX

### ⚡ Advanced Query Processing
- Async query execution with progress tracking
- Memory-efficient streaming for large datasets
- Query cancellation support
- Background job processing

### 📤 Multi-Format Export
- CSV, Excel, JSON, SQL export formats
- Streaming export for large datasets
- Export validation and size limits

### 🔍 Schema Intelligence
- Automatic relationship discovery
- Turkish naming pattern recognition
- Entity type classification
- Schema change detection
- Performance optimization suggestions

### 🛡️ Production-Ready Security
- AES-256 credential encryption
- SQL injection prevention
- Input validation and sanitization
- Circuit breaker patterns
- Error recovery mechanisms

### 📡 Real-Time Communication
- WebSocket support for live progress updates
- System notifications and alerts
- Connection status monitoring

## 🏗️ Architecture

### Backend Stack
- **Framework**: FastAPI (Python 3.8+)
- **Database**: PostgreSQL + SQLAlchemy ORM
- **Cache**: SQLite for metadata caching
- **AI/ML**: Sentence Transformers, NetworkX
- **Processing**: Pandas, NumPy for data processing

### Key Components
- **Database Service**: Connection management and pooling
- **Schema Analyzer**: Intelligent schema analysis
- **Query Executor**: Async query processing
- **AI Engine**: NLP processing and SQL generation
- **Export Service**: Multi-format data export
- **Monitoring Service**: Health checks and metrics
- **Error Recovery**: Circuit breaker and failover

## 📈 Development Progress

### Phase 1: Foundation & Infrastructure ✅
- Project structure and environment setup
- Security framework (AES-256 encryption)
- Connection pool management
- Basic PostgreSQL integration
- Error handling framework

### Phase 2: Database Integration & Schema Analysis ✅
- PostgreSQL schema introspection
- Relationship graph building with NetworkX
- Schema change detection
- Turkish naming pattern recognition
- Semantic analysis and optimization suggestions

### Phase 3: AI Engine Development ✅
- Sentence transformers integration
- Turkish text normalization
- 19 SQL query templates
- Intent recognition and confidence scoring
- Semantic similarity matching

### Phase 4: Query Processing & User Interface ✅
- Async query execution with progress tracking
- Memory management and streaming
- WebSocket real-time communication
- Multi-format export system
- API endpoints (26 total)

### Phase 5: Testing & Production Ready ✅
- Comprehensive integration testing
- Performance optimization
- Security testing and validation
- System monitoring and health checks
- Production deployment preparation

## 🚀 API Endpoints

### Query Processing (7 endpoints)
- `POST /api/query/natural` - Natural language query processing
- `POST /api/query/execute` - Direct SQL execution
- `GET /api/query/status/{query_id}` - Query progress tracking
- `GET /api/query/results/{query_id}` - Paginated results
- `PUT /api/query/cancel/{query_id}` - Query cancellation
- `GET /api/query/export/{query_id}` - Result export
- `GET /api/query/history` - Query history

### Database Management (6 endpoints)
- `GET /api/databases` - List connections
- `POST /api/databases` - Add connection
- `GET /api/databases/{db_id}/test` - Test connection
- `DELETE /api/databases/{db_id}` - Remove connection
- `GET /api/databases/{db_id}/summary` - Database summary
- `GET /api/databases/{db_id}/visualization` - Schema visualization

### Schema Analysis (5 endpoints)
- `GET /api/schema/{db_id}` - Schema information
- `GET /api/schema/{db_id}/visualization` - Graph visualization
- `GET /api/schema/{db_id}/patterns` - Naming patterns
- `GET /api/schema/{db_id}/changes` - Change detection
- `POST /api/schema/{db_id}/analyze` - Trigger analysis

### Dashboard & Monitoring (8 endpoints)
- `GET /api/dashboard/overview` - System overview
- `GET /api/dashboard/health` - System health
- `GET /api/dashboard/analytics` - Usage analytics
- `GET /api/health` - Health check
- WebSocket endpoints for real-time updates

## 💻 Installation & Usage

### Prerequisites
- Python 3.8+ (3.11+ recommended)
- PostgreSQL access
- 4GB+ RAM (8GB+ recommended)

### Quick Start
```bash
# Clone repository
git clone https://github.com/abvural/SQLAI.git
cd SQLAI/backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start server
uvicorn app.main:app --reload --port 8000

# Test health
curl http://localhost:8000/api/health
```

### Natural Language Query Example
```bash
curl -X POST http://localhost:8000/api/query/natural \
  -H "Content-Type: application/json" \
  -d '{
    "query": "En çok sipariş veren müşteriyi bul",
    "database_id": "your-database-id"
  }'
```

### Turkish Language Examples
- "Müşterileri listele" → `SELECT * FROM customers`
- "Toplam sipariş sayısı" → `SELECT COUNT(*) FROM orders`
- "En çok satan ürün" → `SELECT * FROM products ORDER BY sales DESC LIMIT 1`

## 📊 Performance Characteristics

- **Database Connections**: 20+ simultaneous connections
- **Table Analysis**: 1000+ tables in <60 seconds
- **Query Response**: <1 second for simple queries
- **Memory Usage**: <500MB for typical operations
- **Accuracy**: 90%+ SQL generation accuracy target

## 🛡️ Security Features

- **Credential Protection**: AES-256 encryption
- **SQL Injection Prevention**: Parameterized queries
- **Input Validation**: Comprehensive sanitization
- **Access Control**: Role-based permissions ready
- **Audit Logging**: Complete query and access logs

## 📚 Documentation

- **API Documentation**: Complete REST API reference
- **Deployment Guide**: Production setup instructions
- **Development Phases**: Detailed development timeline
- **Test Strategy**: Comprehensive testing approach
- **Critical Notes**: Implementation best practices

## 🔧 Development Status

### Completed ✅
- **Backend API**: 100% complete (50/50 tasks)
- **AI Engine**: Fully functional with Turkish support
- **Database Integration**: Multi-database support
- **Testing**: Comprehensive test coverage
- **Documentation**: Complete API and deployment docs
- **Security**: Production-ready security measures

### Future Enhancements 🚀
- **React Frontend**: Web interface (planned)
- **Dashboard UI**: Visual database management
- **Query Builder**: Drag-and-drop query interface
- **Advanced Analytics**: Query performance insights
- **Machine Learning**: Query optimization suggestions

## 📈 Project Statistics

- **Total Files**: 50+ source files
- **Lines of Code**: 15,000+ lines
- **Test Coverage**: 5 comprehensive test phases
- **API Endpoints**: 26 REST endpoints
- **SQL Templates**: 19 query templates
- **Documentation**: 5 comprehensive guides

## 🤝 Contributing

This project was developed using Claude Code AI assistant with comprehensive planning, implementation, and testing phases.

## 📄 License

[Add your preferred license]

## 📞 Contact

- **Developer**: A. B. Vural
- **Email**: avural@windowslive.com
- **GitHub**: abvural

---

**SQLAI - Making database queries as simple as asking a question in Turkish!**