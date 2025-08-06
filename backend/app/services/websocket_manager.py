"""
WebSocket Manager for Real-time Updates
Handles real-time communication for query progress and notifications
"""
import logging
import json
import asyncio
from typing import Dict, Set, Any, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        # Active connections by type
        self.active_connections: Dict[str, Set[WebSocket]] = {
            'query_progress': set(),
            'system_notifications': set(),
            'schema_updates': set()
        }
        
        # Connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Message queues for different types
        self.message_queues: Dict[str, list] = {
            'query_progress': [],
            'system_notifications': [],
            'schema_updates': []
        }
        
        logger.info("WebSocket Connection Manager initialized")
    
    async def connect(self, websocket: WebSocket, connection_type: str, 
                     user_id: Optional[str] = None, query_id: Optional[str] = None):
        """
        Accept a new WebSocket connection
        
        Args:
            websocket: WebSocket connection
            connection_type: Type of connection (query_progress, system_notifications, etc.)
            user_id: User ID for the connection
            query_id: Query ID for query progress connections
        """
        await websocket.accept()
        
        if connection_type not in self.active_connections:
            self.active_connections[connection_type] = set()
        
        self.active_connections[connection_type].add(websocket)
        
        # Store metadata
        self.connection_metadata[websocket] = {
            'type': connection_type,
            'user_id': user_id,
            'query_id': query_id,
            'connected_at': datetime.utcnow(),
            'last_activity': datetime.utcnow()
        }
        
        logger.info(f"WebSocket connected: {connection_type} (user: {user_id}, query: {query_id})")
        
        # Send welcome message
        await self.send_message(websocket, {
            'type': 'connection_established',
            'message': f'Connected to {connection_type}',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection
        
        Args:
            websocket: WebSocket to disconnect
        """
        metadata = self.connection_metadata.get(websocket, {})
        connection_type = metadata.get('type', 'unknown')
        
        # Remove from active connections
        if connection_type in self.active_connections:
            self.active_connections[connection_type].discard(websocket)
        
        # Remove metadata
        self.connection_metadata.pop(websocket, None)
        
        logger.info(f"WebSocket disconnected: {connection_type}")
    
    async def send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """
        Send message to a specific WebSocket
        
        Args:
            websocket: WebSocket to send to
            message: Message to send
        """
        try:
            await websocket.send_json(message)
            
            # Update last activity
            if websocket in self.connection_metadata:
                self.connection_metadata[websocket]['last_activity'] = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            await self.disconnect(websocket)
    
    async def broadcast_to_type(self, connection_type: str, message: Dict[str, Any]):
        """
        Broadcast message to all connections of a specific type
        
        Args:
            connection_type: Type of connections to broadcast to
            message: Message to broadcast
        """
        if connection_type not in self.active_connections:
            return
        
        connections = self.active_connections[connection_type].copy()
        disconnected = []
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
                
                # Update last activity
                if websocket in self.connection_metadata:
                    self.connection_metadata[websocket]['last_activity'] = datetime.utcnow()
                    
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket, marking for disconnect: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected sockets
        for websocket in disconnected:
            await self.disconnect(websocket)
        
        if connections:
            logger.info(f"Broadcasted to {len(connections) - len(disconnected)} {connection_type} connections")
    
    async def send_query_progress(self, query_id: str, status: str, 
                                 progress: float, rows_processed: int):
        """
        Send query progress update
        
        Args:
            query_id: Query ID
            status: Query status
            progress: Progress percentage (0-1)
            rows_processed: Number of rows processed
        """
        message = {
            'type': 'query_progress',
            'query_id': query_id,
            'status': status,
            'progress': progress,
            'rows_processed': rows_processed,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Send to query-specific connections
        connections = self.active_connections.get('query_progress', set()).copy()
        
        for websocket in connections:
            metadata = self.connection_metadata.get(websocket, {})
            if metadata.get('query_id') == query_id:
                await self.send_message(websocket, message)
    
    async def send_system_notification(self, notification_type: str, 
                                      message: str, severity: str = 'info'):
        """
        Send system notification
        
        Args:
            notification_type: Type of notification
            message: Notification message
            severity: Severity level (info, warning, error)
        """
        notification = {
            'type': 'system_notification',
            'notification_type': notification_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_type('system_notifications', notification)
    
    async def send_schema_update(self, database_id: str, update_type: str, 
                                changes: Dict[str, Any]):
        """
        Send schema update notification
        
        Args:
            database_id: Database ID that was updated
            update_type: Type of update (table_added, column_modified, etc.)
            changes: Details of changes
        """
        update = {
            'type': 'schema_update',
            'database_id': database_id,
            'update_type': update_type,
            'changes': changes,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_type('schema_updates', update)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        stats = {
            'total_connections': sum(len(connections) for connections in self.active_connections.values()),
            'connections_by_type': {
                conn_type: len(connections) 
                for conn_type, connections in self.active_connections.items()
            },
            'active_queries': len([
                ws for ws, metadata in self.connection_metadata.items()
                if metadata.get('type') == 'query_progress' and metadata.get('query_id')
            ])
        }
        
        return stats
    
    async def cleanup_stale_connections(self, max_idle_minutes: int = 30):
        """
        Clean up stale connections
        
        Args:
            max_idle_minutes: Maximum idle time before disconnection
        """
        current_time = datetime.utcnow()
        stale_connections = []
        
        for websocket, metadata in self.connection_metadata.items():
            last_activity = metadata.get('last_activity')
            if last_activity:
                idle_minutes = (current_time - last_activity).total_seconds() / 60
                if idle_minutes > max_idle_minutes:
                    stale_connections.append(websocket)
        
        for websocket in stale_connections:
            await self.disconnect(websocket)
        
        if stale_connections:
            logger.info(f"Cleaned up {len(stale_connections)} stale connections")

# Global connection manager instance
connection_manager = ConnectionManager()

async def query_progress_websocket_handler(websocket: WebSocket, query_id: str, user_id: Optional[str] = None):
    """
    Handle query progress WebSocket connections
    
    Args:
        websocket: WebSocket connection
        query_id: Query ID to track
        user_id: User ID
    """
    await connection_manager.connect(websocket, 'query_progress', user_id, query_id)
    
    try:
        while True:
            # Keep connection alive and handle any client messages
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                # Handle any client messages if needed
                message = json.loads(data)
                logger.info(f"Received WebSocket message: {message}")
            except asyncio.TimeoutError:
                # No message received, continue
                pass
            except Exception as e:
                logger.warning(f"WebSocket receive error: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"Query progress WebSocket disconnected for query {query_id}")
    finally:
        await connection_manager.disconnect(websocket)

async def system_notifications_websocket_handler(websocket: WebSocket, user_id: Optional[str] = None):
    """
    Handle system notifications WebSocket connections
    
    Args:
        websocket: WebSocket connection
        user_id: User ID
    """
    await connection_manager.connect(websocket, 'system_notifications', user_id)
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Handle ping/pong or other client messages
                message = json.loads(data)
                if message.get('type') == 'ping':
                    await websocket.send_json({'type': 'pong'})
            except asyncio.TimeoutError:
                # Send heartbeat
                await connection_manager.send_message(websocket, {
                    'type': 'heartbeat',
                    'timestamp': datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.warning(f"System notifications WebSocket error: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"System notifications WebSocket disconnected for user {user_id}")
    finally:
        await connection_manager.disconnect(websocket)