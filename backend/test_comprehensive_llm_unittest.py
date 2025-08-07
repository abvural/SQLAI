"""
Comprehensive Unit Test Suite for SQLAI LLM Integration
Tests all components: Mistral Turkish Understanding, SQLCoder Generation, Adaptive Learning
"""

import unittest
import asyncio
import os
import tempfile
import json
import shutil
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
import sys

# Add project root to path
sys.path.append('/Users/abdurrahimvural/Documents/GitHub/SQLAI/backend')

# Import modules to test
from app.services.llm_service import LocalLLMService
from app.services.adaptive_learning_service import AdaptiveLearningService  
from app.services.schema_context_service import SchemaContextService
from app.services.cache_service import CacheService
from app.ai.nlp_processor import NLPProcessor

class TestLLMServiceCore(unittest.TestCase):
    """
    TEST AREA: LocalLLMService Core Functions
    Tests: __init__, model loading, connection testing, configuration
    """
    
    def setUp(self):
        """Setup test environment with mock services"""
        # TEST: Environment variable configuration
        os.environ['USE_LOCAL_LLM'] = 'true'
        os.environ['OLLAMA_HOST'] = 'http://localhost:11434'
        os.environ['MISTRAL_MODEL'] = 'mistral:7b-instruct-q4_K_M'
        os.environ['SQLCODER_MODEL'] = 'sqlcoder:latest'
        
        # Mock Ollama client to avoid actual model calls
        self.mock_ollama_client = Mock()
        self.mock_async_client = AsyncMock()
        
        # TEST: Mock model availability
        self.mock_ollama_client.list.return_value = {
            'models': [
                {'name': 'mistral:7b-instruct-q4_K_M'},
                {'name': 'sqlcoder:latest'}
            ]
        }
    
    @patch('ollama.Client')
    @patch('ollama.AsyncClient')
    @patch('app.services.llm_service.AdaptiveLearningService')
    def test_llm_service_initialization(self, mock_adaptive, mock_async_client, mock_client):
        """
        TEST AREA: LLM Service Initialization
        Tests: Constructor, configuration loading, model validation
        """
        # Setup mocks
        mock_client.return_value = self.mock_ollama_client
        mock_async_client.return_value = self.mock_async_client
        mock_adaptive.return_value = Mock()
        
        # TEST: Service creation with database ID
        db_id = 'test-db-12345'
        llm_service = LocalLLMService(db_id)
        
        # VERIFY: Configuration loaded correctly
        self.assertEqual(llm_service.mistral_model, 'mistral:7b-instruct-q4_K_M')
        self.assertEqual(llm_service.sqlcoder_model, 'sqlcoder:latest')
        self.assertEqual(llm_service.db_id, db_id)
        
        # VERIFY: Adaptive learning initialized
        self.assertIsNotNone(llm_service.adaptive_learning)
        mock_adaptive.assert_called_once_with(db_id)
        
        # VERIFY: Ollama clients initialized
        mock_client.assert_called_once()
        mock_async_client.assert_called_once()
    
    @patch('ollama.Client')
    def test_model_availability_check(self, mock_client):
        """
        TEST AREA: Model Availability Verification
        Tests: _check_models method, model validation
        """
        mock_client.return_value = self.mock_ollama_client
        
        with patch('app.services.llm_service.AdaptiveLearningService'):
            # TEST: All models available
            llm_service = LocalLLMService()
            # Should not raise any warnings/errors
            
            # TEST: Missing model scenario
            self.mock_ollama_client.list.return_value = {'models': []}
            with patch('app.services.llm_service.logger') as mock_logger:
                llm_service._check_models()
                # VERIFY: Warning logged for missing models
                self.assertTrue(mock_logger.warning.called)

