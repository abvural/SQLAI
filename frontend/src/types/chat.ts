export interface ChatMessage {
  id: string
  text: string
  sender: 'user' | 'ai'
  timestamp: Date
  status: 'sending' | 'sent' | 'delivered' | 'error'
  metadata?: {
    confidence?: number
    sql?: string
    patterns?: string[]
    executionTime?: number
    rowCount?: number
    processingStages?: ProcessingStage[]
  }
}

export interface ProcessingStage {
  stage: 'parsing' | 'turkish_understanding' | 'sql_generation' | 'execution' | 'complete'
  status: 'pending' | 'in_progress' | 'completed' | 'error'
  message: string
  progress: number
  duration?: number
}

export interface ChatContextType {
  messages: ChatMessage[]
  isTyping: boolean
  isConnected: boolean
  sendMessage: (text: string) => Promise<void>
  clearMessages: () => void
  retryMessage: (messageId: string) => void
}

export interface VoiceInputState {
  isListening: boolean
  transcript: string
  error: string | null
  confidence: number
}

export interface ConversationThread {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: Date
  updatedAt: Date
  dbId: string
}