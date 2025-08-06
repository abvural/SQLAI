# SQLAI - Akıllı PostgreSQL Veritabanı Analiz ve Sorgu Asistanı

## 🎯 Proje Özeti

Kişisel kullanım için geliştirilmiş, 20 PostgreSQL veritabanı ve ~1000 tabloyu analiz eden akıllı veritabanı asistanı. Doğal dil ile sorgu yapma, ilişkileri anlama ve akıllı SQL önerileri sunan yerel AI sistemi.

## 🏗️ Sistem Mimarisi

### Teknoloji Stack
- **Backend**: Python 3.8+ + FastAPI + SQLAlchemy + psycopg2
- **Frontend**: React 18+ + TypeScript + Ant Design + Axios
- **Database**: SQLite (cache/analiz) + PostgreSQL (kaynak veriler)
- **AI Engine**: Hibrit model (Rule-based + sentence-transformers + NetworkX)

### Port Yapılandırması
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **PostgreSQL Servers**: Kullanıcı tanımlı (runtime config)

## 🧠 AI Model Mimarisi

### 3 Katmanlı Hibrit Yaklaşım

#### 1. Schema Intelligence Engine (Rule-based)
```python
# Özellikler:
- Tablo/kolon isimlerinden semantic pattern çıkarma
- Foreign key ilişkilerini graf yapısında modelleme
- Veri tiplerinden context anlama
- Naming convention detection (user_id → User entity)
```

#### 2. Natural Language Processor (sentence-transformers)
```python
# Özellikler:
- Kullanıcı promptlarını SQL intent'lere çevirme
- Semantic similarity ile tablo/kolon matching
- Query template library ile pattern matching
- **Turkish Language Support**: Türkçe tablo/kolon isimleri için özel handling
- **Confidence Scoring**: AI accuracy measurement ve user feedback loop
- **Ambiguous Prompt Handling**: Belirsiz promptlar için clarification
```

#### 3. Query Builder (Graph-based NetworkX)
```python
# Özellikler:
- Otomatik join path bulma
- Akıllı WHERE koşulu önerme
- Performance optimization suggestions
- Query complexity analysis
```

## 📁 Proje Yapısı

```
SQLAI/
├── backend/
│   ├── app/
│   │   ├── models/          # SQLAlchemy models (cache DB)
│   │   ├── routers/         # FastAPI route handlers
│   │   ├── services/        # Business logic
│   │   ├── ai/              # AI engine components
│   │   │   ├── schema_analyzer.py
│   │   │   ├── nlp_processor.py
│   │   │   ├── query_builder.py
│   │   │   └── knowledge_base.py
│   │   ├── utils/           # Helper functions
│   │   └── main.py          # FastAPI app
│   ├── tests/
│   ├── requirements.txt
│   └── config.py
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── services/        # API calls
│   │   ├── types/           # TypeScript types
│   │   ├── hooks/           # Custom hooks
│   │   └── App.tsx
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
├── docs/
├── config/
│   └── database_connections.json
├── SQLAI_PROJECT_SPEC.md    # Bu dosya
├── README.md
└── requirements.txt
```

## 🔗 API Endpoints

### Database Management
- `POST /api/databases/connect` - Veritabanı bağlantısı test
- `GET /api/databases/list` - Kayıtlı veritabanları listele
- `POST /api/databases/analyze` - Şema analizi başlat
- `GET /api/databases/{db_id}/status` - Analiz durumu

### Schema Operations
- `GET /api/schema/{db_id}/tables` - Tablo listesi
- `GET /api/schema/{db_id}/relationships` - İlişki grafı
- `GET /api/schema/{db_id}/table/{table_name}` - Tablo detayları

### AI Query Interface
- `POST /api/query/natural` - Doğal dil sorgusu
- `POST /api/query/suggest` - SQL önerisi
- `POST /api/query/execute` - SQL çalıştırma (async support)
- `PUT /api/query/cancel/{query_id}` - Query cancellation
- `GET /api/query/progress/{query_id}` - Query execution progress
- `GET /api/query/history` - Sorgu geçmişi
- `POST /api/query/export` - Result export (CSV, Excel, JSON)

### Analytics & Monitoring
- `GET /api/analytics/database-insights` - Veritabanı özetleri
- `GET /api/analytics/table-usage` - Tablo kullanım istatistikleri
- `GET /api/monitoring/system-health` - System health metrics
- `GET /api/monitoring/query-performance` - Query performance analytics
- `GET /api/monitoring/connection-status` - Connection pool status

