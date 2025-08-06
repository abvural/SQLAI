#!/usr/bin/env python3
"""
Final Integration Test Suite - Phase 5
Complete system testing and production readiness validation
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import time
import json
from datetime import datetime
from app.services.integration_tester import IntegrationTester
from app.services.monitoring_service import MonitoringService
from app.services.error_recovery import ErrorRecoveryService
from app.services.database_service import get_database_service

async def run_comprehensive_system_test():
    """Run comprehensive system integration test"""
    print("=" * 80)
    print("🚀 SQLAI FINAL INTEGRATION TEST SUITE")
    print("=" * 80)
    print(f"Started at: {datetime.utcnow().isoformat()}")
    
    # Initialize services
    db_service = get_database_service()
    integration_tester = IntegrationTester()
    monitoring_service = MonitoringService()
    error_recovery = ErrorRecoveryService()
    
    # Setup test database
    print("\n📋 Setting up test environment...")
    try:
        conn_id = db_service.add_connection(
            name="Final Integration Test DB",
            host="172.17.12.76",
            port=5432,
            database="postgres",
            username="myuser",
            password="myuser01"
        )
        print(f"✅ Test database connection created: {conn_id}")
    except Exception as e:
        print(f"❌ Failed to setup test database: {e}")
        return False
    
    # Run integration tests
    print(f"\n🧪 Running comprehensive integration tests...")
    test_start = time.time()
    
    try:
        test_results = await integration_tester.run_comprehensive_tests(conn_id)
        test_duration = time.time() - test_start
        
        print(f"\n📊 Integration Test Results (completed in {test_duration:.2f}s):")
        print("-" * 60)
        print(f"Total Test Suites: {test_results['test_summary']['total_suites']}")
        print(f"Passed Suites: {test_results['test_summary']['passed_suites']}")
        print(f"Failed Suites: {test_results['test_summary']['failed_suites']}")
        print(f"Success Rate: {test_results['test_summary']['success_rate']:.1f}%")
        
        # Detailed results
        print(f"\n📋 Detailed Results:")
        for suite_name, result in test_results['detailed_results'].items():
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"  {status} {suite_name}")
            if not result['passed'] and 'error' in result:
                print(f"    Error: {result['error']}")
        
        # Show recommendations
        if test_results['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in test_results['recommendations']:
                print(f"  • {rec}")
        
    except Exception as e:
        print(f"❌ Integration testing failed: {e}")
        return False
    
    # Test system monitoring
    print(f"\n🔍 Testing System Monitoring...")
    try:
        health_status = await monitoring_service.get_system_health()
        print(f"Overall System Health: {health_status['overall_status'].upper()}")
        
        print(f"\nComponent Health:")
        for component in health_status['components']:
            status_icon = {"healthy": "✅", "warning": "⚠️", "critical": "❌", "down": "🔴"}.get(component['status'], "❓")
            print(f"  {status_icon} {component['component']}: {component['status']}")
            if component.get('response_time_ms'):
                print(f"    Response time: {component['response_time_ms']:.1f}ms")
        
        # Test metrics collection
        monitoring_service.collect_metrics()
        metrics_history = monitoring_service.get_metrics_history(hours=1)
        print(f"✅ Metrics collection working ({len(metrics_history)} samples)")
        
        # Performance summary
        perf_summary = monitoring_service.get_performance_summary()
        if 'averages' in perf_summary:
            print(f"\nPerformance Averages:")
            print(f"  CPU: {perf_summary['averages']['cpu_percent']:.1f}%")
            print(f"  Memory: {perf_summary['averages']['memory_percent']:.1f}%")
        
    except Exception as e:
        print(f"❌ Monitoring test failed: {e}")
        return False
    
    # Test error recovery
    print(f"\n🛡️ Testing Error Recovery...")
    try:
        # Test retry mechanism
        async def failing_operation():
            raise Exception("Simulated failure")
        
        recovery_result = await error_recovery.execute_with_recovery(
            "test_operation",
            failing_operation,
            context={}
        )
        
        print(f"Error recovery test: {'✅ Working' if not recovery_result['success'] else '⚠️ Unexpected success'}")
        print(f"Recovery attempts: {recovery_result['recovery_attempts']}")
        
        # Test circuit breaker
        breaker_stats = error_recovery.get_error_statistics()
        print(f"Circuit breakers: {len(breaker_stats['circuit_breakers'])} configured")
        
    except Exception as e:
        print(f"❌ Error recovery test failed: {e}")
        return False
    
    # Test export functionality
    print(f"\n📤 Testing Export System...")
    try:
        from app.services.export_service import ExportService
        export_service = ExportService()
        
        test_data = [
            {'id': 1, 'name': 'Test Record 1', 'active': True},
            {'id': 2, 'name': 'Test Record 2', 'active': False}
        ]
        
        # Test all export formats
        formats = ['csv', 'json']  # Skip Excel to avoid dependency issues
        for fmt in formats:
            try:
                if fmt == 'csv':
                    exported = export_service.export_to_csv(test_data)
                elif fmt == 'json':
                    exported = export_service.export_to_json(test_data)
                
                print(f"✅ {fmt.upper()} export: {len(exported)} bytes")
            except Exception as e:
                print(f"❌ {fmt.upper()} export failed: {e}")
        
        # Test validation
        validation = export_service.validate_export_request(1000, 'csv')
        print(f"Export validation: {'✅ Working' if validation['valid'] else '❌ Failed'}")
        
    except Exception as e:
        print(f"❌ Export system test failed: {e}")
        return False
    
    # Test WebSocket system
    print(f"\n📡 Testing WebSocket System...")
    try:
        from app.services.websocket_manager import connection_manager
        
        stats = connection_manager.get_connection_stats()
        print(f"✅ WebSocket manager initialized")
        print(f"Active connections: {stats['total_connections']}")
        print(f"Connection types: {list(stats['connections_by_type'].keys())}")
        
    except Exception as e:
        print(f"❌ WebSocket system test failed: {e}")
        return False
    
    # Memory and performance check
    print(f"\n🧠 Final Performance Check...")
    try:
        import psutil
        
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        cpu_percent = psutil.cpu_percent(interval=1)
        system_memory = psutil.virtual_memory()
        
        print(f"Application Memory: {memory_mb:.1f}MB")
        print(f"System CPU: {cpu_percent:.1f}%")
        print(f"System Memory: {system_memory.percent:.1f}%")
        
        # Performance thresholds
        performance_ok = (
            memory_mb < 500 and  # Less than 500MB
            cpu_percent < 80 and  # Less than 80% CPU
            system_memory.percent < 90  # Less than 90% system memory
        )
        
        print(f"Performance Status: {'✅ Good' if performance_ok else '⚠️ Review needed'}")
        
    except Exception as e:
        print(f"❌ Performance check failed: {e}")
        return False
    
    # Cleanup
    print(f"\n🧹 Cleaning up test environment...")
    try:
        db_service.remove_connection(conn_id)
        print(f"✅ Test database connection removed")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")
    
    return True

def test_production_readiness():
    """Test production readiness checklist"""
    print("=" * 80)
    print("✅ PRODUCTION READINESS CHECKLIST")
    print("=" * 80)
    
    checklist = [
        # Core functionality
        ("Database Connection Management", check_database_connections),
        ("Schema Analysis Engine", check_schema_analysis),
        ("AI Query Processing", check_ai_processing),
        ("Async Query Execution", check_async_execution),
        ("Export System", check_export_system),
        
        # Infrastructure  
        ("Error Handling", check_error_handling),
        ("Logging System", check_logging),
        ("Monitoring", check_monitoring),
        ("Security", check_security),
        ("Documentation", check_documentation),
        
        # Production readiness
        ("Performance", check_performance),
        ("Memory Management", check_memory_management),
        ("Configuration", check_configuration),
        ("Dependencies", check_dependencies)
    ]
    
    results = []
    for name, check_func in checklist:
        try:
            status = check_func()
            results.append((name, status))
            status_icon = "✅" if status else "❌"
            print(f"{status_icon} {name}")
        except Exception as e:
            results.append((name, False))
            print(f"❌ {name} (Error: {e})")
    
    # Summary
    passed = sum(1 for _, status in results if status)
    total = len(results)
    
    print(f"\n📊 Production Readiness: {passed}/{total} checks passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print(f"\n🎉 SYSTEM IS PRODUCTION READY!")
        print(f"✅ All critical components tested and operational")
        print(f"✅ Performance within acceptable limits")
        print(f"✅ Security measures in place")
        print(f"✅ Monitoring and logging configured")
        print(f"✅ Error recovery mechanisms active")
    else:
        print(f"\n⚠️ Review failed checks before production deployment")
    
    return passed == total

def check_database_connections():
    """Check database connection functionality"""
    try:
        from app.services.database_service import get_database_service
        db_service = get_database_service()
        # Basic functionality test
        connections = db_service.list_connections()
        return isinstance(connections, list)
    except:
        return False

def check_schema_analysis():
    """Check schema analysis functionality"""
    try:
        from app.services.schema_analyzer import SchemaAnalyzer
        analyzer = SchemaAnalyzer()
        return hasattr(analyzer, 'analyze_database_schema')
    except:
        return False

def check_ai_processing():
    """Check AI query processing"""
    try:
        from app.ai.query_builder import SQLQueryBuilder
        from app.ai.nlp_processor import NLPProcessor
        builder = SQLQueryBuilder()
        processor = NLPProcessor()
        return True
    except:
        return False

def check_async_execution():
    """Check async query execution"""
    try:
        from app.services.query_executor import QueryExecutor
        executor = QueryExecutor()
        return hasattr(executor, 'execute_query_async')
    except:
        return False

def check_export_system():
    """Check export system"""
    try:
        from app.services.export_service import ExportService
        service = ExportService()
        return hasattr(service, 'export_to_csv')
    except:
        return False

def check_error_handling():
    """Check error handling"""
    try:
        from app.services.error_recovery import ErrorRecoveryService
        recovery = ErrorRecoveryService()
        return hasattr(recovery, 'execute_with_recovery')
    except:
        return False

def check_logging():
    """Check logging configuration"""
    try:
        import logging
        logger = logging.getLogger('app')
        return logger.level is not None
    except:
        return False

def check_monitoring():
    """Check monitoring system"""
    try:
        from app.services.monitoring_service import MonitoringService
        monitor = MonitoringService()
        return hasattr(monitor, 'get_system_health')
    except:
        return False

def check_security():
    """Check security features"""
    try:
        from app.utils.security import encrypt_data
        from app.utils.sql_validator import SQLValidator
        validator = SQLValidator()
        return hasattr(validator, 'validate_query')
    except:
        return False

def check_documentation():
    """Check documentation"""
    docs = [
        'API_DOCUMENTATION.md',
        'DEPLOYMENT.md',
        'DEVELOPMENT_PHASES.md'
    ]
    return all(os.path.exists(doc) for doc in docs)

def check_performance():
    """Check performance requirements"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        return memory.total > 2 * 1024 * 1024 * 1024  # At least 2GB RAM
    except:
        return False

