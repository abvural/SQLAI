import { useState, useEffect, useCallback, useRef } from 'react'
import { message as antMessage } from 'antd'
import { ChatMessage, ProcessingStage } from '../types/chat'
import { WebSocketService, WebSocketMessage } from '../services/websocket'
import { queryApi } from '../services/api'

interface UseChatOptions {
  autoConnect?: boolean
  maxMessages?: number
  persistMessages?: boolean
}

export const useChat = (dbId: string, options: UseChatOptions = {}) => {
  const {
    autoConnect = true,
    maxMessages = 100,
    persistMessages = true
  } = options

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isTyping, setIsTyping] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocketService | null>(null)
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Load messages from localStorage
  useEffect(() => {
    if (persistMessages) {
      const storedMessages = localStorage.getItem(`chat_messages_${dbId}`)
      if (storedMessages) {
        try {
          const parsed = JSON.parse(storedMessages)
          setMessages(parsed)
        } catch (error) {
          console.error('Failed to parse stored messages:', error)
        }
      }
    }
  }, [dbId, persistMessages])

  // Save messages to localStorage
  useEffect(() => {
    if (persistMessages && messages.length > 0) {
      localStorage.setItem(`chat_messages_${dbId}`, JSON.stringify(messages))
    }
  }, [messages, dbId, persistMessages])

  // Initialize WebSocket connection
  useEffect(() => {
    if (!autoConnect) return

    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:8000/ws/chat/${dbId}`
    
    console.log('Initializing WebSocket connection:', wsUrl)
    
    // Create WebSocket instance
    const ws = new WebSocketService(wsUrl, {
      reconnect: true,
      reconnectAttempts: 5,
      reconnectInterval: 2000,
      heartbeatInterval: 30000
    })

    // Setup event listeners
    ws.on('connected', () => {
      console.log('Chat WebSocket connected')
      setIsConnected(true)
      antMessage.success('Bağlantı kuruldu')
    })

    ws.on('disconnected', () => {
      console.log('Chat WebSocket disconnected')
      setIsConnected(false)
      antMessage.warning('Bağlantı kesildi')
    })

    ws.on('reconnecting', (attempt: number) => {
      console.log(`Reconnecting... Attempt ${attempt}`)
      antMessage.info(`Yeniden bağlanıyor... (${attempt}. deneme)`)
    })

    ws.on('error', (error: Error) => {
      console.error('WebSocket error:', error)
      antMessage.error('Bağlantı hatası')
    })

    ws.on('chat_message', handleIncomingMessage)
    ws.on('typing', handleTypingIndicator)
    ws.on('query_progress', handleQueryProgress)

    // Connect
    ws.connect().catch((error) => {
      console.error('Failed to connect WebSocket:', error)
      // Fallback to API-only mode
      setIsConnected(false)
    })

    wsRef.current = ws

    // Cleanup
    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect()
        wsRef.current = null
      }
    }
  }, [dbId, autoConnect])

  // Handle incoming chat message
  const handleIncomingMessage = useCallback((data: any) => {
    const newMessage: ChatMessage = {
      id: data.id || Date.now().toString(),
      text: data.text,
      sender: data.sender || 'ai',
      timestamp: new Date(data.timestamp || Date.now()),
      status: 'delivered',
      metadata: data.metadata
    }

    setMessages(prev => {
      const updated = [...prev, newMessage]
      // Limit message history
      if (updated.length > maxMessages) {
        return updated.slice(-maxMessages)
      }
      return updated
    })

    // Stop typing indicator
    setIsTyping(false)
  }, [maxMessages])

  // Handle typing indicator
  const handleTypingIndicator = useCallback((data: any) => {
    setIsTyping(data.isTyping)
    
    // Auto-clear typing after timeout
    if (data.isTyping) {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current)
      }
      typingTimeoutRef.current = setTimeout(() => {
        setIsTyping(false)
      }, 10000) // Clear after 10 seconds
    }
  }, [])

  // Handle query progress updates
  const handleQueryProgress = useCallback((data: ProcessingStage) => {
    // Update the last AI message with progress
    setMessages(prev => {
      const lastAiMessageIndex = prev.findLastIndex(m => m.sender === 'ai')
      if (lastAiMessageIndex === -1) return prev

      const updated = [...prev]
      const lastMessage = { ...updated[lastAiMessageIndex] }
      
      if (!lastMessage.metadata) {
        lastMessage.metadata = {}
      }
      
      if (!lastMessage.metadata.processingStages) {
        lastMessage.metadata.processingStages = []
      }
      
      // Update or add the stage
      const stageIndex = lastMessage.metadata.processingStages.findIndex(
        s => s.stage === data.stage
      )
      
      if (stageIndex >= 0) {
        lastMessage.metadata.processingStages[stageIndex] = data
      } else {
        lastMessage.metadata.processingStages.push(data)
      }
      
      updated[lastAiMessageIndex] = lastMessage
      return updated
    })
  }, [])

  // Send message
  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim()) return

    // Create user message
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      text: text.trim(),
      sender: 'user',
      timestamp: new Date(),
      status: 'sending'
    }

    // Add user message to state
    setMessages(prev => [...prev, userMessage])

    try {
      // If WebSocket is connected, send via WebSocket
      if (wsRef.current?.isConnectionOpen()) {
        const sent = wsRef.current.send({
          type: 'chat_message',
          data: {
            text: text.trim(),
            dbId,
            timestamp: Date.now()
          }
        })

        if (sent) {
          // Update message status
          setMessages(prev => prev.map(m => 
            m.id === userMessage.id ? { ...m, status: 'sent' } : m
          ))
          
          // Show typing indicator
          setIsTyping(true)
        } else {
          throw new Error('Failed to send via WebSocket')
        }
      } else {
        // Fallback to API
        console.log('WebSocket not available, using API')
        
        // Update message status to sent
        setMessages(prev => prev.map(m => 
          m.id === userMessage.id ? { ...m, status: 'sent' } : m
        ))
        
        // Show typing indicator
        setIsTyping(true)
        
        // Call API
        const response = await queryApi.executeNaturalQuery({
          prompt: text.trim(),
          db_id: dbId,
          confidence_threshold: 0.1
        })

        // Create AI response message
        const aiMessage: ChatMessage = {
          id: Date.now().toString(),
          text: response.sql || response.error || 'Sorgu işlenemedi',
          sender: 'ai',
          timestamp: new Date(),
          status: 'delivered',
          metadata: {
            sql: response.sql,
            confidence: response.confidence,
            rowCount: response.row_count,
            executionTime: response.execution_time ? response.execution_time * 1000 : undefined
          }
        }

        // Add AI message
        setMessages(prev => [...prev, aiMessage])
        
        // Stop typing indicator
        setIsTyping(false)
        
        // Update user message status
        setMessages(prev => prev.map(m => 
          m.id === userMessage.id ? { ...m, status: 'delivered' } : m
        ))
      }
    } catch (error) {
      console.error('Failed to send message:', error)
      
      // Update message status to error
      setMessages(prev => prev.map(m => 
        m.id === userMessage.id ? { ...m, status: 'error' } : m
      ))
      
      // Stop typing indicator
      setIsTyping(false)
      
      // Show error message
      antMessage.error('Mesaj gönderilemedi')
    }
  }, [dbId])

  // Clear messages
  const clearMessages = useCallback(() => {
    setMessages([])
    if (persistMessages) {
      localStorage.removeItem(`chat_messages_${dbId}`)
    }
    antMessage.success('Konuşma temizlendi')
  }, [dbId, persistMessages])

  // Retry failed message
  const retryMessage = useCallback((messageId: string) => {
    const message = messages.find(m => m.id === messageId)
    if (message && message.status === 'error') {
      // Remove the failed message
      setMessages(prev => prev.filter(m => m.id !== messageId))
      // Resend
      sendMessage(message.text)
    }
  }, [messages, sendMessage])

  // Manual connect
  const connect = useCallback(() => {
    if (wsRef.current && !wsRef.current.isConnectionOpen()) {
      wsRef.current.connect()
    }
  }, [])

  // Manual disconnect
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.disconnect()
    }
  }, [])

  return {
    // State
    messages,
    isTyping,
    isConnected,
    
    // Actions
    sendMessage,
    clearMessages,
    retryMessage,
    connect,
    disconnect
  }
}