## 🚀 Kurulum ve Çalıştırma

### Sistem Gereksinimleri
- **Python**: 3.8+
- **Node.js**: 16+
- **RAM**: 4GB minimum, 8GB önerilen
- **Disk**: 2GB boş alan

### Backend Kurulumu
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\\Scripts\\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend Kurulumu
```bash
cd frontend
npm install
npm start
```

### İlk Kurulum Aksiyonları

#### 1. Dependency Installation
```bash
# Backend dependencies
pip install fastapi uvicorn sqlalchemy psycopg2-binary
pip install sentence-transformers networkx pandas numpy
pip install python-multipart aiofiles

# Frontend dependencies
npm install antd @ant-design/icons axios
npm install @types/react @types/node typescript
```

#### 2. AI Model İndirme
```python
# İlk çalıştırmada otomatik indirilecek
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
# ~500MB, sadece bir kez indirilir
```

#### 3. SQLite Cache Database Oluşturma
```python
# Otomatik oluşturulacak tablolar:
- databases (bağlantı bilgileri)
- tables_cache (tablo metadata)
- relationships_cache (FK ilişkileri)
- query_history (sorgu geçmişi)
- ai_insights (analiz sonuçları)
```

## 💡 Özellikler ve Yetenekler

### Schema Analizi
- ✅ Otomatik tablo/kolon pattern tanıma
- ✅ Foreign key ilişkilerini graf görselleştirme
- ✅ Veri tipi bazlı semantic anlama
- ✅ Naming convention detection
- ✅ Orphaned table detection

### Doğal Dil İşleme
- ✅ Türkçe/İngilizce prompt desteği
- ✅ "En çok satış yapan müşteriyi bul" → SQL
- ✅ Belirsiz promptlar için clarification isteme
- ✅ Complex join'ler için otomatik path bulma

### Akıllı SQL Önerileri
- ✅ Performance optimization önerileri
- ✅ Index usage recommendations
- ✅ Query complexity warnings
- ✅ Alternative query patterns

### Kullanıcı Arayüzü
- ✅ Modern, responsive web arayüzü
- ✅ Schema explorer (tree view)
- ✅ Interactive query builder
- ✅ Result set visualization
- ✅ Query history ve favorites

## 🔒 Güvenlik ve Bağlantı Yönetimi

### Güvenlik Özellikleri
- **Local-First**: Tüm AI işlemleri local
- **Secure Connections**: PostgreSQL SSL desteği
- **Credential Management**: AES-256 encrypted local storage
- **No Data Sharing**: Veriler hiçbir yerde paylaşılmaz
- **Audit Trail**: Query history ve access logs
- **SQL Injection Prevention**: Parametrized queries ve validation

### Connection Pool Management
- **Multi-DB Support**: 20 veritabanı için efficient pooling
- **Connection Timeout**: Configurable timeout ve retry logic
- **Health Checks**: Automatic connection health monitoring
- **Failover Support**: Graceful degradation on connection failures
- **Resource Management**: Memory ve connection leak prevention

## 📊 Performance Özellikleri ve Optimizasyonlar

### İlk Analiz (1000 tablo)
- **Süre**: 30-60 saniye (incremental updates ile daha hızlı)
- **Memory**: ~500MB (stream processing ile optimized)
- **Cache Size**: ~100-500MB
- **Pagination**: Large datasets için smart chunking

### Runtime Performance
- **Query Response**: <1 saniye
- **NLP Processing**: <500ms  
- **Schema Lookup**: <100ms (cache optimized)
- **Graph Analysis**: <200ms
- **Background Jobs**: Long-running queries için async processing

### Memory Management
- **Stream Processing**: Large resultsets için memory-efficient processing
- **Incremental Analysis**: Sadece değişen tabloları re-analyze
- **Cache Optimization**: LRU cache ve smart invalidation
- **Connection Pooling**: Resource leak prevention

## 🔧 Yapılandırma

### Database Connections (config/database_connections.json)
```json
{
  "databases": [
    {
      "id": "db1",
      "name": "Production DB",
      "host": "localhost",
      "port": 5432,
      "database": "prod_db",
      "username": "user",
      "password": "encrypted_password",
      "ssl_mode": "require"
    }
  ]
}
```

