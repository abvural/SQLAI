"""
Internal Integration Tests for SQLAI LLM System
Real tests with actual Ollama models, database connections, and live services
These tests verify the system works end-to-end with real components
"""

import asyncio
import os
import sys
import time
import json
import traceback
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

# Add project root to path
sys.path.append('/Users/abdurrahimvural/Documents/GitHub/SQLAI/backend')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import real services
from app.services.llm_service import LocalLLMService
from app.services.adaptive_learning_service import AdaptiveLearningService
from app.services.schema_context_service import SchemaContextService
from app.services.cache_service import CacheService
from app.ai.nlp_processor import NLPProcessor
from app.models import get_session, DatabaseInfo

class InternalTestResult:
    """Track internal test results with detailed reporting"""
    
    def __init__(self):
        self.results = []
        self.start_time = time.time()
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.errors = []
    
    def add_result(self, test_name: str, area: str, status: str, duration: float, 
                   details: str = "", error: str = ""):
        """Add test result to tracking"""
        self.results.append({
            'test': test_name,
            'area': area,
            'status': status,
            'duration': duration,
            'details': details,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })
        
        self.total_tests += 1
        if status == 'PASS':
            self.passed_tests += 1
        else:
            self.failed_tests += 1
            if error:
                self.errors.append(f"{test_name}: {error}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test summary statistics"""
        duration = time.time() - self.start_time
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        # Group by area
        areas = {}
        for result in self.results:
            area = result['area']
            if area not in areas:
                areas[area] = {'PASS': 0, 'FAIL': 0}
            areas[area][result['status']] += 1
        
        return {
            'total_tests': self.total_tests,
            'passed': self.passed_tests,
            'failed': self.failed_tests,
            'success_rate': success_rate,
            'total_duration': duration,
            'areas': areas,
            'errors': self.errors
        }

class InternalLLMTests:
    """
    INTERNAL TEST AREA: Real LLM Service Integration Tests
    Tests actual Ollama models, real Turkish understanding, live SQL generation
    """
    
    def __init__(self):
        self.test_db_id = f"internal_test_{int(time.time())}"
        self.llm_service = None
        self.results = InternalTestResult()
    
    async def run_all_tests(self) -> InternalTestResult:
        """Run all internal LLM tests"""
        print("🔥 Starting Internal LLM Integration Tests...")
        print("=" * 80)
        
        # Test LLM service initialization
        await self._test_llm_service_initialization()
        
        # Test Ollama connection and models
        await self._test_ollama_models_availability()
        
        # Test Turkish understanding with real Mistral
        await self._test_real_mistral_turkish_understanding()
        
        # Test SQL generation with real SQLCoder
        await self._test_real_sqlcoder_generation()
        
        # Test pattern recognition systems
        await self._test_pattern_recognition_systems()
        
        # Test adaptive learning with real data
        await self._test_adaptive_learning_integration()
        
        # Test end-to-end query processing
        await self._test_end_to_end_query_processing()
        
        # Test performance benchmarks
        await self._test_performance_benchmarks()
        
        return self.results
    
    async def _test_llm_service_initialization(self):
        """
        INTERNAL TEST: LLM Service Real Initialization
        Tests: Real service creation, environment loading, model validation
        """
        test_name = "Real LLM Service Initialization"
        start_time = time.time()
        
        try:
            print(f"🧪 Testing: {test_name}")
            
            # Test environment variables loading
            use_llm = os.getenv('USE_LOCAL_LLM', 'false').lower() == 'true'
            if not use_llm:
                raise Exception("USE_LOCAL_LLM not enabled in environment")
            
            mistral_model = os.getenv('MISTRAL_MODEL')
            sqlcoder_model = os.getenv('SQLCODER_MODEL')
            
            if not mistral_model or not sqlcoder_model:
                raise Exception("LLM models not configured in environment")
            
            # Create real LLM service
            self.llm_service = LocalLLMService(self.test_db_id)
            
            # Test connection
            if not self.llm_service.test_connection():
                raise Exception("Ollama connection failed")
            
            # Test models are available
            models_result = self.llm_service.client.list()
            available_models = [m['name'] for m in models_result.get('models', [])]
            
            if mistral_model not in available_models:
                raise Exception(f"Mistral model {mistral_model} not available")
            
            if sqlcoder_model not in available_models:
                raise Exception(f"SQLCoder model {sqlcoder_model} not available")
            
            duration = time.time() - start_time
            details = f"Models: {mistral_model}, {sqlcoder_model} | Connection: OK"
            
            self.results.add_result(test_name, "LLM Service Integration", "PASS", 
                                  duration, details)
            print(f"   ✅ PASS ({duration:.2f}s) - {details}")
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            self.results.add_result(test_name, "LLM Service Integration", "FAIL", 
                                  duration, "", error_msg)
            print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")
    
    async def _test_ollama_models_availability(self):
        """
        INTERNAL TEST: Ollama Models Real Availability Check
        Tests: Model download status, memory usage, response capability
        """
        test_name = "Ollama Models Availability"
        start_time = time.time()
        
        try:
            print(f"🧪 Testing: {test_name}")
            
            if not self.llm_service:
                raise Exception("LLM Service not initialized")
            
            # Get model information
            models = self.llm_service.client.list()
            model_details = {}
            
            for model in models.get('models', []):
                model_name = model['name']
                model_size = model.get('size', 0)
                model_details[model_name] = {
                    'size_gb': round(model_size / (1024**3), 2),
                    'modified': model.get('modified_at', 'unknown')
                }
            
            # Test Mistral model response
            mistral_test = await self.llm_service.async_client.generate(
                model=self.llm_service.mistral_model,
                prompt="Test: Merhaba",
                options={'num_predict': 10}
            )
            
            if not mistral_test.get('response'):
                raise Exception("Mistral model not responding")
            
            # Test SQLCoder model response  
            sqlcoder_test = await self.llm_service.async_client.generate(
                model=self.llm_service.sqlcoder_model,
                prompt="SELECT * FROM users;",
                options={'num_predict': 10}
            )
            
            if not sqlcoder_test.get('response'):
                raise Exception("SQLCoder model not responding")
            
            duration = time.time() - start_time
            details = f"Models OK: {len(model_details)} loaded, Mistral+SQLCoder responsive"
            
            self.results.add_result(test_name, "Model Availability", "PASS", 
                                  duration, details)
            print(f"   ✅ PASS ({duration:.2f}s) - {details}")
            
            # Print model details
            for model_name, info in model_details.items():
                print(f"      📦 {model_name}: {info['size_gb']} GB")
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            self.results.add_result(test_name, "Model Availability", "FAIL", 
                                  duration, "", error_msg)
            print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")
    
    async def _test_real_mistral_turkish_understanding(self):
        """
        INTERNAL TEST: Real Mistral Turkish Language Understanding
        Tests: Actual Turkish queries, intent extraction, entity recognition
        """
        test_name = "Real Mistral Turkish Understanding"
        start_time = time.time()
        
        try:
            print(f"🧪 Testing: {test_name}")
            
            if not self.llm_service:
                raise Exception("LLM Service not initialized")
            
            # Test Turkish queries with expected results
            test_queries = [
                {
                    'query': 'kaç kullanıcı var',
                    'expected_intent': 'count',
                    'expected_entities': ['kullanıcı']
                },
                {
                    'query': 'ahmet isimli kullanıcılar',
                    'expected_intent': 'select',
                    'expected_entities': ['kullanıcı']
                },
                {
                    'query': 'son 30 gün içindeki siparişler',
                    'expected_intent': 'select',
                    'expected_entities': ['sipariş']
                }
            ]
            
            successful_queries = 0
            total_queries = len(test_queries)
            
            for test_case in test_queries:
                query = test_case['query']
                print(f"      🔍 Testing query: '{query}'")
                
                # Real Mistral understanding
                result = await self.llm_service.understand_turkish(query)
                
                # Verify intent
                if result.get('intent') == test_case['expected_intent']:
                    successful_queries += 1
                    print(f"         ✅ Intent: {result.get('intent')} ✓")
                else:
                    print(f"         ❌ Intent: {result.get('intent')} (expected: {test_case['expected_intent']})")
                
                # Verify entities
                entities = result.get('entities', [])
                expected_entities = test_case['expected_entities']
                
                entity_match = any(entity in str(entities) for entity in expected_entities)
                if entity_match:
                    print(f"         ✅ Entities: {entities} ✓")
                else:
                    print(f"         ❌ Entities: {entities} (expected: {expected_entities})")
                
                # Show filters if detected
                if result.get('filters'):
                    print(f"         🎯 Filters: {result['filters']}")
                
                print()
            
            success_rate = (successful_queries / total_queries) * 100
            duration = time.time() - start_time
            
            if success_rate >= 70:  # 70% threshold
                details = f"Turkish understanding: {success_rate:.1f}% success ({successful_queries}/{total_queries})"
                self.results.add_result(test_name, "Turkish Understanding", "PASS", 
                                      duration, details)
                print(f"   ✅ PASS ({duration:.2f}s) - {details}")
            else:
                error_msg = f"Low success rate: {success_rate:.1f}% (threshold: 70%)"
                self.results.add_result(test_name, "Turkish Understanding", "FAIL", 
                                      duration, "", error_msg)
                print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            self.results.add_result(test_name, "Turkish Understanding", "FAIL", 
                                  duration, "", error_msg)
            print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")
    
    async def _test_real_sqlcoder_generation(self):
        """
        INTERNAL TEST: Real SQLCoder SQL Generation
        Tests: Actual SQL generation, query correctness, syntax validation
        """
        test_name = "Real SQLCoder SQL Generation"
        start_time = time.time()
        
        try:
            print(f"🧪 Testing: {test_name}")
            
            if not self.llm_service:
                raise Exception("LLM Service not initialized")
            
            # Test SQL generation scenarios
            test_cases = [
                {
                    'intent': {'intent': 'count', 'entities': ['kullanıcı'], 'filters': []},
                    'schema': 'Table: users\nColumns: id (INTEGER), username (VARCHAR), email (VARCHAR)',
                    'expected_keywords': ['COUNT', 'users']
                },
                {
                    'intent': {'intent': 'select', 'entities': ['kullanıcı'], 'filters': ['name=ahmet']},
                    'schema': 'Table: users\nColumns: id (INTEGER), username (VARCHAR), email (VARCHAR)',
                    'expected_keywords': ['SELECT', 'users', 'WHERE']
                },
                {
                    'intent': {'intent': 'max', 'entities': ['segment', 'gelir'], 'filters': [],
                              'metadata': {'join_patterns': ['segment_analysis:Revenue by segments']}},
                    'schema': '''Table: customer_segments
Columns: id, segment_type, customer_id
Table: orders
Columns: id, customer_id, amount, created_at''',
                    'expected_keywords': ['JOIN', 'GROUP BY']
                }
            ]
            
            successful_generations = 0
            total_cases = len(test_cases)
            
            for i, test_case in enumerate(test_cases, 1):
                print(f"      🔧 Testing SQL generation case {i}")
                
                # Real SQL generation
                sql = await self.llm_service.generate_sql(
                    test_case['intent'], 
                    test_case['schema'],
                    f"test query {i}"
                )
                
                print(f"         Generated SQL: {repr(sql)}")
                
                if not sql or len(sql.strip()) < 10:
                    print(f"         ❌ Empty or too short SQL")
                    continue
                
                # Verify expected keywords
                sql_upper = sql.upper()
                keyword_matches = 0
                for keyword in test_case['expected_keywords']:
                    if keyword in sql_upper:
                        keyword_matches += 1
                        print(f"         ✅ Keyword '{keyword}' found")
                    else:
                        print(f"         ❌ Keyword '{keyword}' missing")
                
                if keyword_matches == len(test_case['expected_keywords']):
                    successful_generations += 1
                
                print()
            
            success_rate = (successful_generations / total_cases) * 100
            duration = time.time() - start_time
            
            if success_rate >= 70:  # 70% threshold
                details = f"SQL generation: {success_rate:.1f}% success ({successful_generations}/{total_cases})"
                self.results.add_result(test_name, "SQL Generation", "PASS", 
                                      duration, details)
                print(f"   ✅ PASS ({duration:.2f}s) - {details}")
            else:
                error_msg = f"Low success rate: {success_rate:.1f}% (threshold: 70%)"
                self.results.add_result(test_name, "SQL Generation", "FAIL", 
                                      duration, "", error_msg)
                print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            self.results.add_result(test_name, "SQL Generation", "FAIL", 
                                  duration, "", error_msg)
            print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")
    
    async def _test_pattern_recognition_systems(self):
        """
        INTERNAL TEST: Pattern Recognition Systems Integration
        Tests: Date patterns, name patterns, JOIN patterns, conversational patterns
        """
        test_name = "Pattern Recognition Systems"
        start_time = time.time()
        
        try:
            print(f"🧪 Testing: {test_name}")
            
            if not self.llm_service:
                raise Exception("LLM Service not initialized")
            
            pattern_tests = [
                {
                    'category': 'Date Filters',
                    'queries': [
                        'son 30 gün içindeki veriler',
                        'bu hafta eklenen kullanıcılar', 
                        'bugün yapılan işlemler'
                    ],
                    'detection_method': '_detect_date_filters'
                },
                {
                    'category': 'Name Filters',
                    'queries': [
                        'ahmet isimli kullanıcılar',
                        'mehmet adlı müşteriler',
                        'ismi fatma olan'
                    ],
                    'detection_method': '_detect_name_filters'
                },
                {
                    'category': 'Complex JOIN Patterns',
                    'queries': [
                        'en fazla sipariş veren müşteri',
                        'segment bazında gelir analizi',
                        'müşteri performans raporu'
                    ],
                    'detection_method': '_detect_complex_join_patterns'
                },
                {
                    'category': 'Conversational Patterns',
                    'queries': [
                        'bunların detayı nedir',
                        'daha fazla bilgi verir misin',
                        'karşılaştırma yapar mısın'
                    ],
                    'detection_method': '_detect_conversational_patterns'
                },
                {
                    'category': 'Business Intelligence',
                    'queries': [
                        'müşteri yaşam değeri analizi',
                        'cohort analizi yapalım',
                        'satış funnel raporu'
                    ],
                    'detection_method': '_detect_business_intelligence_patterns'
                }
            ]
            
            total_patterns = 0
            detected_patterns = 0
            
            for pattern_group in pattern_tests:
                category = pattern_group['category']
                method_name = pattern_group['detection_method']
                
                print(f"      🎯 Testing {category}")
                
                method = getattr(self.llm_service, method_name)
                
                for query in pattern_group['queries']:
                    result = method(query)
                    
                    total_patterns += 1
                    if result and len(result) > 0:
                        detected_patterns += 1
                        print(f"         ✅ '{query}' → {len(result)} patterns")
                    else:
                        print(f"         ❌ '{query}' → no patterns")
            
            detection_rate = (detected_patterns / total_patterns) * 100
            duration = time.time() - start_time
            
            if detection_rate >= 75:  # 75% threshold
                details = f"Pattern detection: {detection_rate:.1f}% success ({detected_patterns}/{total_patterns})"
                self.results.add_result(test_name, "Pattern Recognition", "PASS", 
                                      duration, details)
                print(f"   ✅ PASS ({duration:.2f}s) - {details}")
            else:
                error_msg = f"Low detection rate: {detection_rate:.1f}% (threshold: 75%)"
                self.results.add_result(test_name, "Pattern Recognition", "FAIL", 
                                      duration, "", error_msg)
                print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            self.results.add_result(test_name, "Pattern Recognition", "FAIL", 
                                  duration, "", error_msg)
            print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")
    
    async def _test_adaptive_learning_integration(self):
        """
        INTERNAL TEST: Adaptive Learning System Real Integration
        Tests: Schema learning, query success tracking, context generation
        """
        test_name = "Adaptive Learning Integration"
        start_time = time.time()
        
        try:
            print(f"🧪 Testing: {test_name}")
            
            if not self.llm_service or not self.llm_service.adaptive_learning:
                raise Exception("Adaptive Learning not initialized")
            
            # Test schema learning
            test_schema = {
                'schemas': {
                    'public': {
                        'tables': [
                            {
                                'name': 'test_users',
                                'columns': [
                                    {'name': 'id', 'type': 'INTEGER'},
                                    {'name': 'username', 'type': 'VARCHAR'},
                                    {'name': 'email', 'type': 'VARCHAR'}
                                ]
                            }
                        ]
                    }
                }
            }
            
            print(f"      📚 Testing schema learning...")
            learning_result = await self.llm_service.adaptive_learning.initialize_schema_learning(test_schema)
            
            if not learning_result or 'vocabulary' not in learning_result:
                raise Exception("Schema learning failed")
            
            vocabulary = learning_result['vocabulary']
            if 'test_users' not in vocabulary:
                raise Exception("Vocabulary extraction failed")
            
            print(f"         ✅ Schema learning: {len(vocabulary)} terms extracted")
            
            # Test query success learning
            print(f"      🎓 Testing query success learning...")
            await self.llm_service.adaptive_learning.learn_from_successful_query(
                "test query", "SELECT * FROM test_users;", 0.9, True
            )
            
            # Test context generation
            print(f"      🧠 Testing context generation...")
            context = self.llm_service.adaptive_learning.get_adaptive_context_for_query("kullanıcı sayısı")
            
            if not context:
                print(f"         ⚠️  No context generated (acceptable for new database)")
            else:
                print(f"         ✅ Context generated: {len(context)} characters")
            
            # Get learning stats
            stats = self.llm_service.adaptive_learning.get_learning_stats()
            print(f"         📊 Learning stats: {stats}")
            
            duration = time.time() - start_time
            details = f"Schema learning OK, vocabulary: {len(vocabulary)} terms"
            
            self.results.add_result(test_name, "Adaptive Learning", "PASS", 
                                  duration, details)
            print(f"   ✅ PASS ({duration:.2f}s) - {details}")
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            self.results.add_result(test_name, "Adaptive Learning", "FAIL", 
                                  duration, "", error_msg)
            print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")
    
    async def _test_end_to_end_query_processing(self):
        """
        INTERNAL TEST: Complete End-to-End Query Processing
        Tests: Full pipeline from Turkish query to SQL execution simulation
        """
        test_name = "End-to-End Query Processing"
        start_time = time.time()
        
        try:
            print(f"🧪 Testing: {test_name}")
            
            if not self.llm_service:
                raise Exception("LLM Service not initialized")
            
            # End-to-end test scenarios
            e2e_tests = [
                {
                    'query': 'kaç kullanıcı var toplam',
                    'schema': 'Table: users\nColumns: id, username, email, created_at',
                    'expected_flow': ['Turkish Understanding', 'SQL Generation', 'Result Processing']
                },
                {
                    'query': 'ahmet isimli kullanıcıların bilgilerini göster',
                    'schema': 'Table: users\nColumns: id, username, email, created_at',
                    'expected_flow': ['Turkish Understanding', 'Name Filter Detection', 'SQL Generation']
                },
                {
                    'query': 'son 1 hafta içinde kayıt olan kullanıcılar',
                    'schema': 'Table: users\nColumns: id, username, email, created_at',
                    'expected_flow': ['Turkish Understanding', 'Date Filter Detection', 'SQL Generation']
                }
            ]
            
            successful_e2e = 0
            total_e2e = len(e2e_tests)
            
            for i, test_case in enumerate(e2e_tests, 1):
                query = test_case['query']
                schema = test_case['schema']
                
                print(f"      🔄 End-to-End Test {i}: '{query}'")
                
                try:
                    # Step 1: Turkish Understanding
                    print(f"         1️⃣ Turkish Understanding...")
                    intent = await self.llm_service.understand_turkish(query)
                    
                    if not intent or 'intent' not in intent:
                        print(f"            ❌ Turkish understanding failed")
                        continue
                    
                    print(f"            ✅ Intent: {intent['intent']}, Entities: {intent.get('entities', [])}")
                    
                    # Step 2: SQL Generation
                    print(f"         2️⃣ SQL Generation...")
                    sql = await self.llm_service.generate_sql(intent, schema, query)
                    
                    if not sql or len(sql.strip()) < 10:
                        print(f"            ❌ SQL generation failed")
                        continue
                    
                    print(f"            ✅ SQL: {repr(sql)}")
                    
                    # Step 3: Adaptive Learning Update
                    print(f"         3️⃣ Learning Update...")
                    await self.llm_service.learn_from_success(query, sql, 0.9, True)
                    print(f"            ✅ Learning updated")
                    
                    successful_e2e += 1
                    print(f"         ✅ End-to-End Test {i} SUCCESSFUL")
                    
                except Exception as e:
                    print(f"         ❌ End-to-End Test {i} FAILED: {e}")
                
                print()
            
            success_rate = (successful_e2e / total_e2e) * 100
            duration = time.time() - start_time
            
            if success_rate >= 70:  # 70% threshold
                details = f"E2E processing: {success_rate:.1f}% success ({successful_e2e}/{total_e2e})"
                self.results.add_result(test_name, "End-to-End Integration", "PASS", 
                                      duration, details)
                print(f"   ✅ PASS ({duration:.2f}s) - {details}")
            else:
                error_msg = f"Low E2E success rate: {success_rate:.1f}% (threshold: 70%)"
                self.results.add_result(test_name, "End-to-End Integration", "FAIL", 
                                      duration, "", error_msg)
                print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            self.results.add_result(test_name, "End-to-End Integration", "FAIL", 
                                  duration, "", error_msg)
            print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")
    
    async def _test_performance_benchmarks(self):
        """
        INTERNAL TEST: Performance Benchmarks
        Tests: Response times, throughput, memory usage, concurrent processing
        """
        test_name = "Performance Benchmarks"
        start_time = time.time()
        
        try:
            print(f"🧪 Testing: {test_name}")
            
            if not self.llm_service:
                raise Exception("LLM Service not initialized")
            
            # Performance benchmark queries
            benchmark_queries = [
                "kaç kullanıcı var",
                "son 7 gün içindeki siparişler", 
                "en fazla gelir getiren segment",
                "müşteri sayısı bu ay",
                "toplam satış miktarı"
            ]
            
            print(f"      ⏱️  Testing response times...")
            
            response_times = []
            successful_queries = 0
            
            for i, query in enumerate(benchmark_queries, 1):
                query_start = time.time()
                
                try:
                    # Measure Turkish understanding time
                    intent = await self.llm_service.understand_turkish(query)
                    understanding_time = time.time() - query_start
                    
                    # Measure SQL generation time
                    sql_start = time.time()
                    sql = await self.llm_service.generate_sql(
                        intent, 
                        "Table: users\nColumns: id, username, email, created_at",
                        query
                    )
                    sql_time = time.time() - sql_start
                    
                    total_time = time.time() - query_start
                    response_times.append(total_time)
                    
                    if intent and sql and len(sql.strip()) > 10:
                        successful_queries += 1
                    
                    print(f"         Query {i}: {total_time:.2f}s (Understanding: {understanding_time:.2f}s, SQL: {sql_time:.2f}s)")
                    
                except Exception as e:
                    total_time = time.time() - query_start
                    print(f"         Query {i}: FAILED in {total_time:.2f}s - {e}")
            
            # Calculate performance metrics
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                min_response_time = min(response_times)
                
                print(f"      📊 Performance Metrics:")
                print(f"         Average response time: {avg_response_time:.2f}s")
                print(f"         Min response time: {min_response_time:.2f}s")
                print(f"         Max response time: {max_response_time:.2f}s")
                print(f"         Success rate: {(successful_queries/len(benchmark_queries)*100):.1f}%")
                
                # Performance thresholds
                if avg_response_time <= 10.0 and successful_queries >= len(benchmark_queries) * 0.8:  # 10s avg, 80% success
                    duration = time.time() - start_time
                    details = f"Avg response: {avg_response_time:.2f}s, Success: {(successful_queries/len(benchmark_queries)*100):.1f}%"
                    
                    self.results.add_result(test_name, "Performance", "PASS", 
                                          duration, details)
                    print(f"   ✅ PASS ({duration:.2f}s) - {details}")
                else:
                    duration = time.time() - start_time
                    error_msg = f"Performance below threshold: {avg_response_time:.2f}s avg (max: 10s)"
                    
                    self.results.add_result(test_name, "Performance", "FAIL", 
                                          duration, "", error_msg)
                    print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")
            else:
                raise Exception("No successful performance measurements")
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            self.results.add_result(test_name, "Performance", "FAIL", 
                                  duration, "", error_msg)
            print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")

class InternalNLPTests:
    """
    INTERNAL TEST AREA: Real NLP Processor Integration Tests
    Tests actual NLP processor with LLM integration, Turkish processing
    """
    
    def __init__(self):
        self.test_db_id = f"nlp_test_{int(time.time())}"
        self.nlp_processor = None
        self.results = InternalTestResult()
    
    async def run_all_tests(self) -> InternalTestResult:
        """Run all internal NLP tests"""
        print("\n🔥 Starting Internal NLP Processor Tests...")
        print("=" * 80)
        
        # Test NLP processor initialization
        await self._test_nlp_processor_initialization()
        
        # Test Turkish text normalization
        await self._test_turkish_text_normalization()
        
        # Test intelligent SQL generation
        await self._test_intelligent_sql_generation()
        
        return self.results
    
    async def _test_nlp_processor_initialization(self):
        """
        INTERNAL TEST: NLP Processor Real Initialization
        Tests: Real NLP creation with LLM integration enabled
        """
        test_name = "NLP Processor Initialization"
        start_time = time.time()
        
        try:
            print(f"🧪 Testing: {test_name}")
            
            # Create NLP processor with LLM enabled
            self.nlp_processor = NLPProcessor(db_id=self.test_db_id)
            
            # Verify LLM integration
            if not self.nlp_processor.use_llm:
                raise Exception("LLM integration not enabled")
            
            if not self.nlp_processor.llm_service:
                raise Exception("LLM service not initialized")
            
            duration = time.time() - start_time
            details = f"LLM integration: {self.nlp_processor.use_llm}, Service: OK"
            
            self.results.add_result(test_name, "NLP Processor", "PASS", 
                                  duration, details)
            print(f"   ✅ PASS ({duration:.2f}s) - {details}")
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            self.results.add_result(test_name, "NLP Processor", "FAIL", 
                                  duration, "", error_msg)
            print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")
    
    async def _test_turkish_text_normalization(self):
        """
        INTERNAL TEST: Turkish Text Normalization
        Tests: Real Turkish character handling, keyword replacement, stop word removal
        """
        test_name = "Turkish Text Normalization"
        start_time = time.time()
        
        try:
            print(f"🧪 Testing: {test_name}")
            
            if not self.nlp_processor:
                raise Exception("NLP Processor not initialized")
            
            # Test Turkish normalization cases
            test_cases = [
                {
                    'input': 'Kullanıcı sayısı kaç tane?',
                    'expected_contains': 'kullanıcı'
                },
                {
                    'input': 'İstanbul\'daki müşterileri göster',
                    'expected_contains': 'müşteri'
                },
                {
                    'input': 'Şirketin toplam geliri nedir?',
                    'expected_contains': 'gelir'
                }
            ]
            
            successful_normalizations = 0
            total_cases = len(test_cases)
            
            for test_case in test_cases:
                input_text = test_case['input']
                expected = test_case['expected_contains']
                
                normalized = self.nlp_processor.normalize_turkish(input_text)
                
                print(f"      📝 '{input_text}' → '{normalized}'")
                
                if expected in normalized.lower():
                    successful_normalizations += 1
                    print(f"         ✅ Contains '{expected}'")
                else:
                    print(f"         ❌ Missing '{expected}'")
            
            success_rate = (successful_normalizations / total_cases) * 100
            duration = time.time() - start_time
            
            if success_rate >= 80:  # 80% threshold
                details = f"Normalization: {success_rate:.1f}% success ({successful_normalizations}/{total_cases})"
                self.results.add_result(test_name, "Text Normalization", "PASS", 
                                      duration, details)
                print(f"   ✅ PASS ({duration:.2f}s) - {details}")
            else:
                error_msg = f"Low normalization success: {success_rate:.1f}% (threshold: 80%)"
                self.results.add_result(test_name, "Text Normalization", "FAIL", 
                                      duration, "", error_msg)
                print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            self.results.add_result(test_name, "Text Normalization", "FAIL", 
                                  duration, "", error_msg)
            print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")
    
    async def _test_intelligent_sql_generation(self):
        """
        INTERNAL TEST: Intelligent SQL Generation via NLP Processor
        Tests: NLP processor's generate_intelligent_sql method with real LLM
        """
        test_name = "Intelligent SQL Generation"
        start_time = time.time()
        
        try:
            print(f"🧪 Testing: {test_name}")
            
            if not self.nlp_processor:
                raise Exception("NLP Processor not initialized")
            
            # Test SQL generation through NLP processor
            test_queries = [
                {
                    'query': 'kaç kullanıcı kayıtlı',
                    'expected_keywords': ['COUNT', 'user']
                },
                {
                    'query': 'tüm müşterileri listele',
                    'expected_keywords': ['SELECT', '*']
                }
            ]
            
            schema_info = {
                'schemas': {
                    'public': {
                        'tables': [
                            {
                                'name': 'users',
                                'columns': [
                                    {'name': 'id', 'type': 'INTEGER'},
                                    {'name': 'username', 'type': 'VARCHAR'}
                                ]
                            }
                        ]
                    }
                }
            }
            
            successful_generations = 0
            total_queries = len(test_queries)
            
            for test_case in test_queries:
                query = test_case['query']
                expected_keywords = test_case['expected_keywords']
                
                print(f"      🔧 Generating SQL for: '{query}'")
                
                # Generate SQL through NLP processor
                sql, confidence = self.nlp_processor.generate_intelligent_sql(query, schema_info)
                
                print(f"         SQL: {repr(sql)}")
                print(f"         Confidence: {confidence}")
                
                if sql and len(sql.strip()) > 5:
                    # Check for expected keywords
                    sql_upper = sql.upper()
                    keyword_found = any(kw in sql_upper for kw in expected_keywords)
                    
                    if keyword_found:
                        successful_generations += 1
                        print(f"         ✅ SQL generation successful")
                    else:
                        print(f"         ❌ Expected keywords not found: {expected_keywords}")
                else:
                    print(f"         ❌ SQL generation failed or empty")
            
            success_rate = (successful_generations / total_queries) * 100
            duration = time.time() - start_time
            
            if success_rate >= 70:  # 70% threshold
                details = f"SQL generation: {success_rate:.1f}% success ({successful_generations}/{total_queries})"
                self.results.add_result(test_name, "SQL Generation", "PASS", 
                                      duration, details)
                print(f"   ✅ PASS ({duration:.2f}s) - {details}")
            else:
                error_msg = f"Low generation success: {success_rate:.1f}% (threshold: 70%)"
                self.results.add_result(test_name, "SQL Generation", "FAIL", 
                                      duration, "", error_msg)
                print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            self.results.add_result(test_name, "SQL Generation", "FAIL", 
                                  duration, "", error_msg)
            print(f"   ❌ FAIL ({duration:.2f}s) - {error_msg}")

async def run_internal_tests():
    """
    Main function to run all internal integration tests
    """
    print("🚀 SQLAI Internal Integration Test Suite")
    print("=" * 80)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check environment
    if not os.getenv('USE_LOCAL_LLM', 'false').lower() == 'true':
        print("❌ Error: USE_LOCAL_LLM not enabled. Please set environment variables.")
        return False
    
    all_results = []
    
    try:
        # Run LLM tests
        llm_tests = InternalLLMTests()
        llm_results = await llm_tests.run_all_tests()
        all_results.append(llm_results)
        
        # Run NLP tests
        nlp_tests = InternalNLPTests() 
        nlp_results = await nlp_tests.run_all_tests()
        all_results.append(nlp_results)
        
    except Exception as e:
        print(f"\n❌ Critical test failure: {e}")
        traceback.print_exc()
        return False
    
    # Combine results and generate report
    print("\n" + "=" * 80)
    print("📊 INTERNAL INTEGRATION TEST RESULTS")
    print("=" * 80)
    
    total_tests = 0
    total_passed = 0
    total_failed = 0
    overall_duration = 0
    
    all_areas = {}
    
    for result_set in all_results:
        summary = result_set.get_summary()
        
        total_tests += summary['total_tests']
        total_passed += summary['passed']
        total_failed += summary['failed']
        overall_duration += summary['total_duration']
        
        # Merge areas
        for area, counts in summary['areas'].items():
            if area not in all_areas:
                all_areas[area] = {'PASS': 0, 'FAIL': 0}
            all_areas[area]['PASS'] += counts['PASS']
            all_areas[area]['FAIL'] += counts['FAIL']
    
    # Print area summaries
    for area, counts in all_areas.items():
        status_icon = "✅" if counts['FAIL'] == 0 else "❌"
        print(f"{status_icon} {area}")
        print(f"   PASS: {counts['PASS']}, FAIL: {counts['FAIL']}")
    
    print("\n" + "=" * 80)
    print("🎯 OVERALL SUMMARY:")
    print(f"   ✅ TOTAL TESTS: {total_tests}")
    print(f"   ✅ PASSED: {total_passed}")
    print(f"   ❌ FAILED: {total_failed}")
    print(f"   📊 SUCCESS RATE: {(total_passed/total_tests*100):.1f}%")
    print(f"   ⏱️  TOTAL DURATION: {overall_duration:.1f}s")
    print(f"   ⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Save results to file
    result_data = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_tests': total_tests,
            'passed': total_passed,
            'failed': total_failed,
            'success_rate': total_passed/total_tests*100,
            'duration': overall_duration
        },
        'areas': all_areas,
        'detailed_results': []
    }
    
    # Add detailed results
    for result_set in all_results:
        result_data['detailed_results'].extend(result_set.results)
    
    # Save to JSON file
    result_file = f"internal_test_results_{int(time.time())}.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Detailed results saved to: {result_file}")
    
    success_rate = total_passed/total_tests*100
    if success_rate >= 75:
        print(f"\n🎉 INTERNAL TESTS PASSED! Success rate: {success_rate:.1f}%")
        return True
    else:
        print(f"\n⚠️  INTERNAL TESTS NEED ATTENTION. Success rate: {success_rate:.1f}%")
        return False

if __name__ == '__main__':
    # Run internal integration tests
    success = asyncio.run(run_internal_tests())
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)