class TestTurkishUnderstanding(unittest.TestCase):
    """
    TEST AREA: Mistral Turkish Language Understanding
    Tests: understand_turkish method, intent extraction, entity recognition, filters
    """
    
    def setUp(self):
        """Setup test environment for Turkish understanding"""
        self.mock_llm_service = Mock()
        self.mock_async_client = AsyncMock()
        self.mock_llm_service.async_client = self.mock_async_client
        self.mock_llm_service.mistral_model = 'mistral:7b-instruct-q4_K_M'
        self.mock_llm_service.temperature = 0.1
        self.mock_llm_service.top_p = 0.95
        
        # Mock adaptive learning
        self.mock_adaptive = Mock()
        self.mock_adaptive.get_adaptive_context_for_query.return_value = ""
        self.mock_llm_service.adaptive_learning = self.mock_adaptive
    
    async def test_turkish_count_query_understanding(self):
        """
        TEST AREA: Turkish Count Query Processing
        Tests: "kaç kullanıcı var" type queries, JSON parsing, intent extraction
        """
        # TEST: Mock Mistral response for count query
        mock_response = {
            'response': '{"intent":"count","entities":["kullanıcı"],"filters":[]}'
        }
        self.mock_async_client.generate.return_value = mock_response
        
        # Create LLM service instance
        with patch('ollama.Client'), patch('ollama.AsyncClient'), \
             patch('app.services.llm_service.AdaptiveLearningService'):
            llm_service = LocalLLMService()
            llm_service.async_client = self.mock_async_client
            llm_service.adaptive_learning = self.mock_adaptive
        
        # TEST: Turkish count query
        query = "kaç kullanıcı var"
        result = await llm_service.understand_turkish(query)
        
        # VERIFY: Correct intent extraction
        self.assertEqual(result['intent'], 'count')
        self.assertIn('kullanıcı', result['entities'])
        self.assertEqual(len(result['filters']), 0)
        
        # VERIFY: Mistral was called with correct parameters
        self.mock_async_client.generate.assert_called_once()
        call_args = self.mock_async_client.generate.call_args
        self.assertEqual(call_args[1]['model'], 'mistral:7b-instruct-q4_K_M')
        self.assertIn(query, call_args[1]['prompt'])
    
    async def test_turkish_name_filter_query(self):
        """
        TEST AREA: Turkish Name Filter Detection
        Tests: "ahmet isimli kullanıcılar" pattern recognition, filter extraction
        """
        # TEST: Mock Mistral response with basic intent
        mock_response = {
            'response': '{"intent":"select","entities":["kullanıcı"],"filters":[]}'
        }
        self.mock_async_client.generate.return_value = mock_response
        
        with patch('ollama.Client'), patch('ollama.AsyncClient'), \
             patch('app.services.llm_service.AdaptiveLearningService'):
            llm_service = LocalLLMService()
            llm_service.async_client = self.mock_async_client
            llm_service.adaptive_learning = self.mock_adaptive
        
        # TEST: Turkish name filter query
        query = "ahmet isimli kullanıcılar"
        result = await llm_service.understand_turkish(query)
        
        # VERIFY: Name filter detected and added
        self.assertEqual(result['intent'], 'select')
        self.assertIn('kullanıcı', result['entities'])
        # Should have detected name filter
        name_filters = [f for f in result['filters'] if 'name=' in f]
        self.assertTrue(len(name_filters) > 0)
    
    async def test_turkish_date_filter_detection(self):
        """
        TEST AREA: Advanced Date/Time Pattern Recognition
        Tests: "son 30 gün", "bu hafta" patterns, PostgreSQL date filter generation
        """
        mock_response = {
            'response': '{"intent":"select","entities":["kullanıcı"],"filters":[]}'
        }
        self.mock_async_client.generate.return_value = mock_response
        
        with patch('ollama.Client'), patch('ollama.AsyncClient'), \
             patch('app.services.llm_service.AdaptiveLearningService'):
            llm_service = LocalLLMService()
            llm_service.async_client = self.mock_async_client
            llm_service.adaptive_learning = self.mock_adaptive
        
        # TEST: Date filter queries
        test_cases = [
            ("son 30 gün içindeki kullanıcılar", "30 days"),
            ("bu hafta kayıt olan müşteriler", "week"),
            ("bugün eklenen veriler", "CURRENT_DATE")
        ]
        
        for query, expected_pattern in test_cases:
            result = await llm_service.understand_turkish(query)
            
            # VERIFY: Date filters detected
            date_filters = [f for f in result['filters'] if 'date:' in f]
            self.assertTrue(len(date_filters) > 0, f"No date filter for: {query}")
            
            # VERIFY: Correct date pattern generated
            date_filter = date_filters[0]
            self.assertIn(expected_pattern, date_filter, f"Wrong pattern for: {query}")

