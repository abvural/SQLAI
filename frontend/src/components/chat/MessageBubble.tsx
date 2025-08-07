import React, { useState } from 'react'
import { 
  Avatar, 
  Space, 
  Typography, 
  Tag, 
  Tooltip, 
  Button,
  Progress,
  Collapse,
  Table,
  message as antMessage
} from 'antd'
import {
  UserOutlined,
  RobotOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  CodeOutlined,
  BarChartOutlined,
  ThunderboltOutlined,
  CopyOutlined,
  ExpandOutlined
} from '@ant-design/icons'
import { ChatMessage, ProcessingStage } from '../../types/chat'
import MonacoEditor from '@monaco-editor/react'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/tr'

dayjs.extend(relativeTime)
dayjs.locale('tr')

const { Text, Paragraph } = Typography
const { Panel } = Collapse

interface MessageBubbleProps {
  message: ChatMessage
  onRetry?: () => void
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, onRetry }) => {
  const [showSQL, setShowSQL] = useState(false)
  const [showDetails, setShowDetails] = useState(false)
  
  const isUser = message.sender === 'user'

  // Get status icon
  const getStatusIcon = () => {
    switch (message.status) {
      case 'sending':
        return <ClockCircleOutlined style={{ color: '#1890ff' }} />
      case 'sent':
      case 'delivered':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case 'error':
        return <ExclamationCircleOutlined style={{ color: '#f5222d' }} />
      default:
        return null
    }
  }

  // Copy SQL to clipboard
  const copySQLToClipboard = () => {
    if (message.metadata?.sql) {
      navigator.clipboard.writeText(message.metadata.sql)
      antMessage.success('SQL kopyalandı!')
    }
  }

  // Render processing stages
  const renderProcessingStages = () => {
    if (!message.metadata?.processingStages) return null

    return (
      <div className="processing-stages">
        <Space direction="vertical" style={{ width: '100%' }}>
          {message.metadata.processingStages.map((stage, index) => (
            <div key={index} className="stage-item">
              <Space>
                {stage.status === 'completed' ? (
                  <CheckCircleOutlined style={{ color: '#52c41a' }} />
                ) : stage.status === 'in_progress' ? (
                  <ClockCircleOutlined style={{ color: '#1890ff' }} />
                ) : stage.status === 'error' ? (
                  <ExclamationCircleOutlined style={{ color: '#f5222d' }} />
                ) : (
                  <ClockCircleOutlined style={{ color: '#d9d9d9' }} />
                )}
                <Text type={stage.status === 'error' ? 'danger' : undefined}>
                  {stage.message}
                </Text>
                {stage.duration && (
                  <Text type="secondary">({stage.duration}ms)</Text>
                )}
              </Space>
              {stage.status === 'in_progress' && (
                <Progress 
                  percent={stage.progress} 
                  size="small" 
                  status="active"
                  strokeColor="#1890ff"
                />
              )}
            </div>
          ))}
        </Space>
      </div>
    )
  }

  // Render metadata tags
  const renderMetadataTags = () => {
    if (!message.metadata) return null

    return (
      <Space wrap style={{ marginTop: 8 }}>
        {message.metadata.confidence !== undefined && (
          <Tooltip title="AI Güven Skoru">
            <Tag 
              icon={<ThunderboltOutlined />}
              color={message.metadata.confidence > 0.8 ? 'green' : 
                     message.metadata.confidence > 0.5 ? 'orange' : 'red'}
            >
              %{Math.round(message.metadata.confidence * 100)}
            </Tag>
          </Tooltip>
        )}
        
        {message.metadata.patterns && message.metadata.patterns.length > 0 && (
          <Tooltip title="Algılanan Desenler">
            <Tag icon={<BarChartOutlined />} color="blue">
              {message.metadata.patterns.length} desen
            </Tag>
          </Tooltip>
        )}
        
        {message.metadata.rowCount !== undefined && (
          <Tag color="purple">
            {message.metadata.rowCount} satır
          </Tag>
        )}
        
        {message.metadata.executionTime !== undefined && (
          <Tag color="cyan">
            {message.metadata.executionTime}ms
          </Tag>
        )}

        {message.metadata.sql && (
          <Button
            size="small"
            icon={<CodeOutlined />}
            onClick={() => setShowSQL(!showSQL)}
          >
            SQL
          </Button>
        )}
      </Space>
    )
  }

  return (
    <div 
      className={`message-bubble ${isUser ? 'user-message' : 'ai-message'}`}
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: 16
      }}
    >
      <Space 
        align="start"
        style={{
          maxWidth: '70%',
          flexDirection: isUser ? 'row-reverse' : 'row'
        }}
      >
        <Avatar
          icon={isUser ? <UserOutlined /> : <RobotOutlined />}
          style={{
            backgroundColor: isUser ? '#1890ff' : '#52c41a',
            flexShrink: 0
          }}
        />
        
        <div
          style={{
            background: isUser ? '#1890ff' : '#f0f0f0',
            color: isUser ? '#fff' : '#000',
            padding: '12px 16px',
            borderRadius: isUser ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
            position: 'relative'
          }}
        >
          {/* Message Text */}
          <Paragraph 
            style={{ 
              margin: 0, 
              color: isUser ? '#fff' : '#000',
              whiteSpace: 'pre-wrap'
            }}
          >
            {message.text}
          </Paragraph>

          {/* Metadata Tags */}
          {!isUser && renderMetadataTags()}

          {/* SQL Display */}
          {showSQL && message.metadata?.sql && (
            <div style={{ marginTop: 12 }}>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 8
              }}>
                <Text strong>Üretilen SQL:</Text>
                <Space>
                  <Button
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={copySQLToClipboard}
                  >
                    Kopyala
                  </Button>
                  <Button
                    size="small"
                    icon={<ExpandOutlined />}
                    onClick={() => setShowDetails(!showDetails)}
                  >
                    Detaylar
                  </Button>
                </Space>
              </div>
              
              <div style={{ 
                background: '#1f1f1f', 
                borderRadius: 4,
                overflow: 'hidden'
              }}>
                <MonacoEditor
                  height="150px"
                  language="sql"
                  theme="vs-dark"
                  value={message.metadata.sql}
                  options={{
                    readOnly: true,
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    fontSize: 12,
                    wordWrap: 'on',
                    lineNumbers: 'off'
                  }}
                />
              </div>
            </div>
          )}

          {/* Processing Details */}
          {showDetails && (
            <Collapse 
              ghost 
              style={{ marginTop: 12 }}
              defaultActiveKey={['stages']}
            >
              <Panel header="İşlem Aşamaları" key="stages">
                {renderProcessingStages()}
              </Panel>
            </Collapse>
          )}

          {/* Footer */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between',
            alignItems: 'center',
            marginTop: 8,
            paddingTop: 8,
            borderTop: isUser ? '1px solid rgba(255,255,255,0.2)' : '1px solid #e8e8e8'
          }}>
            <Space size="small">
              <Tooltip title={dayjs(message.timestamp).format('DD/MM/YYYY HH:mm:ss')}>
                <Text 
                  type="secondary" 
                  style={{ 
                    fontSize: 12,
                    color: isUser ? 'rgba(255,255,255,0.8)' : undefined
                  }}
                >
                  {dayjs(message.timestamp).fromNow()}
                </Text>
              </Tooltip>
              {getStatusIcon()}
            </Space>
            
            {message.status === 'error' && onRetry && (
              <Button
                size="small"
                icon={<ReloadOutlined />}
                onClick={onRetry}
                danger
              >
                Tekrar Dene
              </Button>
            )}
          </div>
        </div>
      </Space>
    </div>
  )
}

export default MessageBubble