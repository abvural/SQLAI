import React, { useState, useRef, useEffect } from 'react'
import { 
  Input, 
  Button, 
  Space, 
  Tooltip, 
  message as antMessage,
  Popover,
  Tag
} from 'antd'
import {
  SendOutlined,
  AudioOutlined,
  AudioMutedOutlined,
  EnterOutlined,
  LoadingOutlined,
  CloseCircleOutlined
} from '@ant-design/icons'
import { useVoiceInput } from '../../hooks/useVoiceInput'

const { TextArea } = Input

interface ChatInputProps {
  onSendMessage: (message: string) => void
  disabled?: boolean
  placeholder?: string
}

const ChatInput: React.FC<ChatInputProps> = ({ 
  onSendMessage, 
  disabled = false,
  placeholder = "Sorgunuzu yazın..."
}) => {
  const [inputValue, setInputValue] = useState('')
  const [isComposing, setIsComposing] = useState(false)
  const textAreaRef = useRef<any>(null)
  
  // Voice input hook
  const {
    isListening,
    transcript,
    error: voiceError,
    confidence,
    startListening,
    stopListening,
    resetTranscript
  } = useVoiceInput()

  // Update input when voice transcript changes
  useEffect(() => {
    if (transcript) {
      setInputValue(prev => {
        // If there's existing text, add a space before transcript
        if (prev && !prev.endsWith(' ')) {
          return prev + ' ' + transcript
        }
        return prev + transcript
      })
      // Reset transcript after adding to input
      resetTranscript()
    }
  }, [transcript, resetTranscript])

  // Show voice error
  useEffect(() => {
    if (voiceError) {
      antMessage.error(`Ses hatası: ${voiceError}`)
    }
  }, [voiceError])

  // Handle send message
  const handleSend = () => {
    const trimmedValue = inputValue.trim()
    if (!trimmedValue || disabled) return
    
    onSendMessage(trimmedValue)
    setInputValue('')
    
    // Focus back to input
    setTimeout(() => {
      textAreaRef.current?.focus()
    }, 100)
  }

  // Handle key press
  const handleKeyPress = (e: React.KeyboardEvent) => {
    // Send on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault()
      handleSend()
    }
  }

  // Toggle voice input
  const toggleVoiceInput = () => {
    if (isListening) {
      stopListening()
    } else {
      startListening()
    }
  }

  // Voice status popover content
  const voiceStatusContent = () => (
    <div style={{ maxWidth: 200 }}>
      {isListening ? (
        <Space direction="vertical">
          <Text>Dinleniyor...</Text>
          {transcript && (
            <div>
              <Text type="secondary">Algılanan:</Text>
              <div style={{ 
                padding: 8, 
                background: '#f0f0f0', 
                borderRadius: 4,
                marginTop: 4
              }}>
                {transcript}
              </div>
            </div>
          )}
          {confidence > 0 && (
            <Tag color={confidence > 0.8 ? 'green' : 'orange'}>
              Güven: %{Math.round(confidence * 100)}
            </Tag>
          )}
        </Space>
      ) : (
        <Text type="secondary">
          Ses girişi için mikrofon butonuna tıklayın
        </Text>
      )}
    </div>
  )

  // Check if browser supports speech recognition
  const isSpeechSupported = 'webkitSpeechRecognition' in window || 
                           'SpeechRecognition' in window

  return (
    <div className="chat-input-container" style={{ padding: 16 }}>
      <Space.Compact style={{ width: '100%' }}>
        <TextArea
          ref={textAreaRef}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyPress}
          onCompositionStart={() => setIsComposing(true)}
          onCompositionEnd={() => setIsComposing(false)}
          placeholder={placeholder}
          disabled={disabled}
          autoSize={{ minRows: 1, maxRows: 4 }}
          style={{ 
            resize: 'none',
            paddingRight: isSpeechSupported ? 120 : 60
          }}
        />
        
        <div 
          style={{ 
            position: 'absolute', 
            right: 16, 
            bottom: 20,
            display: 'flex',
            gap: 8,
            alignItems: 'center'
          }}
        >
          {/* Voice Input Button */}
          {isSpeechSupported && (
            <Popover
              content={voiceStatusContent()}
              title="Sesli Giriş"
              trigger="hover"
              placement="topRight"
            >
              <Tooltip title={isListening ? "Dinlemeyi durdur" : "Sesli giriş"}>
                <Button
                  type={isListening ? "primary" : "default"}
                  icon={
                    isListening ? (
                      <LoadingOutlined spin />
                    ) : voiceError ? (
                      <AudioMutedOutlined />
                    ) : (
                      <AudioOutlined />
                    )
                  }
                  onClick={toggleVoiceInput}
                  disabled={disabled}
                  danger={isListening}
                  style={{
                    animation: isListening ? 'pulse 1.5s infinite' : undefined
                  }}
                />
              </Tooltip>
            </Popover>
          )}

          {/* Send Button */}
          <Tooltip 
            title={
              <Space>
                Gönder
                <Tag color="blue" style={{ margin: 0 }}>
                  <EnterOutlined /> Enter
                </Tag>
              </Space>
            }
          >
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              disabled={disabled || !inputValue.trim()}
            />
          </Tooltip>
        </div>
      </Space.Compact>

      {/* Character counter for long messages */}
      {inputValue.length > 500 && (
        <div style={{ 
          textAlign: 'right', 
          marginTop: 4,
          fontSize: 12,
          color: inputValue.length > 1000 ? '#ff4d4f' : '#8c8c8c'
        }}>
          {inputValue.length} / 1000 karakter
        </div>
      )}

      {/* Voice input indicator */}
      {isListening && (
        <div 
          className="voice-indicator"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginTop: 8,
            padding: '4px 8px',
            background: '#fff7e6',
            border: '1px solid #ffd591',
            borderRadius: 4
          }}
        >
          <div className="voice-wave">
            <span style={{ 
              display: 'inline-block',
              width: 3,
              height: 12,
              background: '#fa8c16',
              margin: '0 2px',
              borderRadius: 2,
              animation: 'wave 0.5s infinite',
              animationDelay: '0s'
            }} />
            <span style={{ 
              display: 'inline-block',
              width: 3,
              height: 16,
              background: '#fa8c16',
              margin: '0 2px',
              borderRadius: 2,
              animation: 'wave 0.5s infinite',
              animationDelay: '0.1s'
            }} />
            <span style={{ 
              display: 'inline-block',
              width: 3,
              height: 20,
              background: '#fa8c16',
              margin: '0 2px',
              borderRadius: 2,
              animation: 'wave 0.5s infinite',
              animationDelay: '0.2s'
            }} />
            <span style={{ 
              display: 'inline-block',
              width: 3,
              height: 16,
              background: '#fa8c16',
              margin: '0 2px',
              borderRadius: 2,
              animation: 'wave 0.5s infinite',
              animationDelay: '0.3s'
            }} />
            <span style={{ 
              display: 'inline-block',
              width: 3,
              height: 12,
              background: '#fa8c16',
              margin: '0 2px',
              borderRadius: 2,
              animation: 'wave 0.5s infinite',
              animationDelay: '0.4s'
            }} />
          </div>
          <Text type="warning">Konuşun...</Text>
          <Button
            size="small"
            type="text"
            icon={<CloseCircleOutlined />}
            onClick={stopListening}
          />
        </div>
      )}

      <style jsx>{`
        @keyframes pulse {
          0% {
            box-shadow: 0 0 0 0 rgba(250, 140, 22, 0.7);
          }
          70% {
            box-shadow: 0 0 0 10px rgba(250, 140, 22, 0);
          }
          100% {
            box-shadow: 0 0 0 0 rgba(250, 140, 22, 0);
          }
        }

        @keyframes wave {
          0%, 100% {
            transform: scaleY(1);
          }
          50% {
            transform: scaleY(1.5);
          }
        }
      `}</style>
    </div>
  )
}

// Add missing import
const { Text } = Typography
import { Typography } from 'antd'

export default ChatInput