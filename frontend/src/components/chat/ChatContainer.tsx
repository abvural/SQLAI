import React, { useEffect, useRef, useState } from 'react'
import { Card, Empty, Spin, Badge, Typography, Space, Button } from 'antd'
import {
  MessageOutlined,
  ClearOutlined,
  WifiOutlined,
  DisconnectOutlined,
  ReloadOutlined
} from '@ant-design/icons'
import MessageBubble from './MessageBubble'
import ChatInput from './ChatInput'
import ConversationHistory from './ConversationHistory'
import { useChat } from '../../hooks/useChat'
import { ChatMessage } from '../../types/chat'
import './ChatContainer.css'

const { Title, Text } = Typography

interface ChatContainerProps {
  dbId: string
  height?: string | number
}

const ChatContainer: React.FC<ChatContainerProps> = ({ dbId, height = '600px' }) => {
  const {
    messages,
    isTyping,
    isConnected,
    sendMessage,
    clearMessages,
    retryMessage
  } = useChat(dbId)
  
  const [showHistory, setShowHistory] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  // Handle sending message
  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return
    
    try {
      await sendMessage(text)
    } catch (error) {
      console.error('Failed to send message:', error)
    }
  }

  // Render connection status
  const renderConnectionStatus = () => (
    <div className="connection-status">
      <Badge
        status={isConnected ? 'success' : 'error'}
        text={
          <Space>
            {isConnected ? (
              <>
                <WifiOutlined />
                <Text type="secondary">Bağlı</Text>
              </>
            ) : (
              <>
                <DisconnectOutlined />
                <Text type="danger">Bağlantı kesildi</Text>
                <Button 
                  size="small" 
                  icon={<ReloadOutlined />}
                  onClick={() => window.location.reload()}
                >
                  Yeniden Bağlan
                </Button>
              </>
            )}
          </Space>
        }
      />
    </div>
  )

  // Render typing indicator
  const renderTypingIndicator = () => {
    if (!isTyping) return null
    
    return (
      <div className="typing-indicator">
        <Space>
          <Spin size="small" />
          <Text type="secondary">AI düşünüyor...</Text>
        </Space>
      </div>
    )
  }

  return (
    <Card
      title={
        <div className="chat-header">
          <Space>
            <MessageOutlined />
            <Title level={4} style={{ margin: 0 }}>AI Asistan</Title>
          </Space>
          <Space>
            {renderConnectionStatus()}
            <Button
              icon={<ClearOutlined />}
              onClick={clearMessages}
              disabled={messages.length === 0}
            >
              Temizle
            </Button>
          </Space>
        </div>
      }
      className="chat-container"
      bodyStyle={{ padding: 0, height, display: 'flex', flexDirection: 'column' }}
    >
      {/* Conversation History Sidebar */}
      {showHistory && (
        <ConversationHistory
          dbId={dbId}
          onClose={() => setShowHistory(false)}
          onSelectThread={(thread) => {
            // Load thread messages
            console.log('Loading thread:', thread)
          }}
        />
      )}

      {/* Messages Area */}
      <div 
        className="messages-area" 
        ref={containerRef}
        style={{ flex: 1, overflowY: 'auto', padding: '16px' }}
      >
        {messages.length === 0 ? (
          <Empty
            description={
              <Space direction="vertical">
                <Text>Merhaba! Size nasıl yardımcı olabilirim?</Text>
                <Text type="secondary">
                  Veritabanınız hakkında Türkçe sorular sorabilirsiniz.
                </Text>
              </Space>
            }
            style={{ marginTop: '20%' }}
          />
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onRetry={() => retryMessage(message.id)}
              />
            ))}
            {renderTypingIndicator()}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="chat-input-area" style={{ borderTop: '1px solid #f0f0f0' }}>
        <ChatInput
          onSendMessage={handleSendMessage}
          disabled={!isConnected}
          placeholder={
            isConnected 
              ? "Sorgunuzu yazın... (Örn: 'En çok satan ürünler neler?')"
              : "Bağlantı bekleniyor..."
          }
        />
      </div>
    </Card>
  )
}

export default ChatContainer