### AI Model Settings
```python
AI_CONFIG = {
    "sentence_transformer_model": "paraphrase-multilingual-MiniLM-L12-v2",
    "similarity_threshold": 0.7,
    "max_query_complexity": 10,
    "cache_ttl": 3600,  # 1 hour
    "auto_analyze_interval": 86400  # 24 hours
}
```

## 🚦 Development Roadmap - Revize Edilmiş Plan

### Phase 1: Core Infrastructure (Week 1)
- [ ] Backend Setup: FastAPI + SQLAlchemy + psycopg2
- [ ] Frontend Setup: React + TypeScript + Ant Design
- [ ] **Connection Pool Manager**: Efficient 20-DB connection handling
- [ ] SQLite Cache System: Schema metadata ve query history
- [ ] **Basic Security**: Connection encryption, credential management

### Phase 2: AI Engine Foundation (Week 2)
- [ ] **Schema Intelligence**: Rule-based pattern recognition
- [ ] **NLP Processor**: sentence-transformers integration
- [ ] **Graph Builder**: NetworkX ile relationship mapping
- [ ] **Query Builder**: Template-based SQL generation
- [ ] **Confidence Scoring**: AI accuracy measurement system

### Phase 3: Advanced Query Processing (Week 3)
- [ ] **Async Query Engine**: Background processing, cancellation
- [ ] **Memory Management**: Stream processing for large datasets
- [ ] **Query Optimization**: EXPLAIN plan analysis
- [ ] **Error Handling**: User-friendly error messages ve recovery

### Phase 4: User Experience (Week 4)
- [ ] **Web Interface**: Modern, responsive UI
- [ ] **Schema Visualization**: Interactive graph layouts
- [ ] **Export System**: CSV, Excel, JSON formats
- [ ] **Progress Tracking**: Real-time query execution status

### Phase 5: Production Ready (Week 5)
- [ ] **Monitoring & Logging**: Comprehensive system tracking
- [ ] **Performance Optimization**: Caching, indexing strategies
- [ ] **Documentation**: User guide, API documentation
- [ ] **Testing**: Unit, integration, performance tests

## 🧪 Testing Strategy

### Backend Tests
- Unit tests: AI engine components
- Integration tests: Database connections
- Performance tests: 1000+ table scenarios

### Frontend Tests
- Component tests: React components
- E2E tests: Complete user workflows
- Accessibility tests: WCAG compliance

## 📝 Usage Examples

### Doğal Dil Sorguları
```
"En çok sipariş alan müşteriyi bul"
→ SELECT c.name, COUNT(o.id) as order_count 
   FROM customers c JOIN orders o ON c.id = o.customer_id 
   GROUP BY c.id ORDER BY order_count DESC LIMIT 1;

"Geçen ay satılan ürünleri listele"
→ SELECT p.name, SUM(oi.quantity) as total_sold
   FROM products p JOIN order_items oi ON p.id = oi.product_id
   JOIN orders o ON oi.order_id = o.id 
   WHERE o.created_at >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month')
   GROUP BY p.id;
```

## 🎯 Başarı Kriterleri

### Performance Hedefleri
- ✅ 20 veritabanına eşzamanlı bağlantı (connection pooling ile)
- ✅ 1000+ tablo analizi <60 saniye (incremental analysis ile)
- ✅ %90+ doğrulukta SQL üretimi (confidence scoring ile)
- ✅ <1 saniye query response time
- ✅ Memory-efficient processing (large datasets için)

### Kullanıcı Deneyimi
- ✅ Modern, responsive web arayüzü
- ✅ Real-time query progress tracking
- ✅ Interactive schema visualization
- ✅ Multi-format export (CSV, Excel, JSON)
- ✅ Turkish language support

### Teknik Gereksinimler
- ✅ Local deployment (no internet required)
- ✅ Async query processing with cancellation
- ✅ Comprehensive error handling
- ✅ System monitoring ve logging
- ✅ Güvenli credential management

## 📞 Destek ve Katkı

Bu proje kişisel kullanım için geliştirilmiştir. Özellik istekleri ve bug raporları için GitHub issues kullanılabilir.

---

**Son Güncelleme**: 2025-08-06
**Versiyon**: 1.0.0
**Durum**: Development Phase - Ready to Start Implementation