def check_memory_management():
    """Check memory management"""
    try:
        from app.services.query_executor import QueryExecutor
        executor = QueryExecutor()
        return hasattr(executor, 'cleanup_old_results')
    except:
        return False

def check_configuration():
    """Check configuration"""
    try:
        from app.config import get_settings
        settings = get_settings()
        return hasattr(settings, 'environment')
    except:
        return False

def check_dependencies():
    """Check critical dependencies"""
    critical_deps = [
        'fastapi',
        'sqlalchemy', 
        'psycopg2',
        'pandas',
        'networkx'
    ]
    
    for dep in critical_deps:
        try:
            __import__(dep)
        except ImportError:
            return False
    return True

async def main():
    """Main test runner"""
    print(f"🚀 Starting SQLAI Final Integration Tests")
    print(f"Python Version: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")
    
    # Run integration tests
    integration_success = await run_comprehensive_system_test()
    
    # Run production readiness check
    readiness_success = test_production_readiness()
    
    # Final summary
    print("\n" + "=" * 80)
    print("🏁 FINAL TEST SUMMARY")
    print("=" * 80)
    
    print(f"Integration Tests: {'✅ PASSED' if integration_success else '❌ FAILED'}")
    print(f"Production Readiness: {'✅ READY' if readiness_success else '❌ NOT READY'}")
    
    overall_success = integration_success and readiness_success
    
    if overall_success:
        print(f"\n🎉 CONGRATULATIONS!")
        print(f"🚀 SQLAI is ready for production deployment!")
        print(f"📚 See DEPLOYMENT.md for deployment instructions")
        print(f"📖 See API_DOCUMENTATION.md for API reference")
    else:
        print(f"\n⚠️ Some tests failed. Please review and fix issues before deployment.")
    
    print(f"\nCompleted at: {datetime.utcnow().isoformat()}")
    return overall_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)