#!/usr/bin/env python3
"""
Test Schema Analyzer - Phase 2.1
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from app.services.schema_analyzer import SchemaAnalyzer
from app.services.database_service import get_database_service

def test_schema_analysis():
    """Test comprehensive schema analysis"""
    print("=" * 60)
    print("Testing Schema Analyzer")
    print("=" * 60)
    
    # Setup database connection
    db_service = get_database_service()
    
    # Always create a fresh connection for testing
    conn_id = db_service.add_connection(
        name=f"Test Database Schema Analysis",
        host="172.17.12.76",
        port=5432,
        database="postgres",
        username="myuser",
        password="myuser01"
    )
    print(f"✅ Created test connection: {conn_id}")
    
    # Create the connection pool
    from app.services.connection_pool import ConnectionPoolManager
    pool_manager = ConnectionPoolManager()
    pool_manager.create_pool(conn_id)
    
    # Initialize analyzer
    analyzer = SchemaAnalyzer()
    
    print("\n⏳ Performing deep schema analysis...")
    analysis = analyzer.analyze_database_schema(conn_id, deep_analysis=True)
    
    print("\n📊 Analysis Results:")
    print("-" * 40)
    
    # Basic info
    print(f"Total Tables: {analysis['total_tables']}")
    print(f"Total Columns: {analysis['total_columns']}")
    print(f"Total Relationships: {analysis['total_relationships']}")
    print(f"Analysis Time: {analysis.get('analysis_time_seconds', 0):.2f} seconds")
    
    # Patterns
    if 'patterns' in analysis:
        print("\n🔍 Detected Patterns:")
        patterns = analysis['patterns']
        
        # Naming convention
        if 'naming_convention' in patterns:
            conv = patterns['naming_convention']
            print(f"  Naming Style: {conv.get('case_style', 'unknown')}")
            print(f"  Table Naming: {conv.get('table_naming', 'unknown')}")
            if conv.get('uses_prefixes'):
                print(f"  Common Prefix: {conv.get('common_prefix', '')}")
        
        # Entity types
        if 'entity_types' in patterns:
            print("\n  Identified Entity Types:")
            for entity_type, tables in patterns['entity_types'].items():
                print(f"    - {entity_type}: {', '.join(tables[:3])}")
        
        # Turkish usage
        if 'turkish_usage' in patterns:
            turkish = patterns['turkish_usage']
            if turkish.get('uses_turkish'):
                print(f"\n  Turkish Usage Detected:")
                print(f"    Turkish Tables: {len(turkish.get('turkish_tables', []))}")
                print(f"    Turkish Columns: {len(turkish.get('turkish_columns', []))}")
                print(f"    Mixed Language: {turkish.get('mixed_language', False)}")
    
    # Statistics
    if 'statistics' in analysis:
        print("\n📈 Statistics:")
        stats = analysis['statistics']
        print(f"  Avg Columns per Table: {stats.get('avg_columns_per_table', 0):.1f}")
        print(f"  Avg Relationships per Table: {stats.get('avg_relationships_per_table', 0):.1f}")
        print(f"  Data Size Estimate: {stats.get('data_size_estimate_mb', 0):.2f} MB")
        
        if stats.get('largest_tables'):
            print("\n  Largest Tables:")
            for table in stats['largest_tables'][:3]:
                print(f"    - {table['name']}: {table['row_count']} rows")
    
    # Insights
    if 'insights' in analysis:
        print(f"\n💡 Insights ({len(analysis['insights'])} found):")
        for insight in analysis['insights'][:5]:
            print(f"  [{insight['type'].upper()}] {insight['title']}")
            print(f"    {insight['description']}")
    
    # Recommendations
    if 'recommendations' in analysis:
        print(f"\n🎯 Recommendations ({len(analysis['recommendations'])} found):")
        for rec in analysis['recommendations'][:3]:
            print(f"  [{rec['priority'].upper()}] {rec['title']}")
            print(f"    {rec['description']}")
            if 'sql' in rec:
                print(f"    SQL: {rec['sql'][:80]}...")
    
    # Test importance scores
    print("\n⭐ Table Importance Scores:")
    scores = analyzer.get_table_importance_scores(conn_id)
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    for table, score in sorted_scores[:5]:
        print(f"  {table}: {score:.2f}")
    
    # Save analysis to file
    with open('schema_analysis_detailed.json', 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    print("\n✅ Full analysis saved to: schema_analysis_detailed.json")
    
    return True

if __name__ == "__main__":
    try:
        success = test_schema_analysis()
        if success:
            print("\n" + "=" * 60)
            print("🎉 Schema Analyzer Test Completed Successfully!")
            print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()