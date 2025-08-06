# SQLAI - Test Strategy ve Database Requirements

## 🎯 Testing Overview

### Test Philosophy
- **Progressive Testing**: Her fase sonunda functionality + performance
- **Real-world Simulation**: Gerçek use case'lere yakın test scenarios
- **Turkish Context**: Türkçe tablo/kolon isimleri ile testing
- **Performance Benchmarks**: 1000+ tablo, 20 DB simulation

---

## 📊 Test Database Evolution

### 🔧 Phase 1 Test DB (Day 4)
**Amaç**: Connection & Security Testing

```sql
-- Minimal test structure
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200),
    price DECIMAL(10,2),
    category_id INTEGER
);

-- Test scenarios:
-- ✓ Basic connection test
-- ✓ Credential encryption test
-- ✓ SQL injection prevention test
```

### 🔧 Phase 2 Test DB (Day 8)
**Amaç**: Schema Analysis & Relationship Testing

```sql
-- Extended structure with relationships
CREATE TABLE kategoriler (
    id SERIAL PRIMARY KEY,
    ad VARCHAR(100),
    aciklama TEXT
);

CREATE TABLE tedarikci (
    id SERIAL PRIMARY KEY,
    firma_adi VARCHAR(200),
    iletisim_kisi VARCHAR(100),
    telefon VARCHAR(20)
);

CREATE TABLE urunler (
    id SERIAL PRIMARY KEY,
    ad VARCHAR(200),
    fiyat DECIMAL(10,2),
    kategori_id INTEGER REFERENCES kategoriler(id),
    tedarikci_id INTEGER REFERENCES tedarikci(id),
    stok_miktari INTEGER,
    olusturma_tarihi TIMESTAMP DEFAULT NOW()
);

CREATE TABLE musteriler (
    id SERIAL PRIMARY KEY,
    ad VARCHAR(100),
    soyad VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    telefon VARCHAR(20),
    adres TEXT,
    kayit_tarihi DATE DEFAULT CURRENT_DATE
);

CREATE TABLE siparisler (
    id SERIAL PRIMARY KEY,
    musteri_id INTEGER REFERENCES musteriler(id),
    siparis_tarihi DATE DEFAULT CURRENT_DATE,
    toplam_tutar DECIMAL(10,2),
    durum VARCHAR(50) DEFAULT 'Beklemede'
);

CREATE TABLE siparis_detaylari (
    id SERIAL PRIMARY KEY,
    siparis_id INTEGER REFERENCES siparisler(id),
    urun_id INTEGER REFERENCES urunler(id),
    miktar INTEGER,
    birim_fiyat DECIMAL(10,2)
);

-- Test scenarios:
-- ✓ Turkish naming convention detection
-- ✓ Foreign key relationship mapping  
-- ✓ Complex relationship graph analysis
-- ✓ Schema pattern recognition
```

### 🔧 Phase 3 Test DB (Day 13)
**Amaç**: AI Engine & NLP Testing

```sql
-- Sample data for meaningful NLP testing
INSERT INTO kategoriler (ad, aciklama) VALUES 
('Elektronik', 'Elektronik ürünler'),
('Giyim', 'Giyim ve aksesuar'),
('Ev Eşyası', 'Ev için gerekli eşyalar');

INSERT INTO tedarikci (firma_adi, iletisim_kisi, telefon) VALUES
('Tech Solutions', 'Ahmet Yılmaz', '0532-123-4567'),
('Fashion World', 'Ayşe Demir', '0533-987-6543'),
('Home Comfort', 'Mehmet Kaya', '0534-456-7890');

INSERT INTO musteriler (ad, soyad, email, telefon, adres) VALUES
('Ali', 'Özkan', 'ali.ozkan@email.com', '0532-111-2222', 'İstanbul'),
('Fatma', 'Çelik', 'fatma.celik@email.com', '0533-333-4444', 'Ankara'),
('Osman', 'Acar', 'osman.acar@email.com', '0534-555-6666', 'İzmir');

-- More sample data for comprehensive testing...

-- Test queries for AI:
-- "En çok sipariş veren müşteriyi bul"
-- "Hangi kategoride en fazla ürün var?"
-- "Geçen ay satılan toplam tutar nedir?"
-- "Stokta azalan ürünleri listele"
```

