import React, { useEffect, useState } from 'react'
import { Badge, Card, Tooltip, Space, Button, Progress, Typography, Spin } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, SyncOutlined, CloudDownloadOutlined, RobotOutlined, ThunderboltOutlined } from '@ant-design/icons'

const { Text, Title } = Typography

interface LLMModel {
  name: string
  size: number
  size_gb: number
  modified: string
  digest: string
}

interface LLMStatus {
  status: 'ready' | 'partial' | 'offline' | 'error'
  timestamp: string
  ollama: {
    running: boolean
    version: string | null
    endpoint: string
  }
  models: {
    available: LLMModel[]
    required: {
      mistral: {
        required: string
        available: boolean
        status: string
      }
      sqlcoder: {
        required: string
        available: boolean
        status: string
      }
    }
    all_ready: boolean
  }
  capabilities: {
    natural_language: boolean
    sql_generation: boolean
    turkish_support: boolean
    streaming: boolean
  }
}

const LLMStatusIndicator: React.FC = () => {
  const [status, setStatus] = useState<LLMStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStatus = async () => {
    try {
      setLoading(true)
      // First try the new endpoint
      const response = await fetch('http://localhost:8000/api/llm/status')
      if (response.ok) {
        const data = await response.json()
        setStatus(data)
        setError(null)
      } else {
        // Fallback to checking Ollama directly
        const ollamaResponse = await fetch('http://localhost:11434/api/tags')
        if (ollamaResponse.ok) {
          const ollamaData = await ollamaResponse.json()
          // Create a mock status from Ollama data
          const models = ollamaData.models || []
          const hasMistral = models.some((m: any) => m.name?.includes('mistral'))
          const hasSqlcoder = models.some((m: any) => m.name?.includes('sqlcoder'))
          
          setStatus({
            status: hasMistral && hasSqlcoder ? 'ready' : 'partial',
            timestamp: new Date().toISOString(),
            ollama: {
              running: true,
              version: 'unknown',
              endpoint: 'http://localhost:11434'
            },
            models: {
              available: models,
              required: {
                mistral: {
                  required: 'mistral:7b-instruct-q4_K_M',
                  available: hasMistral,
                  status: hasMistral ? 'ready' : 'missing'
                },
                sqlcoder: {
                  required: 'sqlcoder:latest',
                  available: hasSqlcoder,
                  status: hasSqlcoder ? 'ready' : 'missing'
                }
              },
              all_ready: hasMistral && hasSqlcoder
            },
            capabilities: {
              natural_language: hasMistral && hasSqlcoder,
              sql_generation: hasSqlcoder,
              turkish_support: true,
              streaming: true
            }
          })
          setError(null)
        } else {
          throw new Error('Ollama service not available')
        }
      }
    } catch (err) {
      console.error('Error fetching LLM status:', err)
      setError('LLM service unavailable')
      setStatus({
        status: 'offline',
        timestamp: new Date().toISOString(),
        ollama: {
          running: false,
          version: null,
          endpoint: 'http://localhost:11434'
        },
        models: {
          available: [],
          required: {
            mistral: {
              required: 'mistral:7b-instruct-q4_K_M',
              available: false,
              status: 'missing'
            },
            sqlcoder: {
              required: 'sqlcoder:latest',
              available: false,
              status: 'missing'
            }
          },
          all_ready: false
        },
        capabilities: {
          natural_language: false,
          sql_generation: false,
          turkish_support: false,
          streaming: false
        }
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 30000) // Check every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const getStatusColor = () => {
    if (!status) return 'default'
    switch (status.status) {
      case 'ready': return 'success'
      case 'partial': return 'warning'
      case 'offline': return 'error'
      default: return 'default'
    }
  }

  const getStatusIcon = () => {
    if (!status) return <SyncOutlined spin />
    switch (status.status) {
      case 'ready': return <CheckCircleOutlined />
      case 'partial': return <SyncOutlined />
      case 'offline': return <CloseCircleOutlined />
      default: return <SyncOutlined spin />
    }
  }

  if (loading && !status) {
    return (
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space>
          <Spin size="small" />
          <Text>Checking LLM status...</Text>
        </Space>
      </Card>
    )
  }

  return (
    <Card 
      title={
        <Space>
          <RobotOutlined />
          <Text strong>LLM Status</Text>
        </Space>
      }
      size="small" 
      style={{ marginBottom: 16 }}
      extra={
        <Badge 
          status={getStatusColor() as any}
          text={status?.status.toUpperCase()}
          icon={getStatusIcon()}
        />
      }
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        {/* Ollama Service Status */}
        <div>
          <Text type="secondary">Ollama Service: </Text>
          {status?.ollama.running ? (
            <Badge status="success" text={`Running ${status.ollama.version ? `(v${status.ollama.version})` : ''}`} />
          ) : (
            <Badge status="error" text="Offline" />
          )}
        </div>

        {/* Required Models */}
        <div>
          <Text type="secondary">Required Models:</Text>
          <div style={{ marginLeft: 16, marginTop: 8 }}>
            <Space direction="vertical" size="small">
              <Tooltip title="Natural language understanding model">
                <Space>
                  {status?.models.required.mistral.available ? 
                    <CheckCircleOutlined style={{ color: '#52c41a' }} /> : 
                    <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                  }
                  <Text code>Mistral 7B</Text>
                  {!status?.models.required.mistral.available && (
                    <Button 
                      size="small" 
                      icon={<CloudDownloadOutlined />}
                      onClick={() => console.log('Download Mistral')}
                    >
                      Download
                    </Button>
                  )}
                </Space>
              </Tooltip>
              
              <Tooltip title="SQL generation specialized model">
                <Space>
                  {status?.models.required.sqlcoder.available ? 
                    <CheckCircleOutlined style={{ color: '#52c41a' }} /> : 
                    <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                  }
                  <Text code>SQLCoder</Text>
                  {!status?.models.required.sqlcoder.available && (
                    <Button 
                      size="small" 
                      icon={<CloudDownloadOutlined />}
                      onClick={() => console.log('Download SQLCoder')}
                    >
                      Download
                    </Button>
                  )}
                </Space>
              </Tooltip>
            </Space>
          </div>
        </div>

        {/* Capabilities */}
        <div>
          <Text type="secondary">Capabilities:</Text>
          <div style={{ marginLeft: 16, marginTop: 8 }}>
            <Space wrap>
              <Tooltip title="Convert natural language to SQL">
                <Badge 
                  status={status?.capabilities.natural_language ? 'success' : 'default'} 
                  text="NL to SQL" 
                />
              </Tooltip>
              <Tooltip title="Generate optimized SQL queries">
                <Badge 
                  status={status?.capabilities.sql_generation ? 'success' : 'default'} 
                  text="SQL Gen" 
                />
              </Tooltip>
              <Tooltip title="Turkish language support">
                <Badge 
                  status={status?.capabilities.turkish_support ? 'success' : 'default'} 
                  text="Turkish" 
                />
              </Tooltip>
              <Tooltip title="Real-time streaming responses">
                <Badge 
                  status={status?.capabilities.streaming ? 'success' : 'default'} 
                  text="Streaming" 
                />
              </Tooltip>
            </Space>
          </div>
        </div>

        {/* Available Models Count */}
        {status?.models.available.length > 0 && (
          <div>
            <Text type="secondary">Available Models: </Text>
            <Text strong>{status.models.available.length}</Text>
            <Text type="secondary"> ({status.models.available.reduce((acc, m) => acc + m.size_gb, 0).toFixed(1)} GB total)</Text>
          </div>
        )}

        {/* Refresh Button */}
        <Button 
          size="small" 
          icon={<SyncOutlined spin={loading} />} 
          onClick={fetchStatus}
          disabled={loading}
        >
          Refresh Status
        </Button>
      </Space>
    </Card>
  )
}

export default LLMStatusIndicator