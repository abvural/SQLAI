# Frontend Implementation Tasks - Phase 1

> **Start Date**: 2025-08-07  
> **Target Completion**: 2025-08-21 (2 weeks)  
> **Priority Features**: Chat Interface, Real-time Monitoring, AI Insights, Dark Mode  

## 📋 Task Breakdown

### Week 1: Foundation & Core Features

#### Day 1-2: Chat Interface Implementation
- [ ] Create `ChatContainer.tsx` component with message list
- [ ] Implement `MessageBubble.tsx` with user/AI distinction
- [ ] Build `ChatInput.tsx` with multiline support
- [ ] Add voice input button (Web Speech API integration)
- [ ] Create `ConversationHistory.tsx` for thread management
- [ ] Implement auto-scroll to latest message
- [ ] Add typing indicators during AI processing
- [ ] Create ChatContext for state management

#### Day 3: WebSocket Integration
- [ ] Setup WebSocket service class (`websocket.ts`)
- [ ] Implement reconnection logic with exponential backoff
- [ ] Create WebSocket hooks (`useWebSocket.ts`)
- [ ] Add message queue for offline support
- [ ] Implement heartbeat/ping-pong mechanism
- [ ] Add connection status indicator

#### Day 4: Backend WebSocket Endpoints
- [ ] Create WebSocket manager in FastAPI
- [ ] Implement CORS configuration for WebSocket
- [ ] Add connection authentication
- [ ] Create message broadcasting system
- [ ] Implement room/channel support for multiple users
- [ ] Add WebSocket event types (message, typing, status)

#### Day 5: Chat Integration & Testing
- [ ] Connect chat UI with WebSocket service
- [ ] Implement message persistence (backend)
- [ ] Add conversation history API endpoint
- [ ] Test real-time messaging flow
- [ ] Add error handling and retry logic
- [ ] Implement message delivery confirmation

### Week 2: Monitoring & Polish

#### Day 6-7: Real-time Query Monitoring
- [ ] Create `QueryMonitor.tsx` main component
- [ ] Build `ProcessingStage.tsx` with progress bars
- [ ] Implement stage transitions animation
- [ ] Add `ConfidenceMeter.tsx` with gauge visualization
- [ ] Create `PatternIndicator.tsx` for detected patterns
- [ ] Connect to WebSocket for live updates
- [ ] Add cancel query functionality
- [ ] Implement execution timeline view

#### Day 8-9: AI Insights Dashboard
- [ ] Create `InsightsDashboard.tsx` layout
- [ ] Build confidence gauge with Recharts
- [ ] Implement pattern success rate chart
- [ ] Add adaptive learning metrics display
- [ ] Create model performance timeline
- [ ] Add real-time pattern trigger alerts
- [ ] Implement metrics export functionality
- [ ] Add refresh and auto-update toggles

#### Day 10: Dark Mode Implementation
- [ ] Setup ThemeContext provider
- [ ] Implement CSS variables for theming
- [ ] Create theme toggle component
- [ ] Add system preference detection
- [ ] Implement smooth transitions
- [ ] Update all components for dark mode
- [ ] Add theme persistence to localStorage
- [ ] Test contrast ratios for accessibility

#### Day 11-12: Integration & Bug Fixes
- [ ] Full integration testing
- [ ] Fix CORS issues if any
- [ ] Performance optimization
- [ ] Mobile responsiveness testing
- [ ] Cross-browser compatibility
- [ ] Documentation updates
- [ ] Code cleanup and refactoring

---

## 🔧 Implementation Details

### 1. Chat Interface Component Structure

```typescript
// frontend/src/components/chat/ChatContainer.tsx
interface ChatMessage {
  id: string
  text: string
  sender: 'user' | 'ai'
  timestamp: Date
  status: 'sending' | 'sent' | 'delivered' | 'error'
  metadata?: {
    confidence?: number
    sql?: string
    patterns?: string[]
  }
}

// frontend/src/hooks/useChat.ts
const useChat = (dbId: string) => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isTyping, setIsTyping] = useState(false)
  const ws = useWebSocket(`/ws/chat/${dbId}`)
  
  const sendMessage = async (text: string) => {
    // Implementation
  }
  
  return { messages, sendMessage, isTyping }
}
```

### 2. WebSocket Service Implementation

```typescript
// frontend/src/services/websocket.ts
export class WebSocketService {
  private ws: WebSocket | null = null
  private messageQueue: any[] = []
  private reconnectTimer: NodeJS.Timeout | null = null
  
  connect(url: string, options: WebSocketOptions) {
    // Implementation with reconnection logic
  }
  
  send(message: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      this.messageQueue.push(message)
    }
  }
}
```

