"""
WebSocket Connection Manager for real-time chat and monitoring
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional
import json
import logging
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for chat and monitoring"""
    
    def __init__(self):
        # Store active connections by room/channel
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Store connection metadata
        self.connection_info: Dict[WebSocket, Dict] = {}
        
    async def connect(self, websocket: WebSocket, room_id: str, user_info: Optional[Dict] = None):
        """Accept and register a new WebSocket connection"""
        try:
            # Check origin for CORS
            origin = websocket.headers.get("origin", "")
            allowed_origins = [
                "http://localhost:3000",
                "http://localhost:3001", 
                "http://localhost:3002",
                "http://localhost:5173",
                "http://127.0.0.1:5173"
            ]
            
            # Allow connections from allowed origins or file:// (null origin)
            if (any(origin.startswith(allowed) for allowed in allowed_origins) if origin else True) or origin == "null":
                await websocket.accept()
                
                # Add to room
                if room_id not in self.active_connections:
                    self.active_connections[room_id] = []
                self.active_connections[room_id].append(websocket)
                
                # Store connection metadata
                self.connection_info[websocket] = {
                    'room_id': room_id,
                    'connected_at': datetime.now(),
                    'user_info': user_info or {}
                }
                
                logger.info(f"WebSocket connected to room {room_id}")
                
                # Send connection confirmation
                await self.send_personal_message({
                    'type': 'connection',
                    'status': 'connected',
                    'room_id': room_id,
                    'timestamp': datetime.now().isoformat()
                }, websocket)
                
                # Notify others in room
                await self.broadcast({
                    'type': 'user_joined',
                    'room_id': room_id,
                    'timestamp': datetime.now().isoformat()
                }, room_id, exclude=websocket)
                
            else:
                logger.warning(f"WebSocket connection rejected from origin: {origin}")
                await websocket.close(code=1008, reason="Origin not allowed")
                
        except Exception as e:
            logger.error(f"Error connecting WebSocket: {e}")
            await websocket.close(code=1011, reason="Server error")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        try:
            # Get room info
            conn_info = self.connection_info.get(websocket)
            if conn_info:
                room_id = conn_info['room_id']
                
                # Remove from room
                if room_id in self.active_connections:
                    if websocket in self.active_connections[room_id]:
                        self.active_connections[room_id].remove(websocket)
                        
                    # Clean up empty rooms
                    if not self.active_connections[room_id]:
                        del self.active_connections[room_id]
                
                # Remove connection info
                del self.connection_info[websocket]
                
                logger.info(f"WebSocket disconnected from room {room_id}")
                
                # Notify others in room
                asyncio.create_task(self.broadcast({
                    'type': 'user_left',
                    'room_id': room_id,
                    'timestamp': datetime.now().isoformat()
                }, room_id))
                
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {e}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            if isinstance(message, dict):
                await websocket.send_json(message)
            else:
                await websocket.send_text(str(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict, room_id: str, exclude: Optional[WebSocket] = None):
        """Broadcast a message to all connections in a room"""
        if room_id not in self.active_connections:
            return
            
        disconnected = []
        for connection in self.active_connections[room_id]:
            if connection != exclude:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to connection: {e}")
                    disconnected.append(connection)
        
        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_to_room(self, message: dict, room_id: str):
        """Send a message to all connections in a room"""
        await self.broadcast(message, room_id)
    
    def get_room_connections(self, room_id: str) -> int:
        """Get the number of active connections in a room"""
        return len(self.active_connections.get(room_id, []))
    
    def get_all_rooms(self) -> List[str]:
        """Get all active room IDs"""
        return list(self.active_connections.keys())
    
    async def handle_message(self, websocket: WebSocket, room_id: str, message: dict):
        """Handle incoming WebSocket messages"""
        try:
            message_type = message.get('type', 'unknown')
            logger.info(f"Handling message type: {message_type}")
            
            if message_type == 'ping':
                # Respond to ping
                await self.send_personal_message({
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                }, websocket)
                
            elif message_type == 'chat_message':
                # Broadcast chat message to room
                await self.broadcast({
                    'type': 'chat_message',
                    'data': message.get('data', {}),
                    'timestamp': datetime.now().isoformat(),
                    'sender': 'user'
                }, room_id, exclude=websocket)
                
                # TODO: Process with AI and send response
                await self.process_chat_message(websocket, room_id, message.get('data', {}))
                
            elif message_type == 'typing':
                # Broadcast typing indicator
                await self.broadcast({
                    'type': 'typing',
                    'data': {
                        'isTyping': message.get('data', {}).get('isTyping', False)
                    },
                    'timestamp': datetime.now().isoformat()
                }, room_id, exclude=websocket)
                
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.send_personal_message({
                'type': 'error',
                'message': 'Failed to process message',
                'timestamp': datetime.now().isoformat()
            }, websocket)
    
    async def process_chat_message(self, websocket: WebSocket, room_id: str, data: dict):
        """Process chat message with AI"""
        try:
            # Send typing indicator
            await self.broadcast({
                'type': 'typing',
                'data': {'isTyping': True},
                'timestamp': datetime.now().isoformat()
            }, room_id)
            
            # Extract database ID from room_id (format: chat_db_id)
            db_id = room_id.replace('chat_', '')
            query_text = data.get('text', '')
            
            # Import here to avoid circular import
            from app.services.llm_service import LocalLLMService
            from app.services.cache_service import CacheService
            from app.ai.nlp_processor import NLPProcessor
            
            try:
                # Use NLP processor which integrates with LLM
                nlp = NLPProcessor(db_id=db_id)
                cache_service = CacheService()
                
                # Get database info
                db_info = cache_service.get_database_info(db_id)
                if not db_info:
                    raise Exception("Database not found")
                
                # Process query with LLM
                sql, confidence = nlp.generate_intelligent_sql(
                    query=query_text
                )
                
                # Prepare response based on result
                if sql:
                    response_text = f"İşte sorgunuz için oluşturulan SQL:\n```sql\n{sql}\n```"
                    metadata = {
                        'confidence': confidence,
                        'sql': sql,
                        'patterns': [],
                        'intent': 'query'
                    }
                else:
                    response_text = "Üzgünüm, sorgunuzu SQL'e çeviremedim. Lütfen daha açık bir şekilde ifade edebilir misiniz?"
                    metadata = {
                        'confidence': 0,
                        'sql': None,
                        'error': 'Could not generate SQL'
                    }
                
                # Send AI response
                await self.broadcast({
                    'type': 'chat_message',
                    'data': {
                        'text': response_text,
                        'metadata': metadata
                    },
                    'timestamp': datetime.now().isoformat(),
                    'sender': 'ai'
                }, room_id)
                
            except Exception as e:
                logger.error(f"Error processing with AI: {e}")
                # Send error response
                await self.broadcast({
                    'type': 'chat_message',
                    'data': {
                        'text': f"Üzgünüm, sorgunuzu işlerken bir hata oluştu: {str(e)}",
                        'metadata': {
                            'error': True,
                            'message': str(e)
                        }
                    },
                    'timestamp': datetime.now().isoformat(),
                    'sender': 'ai'
                }, room_id)
            
            # Stop typing indicator
            await self.broadcast({
                'type': 'typing',
                'data': {'isTyping': False},
                'timestamp': datetime.now().isoformat()
            }, room_id)
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            await self.send_personal_message({
                'type': 'error',
                'message': 'Failed to process message with AI',
                'timestamp': datetime.now().isoformat()
            }, websocket)

# Global connection manager instance
manager = ConnectionManager()