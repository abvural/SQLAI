#!/usr/bin/env python3
"""
Test Suite for LLM Integration
Tests the complete LLM pipeline including Mistral, SQLCoder, and ChromaDB
"""
import os
import sys
import asyncio
import logging
from typing import Dict, Any, List
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test results storage
test_results = {
    "timestamp": datetime.now().isoformat(),
    "tests": [],
    "summary": {
        "total": 0,
        "passed": 0,
        "failed": 0
    }
}

def record_test(test_name: str, passed: bool, details: str = ""):
    """Record test result"""
    test_results["tests"].append({
        "name": test_name,
        "passed": passed,
        "details": details,
        "timestamp": datetime.now().isoformat()
    })
    test_results["summary"]["total"] += 1
    if passed:
        test_results["summary"]["passed"] += 1
    else:
        test_results["summary"]["failed"] += 1
    
    status = "✓ PASSED" if passed else "✗ FAILED"
    print(f"{status}: {test_name}")
    if details:
        print(f"  Details: {details}")

def test_environment():
    """Test 1: Environment Configuration"""
    print("\n" + "="*50)
    print("Test 1: Environment Configuration")
    print("="*50)
    
    required_vars = [
        "USE_LOCAL_LLM",
        "OLLAMA_HOST",
        "MISTRAL_MODEL",
        "SQLCODER_MODEL",
        "CHROMA_PERSIST_PATH"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            print(f"  {var}: {value}")
    
    if missing_vars:
        record_test("Environment Configuration", False, f"Missing: {', '.join(missing_vars)}")
        return False
    
    llm_enabled = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"
    if not llm_enabled:
        record_test("Environment Configuration", False, "USE_LOCAL_LLM is not set to true")
        return False
    
    record_test("Environment Configuration", True)
    return True

def test_ollama_connection():
    """Test 2: Ollama Service Connection"""
    print("\n" + "="*50)
    print("Test 2: Ollama Service Connection")
    print("="*50)
    
    try:
        import ollama
        client = ollama.Client()
        models = client.list()
        
        print(f"  Connected to Ollama")
        print(f"  Found {len(models.get('models', []))} models")
        
        record_test("Ollama Service Connection", True)
        return True
    except Exception as e:
        record_test("Ollama Service Connection", False, str(e))
        return False

def test_model_availability():
    """Test 3: Model Availability"""
    print("\n" + "="*50)
    print("Test 3: Model Availability")
    print("="*50)
    
    try:
        import ollama
        client = ollama.Client()
        models = client.list()
        
        available_models = [m['name'] for m in models.get('models', [])]
        mistral_model = os.getenv('MISTRAL_MODEL', 'mistral:7b-instruct-q4_K_M')
        sqlcoder_model = os.getenv('SQLCODER_MODEL', 'sqlcoder')
        
        mistral_found = any(mistral_model in m for m in available_models)
        sqlcoder_found = any(sqlcoder_model in m for m in available_models)
        
        print(f"  Mistral ({mistral_model}): {'Found' if mistral_found else 'Not Found'}")
        print(f"  SQLCoder ({sqlcoder_model}): {'Found' if sqlcoder_found else 'Not Found'}")
        
        if not mistral_found:
            record_test("Model Availability", False, f"Mistral model {mistral_model} not found")
            return False
        
        # SQLCoder is optional, warn if not found
        if not sqlcoder_found:
            print(f"  Warning: SQLCoder not found, will use fallback")
        
        record_test("Model Availability", True)
        return True
    except Exception as e:
        record_test("Model Availability", False, str(e))
        return False

async def test_llm_service():
    """Test 4: LLM Service Initialization"""
    print("\n" + "="*50)
    print("Test 4: LLM Service Initialization")
    print("="*50)
    
    try:
        from app.services.llm_service import LocalLLMService
        
        llm_service = LocalLLMService()
        
        # Test connection
        connected = llm_service.test_connection()
        print(f"  Connection test: {'Success' if connected else 'Failed'}")
        
        if not connected:
            record_test("LLM Service Initialization", False, "Connection test failed")
            return False
        
        record_test("LLM Service Initialization", True)
        return True
    except Exception as e:
        record_test("LLM Service Initialization", False, str(e))
        return False

async def test_turkish_understanding():
    """Test 5: Turkish Language Understanding"""
    print("\n" + "="*50)
    print("Test 5: Turkish Language Understanding")
    print("="*50)
    
    try:
        from app.services.llm_service import LocalLLMService
        
        llm_service = LocalLLMService()
        
        test_queries = [
            "kullanıcıları listele",
            "en fazla satış yapan bayi",
            "ismi ahmet olan müşteriler",
            "toplam sipariş sayısı"
        ]
        
        for query in test_queries:
            print(f"\n  Testing: '{query}'")
            intent = await llm_service.understand_turkish(query)
            print(f"    Intent: {intent.get('intent', 'unknown')}")
            print(f"    Entities: {intent.get('entities', [])}")
            
            if not intent or not intent.get('intent'):
                record_test("Turkish Language Understanding", False, f"Failed on: {query}")
                return False
        
        record_test("Turkish Language Understanding", True)
        return True
    except Exception as e:
        record_test("Turkish Language Understanding", False, str(e))
        return False

async def test_sql_generation():
    """Test 6: SQL Generation"""
    print("\n" + "="*50)
    print("Test 6: SQL Generation")
    print("="*50)
    
    try:
        from app.services.llm_service import LocalLLMService
        
        llm_service = LocalLLMService()
        
        # Sample schema context
        schema_context = """
        Database Schema:
        ==================================================
        
        Table: public.users
        Columns:
          - id (integer) [PK]
          - username (varchar)
          - email (varchar)
          - created_at (timestamp)
        
        Table: public.orders
        Columns:
          - id (integer) [PK]
          - user_id (integer) [FK]
          - amount (decimal)
          - order_date (date)
        
        Relationships:
          - orders.user_id -> users.id
        """
        
        # Test intent
        intent = {
            "intent": "select",
            "entities": ["users"],
            "filters": ["username=ahmet"],
            "metrics": ["username", "email"]
        }
        
        print(f"  Generating SQL for intent: {intent['intent']}")
        sql = await llm_service.generate_sql(intent, schema_context)
        
        if not sql:
            record_test("SQL Generation", False, "No SQL generated")
            return False
        
        print(f"  Generated SQL: {sql[:100]}...")
        
        # Check if SQL contains expected keywords
        sql_lower = sql.lower()
        if "select" not in sql_lower or "from" not in sql_lower:
            record_test("SQL Generation", False, "Invalid SQL structure")
            return False
        
        record_test("SQL Generation", True)
        return True
    except Exception as e:
        record_test("SQL Generation", False, str(e))
        return False

def test_chromadb_setup():
    """Test 7: ChromaDB Vector Database"""
    print("\n" + "="*50)
    print("Test 7: ChromaDB Vector Database")
    print("="*50)
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        # Test ChromaDB initialization
        persist_path = os.getenv('CHROMA_PERSIST_PATH', './chroma_db')
        client = chromadb.PersistentClient(
            path=persist_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create test collection
        test_collection = client.create_collection(
            name="test_collection",
            metadata={"test": True}
        )
        
        # Add test documents
        test_collection.add(
            documents=["test document 1", "test document 2"],
            metadatas=[{"type": "test"}, {"type": "test"}],
            ids=["test1", "test2"]
        )
        
        # Query test
        results = test_collection.query(
            query_texts=["test"],
            n_results=2
        )
        
        # Clean up
        client.delete_collection("test_collection")
        
        print(f"  ChromaDB initialized at: {persist_path}")
        print(f"  Test collection created and queried successfully")
        
        record_test("ChromaDB Vector Database", True)
        return True
    except Exception as e:
        record_test("ChromaDB Vector Database", False, str(e))
        return False

def test_schema_context_service():
    """Test 8: Schema Context Service"""
    print("\n" + "="*50)
    print("Test 8: Schema Context Service")
    print("="*50)
    
    try:
        from app.services.schema_context_service import SchemaContextService
        
        # Create service with test database ID
        db_id = "test_db_001"
        service = SchemaContextService(db_id)
        
        # Test schema data
        test_schema = {
            "schemas": {
                "public": {
                    "tables": [
                        {
                            "name": "users",
                            "columns": [
                                {"name": "id", "type": "integer", "is_primary_key": True},
                                {"name": "username", "type": "varchar"},
                                {"name": "email", "type": "varchar"}
                            ],
                            "row_count": 100
                        }
                    ],
                    "relationships": []
                }
            }
        }
        
        # Index schema
        service.index_schema(test_schema, force_reindex=True)
        
        # Get relevant context
        context = service.get_relevant_context("kullanıcıları listele", limit=10)
        
        print(f"  Schema indexed for database: {db_id}")
        print(f"  Context retrieved: {len(context)} characters")
        
        if not context:
            record_test("Schema Context Service", False, "No context retrieved")
            return False
        
        record_test("Schema Context Service", True)
        return True
    except Exception as e:
        record_test("Schema Context Service", False, str(e))
        return False

def test_nlp_processor_integration():
    """Test 9: NLP Processor with LLM"""
    print("\n" + "="*50)
    print("Test 9: NLP Processor with LLM")
    print("="*50)
    
    try:
        from app.ai.nlp_processor import NLPProcessor
        
        # Create processor with test database
        processor = NLPProcessor(db_id="test_db_001")
        
        # Test schema
        test_schema = {
            "schemas": {
                "public": {
                    "tables": [
                        {
                            "name": "users",
                            "columns": [
                                {"name": "id", "type": "integer"},
                                {"name": "username", "type": "varchar"},
                                {"name": "email", "type": "varchar"}
                            ]
                        }
                    ]
                }
            }
        }
        
        # Test query
        query = "ismi elif olan kullanıcıları getir"
        
        print(f"  Testing query: '{query}'")
        sql, confidence = processor.generate_intelligent_sql(query, test_schema)
        
        if not sql:
            record_test("NLP Processor with LLM", False, "No SQL generated")
            return False
        
        print(f"  Generated SQL: {sql[:100]}...")
        print(f"  Confidence: {confidence:.2f}")
        
        if confidence < 0.5:
            record_test("NLP Processor with LLM", False, f"Low confidence: {confidence}")
            return False
        
        record_test("NLP Processor with LLM", True)
        return True
    except Exception as e:
        record_test("NLP Processor with LLM", False, str(e))
        return False

def test_query_builder_integration():
    """Test 10: Query Builder with LLM"""
    print("\n" + "="*50)
    print("Test 10: Query Builder with LLM")
    print("="*50)
    
    try:
        from app.ai.query_builder import SQLQueryBuilder
        from app.services.cache_service import CacheService
        
        # Create query builder
        db_id = "test_db_001"
        builder = SQLQueryBuilder(db_id=db_id)
        
        # Mock schema in cache
        cache = CacheService()
        test_schema = {
            "schemas": {
                "public": {
                    "tables": [
                        {
                            "name": "products",
                            "columns": [
                                {"name": "id", "type": "integer", "is_primary_key": True},
                                {"name": "name", "type": "varchar"},
                                {"name": "price", "type": "decimal"}
                            ]
                        }
                    ],
                    "relationships": []
                }
            }
        }
        cache.set_cache(f"schema_analysis_{db_id}", test_schema, 'schema', ttl=3600)
        
        # Build query
        result = builder.build_query("en pahalı ürünü göster", db_id)
        
        if not result.get('success'):
            record_test("Query Builder with LLM", False, result.get('error', 'Unknown error'))
            return False
        
        print(f"  Query built successfully")
        print(f"  SQL: {result.get('sql', '')[:100]}...")
        print(f"  Confidence: {result.get('confidence', 0):.2f}")
        print(f"  LLM Generated: {result.get('llm_generated', False)}")
        
        record_test("Query Builder with LLM", True)
        return True
    except Exception as e:
        record_test("Query Builder with LLM", False, str(e))
        return False

async def run_all_tests():
    """Run all LLM integration tests"""
    print("\n" + "="*70)
    print("SQLAI LLM Integration Test Suite")
    print("="*70)
    print(f"Starting tests at: {datetime.now().isoformat()}")
    
    # Run tests in order
    tests = [
        ("Environment Configuration", test_environment),
        ("Ollama Connection", test_ollama_connection),
        ("Model Availability", test_model_availability),
        ("LLM Service", test_llm_service),
        ("Turkish Understanding", test_turkish_understanding),
        ("SQL Generation", test_sql_generation),
        ("ChromaDB Setup", test_chromadb_setup),
        ("Schema Context Service", test_schema_context_service),
        ("NLP Processor Integration", test_nlp_processor_integration),
        ("Query Builder Integration", test_query_builder_integration)
    ]
    
    # Run synchronous tests
    for test_name, test_func in tests[:3]:
        if not asyncio.iscoroutinefunction(test_func):
            test_func()
    
    # Run async tests
    for test_name, test_func in tests[3:]:
        if asyncio.iscoroutinefunction(test_func):
            await test_func()
        else:
            test_func()
    
    # Print summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    print(f"Total Tests: {test_results['summary']['total']}")
    print(f"Passed: {test_results['summary']['passed']}")
    print(f"Failed: {test_results['summary']['failed']}")
    
    success_rate = (test_results['summary']['passed'] / test_results['summary']['total'] * 100) if test_results['summary']['total'] > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Save results to file
    with open("test_llm_results.json", "w") as f:
        json.dump(test_results, f, indent=2)
    print(f"\nDetailed results saved to: test_llm_results.json")
    
    if test_results['summary']['failed'] > 0:
        print("\n⚠️  Some tests failed. Please check the details above.")
        return False
    else:
        print("\n✅ All tests passed successfully!")
        return True

if __name__ == "__main__":
    # Check Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Run tests
    success = asyncio.run(run_all_tests())
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)