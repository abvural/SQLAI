"""
Dashboard API Routes
Main interface for database connections and overview
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.services.database_service import get_database_service
from app.services.schema_analyzer import SchemaAnalyzer
from app.services.query_executor import QueryExecutor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

# Global instances
db_service = get_database_service()
schema_analyzer = SchemaAnalyzer()
query_executor = QueryExecutor()

@router.get("/overview")
async def get_dashboard_overview():
    """Get dashboard overview with system statistics"""
    try:
        # Get database connections
        connections = db_service.list_connections()
        
        # Get recent query history
        history = query_executor.get_query_history(limit=10)
        
        # Calculate statistics
        total_databases = len(connections)
        active_connections = len([c for c in connections if c['status'] == 'connected'])
        
        recent_queries = len([h for h in history 
                            if datetime.fromisoformat(h['created_at']) > 
                            datetime.utcnow() - timedelta(days=1)])
        
        return {
            "statistics": {
                "total_databases": total_databases,
                "active_connections": active_connections,
                "recent_queries": recent_queries,
                "system_status": "healthy"
            },
            "connections": connections,
            "recent_history": history[:5],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/database/{db_id}/summary")
async def get_database_summary(db_id: str):
    """Get summary for a specific database"""
    try:
        # Get connection info
        connection = db_service.get_connection(db_id)
        if not connection:
            raise HTTPException(status_code=404, detail="Database not found")
        
        # Get schema analysis
        schema_info = schema_analyzer.analyze_database_schema(db_id, deep_analysis=False)
        
        # Calculate summary statistics
        summary = {
            "connection": {
                "id": db_id,
                "name": connection['name'],
                "host": connection['host'],
                "database": connection['database'],
                "status": connection['status']
            },
            "schema_stats": {},
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
        if schema_info:
            total_tables = 0
            total_columns = 0
            total_relationships = 0
            
            for schema_name, schema_data in schema_info.get('schemas', {}).items():
                tables = schema_data.get('tables', [])
                total_tables += len(tables)
                
                for table in tables:
                    total_columns += len(table.get('columns', []))
                
                total_relationships += len(schema_data.get('relationships', []))
            
            summary['schema_stats'] = {
                "total_schemas": len(schema_info.get('schemas', {})),
                "total_tables": total_tables,
                "total_columns": total_columns,
                "total_relationships": total_relationships,
                "largest_table": schema_info.get('insights', {}).get('largest_table'),
                "most_connected_table": schema_info.get('insights', {}).get('hub_tables', [{}])[0] if schema_info.get('insights', {}).get('hub_tables') else None
            }
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get database summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/database/{db_id}/visualization")
async def get_database_visualization(db_id: str):
    """Get visualization data for database schema"""
    try:
        from app.services.relationship_graph import RelationshipGraphBuilder
        
        # Build relationship graph
        graph_builder = RelationshipGraphBuilder()
        graph = graph_builder.build_graph(db_id)
        
        # Get visualization data
        viz_data = graph_builder.visualize_graph_stats()
        
        return {
            "visualization": viz_data,
            "metrics": graph_builder.analyze_graph_metrics(),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get visualization data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def get_system_health():
    """Get system health status"""
    try:
        # Check database connections
        connections = db_service.list_connections()
        healthy_connections = 0
        
        for conn in connections:
            try:
                # Quick health check
                if db_service.test_connection(conn['id']):
                    healthy_connections += 1
            except:
                pass
        
        # Check memory usage (basic)
        import psutil
        memory_percent = psutil.virtual_memory().percent
        
        # System health assessment
        health_status = "healthy"
        if memory_percent > 90:
            health_status = "critical"
        elif memory_percent > 75:
            health_status = "warning"
        
        return {
            "status": health_status,
            "connections": {
                "total": len(connections),
                "healthy": healthy_connections,
                "unhealthy": len(connections) - healthy_connections
            },
            "system": {
                "memory_usage_percent": memory_percent,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics")
async def get_analytics():
    """Get usage analytics and metrics"""
    try:
        # Get query history for analytics
        history = query_executor.get_query_history(limit=1000)
        
        # Analyze query patterns
        total_queries = len(history)
        successful_queries = len([h for h in history if h['status'] == 'completed'])
        failed_queries = len([h for h in history if h['status'] == 'failed'])
        
        # Query execution times
        execution_times = [h['execution_time'] for h in history if h['execution_time']]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Most active databases
        db_usage = {}
        for h in history:
            db_id = h['database_id']
            db_usage[db_id] = db_usage.get(db_id, 0) + 1
        
        most_used_databases = sorted(db_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "query_statistics": {
                "total_queries": total_queries,
                "successful_queries": successful_queries,
                "failed_queries": failed_queries,
                "success_rate": (successful_queries / total_queries * 100) if total_queries > 0 else 0,
                "average_execution_time": avg_execution_time
            },
            "database_usage": {
                "most_used": most_used_databases
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))