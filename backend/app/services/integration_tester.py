"""
Integration Testing Service
End-to-end workflow testing and validation
"""
import logging
import asyncio
import time
import psutil
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from app.services.database_service import get_database_service
from app.services.schema_analyzer import SchemaAnalyzer
from app.services.query_executor import QueryExecutor
from app.ai.query_builder import SQLQueryBuilder
from app.services.export_service import ExportService
from app.services.websocket_manager import connection_manager

logger = logging.getLogger(__name__)

class IntegrationTester:
    """Comprehensive integration testing service"""
    
    def __init__(self):
        """Initialize integration tester"""
        self.db_service = get_database_service()
        self.schema_analyzer = SchemaAnalyzer()
        self.query_executor = QueryExecutor()
        self.query_builder = SQLQueryBuilder()
        self.export_service = ExportService()
        
        self.test_results = {
            'connection_tests': [],
            'schema_tests': [],
            'query_tests': [],
            'performance_tests': [],
            'security_tests': [],
            'export_tests': [],
            'memory_tests': []
        }
        
        logger.info("Integration Tester initialized")
    
    async def run_comprehensive_tests(self, db_id: str) -> Dict[str, Any]:
        """
        Run comprehensive integration tests
        
        Args:
            db_id: Database connection ID to test
            
        Returns:
            Complete test results
        """
        logger.info(f"Starting comprehensive integration tests for database: {db_id}")
        start_time = time.time()
        
        # Test suites
        test_suites = [
            ("Connection Tests", self.test_database_connection),
            ("Schema Analysis Tests", self.test_schema_analysis),
            ("Query Processing Tests", self.test_query_processing),
            ("Performance Tests", self.test_performance),
            ("Security Tests", self.test_security),
            ("Export Tests", self.test_export_functionality),
            ("Memory Management Tests", self.test_memory_management)
        ]
        
        results = {
            'test_summary': {
                'total_suites': len(test_suites),
                'passed_suites': 0,
                'failed_suites': 0,
                'start_time': datetime.utcnow().isoformat(),
                'database_id': db_id
            },
            'detailed_results': {},
            'recommendations': []
        }
        
        for suite_name, test_func in test_suites:
            logger.info(f"Running {suite_name}...")
            try:
                suite_result = await test_func(db_id)
                results['detailed_results'][suite_name] = suite_result
                
                if suite_result['passed']:
                    results['test_summary']['passed_suites'] += 1
                else:
                    results['test_summary']['failed_suites'] += 1
                    
            except Exception as e:
                logger.error(f"Test suite {suite_name} failed with error: {e}")
                results['detailed_results'][suite_name] = {
                    'passed': False,
                    'error': str(e),
                    'tests': []
                }
                results['test_summary']['failed_suites'] += 1
        
        # Calculate overall results
        total_time = time.time() - start_time
        results['test_summary']['total_time_seconds'] = total_time
        results['test_summary']['end_time'] = datetime.utcnow().isoformat()
        results['test_summary']['success_rate'] = (
            results['test_summary']['passed_suites'] / 
            results['test_summary']['total_suites'] * 100
        )
        
        # Generate recommendations
        results['recommendations'] = self._generate_recommendations(results)
        
        logger.info(f"Integration tests completed in {total_time:.2f}s")
        return results
    
    async def test_database_connection(self, db_id: str) -> Dict[str, Any]:
        """Test database connection functionality"""
        tests = []
        
        # Test 1: Basic connection
        try:
            connection_info = self.db_service.get_connection(db_id)
            success = connection_info is not None
            tests.append({
                'name': 'Get Connection Info',
                'passed': success,
                'message': 'Connection info retrieved' if success else 'Failed to get connection info'
            })
        except Exception as e:
            tests.append({
                'name': 'Get Connection Info',
                'passed': False,
                'error': str(e)
            })
        
        # Test 2: Connection health check
        try:
            is_healthy = self.db_service.test_connection(db_id)
            tests.append({
                'name': 'Connection Health Check',
                'passed': is_healthy,
                'message': 'Connection is healthy' if is_healthy else 'Connection health check failed'
            })
        except Exception as e:
            tests.append({
                'name': 'Connection Health Check',
                'passed': False,
                'error': str(e)
            })
        
        # Test 3: Connection pool
        try:
            from app.services.connection_pool import ConnectionPoolManager
            pool_manager = ConnectionPoolManager()
            pool = pool_manager.get_pool(db_id)
            success = pool is not None
            tests.append({
                'name': 'Connection Pool Access',
                'passed': success,
                'message': 'Connection pool accessible' if success else 'Connection pool not accessible'
            })
        except Exception as e:
            tests.append({
                'name': 'Connection Pool Access',
                'passed': False,
                'error': str(e)
            })
        
        passed = all(test['passed'] for test in tests)
        return {
            'passed': passed,
            'tests': tests,
            'summary': f"{sum(1 for t in tests if t['passed'])}/{len(tests)} connection tests passed"
        }
    
    async def test_schema_analysis(self, db_id: str) -> Dict[str, Any]:
        """Test schema analysis functionality"""
        tests = []
        
        # Test 1: Basic schema analysis
        try:
            schema_info = self.schema_analyzer.analyze_database_schema(db_id, deep_analysis=False)
            success = schema_info is not None and 'schemas' in schema_info
            tests.append({
                'name': 'Basic Schema Analysis',
                'passed': success,
                'message': f"Analyzed {len(schema_info.get('schemas', {}))} schemas" if success else 'Schema analysis failed'
            })
            
            if success:
                # Count tables and relationships
                total_tables = sum(len(s.get('tables', [])) for s in schema_info['schemas'].values())
                total_relationships = sum(len(s.get('relationships', [])) for s in schema_info['schemas'].values())
                
                tests.append({
                    'name': 'Schema Content Validation',
                    'passed': total_tables > 0,
                    'message': f"Found {total_tables} tables, {total_relationships} relationships"
                })
                
        except Exception as e:
            tests.append({
                'name': 'Basic Schema Analysis',
                'passed': False,
                'error': str(e)
            })
        
        # Test 2: Pattern recognition
        try:
            patterns = self.schema_analyzer.analyze_naming_patterns(db_id)
            success = patterns is not None
            tests.append({
                'name': 'Pattern Recognition',
                'passed': success,
                'message': f"Detected {len(patterns)} naming patterns" if success else 'Pattern recognition failed'
            })
        except Exception as e:
            tests.append({
                'name': 'Pattern Recognition',
                'passed': False,
                'error': str(e)
            })
        
        # Test 3: Relationship graph
        try:
            from app.services.relationship_graph import RelationshipGraphBuilder
            graph_builder = RelationshipGraphBuilder()
            graph = graph_builder.build_graph(db_id)
            success = graph.number_of_nodes() > 0
            tests.append({
                'name': 'Relationship Graph',
                'passed': success,
                'message': f"Built graph with {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges" if success else 'Graph building failed'
            })
        except Exception as e:
            tests.append({
                'name': 'Relationship Graph',
                'passed': False,
                'error': str(e)
            })
        
        passed = all(test['passed'] for test in tests)
        return {
            'passed': passed,
            'tests': tests,
            'summary': f"{sum(1 for t in tests if t['passed'])}/{len(tests)} schema tests passed"
        }
    
    async def test_query_processing(self, db_id: str) -> Dict[str, Any]:
        """Test query processing functionality"""
        tests = []
        
        # Test queries with different complexity levels
        test_queries = [
            {
                'name': 'Simple Natural Language Query',
                'query': 'Show all users',
                'expected_sql_contains': ['SELECT', 'users']
            },
            {
                'name': 'Aggregation Query',
                'query': 'Count total orders',
                'expected_sql_contains': ['COUNT', 'orders']
            },
            {
                'name': 'Direct SQL Execution',
                'query': "SELECT 'test' as message",
                'is_direct_sql': True
            }
        ]
        
        for test_query in test_queries:
            try:
                if test_query.get('is_direct_sql'):
                    # Test direct SQL execution
                    query_id = await self.query_executor.execute_query_async(
                        db_id, test_query['query']
                    )
                    
                    # Wait a moment for processing
                    await asyncio.sleep(0.1)
                    
                    status = self.query_executor.get_query_status(query_id)
                    success = status is not None
                    
                    tests.append({
                        'name': test_query['name'],
                        'passed': success,
                        'message': f"Query status: {status['status']}" if success else 'Query execution failed'
                    })
                else:
                    # Test natural language processing
                    result = self.query_builder.build_query(test_query['query'], db_id)
                    
                    if result['success']:
                        sql = result['sql']
                        confidence = result['confidence']
                        
                        # Check if expected SQL elements are present
                        contains_expected = all(
                            expected.lower() in sql.lower() 
                            for expected in test_query['expected_sql_contains']
                        )
                        
                        tests.append({
                            'name': test_query['name'],
                            'passed': contains_expected and confidence > 0.3,
                            'message': f"Generated SQL with {confidence:.1%} confidence"
                        })
                    else:
                        tests.append({
                            'name': test_query['name'],
                            'passed': False,
                            'message': result.get('error', 'Query building failed')
                        })
                        
            except Exception as e:
                tests.append({
                    'name': test_query['name'],
                    'passed': False,
                    'error': str(e)
                })
        
        passed = all(test['passed'] for test in tests)
        return {
            'passed': passed,
            'tests': tests,
            'summary': f"{sum(1 for t in tests if t['passed'])}/{len(tests)} query tests passed"
        }
    
    async def test_performance(self, db_id: str) -> Dict[str, Any]:
        """Test system performance"""
        tests = []
        
        # Test 1: Schema analysis performance
        start_time = time.time()
        try:
            self.schema_analyzer.analyze_database_schema(db_id, deep_analysis=False)
            analysis_time = time.time() - start_time
            
            # Should complete within 30 seconds for moderate schemas
            success = analysis_time < 30.0
            tests.append({
                'name': 'Schema Analysis Performance',
                'passed': success,
                'message': f"Completed in {analysis_time:.2f}s {'(✓ Good)' if success else '(⚠ Slow)'}"
            })
        except Exception as e:
            tests.append({
                'name': 'Schema Analysis Performance',
                'passed': False,
                'error': str(e)
            })
        
        # Test 2: Memory usage
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # Should use less than 500MB for basic operations
            success = memory_mb < 500
            tests.append({
                'name': 'Memory Usage',
                'passed': success,
                'message': f"Using {memory_mb:.1f}MB {'(✓ Efficient)' if success else '(⚠ High)'}"
            })
        except Exception as e:
            tests.append({
                'name': 'Memory Usage',
                'passed': False,
                'error': str(e)
            })
        
        # Test 3: Query response time
        start_time = time.time()
        try:
            # Simple query test
            result = self.query_builder.build_query("Show users", db_id)
            response_time = time.time() - start_time
            
            # Should respond within 5 seconds
            success = response_time < 5.0 and result.get('success', False)
            tests.append({
                'name': 'Query Response Time',
                'passed': success,
                'message': f"Response in {response_time:.2f}s {'(✓ Fast)' if success else '(⚠ Slow)'}"
            })
        except Exception as e:
            tests.append({
                'name': 'Query Response Time',
                'passed': False,
                'error': str(e)
            })
        
        passed = all(test['passed'] for test in tests)
        return {
            'passed': passed,
            'tests': tests,
            'summary': f"{sum(1 for t in tests if t['passed'])}/{len(tests)} performance tests passed"
        }
    
    async def test_security(self, db_id: str) -> Dict[str, Any]:
        """Test security features"""
        tests = []
        
        # Test 1: SQL Injection Prevention
        malicious_queries = [
            "'; DROP TABLE users; --",
            "' UNION SELECT password FROM admin --",
            "'; SELECT pg_sleep(10); --"
        ]
        
        injection_blocked = 0
        for malicious_query in malicious_queries:
            try:
                result = self.query_builder.build_query(malicious_query, db_id)
                if not result.get('success') or 'dangerous' in result.get('error', '').lower():
                    injection_blocked += 1
            except:
                injection_blocked += 1  # Exception means it was blocked
        
        tests.append({
            'name': 'SQL Injection Prevention',
            'passed': injection_blocked == len(malicious_queries),
            'message': f"Blocked {injection_blocked}/{len(malicious_queries)} injection attempts"
        })
        
        # Test 2: Credential Security
        try:
            connection = self.db_service.get_connection(db_id)
            # Check if password is encrypted (not in plain text)
            password_encrypted = 'password' not in str(connection).lower() or len(str(connection.get('password', ''))) > 20
            
            tests.append({
                'name': 'Credential Security',
                'passed': password_encrypted,
                'message': 'Credentials appear to be encrypted' if password_encrypted else 'Credentials may not be encrypted'
            })
        except Exception as e:
            tests.append({
                'name': 'Credential Security',
                'passed': False,
                'error': str(e)
            })
        
        # Test 3: Query Validation
        try:
            from app.utils.sql_validator import SQLValidator
            validator = SQLValidator()
            
            # Test valid query
            valid_sql = "SELECT id, name FROM users WHERE active = true"
            is_valid, errors = validator.validate_query(valid_sql)
            
            tests.append({
                'name': 'Query Validation',
                'passed': is_valid,
                'message': 'Query validator working correctly' if is_valid else f'Validation errors: {errors}'
            })
        except Exception as e:
            tests.append({
                'name': 'Query Validation',
                'passed': False,
                'error': str(e)
            })
        
        passed = all(test['passed'] for test in tests)
        return {
            'passed': passed,
            'tests': tests,
            'summary': f"{sum(1 for t in tests if t['passed'])}/{len(tests)} security tests passed"
        }
    
    async def test_export_functionality(self, db_id: str) -> Dict[str, Any]:
        """Test export functionality"""
        tests = []
        
        # Sample data for export testing
        test_data = [
            {'id': 1, 'name': 'Test User 1', 'email': 'test1@example.com', 'active': True},
            {'id': 2, 'name': 'Test User 2', 'email': 'test2@example.com', 'active': False}
        ]
        
        # Test different export formats
        formats = ['csv', 'json', 'sql']
        
        for export_format in formats:
            try:
                if export_format == 'csv':
                    result = self.export_service.export_to_csv(test_data)
                elif export_format == 'json':
                    result = self.export_service.export_to_json(test_data)
                elif export_format == 'sql':
                    result = self.export_service.export_to_sql_inserts(test_data, 'test_table')
                
                success = len(result) > 0
                tests.append({
                    'name': f'{export_format.upper()} Export',
                    'passed': success,
                    'message': f"Generated {len(result)} bytes" if success else 'Export failed'
                })
                
            except Exception as e:
                tests.append({
                    'name': f'{export_format.upper()} Export',
                    'passed': False,
                    'error': str(e)
                })
        
        # Test export validation
        try:
            validation = self.export_service.validate_export_request(1000, 'csv')
            tests.append({
                'name': 'Export Validation',
                'passed': validation['valid'],
                'message': 'Export validation working' if validation['valid'] else validation.get('error')
            })
        except Exception as e:
            tests.append({
                'name': 'Export Validation',
                'passed': False,
                'error': str(e)
            })
        
        passed = all(test['passed'] for test in tests)
        return {
            'passed': passed,
            'tests': tests,
            'summary': f"{sum(1 for t in tests if t['passed'])}/{len(tests)} export tests passed"
        }
    
    async def test_memory_management(self, db_id: str) -> Dict[str, Any]:
        """Test memory management"""
        tests = []
        
        # Test 1: Query result cleanup
        try:
            # Add test queries to memory
            test_queries = ['query1', 'query2', 'query3']
            for query_id in test_queries:
                self.query_executor.active_queries[query_id] = {
                    'status': 'completed',
                    'end_time': datetime.utcnow()
                }
                self.query_executor.query_results[query_id] = {'data': []}
            
            initial_count = len(self.query_executor.active_queries)
            
            # Test cleanup
            self.query_executor.cleanup_old_results(max_age_hours=0)
            
            final_count = len(self.query_executor.active_queries)
            cleaned = initial_count - final_count
            
            tests.append({
                'name': 'Query Cleanup',
                'passed': cleaned >= len(test_queries),
                'message': f"Cleaned {cleaned} old queries"
            })
            
        except Exception as e:
            tests.append({
                'name': 'Query Cleanup',
                'passed': False,
                'error': str(e)
            })
        
        # Test 2: Memory monitoring
        try:
            process = psutil.Process()
            memory_percent = psutil.virtual_memory().percent
            
            tests.append({
                'name': 'Memory Monitoring',
                'passed': memory_percent < 95,
                'message': f"System memory usage: {memory_percent:.1f}%"
            })
            
        except Exception as e:
            tests.append({
                'name': 'Memory Monitoring',
                'passed': False,
                'error': str(e)
            })
        
        passed = all(test['passed'] for test in tests)
        return {
            'passed': passed,
            'tests': tests,
            'summary': f"{sum(1 for t in tests if t['passed'])}/{len(tests)} memory tests passed"
        }
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check performance issues
        performance_result = results['detailed_results'].get('Performance Tests', {})
        if not performance_result.get('passed', True):
            recommendations.append("Consider optimizing query processing for better performance")
            recommendations.append("Monitor memory usage during peak operations")
        
        # Check security issues
        security_result = results['detailed_results'].get('Security Tests', {})
        if not security_result.get('passed', True):
            recommendations.append("Review and strengthen security measures")
            recommendations.append("Ensure all credentials are properly encrypted")
        
        # Check integration issues
        if results['test_summary']['success_rate'] < 80:
            recommendations.append("Address failing integration tests before production deployment")
        
        # General recommendations
        recommendations.extend([
            "Implement comprehensive logging for production monitoring",
            "Set up regular health checks and alerting",
            "Consider implementing connection pooling optimizations",
            "Plan for horizontal scaling if handling large datasets"
        ])
        
        return recommendations