class TestSQLGeneration(unittest.TestCase):
    """
    TEST AREA: SQLCoder SQL Generation
    Tests: generate_sql method, prompt building, SQL cleaning, complex JOIN detection
    """
    
    def setUp(self):
        """Setup test environment for SQL generation"""
        self.mock_async_client = AsyncMock()
        self.mock_adaptive = Mock()
        self.mock_adaptive.get_adaptive_context_for_query.return_value = ""
    
    async def test_basic_count_sql_generation(self):
        """
        TEST AREA: Basic COUNT Query SQL Generation
        Tests: Simple count queries, template-based generation
        """
        # TEST: Mock SQLCoder response
        expected_sql = "SELECT COUNT(*) as count FROM users;"
        self.mock_async_client.generate.return_value = {
            'response': expected_sql
        }
        
        with patch('ollama.Client'), patch('ollama.AsyncClient'), \
             patch('app.services.llm_service.AdaptiveLearningService'):
            llm_service = LocalLLMService()
            llm_service.async_client = self.mock_async_client
            llm_service.adaptive_learning = self.mock_adaptive
            llm_service.sqlcoder_model = 'sqlcoder:latest'
        
        # TEST: Intent for count query
        intent = {
            'intent': 'count',
            'entities': ['kullanıcı'],
            'filters': []
        }
        
        schema_context = "Table: users\nColumns: id, username, email"
        result = await llm_service.generate_sql(intent, schema_context)
        
        # VERIFY: Correct SQL generated
        self.assertIn("COUNT(*)", result)
        self.assertIn("users", result)
        
        # VERIFY: SQLCoder called with correct model
        self.mock_async_client.generate.assert_called()
        call_args = self.mock_async_client.generate.call_args
        self.assertEqual(call_args[1]['model'], 'sqlcoder:latest')
    
    async def test_complex_join_sql_generation(self):
        """
        TEST AREA: Complex JOIN Query Generation
        Tests: Multi-table queries, JOIN pattern detection, business intelligence
        """
        # TEST: Mock SQLCoder response for complex query
        expected_sql = """SELECT c.segment_type, SUM(o.amount) as total_revenue 
                         FROM customer_segments c 
                         JOIN orders o ON c.customer_id = o.customer_id 
                         GROUP BY c.segment_type 
                         ORDER BY total_revenue DESC;"""
        
        self.mock_async_client.generate.return_value = {
            'response': expected_sql
        }
        
        with patch('ollama.Client'), patch('ollama.AsyncClient'), \
             patch('app.services.llm_service.AdaptiveLearningService'):
            llm_service = LocalLLMService()
            llm_service.async_client = self.mock_async_client
            llm_service.adaptive_learning = self.mock_adaptive
        
        # TEST: Complex intent with JOIN patterns
        intent = {
            'intent': 'max',
            'entities': ['segment', 'gelir'],
            'filters': [],
            'metadata': {
                'join_patterns': ['segment_analysis:Analyze revenue by customer segments - requires JOIN']
            }
        }
        
        schema_context = """Table: customer_segments
Columns: id, customer_id, segment_type
Table: orders  
Columns: id, customer_id, amount, created_at"""
        
        result = await llm_service.generate_sql(intent, schema_context)
        
        # VERIFY: JOIN query generated
        self.assertIn("JOIN", result.upper())
        self.assertIn("GROUP BY", result.upper())
        
    def test_sql_cleaning_functionality(self):
        """
        TEST AREA: SQL Response Cleaning
        Tests: _clean_sql method, artifact removal, format standardization
        """
        with patch('ollama.Client'), patch('ollama.AsyncClient'), \
             patch('app.services.llm_service.AdaptiveLearningService'):
            llm_service = LocalLLMService()
        
        # TEST: Various SQL cleaning scenarios
        test_cases = [
            # Raw SQL with markdown
            ("```sql\nSELECT * FROM users;\n```", "SELECT * FROM users;"),
            # SQL with prefixes
            ("SQL Query: SELECT COUNT(*) FROM products", "SELECT COUNT(*) FROM products;"),
            # SQL with artifacts
            ("<sql>SELECT * FROM orders</sql>", "SELECT * FROM orders;"),
            # Multiple lines with comments
            ("-- Comment\nSELECT id, name\nFROM users;", "SELECT id, name FROM users;")
        ]
        
        for dirty_sql, expected_clean in test_cases:
            result = llm_service._clean_sql(dirty_sql)
            # VERIFY: SQL properly cleaned
            self.assertEqual(result.strip(), expected_clean, f"Failed to clean: {dirty_sql}")