### 3. Backend WebSocket Setup

```python
# backend/app/websocket/manager.py
from fastapi import WebSocket
from typing import Dict, List
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
    
    async def broadcast(self, message: dict, room_id: str):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                await connection.send_json(message)

# backend/app/main.py - Add WebSocket route
@app.websocket("/ws/chat/{db_id}")
async def websocket_endpoint(websocket: WebSocket, db_id: str):
    await manager.connect(websocket, db_id)
    try:
        while True:
            data = await websocket.receive_json()
            # Process message
            await manager.broadcast(response, db_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, db_id)
```

### 4. Real-time Monitoring Events

```typescript
// frontend/src/types/monitoring.ts
interface QueryProgressEvent {
  queryId: string
  stage: 'parsing' | 'turkish_understanding' | 'sql_generation' | 'execution' | 'complete'
  progress: number
  message: string
  details?: {
    confidence?: number
    patterns?: string[]
    sql?: string
    rowCount?: number
    executionTime?: number
  }
  timestamp: number
}

// Hook for monitoring
const useQueryMonitor = (queryId: string) => {
  const [progress, setProgress] = useState<QueryProgressEvent[]>([])
  const ws = useWebSocket(`/ws/monitor/${queryId}`)
  
  useEffect(() => {
    ws.on('progress', (event: QueryProgressEvent) => {
      setProgress(prev => [...prev, event])
    })
  }, [ws])
  
  return { progress }
}
```

### 5. Theme Implementation

```css
/* frontend/src/styles/theme.css */
:root {
  --color-bg-primary: #ffffff;
  --color-bg-secondary: #f5f5f5;
  --color-text-primary: #262626;
  --color-text-secondary: #8c8c8c;
  --color-accent: #1890ff;
  --color-success: #52c41a;
  --color-warning: #faad14;
  --color-error: #f5222d;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.07);
}

[data-theme="dark"] {
  --color-bg-primary: #141414;
  --color-bg-secondary: #1f1f1f;
  --color-text-primary: #ffffff;
  --color-text-secondary: #8c8c8c;
  --color-accent: #177ddc;
  --color-success: #49aa19;
  --color-warning: #d89614;
  --color-error: #d32029;
}
```

---

## 🚨 Critical CORS Configuration

### Backend Updates Required

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Update CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:3005",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Add WebSocket support
@app.on_event("startup")
async def startup_event():
    # Initialize WebSocket manager
    app.state.ws_manager = ConnectionManager()
```

### Frontend API Configuration

```typescript
// frontend/src/services/api.ts
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: `${API_BASE}/api`,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

// WebSocket URL
export const WS_BASE = API_BASE.replace('http', 'ws')
```

---

## 📝 Testing Checklist

### Unit Tests
- [ ] Chat components render correctly
- [ ] Message sending/receiving logic
- [ ] WebSocket reconnection works
- [ ] Theme switching persists
- [ ] Voice input captures correctly

### Integration Tests
- [ ] End-to-end chat flow
- [ ] Real-time monitoring updates
- [ ] AI insights data accuracy
- [ ] Theme applies to all components

### Performance Tests
- [ ] WebSocket latency < 100ms
- [ ] Theme switch < 50ms
- [ ] Message render < 16ms
- [ ] Voice input response < 200ms

### Accessibility Tests
- [ ] Keyboard navigation works
- [ ] Screen reader compatibility
- [ ] Color contrast ratios (WCAG AA)
- [ ] Focus indicators visible

---

## 🎯 Success Criteria

1. **Chat Interface**: Real-time messaging with < 100ms latency
2. **Query Monitoring**: Live updates for all processing stages
3. **AI Insights**: Accurate metrics with auto-refresh
4. **Dark Mode**: Smooth transitions, persisted preference
5. **CORS**: No cross-origin errors in any environment
6. **WebSocket**: Stable connection with auto-reconnect
7. **Performance**: All interactions < 100ms response
8. **Mobile**: Fully responsive on all devices

---

## 📚 Resources

- [WebSocket API MDN](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)
- [FastAPI WebSocket](https://fastapi.tiangolo.com/advanced/websockets/)
- [React Query](https://tanstack.com/query/latest)
- [Recharts](https://recharts.org/)
- [Ant Design Dark Theme](https://ant.design/docs/react/customize-theme)

---

**Note**: All tasks should be completed with proper error handling, loading states, and user feedback. Code should follow TypeScript best practices and maintain > 80% test coverage for critical paths.