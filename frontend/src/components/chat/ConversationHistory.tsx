import React, { useState, useEffect } from 'react'
import {
  Drawer,
  List,
  Input,
  Button,
  Space,
  Typography,
  Empty,
  Spin,
  Tag,
  Popconfirm,
  message
} from 'antd'
import {
  HistoryOutlined,
  SearchOutlined,
  DeleteOutlined,
  MessageOutlined,
  ClockCircleOutlined,
  PlusOutlined,
  FilterOutlined
} from '@ant-design/icons'
import { ConversationThread } from '../../types/chat'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/tr'

dayjs.extend(relativeTime)
dayjs.locale('tr')

const { Title, Text, Paragraph } = Typography
const { Search } = Input

interface ConversationHistoryProps {
  dbId: string
  onClose: () => void
  onSelectThread: (thread: ConversationThread) => void
}

const ConversationHistory: React.FC<ConversationHistoryProps> = ({
  dbId,
  onClose,
  onSelectThread
}) => {
  const [threads, setThreads] = useState<ConversationThread[]>([])
  const [filteredThreads, setFilteredThreads] = useState<ConversationThread[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null)

  // Load conversation threads
  useEffect(() => {
    loadThreads()
  }, [dbId])

  // Filter threads based on search
  useEffect(() => {
    if (searchTerm) {
      const filtered = threads.filter(thread => 
        thread.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        thread.messages.some(msg => 
          msg.text.toLowerCase().includes(searchTerm.toLowerCase())
        )
      )
      setFilteredThreads(filtered)
    } else {
      setFilteredThreads(threads)
    }
  }, [searchTerm, threads])

  const loadThreads = async () => {
    setLoading(true)
    try {
      // TODO: Replace with actual API call
      // const response = await chatApi.getThreads(dbId)
      
      // Mock data for now
      const mockThreads: ConversationThread[] = [
        {
          id: '1',
          title: 'En çok satan ürünler analizi',
          messages: [],
          createdAt: new Date('2024-01-15'),
          updatedAt: new Date('2024-01-15'),
          dbId
        },
        {
          id: '2',
          title: 'Müşteri segmentasyonu sorguları',
          messages: [],
          createdAt: new Date('2024-01-14'),
          updatedAt: new Date('2024-01-14'),
          dbId
        },
        {
          id: '3',
          title: 'Aylık satış raporları',
          messages: [],
          createdAt: new Date('2024-01-13'),
          updatedAt: new Date('2024-01-13'),
          dbId
        }
      ]
      
      setThreads(mockThreads)
      setFilteredThreads(mockThreads)
    } catch (error) {
      console.error('Failed to load threads:', error)
      message.error('Konuşma geçmişi yüklenemedi')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteThread = async (threadId: string) => {
    try {
      // TODO: Replace with actual API call
      // await chatApi.deleteThread(threadId)
      
      setThreads(prev => prev.filter(t => t.id !== threadId))
      message.success('Konuşma silindi')
    } catch (error) {
      console.error('Failed to delete thread:', error)
      message.error('Konuşma silinemedi')
    }
  }

  const handleCreateNewThread = () => {
    // Close drawer and clear current conversation
    onClose()
    // TODO: Implement new thread creation
    message.info('Yeni konuşma başlatıldı')
  }

  const handleSelectThread = (thread: ConversationThread) => {
    setSelectedThreadId(thread.id)
    onSelectThread(thread)
    onClose()
  }

  const getThreadSummary = (thread: ConversationThread) => {
    const messageCount = thread.messages.length
    const lastMessage = thread.messages[thread.messages.length - 1]
    
    return (
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Text strong>{thread.title}</Text>
          <Tag color="blue">{messageCount} mesaj</Tag>
        </div>
        
        {lastMessage && (
          <Paragraph 
            ellipsis={{ rows: 2 }} 
            type="secondary"
            style={{ margin: 0, fontSize: 12 }}
          >
            {lastMessage.text}
          </Paragraph>
        )}
        
        <Space size="small">
          <ClockCircleOutlined style={{ fontSize: 12 }} />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {dayjs(thread.updatedAt).fromNow()}
          </Text>
        </Space>
      </Space>
    )
  }

  return (
    <Drawer
      title={
        <Space>
          <HistoryOutlined />
          <Title level={4} style={{ margin: 0 }}>Konuşma Geçmişi</Title>
        </Space>
      }
      placement="left"
      onClose={onClose}
      open={true}
      width={400}
      extra={
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleCreateNewThread}
        >
          Yeni Konuşma
        </Button>
      }
    >
      {/* Search Bar */}
      <Search
        placeholder="Konuşmalarda ara..."
        prefix={<SearchOutlined />}
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        style={{ marginBottom: 16 }}
        allowClear
      />

      {/* Filter Options */}
      <div style={{ marginBottom: 16 }}>
        <Space wrap>
          <Tag 
            icon={<FilterOutlined />}
            color="blue"
            style={{ cursor: 'pointer' }}
          >
            Tümü ({threads.length})
          </Tag>
          <Tag style={{ cursor: 'pointer' }}>
            Bugün
          </Tag>
          <Tag style={{ cursor: 'pointer' }}>
            Bu Hafta
          </Tag>
          <Tag style={{ cursor: 'pointer' }}>
            Bu Ay
          </Tag>
        </Space>
      </div>

      {/* Thread List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin size="large" />
        </div>
      ) : filteredThreads.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            searchTerm 
              ? "Arama sonucu bulunamadı"
              : "Henüz konuşma geçmişi yok"
          }
        >
          {!searchTerm && (
            <Button 
              type="primary" 
              icon={<PlusOutlined />}
              onClick={handleCreateNewThread}
            >
              İlk Konuşmayı Başlat
            </Button>
          )}
        </Empty>
      ) : (
        <List
          itemLayout="horizontal"
          dataSource={filteredThreads}
          renderItem={(thread) => (
            <List.Item
              className={`thread-item ${selectedThreadId === thread.id ? 'selected' : ''}`}
              style={{
                cursor: 'pointer',
                padding: '12px',
                borderRadius: 8,
                marginBottom: 8,
                background: selectedThreadId === thread.id ? '#e6f7ff' : '#fafafa',
                border: selectedThreadId === thread.id ? '1px solid #1890ff' : '1px solid #f0f0f0',
                transition: 'all 0.3s'
              }}
              onClick={() => handleSelectThread(thread)}
              actions={[
                <Popconfirm
                  title="Bu konuşmayı silmek istediğinize emin misiniz?"
                  onConfirm={(e) => {
                    e?.stopPropagation()
                    handleDeleteThread(thread.id)
                  }}
                  onCancel={(e) => e?.stopPropagation()}
                  okText="Evet"
                  cancelText="Hayır"
                >
                  <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    size="small"
                    onClick={(e) => e.stopPropagation()}
                  />
                </Popconfirm>
              ]}
            >
              <List.Item.Meta
                avatar={
                  <div style={{
                    width: 40,
                    height: 40,
                    borderRadius: 8,
                    background: '#1890ff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <MessageOutlined style={{ color: '#fff', fontSize: 18 }} />
                  </div>
                }
                description={getThreadSummary(thread)}
              />
            </List.Item>
          )}
        />
      )}

      <style jsx>{`
        .thread-item:hover {
          background: #f0f7ff !important;
          border-color: #69c0ff !important;
        }
        
        .thread-item.selected {
          box-shadow: 0 2px 8px rgba(24, 144, 255, 0.2);
        }
      `}</style>
    </Drawer>
  )
}

export default ConversationHistory