class TestPatternRecognition(unittest.TestCase):
    """
    TEST AREA: Advanced Pattern Recognition Systems
    Tests: Date patterns, name patterns, complex JOINs, conversational, BI patterns
    """
    
    def setUp(self):
        """Setup for pattern recognition tests"""
        with patch('ollama.Client'), patch('ollama.AsyncClient'), \
             patch('app.services.llm_service.AdaptiveLearningService'):
            self.llm_service = LocalLLMService()
    
    def test_name_filter_pattern_detection(self):
        """
        TEST AREA: Turkish Name Filter Pattern Recognition  
        Tests: _detect_name_filters method, Turkish name patterns, regex matching
        """
        # TEST: Various Turkish name patterns
        test_cases = [
            ("ahmet isimli kullanıcılar", ["name=ahmet"]),
            ("ismi mehmet olan", ["name=mehmet"]),
            ("fatma adlı müşteriler", ["name=fatma"]),
            ("john ismi geçen", ["name=john"])
        ]
        
        for query, expected_filters in test_cases:
            result = self.llm_service._detect_name_filters(query)
            # VERIFY: Name filters correctly detected
            self.assertEqual(len(result), len(expected_filters), f"Wrong filter count for: {query}")
            for expected in expected_filters:
                self.assertIn(expected, result, f"Missing filter {expected} for: {query}")
    
    def test_date_filter_pattern_detection(self):
        """
        TEST AREA: Advanced Date/Time Filter Pattern Recognition
        Tests: _detect_date_filters method, Turkish temporal expressions
        """
        # TEST: Turkish date patterns
        test_cases = [
            ("son 7 gün", "7 days"),
            ("bu hafta", "date_trunc('week'"),
            ("geçen ay", "1 month"),
            ("bugün", "CURRENT_DATE"),
            ("last 30 days", "30 days")
        ]
        
        for query, expected_pattern in test_cases:
            result = self.llm_service._detect_date_filters(query)
            # VERIFY: Date filters correctly detected
            self.assertTrue(len(result) > 0, f"No date filter detected for: {query}")
            date_filter = result[0]
            self.assertIn(expected_pattern, date_filter, f"Wrong pattern for: {query}")
    
    def test_complex_join_pattern_detection(self):
        """
        TEST AREA: Complex JOIN Pattern Recognition
        Tests: _detect_complex_join_patterns method, business intelligence queries
        """
        # TEST: Complex JOIN patterns
        test_cases = [
            ("en fazla sipariş veren müşteri", "max_aggregation"),
            ("müşteri başına ortalama gelir", "per_group_aggregation"), 
            ("segment bazında satış analizi", "segment_based"),
            ("satış performans analizi", "performance_analysis"),
            ("müşteri davranış analizi", "customer_behavior")
        ]
        
        for query, expected_pattern in test_cases:
            result = self.llm_service._detect_complex_join_patterns(query)
            # VERIFY: Complex patterns detected
            self.assertTrue(len(result) > 0, f"No complex pattern for: {query}")
            pattern = result[0]
            self.assertIn(expected_pattern, pattern, f"Wrong pattern for: {query}")
    
    def test_conversational_pattern_detection(self):
        """
        TEST AREA: Conversational Query Understanding
        Tests: _detect_conversational_patterns method, context-dependent queries
        """
        # TEST: Conversational patterns
        test_cases = [
            ("bunların detayı", True, "detail_request"),
            ("daha fazla bilgi", True, "more_information"),
            ("karşılaştırma yapar mısın", True, "comparison_request"),
            ("bu müşterilerin profili", True, None)  # Context dependent but no follow-up
        ]
        
        for query, should_be_contextual, expected_followup in test_cases:
            result = self.llm_service._detect_conversational_patterns(query)
            # VERIFY: Conversational patterns detected
            if should_be_contextual:
                self.assertTrue(result['context_dependent'] or result['follow_up_type'], 
                              f"No conversational pattern for: {query}")
            if expected_followup:
                self.assertEqual(result['follow_up_type'], expected_followup, 
                               f"Wrong follow-up type for: {query}")
    
    def test_business_intelligence_pattern_detection(self):
        """
        TEST AREA: Business Intelligence Pattern Recognition
        Tests: _detect_business_intelligence_patterns method, advanced analytics
        """
        # TEST: BI patterns
        test_cases = [
            ("müşteri yaşam değeri analizi", "customer_ltv"),
            ("churn müşteri oranı", "churn_analysis"),
            ("cohort analizi", "cohort_analysis"),
            ("satış funnel analizi", "sales_funnel"),
            ("mrr aylık yinelenen gelir", "mrr_analysis"),
            ("growth rate büyüme oranı", "growth_rate")
        ]
        
        for query, expected_pattern in test_cases:
            result = self.llm_service._detect_business_intelligence_patterns(query)
            # VERIFY: BI patterns detected
            self.assertTrue(len(result) > 0, f"No BI pattern for: {query}")
            pattern = result[0]
            self.assertIn(expected_pattern, pattern, f"Wrong BI pattern for: {query}")