### 🔧 Phase 4 Test DB (Day 18)
**Amaç**: Performance & Large Dataset Testing

```sql
-- Generate large datasets for performance testing
-- Using PostgreSQL generate_series for bulk data

-- Large customer dataset
INSERT INTO musteriler (ad, soyad, email, telefon, adres)
SELECT 
    'Müşteri' || generate_series,
    'Soyad' || generate_series,
    'musteri' || generate_series || '@test.com',
    '0532' || LPAD(generate_series::text, 7, '0'),
    'Adres ' || generate_series
FROM generate_series(1, 10000);

-- Large product dataset  
INSERT INTO urunler (ad, fiyat, kategori_id, tedarikci_id, stok_miktari)
SELECT 
    'Ürün ' || generate_series,
    (random() * 1000 + 10)::DECIMAL(10,2),
    (random() * 3 + 1)::INTEGER,
    (random() * 3 + 1)::INTEGER,
    (random() * 100)::INTEGER
FROM generate_series(1, 50000);

-- Large order dataset
-- ... (10K+ orders with order details)

-- Test scenarios:
-- ✓ Large dataset query performance
-- ✓ Memory usage during big results
-- ✓ Query cancellation testing
-- ✓ Export functionality with large data
```

### 🔧 Phase 5 Test DB (Day 21)
**Amaç**: Production Simulation & Stress Testing

```sql
-- Create comprehensive test database structure
-- Simulating real-world complexity

-- Additional tables for comprehensive testing:
CREATE TABLE log_table (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(100),
    action VARCHAR(50),
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create 50+ additional tables to simulate large schema
CREATE TABLE test_table_01 (id SERIAL PRIMARY KEY, data TEXT);
CREATE TABLE test_table_02 (id SERIAL PRIMARY KEY, data TEXT);
-- ... up to test_table_50

-- Test scenarios:
-- ✓ 50+ table schema analysis performance
-- ✓ Complex multi-join query generation
-- ✓ Concurrent user simulation
-- ✓ System stability under load
```

---

## 🧪 Test Scenarios by Category

### 🔒 Security Testing

#### Phase 1 Security Tests:
```sql
-- SQL Injection Prevention Tests
-- These should be BLOCKED by the system:

-- Basic injection attempt
"'; DROP TABLE users; --"

-- Union-based injection
"' UNION SELECT password FROM admin_users --"

-- Time-based injection  
"'; SELECT pg_sleep(10); --"

-- Expected: All blocked with proper error messages
```

#### Credential Security Tests:
- Encryption/decryption accuracy
- Keyring integration testing
- Environment variable security

### 🎯 AI Accuracy Testing

#### Natural Language Queries:
```javascript
// Test cases with expected SQL outputs
const testCases = [
  {
    input: "En çok sipariş veren müşteriyi bul",
    expected: "SELECT m.ad, m.soyad, COUNT(s.id) as siparis_sayisi FROM musteriler m JOIN siparisler s ON m.id = s.musteri_id GROUP BY m.id ORDER BY siparis_sayisi DESC LIMIT 1",
    confidence_threshold: 0.8
  },
  {
    input: "Geçen ay satılan toplam tutar",
    expected: "SELECT SUM(toplam_tutar) FROM siparisler WHERE siparis_tarihi >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month')",
    confidence_threshold: 0.7
  },
  {
    input: "Stokta azalan ürünler",
    expected: "SELECT ad, stok_miktari FROM urunler WHERE stok_miktari < 10 ORDER BY stok_miktari ASC",
    confidence_threshold: 0.6
  }
];
```

#### Turkish Language Tests:
- Türkçe keyword mapping accuracy
- Character encoding handling (ğ, ü, ş, ı, ç, ö)
- Collation and sorting tests

