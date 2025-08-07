// Simple EventEmitter implementation for browser compatibility
class EventEmitter {
  private events: Map<string, Array<(...args: any[]) => void>> = new Map()

  on(event: string, listener: (...args: any[]) => void): this {
    if (!this.events.has(event)) {
      this.events.set(event, [])
    }
    this.events.get(event)!.push(listener)
    return this
  }

  off(event: string, listener: (...args: any[]) => void): this {
    const listeners = this.events.get(event)
    if (listeners) {
      const index = listeners.indexOf(listener)
      if (index !== -1) {
        listeners.splice(index, 1)
      }
    }
    return this
  }

  emit(event: string, ...args: any[]): boolean {
    const listeners = this.events.get(event)
    if (listeners && listeners.length > 0) {
      listeners.forEach(listener => {
        try {
          listener(...args)
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error)
        }
      })
      return true
    }
    return false
  }

  removeAllListeners(event?: string): this {
    if (event) {
      this.events.delete(event)
    } else {
      this.events.clear()
    }
    return this
  }
}

export interface WebSocketOptions {
  reconnect?: boolean
  reconnectAttempts?: number
  reconnectInterval?: number
  heartbeatInterval?: number
}

export interface WebSocketMessage {
  type: string
  data: any
  timestamp?: number
  id?: string
}

export class WebSocketService extends EventEmitter {
  private ws: WebSocket | null = null
  private url: string
  private options: WebSocketOptions
  private reconnectAttempts = 0
  private reconnectTimer: NodeJS.Timeout | null = null
  private heartbeatTimer: NodeJS.Timeout | null = null
  private messageQueue: WebSocketMessage[] = []
  private isConnected = false
  private isReconnecting = false

  constructor(url: string, options: WebSocketOptions = {}) {
    super()
    this.url = url
    this.options = {
      reconnect: true,
      reconnectAttempts: 5,
      reconnectInterval: 1000,
      heartbeatInterval: 30000,
      ...options
    }
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // Close existing connection if any
        if (this.ws) {
          this.disconnect()
        }

        console.log(`Connecting to WebSocket: ${this.url}`)
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          console.log('WebSocket connected')
          this.isConnected = true
          this.isReconnecting = false
          this.reconnectAttempts = 0
          
          // Start heartbeat
          this.startHeartbeat()
          
          // Send queued messages
          this.flushMessageQueue()
          
          // Emit connected event
          this.emit('connected')
          
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
            this.emit('error', error)
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.emit('error', error)
          
          if (!this.isConnected) {
            reject(error)
          }
        }

        this.ws.onclose = (event) => {
          console.log('WebSocket disconnected', event.code, event.reason)
          this.isConnected = false
          
          // Stop heartbeat
          this.stopHeartbeat()
          
          // Emit disconnected event
          this.emit('disconnected', event)
          
          // Attempt reconnection if enabled
          if (this.options.reconnect && !this.isReconnecting) {
            this.reconnect()
          }
        }
      } catch (error) {
        console.error('Failed to create WebSocket:', error)
        reject(error)
      }
    })
  }

  private reconnect() {
    if (this.isReconnecting) return
    
    if (this.reconnectAttempts >= (this.options.reconnectAttempts || 5)) {
      console.error('Max reconnection attempts reached')
      this.emit('reconnect_failed')
      return
    }

    this.isReconnecting = true
    this.reconnectAttempts++
    
    const delay = Math.min(
      (this.options.reconnectInterval || 1000) * Math.pow(2, this.reconnectAttempts - 1),
      30000
    )
    
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)
    this.emit('reconnecting', this.reconnectAttempts)
    
    this.reconnectTimer = setTimeout(() => {
      this.connect().catch((error) => {
        console.error('Reconnection failed:', error)
        this.isReconnecting = false
        this.reconnect()
      })
    }, delay)
  }

  disconnect() {
    this.isReconnecting = false
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    
    this.stopHeartbeat()
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
    
    this.isConnected = false
  }

  send(message: WebSocketMessage): boolean {
    if (!message.timestamp) {
      message.timestamp = Date.now()
    }
    
    if (!message.id) {
      message.id = this.generateMessageId()
    }

    if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(message))
        this.emit('message_sent', message)
        return true
      } catch (error) {
        console.error('Failed to send message:', error)
        this.queueMessage(message)
        return false
      }
    } else {
      console.log('WebSocket not connected, queuing message')
      this.queueMessage(message)
      return false
    }
  }

  private queueMessage(message: WebSocketMessage) {
    this.messageQueue.push(message)
    this.emit('message_queued', message)
  }

  private flushMessageQueue() {
    if (this.messageQueue.length === 0) return
    
    console.log(`Flushing ${this.messageQueue.length} queued messages`)
    
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift()
      if (message) {
        this.send(message)
      }
    }
  }

  private handleMessage(message: WebSocketMessage) {
    // Emit general message event
    this.emit('message', message)
    
    // Emit specific event based on message type
    if (message.type) {
      this.emit(message.type, message.data)
    }
    
    // Handle system messages
    switch (message.type) {
      case 'pong':
        // Heartbeat response
        break
      case 'error':
        this.emit('server_error', message.data)
        break
      case 'chat_message':
        this.emit('chat_message', message.data)
        break
      case 'typing':
        this.emit('typing', message.data)
        break
      case 'query_progress':
        this.emit('query_progress', message.data)
        break
      default:
        // Unknown message type
        break
    }
  }

  private startHeartbeat() {
    this.stopHeartbeat()
    
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected) {
        this.send({
          type: 'ping',
          data: { timestamp: Date.now() }
        })
      }
    }, this.options.heartbeatInterval || 30000)
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  private generateMessageId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  // Public methods for status checking
  isConnectionOpen(): boolean {
    return this.isConnected && this.ws?.readyState === WebSocket.OPEN
  }

  getConnectionState(): string {
    if (!this.ws) return 'disconnected'
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting'
      case WebSocket.OPEN:
        return 'connected'
      case WebSocket.CLOSING:
        return 'closing'
      case WebSocket.CLOSED:
        return 'closed'
      default:
        return 'unknown'
    }
  }

  getQueueSize(): number {
    return this.messageQueue.length
  }

  clearQueue() {
    this.messageQueue = []
  }
}

// Singleton instance for app-wide WebSocket
let wsInstance: WebSocketService | null = null

export const getWebSocketInstance = (url?: string): WebSocketService => {
  if (!wsInstance && url) {
    wsInstance = new WebSocketService(url)
  }
  
  if (!wsInstance) {
    throw new Error('WebSocket instance not initialized. Provide URL first.')
  }
  
  return wsInstance
}

export const disconnectWebSocket = () => {
  if (wsInstance) {
    wsInstance.disconnect()
    wsInstance = null
  }
}