class TestAdaptiveLearning(unittest.TestCase):
    """
    TEST AREA: Adaptive Learning System
    Tests: Schema learning, query pattern storage, success tracking, context generation
    """
    
    def setUp(self):
        """Setup adaptive learning test environment"""
        # Create temporary directory for test database
        self.temp_dir = tempfile.mkdtemp()
        self.db_id = "test-adaptive-db"
        
        # Mock schema context service to avoid ChromaDB issues
        with patch('app.services.adaptive_learning_service.SchemaContextService'):
            self.adaptive_service = AdaptiveLearningService(self.db_id)
            self.adaptive_service.cache = Mock()  # Mock cache service
    
    def tearDown(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def test_schema_learning_initialization(self):
        """
        TEST AREA: Schema Learning Initialization
        Tests: initialize_schema_learning method, vocabulary extraction, mapping generation
        """
        # TEST: Sample schema information
        schema_info = {
            'schemas': {
                'public': {
                    'tables': [
                        {
                            'name': 'users',
                            'columns': [
                                {'name': 'id', 'type': 'INTEGER'},
                                {'name': 'username', 'type': 'VARCHAR'},
                                {'name': 'email', 'type': 'VARCHAR'}
                            ]
                        },
                        {
                            'name': 'customer_segments',
                            'columns': [
                                {'name': 'id', 'type': 'INTEGER'},
                                {'name': 'segment_type', 'type': 'VARCHAR'},
                                {'name': 'customer_id', 'type': 'INTEGER'}
                            ]
                        }
                    ]
                }
            }
        }
        
        # TEST: Initialize schema learning
        result = await self.adaptive_service.initialize_schema_learning(schema_info)
        
        # VERIFY: Vocabulary extracted
        self.assertIn('vocabulary', result)
        vocabulary = result['vocabulary']
        self.assertIn('users', vocabulary)
        self.assertIn('customer', vocabulary)  # Should extract from customer_segments
        self.assertIn('segments', vocabulary)
        
        # VERIFY: Language mappings created
        self.assertIn('language_mappings', result)
        mappings = result['language_mappings']
        self.assertIn('users', mappings.values())  # Should have Turkish->English mapping
    
    async def test_successful_query_learning(self):
        """
        TEST AREA: Query Success Learning
        Tests: learn_from_successful_query method, pattern extraction, metrics tracking
        """
        # TEST: Learn from successful query
        query = "kaç kullanıcı var"
        sql = "SELECT COUNT(*) as count FROM users;"
        confidence = 0.95
        success = True
        
        await self.adaptive_service.learn_from_successful_query(query, sql, confidence, success)
        
        # VERIFY: Metrics updated
        self.assertEqual(self.adaptive_service.learning_metrics['total_queries'], 1)
        self.assertEqual(self.adaptive_service.learning_metrics['successful_queries'], 1)
        
        # VERIFY: Cache called to store learning
        self.assertTrue(self.adaptive_service.cache.set_cache.called)
    
    def test_adaptive_context_generation(self):
        """
        TEST AREA: Adaptive Context Generation
        Tests: get_adaptive_context_for_query method, context building from learned patterns
        """
        # TEST: Mock stored learning data
        mock_learning_data = {
            'vocabulary': ['users', 'customer', 'segments', 'orders'],
            'language_mappings': {
                'kullanıcılar': 'users',
                'müşteriler': 'customers',
                'siparişler': 'orders'
            },
            'query_patterns': []
        }
        
        # Mock the cache to return our test data
        self.adaptive_service._load_learning_data = Mock(return_value=mock_learning_data)
        
        # TEST: Get adaptive context for query
        query = "kullanıcı sayısı"
        context = self.adaptive_service.get_adaptive_context_for_query(query)
        
        # VERIFY: Context contains relevant information
        self.assertIn('Database Terms', context)
        self.assertIn('Turkish Mappings', context)
        self.assertIn('kullanıcılar=users', context)  # Should find relevant mapping

class TestNLPProcessorIntegration(unittest.TestCase):
    """
    TEST AREA: NLP Processor LLM Integration
    Tests: NLPProcessor with LLM enabled, generate_intelligent_sql method
    """
    
    def setUp(self):
        """Setup NLP processor tests"""
        # Set LLM environment
        os.environ['USE_LOCAL_LLM'] = 'true'
    
    @patch('app.ai.nlp_processor.LocalLLMService')
    @patch('app.ai.nlp_processor.SchemaContextService')  
    def test_nlp_processor_llm_initialization(self, mock_schema_context, mock_llm_service):
        """
        TEST AREA: NLP Processor LLM Initialization
        Tests: LLM service integration, environment variable handling
        """
        # Setup mocks
        mock_llm = Mock()
        mock_llm_service.return_value = mock_llm
        mock_schema_context.return_value = Mock()
        
        # TEST: Create NLP processor with database ID
        db_id = "test-nlp-db"
        nlp = NLPProcessor(db_id=db_id)
        
        # VERIFY: LLM integration enabled
        self.assertTrue(nlp.use_llm)
        self.assertIsNotNone(nlp.llm_service)
        
        # VERIFY: LLM service created with correct database ID
        mock_llm_service.assert_called_once_with(db_id)
    
    @patch('app.ai.nlp_processor.LocalLLMService')
    def test_turkish_text_normalization(self, mock_llm_service):
        """
        TEST AREA: Turkish Text Normalization
        Tests: normalize_turkish method, character handling, stop word removal
        """
        nlp = NLPProcessor()
        
        # TEST: Turkish text normalization
        test_cases = [
            ("Kullanıcı sayısı kaç?", "kullanıcı [COUNT]"),  # Should replace 'sayısı' with [COUNT]
            ("Müşteri listesi göster", "müşteri listesi göster"),
            ("İstanbul'daki kullanıcılar", "istanbul kullanıcılar")  # Should remove stop words
        ]
        
        for input_text, expected_pattern in test_cases:
            result = nlp.normalize_turkish(input_text)
            # VERIFY: Text properly normalized
            self.assertIn(expected_pattern.split()[0], result.lower(), 
                         f"Normalization failed for: {input_text}")

class TestEndToEndIntegration(unittest.TestCase):
    """
    TEST AREA: End-to-End Integration Testing
    Tests: Complete query flow from Turkish input to SQL output
    """
    
    def setUp(self):
        """Setup end-to-end test environment"""
        os.environ['USE_LOCAL_LLM'] = 'true'
        self.test_schema = {
            'schemas': {
                'public': {
                    'tables': [
                        {
                            'name': 'users',
                            'columns': [
                                {'name': 'id', 'type': 'INTEGER'},
                                {'name': 'username', 'type': 'VARCHAR'},
                                {'name': 'email', 'type': 'VARCHAR'},
                                {'name': 'created_at', 'type': 'TIMESTAMP'}
                            ]
                        }
                    ]
                }
            }
        }
    
    @patch('ollama.AsyncClient')
    @patch('ollama.Client')
    @patch('app.services.llm_service.AdaptiveLearningService')
    async def test_complete_turkish_query_flow(self, mock_adaptive, mock_client, mock_async_client):
        """
        TEST AREA: Complete Turkish Query Processing Flow
        Tests: Full pipeline from Turkish query to SQL generation
        """
        # Setup mocks for complete flow
        mock_async = AsyncMock()
        mock_async_client.return_value = mock_async
        
        # Mock Mistral response for Turkish understanding
        mock_mistral_response = {
            'response': '{"intent":"count","entities":["kullanıcı"],"filters":[]}'
        }
        
        # Mock SQLCoder response for SQL generation
        mock_sqlcoder_response = {
            'response': 'SELECT COUNT(*) as count FROM users;'
        }
        
        # Configure mock to return different responses based on model
        async def mock_generate(model, prompt, options):
            if 'mistral' in model:
                return mock_mistral_response
            elif 'sqlcoder' in model:
                return mock_sqlcoder_response
            return {'response': ''}
        
        mock_async.generate.side_effect = mock_generate
        
        # Setup adaptive learning mock
        mock_adaptive_instance = Mock()
        mock_adaptive_instance.get_adaptive_context_for_query.return_value = ""
        mock_adaptive.return_value = mock_adaptive_instance
        
        # TEST: Create LLM service and process complete query
        llm_service = LocalLLMService('test-db')
        llm_service.async_client = mock_async
        
        # Process Turkish query through complete pipeline
        query = "kaç kullanıcı var"
        
        # Step 1: Turkish understanding
        intent = await llm_service.understand_turkish(query)
        
        # Step 2: SQL generation
        schema_context = "Table: users\nColumns: id, username, email, created_at"
        sql = await llm_service.generate_sql(intent, schema_context, query)
        
        # VERIFY: Complete flow successful
        self.assertEqual(intent['intent'], 'count')
        self.assertIn('kullanıcı', intent['entities'])
        self.assertIn('COUNT(*)', sql)
        self.assertIn('users', sql)
        
        # VERIFY: Both models were called
        self.assertEqual(mock_async.generate.call_count, 2)  # Mistral + SQLCoder

# Custom Test Runner with detailed reporting
class DetailedTestResult(unittest.TextTestResult):
    """
    Custom test result class for detailed reporting
    """
    
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.test_results = []
    
    def addSuccess(self, test):
        super().addSuccess(test)
        self.test_results.append({
            'test': str(test),
            'status': 'PASS',
            'area': self._get_test_area(test)
        })
    
    def addError(self, test, err):
        super().addError(test, err)
        self.test_results.append({
            'test': str(test),
            'status': 'ERROR',
            'area': self._get_test_area(test),
            'error': str(err[1])
        })
    
    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.test_results.append({
            'test': str(test),
            'status': 'FAIL',
            'area': self._get_test_area(test),
            'error': str(err[1])
        })
    
    def _get_test_area(self, test):
        """Extract test area from test docstring"""
        if hasattr(test, '_testMethodDoc') and test._testMethodDoc:
            if 'TEST AREA:' in test._testMethodDoc:
                return test._testMethodDoc.split('TEST AREA:')[1].split('\n')[0].strip()
        return test.__class__.__name__

def run_comprehensive_tests():
    """
    TEST AREA: Test Suite Runner
    Runs all tests and provides detailed reporting
    """
    print("🧪 Starting Comprehensive SQLAI LLM Unit Tests...")
    print("=" * 80)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestLLMServiceCore,
        TestTurkishUnderstanding, 
        TestSQLGeneration,
        TestPatternRecognition,
        TestAdaptiveLearning,
        TestNLPProcessorIntegration,
        TestEndToEndIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with custom result class
    runner = unittest.TextTestRunner(
        verbosity=2,
        resultclass=DetailedTestResult,
        stream=sys.stdout
    )
    
    result = runner.run(suite)
    
    # Print detailed results
    print("\n" + "=" * 80)
    print("📊 TEST RESULTS BY AREA:")
    print("=" * 80)
    
    # Group results by test area
    areas = {}
    for test_result in result.test_results:
        area = test_result['area']
        if area not in areas:
            areas[area] = {'PASS': 0, 'FAIL': 0, 'ERROR': 0}
        areas[area][test_result['status']] += 1
    
    # Print area summaries
    total_pass = total_fail = total_error = 0
    for area, counts in areas.items():
        status_icon = "✅" if counts['FAIL'] == 0 and counts['ERROR'] == 0 else "❌"
        print(f"{status_icon} {area}")
        print(f"   PASS: {counts['PASS']}, FAIL: {counts['FAIL']}, ERROR: {counts['ERROR']}")
        
        total_pass += counts['PASS']
        total_fail += counts['FAIL'] 
        total_error += counts['ERROR']
    
    print("\n" + "=" * 80)
    print("🎯 OVERALL SUMMARY:")
    print(f"   ✅ PASSED: {total_pass}")
    print(f"   ❌ FAILED: {total_fail}")
    print(f"   🔥 ERRORS: {total_error}")
    print(f"   📊 SUCCESS RATE: {total_pass/(total_pass+total_fail+total_error)*100:.1f}%")
    
    # Print failed tests details
    if total_fail > 0 or total_error > 0:
        print("\n" + "=" * 80)
        print("🔍 FAILED TEST DETAILS:")
        for test_result in result.test_results:
            if test_result['status'] in ['FAIL', 'ERROR']:
                print(f"❌ {test_result['test']}")
                print(f"   Area: {test_result['area']}")
                print(f"   Error: {test_result.get('error', 'Unknown error')}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    # Run comprehensive test suite
    success = run_comprehensive_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)