#!/usr/bin/env python3
"""
Test Relationship Graph Builder - Phase 2.5
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from app.services.relationship_graph import RelationshipGraphBuilder
from app.services.database_service import get_database_service
from app.services.connection_pool import ConnectionPoolManager

def test_graph_builder():
    """Test relationship graph builder"""
    print("=" * 60)
    print("Testing Relationship Graph Builder")
    print("=" * 60)
    
    # Setup database connection
    db_service = get_database_service()
    
    # Create test connection
    conn_id = db_service.add_connection(
        name="Test Graph Database",
        host="172.17.12.76",
        port=5432,
        database="postgres",
        username="myuser",
        password="myuser01"
    )
    print(f"✅ Created test connection: {conn_id}")
    
    # Create connection pool
    pool_manager = ConnectionPoolManager()
    pool_manager.create_pool(conn_id)
    
    # First, run schema analysis to populate cache
    from app.services.schema_analyzer import SchemaAnalyzer
    analyzer = SchemaAnalyzer()
    print("\n⏳ Running schema analysis to populate cache...")
    analyzer.analyze_database_schema(conn_id, deep_analysis=False)
    
    # Initialize graph builder
    graph_builder = RelationshipGraphBuilder()
    
    print("\n🔨 Building relationship graph...")
    graph = graph_builder.build_graph(conn_id)
    
    print(f"✅ Graph built with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
    
    # Test join path finding
    print("\n🔍 Testing Join Path Finding:")
    print("-" * 40)
    
    test_paths = [
        ("users", "orders"),
        ("users", "order_items"),
        ("products", "orders")
    ]
    
    for from_table, to_table in test_paths:
        try:
            path = graph_builder.find_join_path(from_table, to_table)
            if path:
                print(f"\n  Path from '{from_table}' to '{to_table}':")
                for i, step in enumerate(path, 1):
                    print(f"    Step {i}: {step['from_table']} -> {step['to_table']}")
                    print(f"            ON {step['from_table']}.{step['from_column']} = {step['to_table']}.{step['to_column']}")
            else:
                print(f"\n  ❌ No path found from '{from_table}' to '{to_table}'")
        except Exception as e:
            print(f"\n  ❌ Error finding path from '{from_table}' to '{to_table}': {e}")
    
    # Test related tables
    print("\n🔗 Testing Related Tables Discovery:")
    print("-" * 40)
    
    for table in ["users", "orders"]:
        try:
            related = graph_builder.find_related_tables(table, depth=2)
            print(f"\n  Tables related to '{table}':")
            print(f"    Directly: {', '.join(related['directly_related']) if related['directly_related'] else 'None'}")
            print(f"    Indirectly (depth=2): {', '.join(related['indirectly_related']) if related['indirectly_related'] else 'None'}")
        except Exception as e:
            print(f"\n  ❌ Error finding related tables for '{table}': {e}")
    
    # Analyze graph metrics
    print("\n📊 Graph Metrics:")
    print("-" * 40)
    
    metrics = graph_builder.analyze_graph_metrics()
    print(f"  Total Nodes: {metrics['total_nodes']}")
    print(f"  Total Edges: {metrics['total_edges']}")
    print(f"  Is Connected: {metrics['is_connected']}")
    print(f"  Average Degree: {metrics['average_degree']:.2f}")
    print(f"  Density: {metrics['density']:.4f}")
    print(f"  Has Cycles: {metrics['has_cycles']}")
    
    if metrics['hub_tables']:
        print("\n  Hub Tables (most connected):")
        for table, connections in metrics['hub_tables'][:3]:
            print(f"    - {table}: {connections} connections")
    
    if metrics['isolated_tables']:
        print("\n  Isolated Tables (no connections):")
        for table in metrics['isolated_tables']:
            print(f"    - {table}")
    
    if metrics.get('most_central_tables'):
        print("\n  Most Central Tables (betweenness):")
        for table, score in metrics['most_central_tables'][:3]:
            print(f"    - {table}: {score:.3f}")
    
    # Test join complexity
    print("\n🔀 Testing Join Complexity:")
    print("-" * 40)
    
    test_joins = [
        ["users", "orders"],
        ["users", "products"],
        ["users", "orders", "order_items", "products"]
    ]
    
    for tables in test_joins:
        complexity = graph_builder.get_join_complexity(tables)
        print(f"\n  Joining {', '.join(tables)}:")
        print(f"    Complexity: {complexity['complexity']}")
        print(f"    Tables involved: {complexity['tables_involved']}")
        print(f"    Join count: {complexity['join_count']}")
        if complexity['intermediate_tables'] > 0:
            print(f"    Intermediate tables needed: {complexity['intermediate_tables']}")
    
    # Test join order suggestion
    print("\n📋 Testing Join Order Suggestion:")
    print("-" * 40)
    
    tables_to_join = ["order_items", "users", "products", "orders"]
    suggested_order = graph_builder.suggest_join_order(tables_to_join)
    print(f"  Original order: {', '.join(tables_to_join)}")
    print(f"  Suggested order: {', '.join(suggested_order)}")
    
    # Export graph
    print("\n💾 Exporting Graph:")
    print("-" * 40)
    
    graph_json = graph_builder.export_graph('json')
    graph_data = json.loads(graph_json)
    print(f"  Graph exported to JSON format")
    print(f"  Nodes in export: {len(graph_data['nodes'])}")
    print(f"  Links in export: {len(graph_data['links'])}")
    
    # Save to file
    with open('relationship_graph.json', 'w') as f:
        f.write(graph_json)
    print(f"  ✅ Graph saved to: relationship_graph.json")
    
    # Get visualization data
    viz_data = graph_builder.visualize_graph_stats()
    with open('graph_visualization.json', 'w') as f:
        json.dump(viz_data, f, indent=2)
    print(f"  ✅ Visualization data saved to: graph_visualization.json")
    
    return True

if __name__ == "__main__":
    try:
        success = test_graph_builder()
        if success:
            print("\n" + "=" * 60)
            print("🎉 Relationship Graph Builder Test Completed!")
            print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()