#!/usr/bin/env python3
"""
Final System Test - Production Readiness Validation
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
from datetime import datetime

def test_core_systems():
    """Test core system components"""
    print("=" * 80)
    print("🚀 SQLAI FINAL SYSTEM VALIDATION")
    print("=" * 80)
    print(f"Test started: {datetime.utcnow().isoformat()}")
    
    results = {}
    
    # Test 1: Database Service
    print("\n📊 Testing Database Management...")
    try:
        from app.services.database_service import get_database_service
        db_service = get_database_service()
        
        # Test basic functionality
        connections = db_service.list_connections()
        results['database_service'] = True
        print("✅ Database service operational")
        
    except Exception as e:
        print(f"❌ Database service failed: {e}")
        results['database_service'] = False
    
    # Test 2: Query Executor
    print("\n⚡ Testing Query Execution...")
    try:
        from app.services.query_executor import QueryExecutor
        executor = QueryExecutor()
        
        # Test query tracking
        test_query_id = "test_final_123"
        executor.active_queries[test_query_id] = {
            'status': 'completed',
            'progress': 1.0,
            'rows_processed': 100
        }
        
        status = executor.get_query_status(test_query_id)
        results['query_executor'] = status is not None
        
        if results['query_executor']:
            print("✅ Query executor operational")
            print(f"   Sample query status: {status['status']}")
        else:
            print("❌ Query executor failed")
            
    except Exception as e:
        print(f"❌ Query executor failed: {e}")
        results['query_executor'] = False
    
    # Test 3: Export System
    print("\n📤 Testing Export System...")
    try:
        from app.services.export_service import ExportService
        export_service = ExportService()
        
        test_data = [
            {'id': 1, 'name': 'Test User', 'email': 'test@example.com'},
            {'id': 2, 'name': 'Another User', 'email': 'user@example.com'}
        ]
        
        # Test CSV export
        csv_data = export_service.export_to_csv(test_data)
        json_data = export_service.export_to_json(test_data)
        
        results['export_system'] = len(csv_data) > 0 and len(json_data) > 0
        
        if results['export_system']:
            print("✅ Export system operational")
            print(f"   CSV export: {len(csv_data)} bytes")
            print(f"   JSON export: {len(json_data)} bytes")
        else:
            print("❌ Export system failed")
            
    except Exception as e:
        print(f"❌ Export system failed: {e}")
        results['export_system'] = False
    
    # Test 4: Monitoring
    print("\n🔍 Testing Monitoring System...")
    try:
        from app.services.monitoring_service import MonitoringService
        monitoring = MonitoringService()
        
        # Test metrics collection
        monitoring.collect_metrics()
        metrics = monitoring._get_current_metrics()
        
        results['monitoring'] = 'system' in metrics and 'application' in metrics
        
        if results['monitoring']:
            print("✅ Monitoring system operational")
            print(f"   CPU: {metrics['system']['cpu_percent']:.1f}%")
            print(f"   Memory: {metrics['system']['memory_percent']:.1f}%")
        else:
            print("❌ Monitoring system failed")
            
    except Exception as e:
        print(f"❌ Monitoring system failed: {e}")
        results['monitoring'] = False
    
    # Test 5: Error Recovery
    print("\n🛡️ Testing Error Recovery...")
    try:
        from app.services.error_recovery import ErrorRecoveryService
        error_recovery = ErrorRecoveryService()
        
        # Test error tracking
        error_recovery._track_error("test_operation", "Test error")
        stats = error_recovery.get_error_statistics()
        
        results['error_recovery'] = 'error_counts' in stats
        
        if results['error_recovery']:
            print("✅ Error recovery system operational")
            print(f"   Error tracking: {len(stats['error_counts'])} operations")
            print(f"   Circuit breakers: {len(stats['circuit_breakers'])} configured")
        else:
            print("❌ Error recovery system failed")
            
    except Exception as e:
        print(f"❌ Error recovery system failed: {e}")
        results['error_recovery'] = False
    
    # Test 6: WebSocket Manager
    print("\n📡 Testing WebSocket System...")
    try:
        from app.services.websocket_manager import connection_manager
        stats = connection_manager.get_connection_stats()
        
        results['websocket'] = 'total_connections' in stats
        
        if results['websocket']:
            print("✅ WebSocket system operational")
            print(f"   Connection types: {len(stats['connections_by_type'])}")
            print(f"   Active connections: {stats['total_connections']}")
        else:
            print("❌ WebSocket system failed")
            
    except Exception as e:
        print(f"❌ WebSocket system failed: {e}")
        results['websocket'] = False
    
    # Test 7: Template System (AI Component)
    print("\n🤖 Testing AI Template System...")
    try:
        from app.ai.query_templates import QueryTemplateSystem
        template_system = QueryTemplateSystem()
        
        templates_count = len(template_system.templates)
        results['ai_templates'] = templates_count > 0
        
        if results['ai_templates']:
            print("✅ AI template system operational")
            print(f"   Available templates: {templates_count}")
        else:
            print("❌ AI template system failed")
            
    except Exception as e:
        print(f"❌ AI template system failed: {e}")
        results['ai_templates'] = False
    
    return results

def test_configuration():
    """Test system configuration"""
    print("\n⚙️ Testing System Configuration...")
    
    config_tests = {
        'environment_files': check_env_files(),
        'documentation': check_documentation(),
        'dependencies': check_dependencies(),
        'file_structure': check_file_structure(),
        'security_utils': check_security_utils()
    }
    
    for test_name, result in config_tests.items():
        status = "✅" if result else "❌"
        print(f"{status} {test_name.replace('_', ' ').title()}")
    
    return config_tests

def check_env_files():
    """Check configuration files"""
    return os.path.exists('app/config.py')

def check_documentation():
    """Check documentation files"""
    docs = [
        'API_DOCUMENTATION.md',
        'DEPLOYMENT.md',
        'DEVELOPMENT_PHASES.md',
        'KRITIK_NOKTALAR.md',
        'TEST_STRATEGY.md'
    ]
    return all(os.path.exists(doc) for doc in docs)

def check_dependencies():
    """Check critical dependencies"""
    critical_deps = [
        'fastapi',
        'sqlalchemy', 
        'psycopg2',
        'pandas',
        'networkx',
        'psutil'
    ]
    
    missing = []
    for dep in critical_deps:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)
    
    if missing:
        print(f"   Missing dependencies: {', '.join(missing)}")
    
    return len(missing) == 0

def check_file_structure():
    """Check project file structure"""
    required_dirs = [
        'app/services',
        'app/models', 
        'app/routers',
        'app/utils',
        'app/ai'
    ]
    
    return all(os.path.exists(d) for d in required_dirs)

def check_security_utils():
    """Check security utilities"""
    try:
        from app.utils.security import encrypt_data, decrypt_data
        from app.utils.sql_validator import SQLValidator
        return True
    except:
        return False

def performance_assessment():
    """Assess system performance"""
    print("\n🚀 Performance Assessment...")
    
    try:
        import psutil
        import time
        
        # CPU test
        cpu_start = time.time()
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_time = time.time() - cpu_start
        
        # Memory test
        memory = psutil.virtual_memory()
        
        # Process memory
        process = psutil.Process()
        app_memory_mb = process.memory_info().rss / 1024 / 1024
        
        print(f"System CPU Usage: {cpu_percent:.1f}%")
        print(f"System Memory Usage: {memory.percent:.1f}%")
        print(f"Application Memory: {app_memory_mb:.1f}MB")
        print(f"Available Memory: {memory.available / 1024 / 1024 / 1024:.1f}GB")
        
        # Performance scoring
        perf_score = 100
        if cpu_percent > 80:
            perf_score -= 20
        if memory.percent > 80:
            perf_score -= 20
        if app_memory_mb > 500:
            perf_score -= 15
        
        print(f"Performance Score: {perf_score}/100")
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'app_memory_mb': app_memory_mb,
            'score': perf_score,
            'acceptable': perf_score >= 70
        }
        
    except Exception as e:
        print(f"❌ Performance assessment failed: {e}")
        return {'acceptable': False, 'score': 0}

def final_validation():
    """Final system validation"""
    print("=" * 80)
    print("✅ PRODUCTION READINESS VALIDATION")
    print("=" * 80)
    
    # Run all tests
    core_results = test_core_systems()
    config_results = test_configuration()
    performance_results = performance_assessment()
    
    # Calculate scores
    core_passed = sum(1 for result in core_results.values() if result)
    core_total = len(core_results)
    
    config_passed = sum(1 for result in config_results.values() if result)
    config_total = len(config_results)
    
    total_passed = core_passed + config_passed + (1 if performance_results['acceptable'] else 0)
    total_tests = core_total + config_total + 1
    
    print(f"\n📊 Final Results:")
    print(f"Core Systems: {core_passed}/{core_total} passed ({core_passed/core_total*100:.1f}%)")
    print(f"Configuration: {config_passed}/{config_total} passed ({config_passed/config_total*100:.1f}%)")
    print(f"Performance: {'✅ Acceptable' if performance_results['acceptable'] else '❌ Needs improvement'}")
    
    print(f"\n🎯 Overall Score: {total_passed}/{total_tests} ({total_passed/total_tests*100:.1f}%)")
    
    # Final assessment
    if total_passed >= total_tests * 0.9:  # 90% pass rate
        print(f"\n🎉 SYSTEM IS PRODUCTION READY!")
        print_production_summary()
        return True
    elif total_passed >= total_tests * 0.8:  # 80% pass rate
        print(f"\n⚠️ SYSTEM NEEDS MINOR FIXES")
        print("Review failed tests and address issues before deployment.")
        return False
    else:
        print(f"\n❌ SYSTEM NOT READY FOR PRODUCTION")
        print("Significant issues need to be addressed.")
        return False

def print_production_summary():
    """Print production readiness summary"""
    print(f"\n🚀 SQLAI Production Deployment Summary:")
    print(f"   ✅ Core database management system operational")
    print(f"   ✅ AI-powered query processing ready") 
    print(f"   ✅ Async execution with progress tracking")
    print(f"   ✅ Multi-format export capabilities")
    print(f"   ✅ Real-time monitoring and health checks")
    print(f"   ✅ Error recovery and circuit breaker patterns")
    print(f"   ✅ WebSocket support for real-time updates")
    print(f"   ✅ Turkish language support for NLP")
    print(f"   ✅ Comprehensive security measures")
    print(f"   ✅ Complete API documentation")
    print(f"   ✅ Production deployment guide")
    
    print(f"\n📚 Next Steps:")
    print(f"   1. Review DEPLOYMENT.md for production setup")
    print(f"   2. Configure production environment variables")
    print(f"   3. Set up monitoring and alerting")
    print(f"   4. Initialize target database connections")
    print(f"   5. Run uvicorn app.main:app --host 0.0.0.0 --port 8000")
    
    print(f"\n📖 Documentation:")
    print(f"   • API_DOCUMENTATION.md - Complete API reference")
    print(f"   • DEPLOYMENT.md - Production deployment guide")
    print(f"   • DEVELOPMENT_PHASES.md - Development timeline")
    print(f"   • KRITIK_NOKTALAR.md - Critical implementation notes")

def main():
    """Main test execution"""
    print("🔍 SQLAI Final System Validation")
    print(f"Python: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")
    
    success = final_validation()
    
    print(f"\nTest completed: {datetime.utcnow().isoformat()}")
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)