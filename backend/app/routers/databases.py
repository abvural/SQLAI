from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import psycopg2

from app.services.database_service import get_database_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/databases")

class DatabaseConnection(BaseModel):
    """Database connection model"""
    name: str = Field(..., description="Database display name")
    host: str = Field(..., description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(..., description="Database name")
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    ssl_mode: Optional[str] = Field(default="prefer", description="SSL mode")

class DatabaseConnectionResponse(BaseModel):
    """Database connection response"""
    id: str
    name: str
    host: str
    port: int
    database: str
    status: str
    last_connected: Optional[datetime]
    schema_analyzed: bool

class TestConnectionResponse(BaseModel):
    """Test connection response"""
    success: bool
    message: str
    version: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

@router.post("/connect", response_model=TestConnectionResponse)
async def test_connection(connection: DatabaseConnection):
    """Test database connection and optionally save it"""
    try:
        conn_string = (
            f"host={connection.host} "
            f"port={connection.port} "
            f"dbname={connection.database} "
            f"user={connection.username} "
            f"password={connection.password} "
            f"sslmode={connection.ssl_mode}"
        )
        
        conn = psycopg2.connect(conn_string, connect_timeout=5)
        cursor = conn.cursor()
        
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        
        cursor.execute("SELECT current_database(), current_user, now()")
        db_info = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        logger.info(f"Successfully connected to {connection.host}:{connection.port}/{connection.database}")
        
        # Save connection with encrypted credentials
        db_service = get_database_service()
        conn_id = db_service.add_connection(
            name=connection.name,
            host=connection.host,
            port=connection.port,
            database=connection.database,
            username=connection.username,
            password=connection.password,
            ssl_mode=connection.ssl_mode
        )
        
        # Update connection status
        db_service.update_connection_status(conn_id, "connected", datetime.utcnow())
        
        return TestConnectionResponse(
            success=True,
            message="Connection successful and saved",
            version=version,
            details={
                "connection_id": conn_id,
                "database": db_info[0],
                "user": db_info[1],
                "server_time": db_info[2].isoformat() if db_info[2] else None
            }
        )
        
    except Exception as e:
        logger.error(f"Connection failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection failed: {str(e)}"
        )

@router.get("/list", response_model=List[DatabaseConnectionResponse])
async def list_databases():
    """List all registered databases"""
    db_service = get_database_service()
    connections = db_service.list_connections()
    
    return [
        DatabaseConnectionResponse(
            id=conn['id'],
            name=conn['name'],
            host=conn['host'],
            port=conn['port'],
            database=conn['database'],
            status=conn.get('status', 'unknown'),
            last_connected=datetime.fromisoformat(conn['last_connected']) if conn.get('last_connected') else None,
            schema_analyzed=conn.get('schema_analyzed', False)
        )
        for conn in connections
    ]

@router.post("/analyze/{db_id}")
async def analyze_database(db_id: str):
    """Start schema analysis for a database"""
    # TODO: Implement schema analysis
    return {
        "message": f"Analysis started for database {db_id}",
        "job_id": "analysis_123",
        "status": "pending"
    }

@router.get("/{db_id}/status")
async def get_database_status(db_id: str):
    """Get database analysis status"""
    # TODO: Implement status checking
    return {
        "db_id": db_id,
        "status": "pending",
        "progress": 0,
        "message": "Analysis not started"
    }

@router.delete("/{db_id}")
async def remove_database(db_id: str):
    """Remove a database connection"""
    db_service = get_database_service()
    
    if not db_service.delete_connection(db_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database {db_id} not found"
        )
    
    return {"message": f"Database {db_id} removed successfully"}