### ⚡ Performance Testing

#### Schema Analysis Performance:
```python
# Performance benchmarks
performance_targets = {
    "10_tables": "< 5 seconds",
    "50_tables": "< 15 seconds", 
    "100_tables": "< 30 seconds",
    "1000_tables": "< 60 seconds"
}

# Memory usage limits
memory_targets = {
    "small_schema": "< 100MB",
    "medium_schema": "< 250MB",
    "large_schema": "< 500MB"
}
```

#### Query Performance:
```sql
-- Large dataset query tests
-- Target: Results in < 5 seconds

-- Join performance test (10K+ rows)
SELECT m.ad, COUNT(s.id) as siparis_count
FROM musteriler m 
LEFT JOIN siparisler s ON m.id = s.musteri_id 
GROUP BY m.id 
ORDER BY siparis_count DESC 
LIMIT 100;

-- Complex aggregation test
SELECT 
    k.ad as kategori,
    COUNT(u.id) as urun_sayisi,
    AVG(u.fiyat) as ortalama_fiyat,
    SUM(sd.miktar * sd.birim_fiyat) as toplam_satis
FROM kategoriler k
JOIN urunler u ON k.id = u.kategori_id
JOIN siparis_detaylari sd ON u.id = sd.urun_id
GROUP BY k.id, k.ad
ORDER BY toplam_satis DESC;
```

---

## 📋 Test Database Timeline

### 📅 Database Setup Schedule

#### Day 3 (Phase 1 Prep):
- **Request**: Basic PostgreSQL connection info
- **Setup**: Minimal 2-table structure
- **Purpose**: Connection & security testing

#### Day 7 (Phase 2 Prep):
- **Action**: Expand to 10-table structure  
- **Add**: Turkish naming, relationships
- **Purpose**: Schema analysis testing

#### Day 12 (Phase 3 Prep):
- **Action**: Add sample data (1K+ rows)
- **Add**: Meaningful business data
- **Purpose**: AI/NLP accuracy testing

#### Day 17 (Phase 4 Prep):
- **Action**: Generate large datasets (10K+ rows)
- **Add**: Performance test data
- **Purpose**: UI & export testing

#### Day 20 (Phase 5 Prep):
- **Action**: Create comprehensive test environment
- **Add**: 50+ tables, complex relationships
- **Purpose**: Production simulation

---

## ✅ Testing Success Criteria

### 🎯 Phase Success Metrics

#### Phase 1 Success:
- [ ] Secure connection to test DB
- [ ] Encrypted credential storage  
- [ ] SQL injection prevention
- [ ] Basic health checks pass

#### Phase 2 Success:
- [ ] Schema analysis < 15 seconds (10 tables)
- [ ] 100% FK relationship detection
- [ ] Turkish naming pattern recognition
- [ ] Accurate semantic categorization

#### Phase 3 Success:
- [ ] 85%+ AI query accuracy on test cases
- [ ] Turkish language processing works
- [ ] Confidence scoring calibrated
- [ ] Complex join path discovery

#### Phase 4 Success:
- [ ] Large dataset queries < 5 seconds
- [ ] Export functionality (CSV, Excel, JSON)
- [ ] Query cancellation works
- [ ] UI responsive with large results

#### Phase 5 Success:
- [ ] 50+ table analysis < 60 seconds
- [ ] System stable under concurrent load
- [ ] Full error recovery testing
- [ ] Production-ready performance

---

## 🚀 Test Automation

### Automated Test Suite:
```python
# Test categories to be automated
test_categories = [
    "connection_security",
    "schema_analysis_performance", 
    "ai_query_accuracy",
    "large_dataset_handling",
    "error_recovery",
    "concurrent_access"
]

# Continuous testing during development
# Run after each significant change
```

---

**Next Step**: PostgreSQL test database connection bilgilerini paylaş, Phase 1 testing için hazırlık yapacağım! 🚀

**Test DB İhtiyacı**: Boş PostgreSQL database, create/drop table yetkisi olan user hesabı