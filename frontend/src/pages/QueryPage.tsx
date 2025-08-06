import React, { useState } from 'react'
import { 
  Card, 
  Input, 
  Button, 
  Space, 
  Select, 
  Table,
  Tabs,
  message,
  Empty,
  Spin
} from 'antd'
import {
  PlayCircleOutlined,
  ClearOutlined,
  DownloadOutlined,
  StopOutlined
} from '@ant-design/icons'
import MonacoEditor from '@monaco-editor/react'
import { queryApi } from '../services/api'

const { TextArea } = Input
const { TabPane } = Tabs

const QueryPage: React.FC = () => {
  const [naturalQuery, setNaturalQuery] = useState('')
  const [sqlQuery, setSqlQuery] = useState('')
  const [selectedDb, setSelectedDb] = useState<string>('')
  const [queryResults, setQueryResults] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('natural')

  const handleNaturalQuery = async () => {
    if (!selectedDb) {
      message.warning('Please select a database first')
      return
    }
    if (!naturalQuery.trim()) {
      message.warning('Please enter a query')
      return
    }

    setLoading(true)
    try {
      const response = await queryApi.executeNaturalQuery({
        prompt: naturalQuery,
        db_id: selectedDb,
      })
      setSqlQuery(response.sql || '')
      setQueryResults(response.results)
      message.success('Query executed successfully')
    } catch (error: any) {
      message.error('Query failed: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoading(false)
    }
  }

  const handleSQLQuery = async () => {
    if (!selectedDb) {
      message.warning('Please select a database first')
      return
    }
    if (!sqlQuery.trim()) {
      message.warning('Please enter a SQL query')
      return
    }

    setLoading(true)
    try {
      const response = await queryApi.executeSQLQuery({
        sql: sqlQuery,
        db_id: selectedDb,
      })
      setQueryResults(response.results)
      message.success('Query executed successfully')
    } catch (error: any) {
      message.error('Query failed: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async (format: string) => {
    if (!queryResults) {
      message.warning('No results to export')
      return
    }
    
    try {
      // TODO: Implement export
      message.success(`Exporting to ${format}...`)
    } catch (error) {
      message.error('Export failed')
    }
  }

  const getTableColumns = () => {
    if (!queryResults || queryResults.length === 0) return []
    
    return Object.keys(queryResults[0]).map(key => ({
      title: key,
      dataIndex: key,
      key: key,
      ellipsis: true,
    }))
  }

  return (
    <div>
      <Card title="Query Interface">
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Select
            style={{ width: '100%' }}
            placeholder="Select a database"
            value={selectedDb}
            onChange={setSelectedDb}
          >
            {/* TODO: Load databases dynamically */}
            <Select.Option value="db1">Test Database</Select.Option>
          </Select>

          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            <TabPane tab="Natural Language" key="natural">
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <TextArea
                  rows={4}
                  placeholder="Enter your query in natural language... e.g., 'Show me all customers who placed orders last month'"
                  value={naturalQuery}
                  onChange={(e) => setNaturalQuery(e.target.value)}
                />
                <Space>
                  <Button 
                    type="primary" 
                    icon={<PlayCircleOutlined />}
                    onClick={handleNaturalQuery}
                    loading={loading}
                  >
                    Execute Query
                  </Button>
                  <Button 
                    icon={<ClearOutlined />}
                    onClick={() => {
                      setNaturalQuery('')
                      setSqlQuery('')
                      setQueryResults(null)
                    }}
                  >
                    Clear
                  </Button>
                </Space>
                
                {sqlQuery && (
                  <Card title="Generated SQL" size="small">
                    <MonacoEditor
                      height="200px"
                      language="sql"
                      theme="vs-light"
                      value={sqlQuery}
                      onChange={(value) => setSqlQuery(value || '')}
                      options={{
                        minimap: { enabled: false },
                        fontSize: 14,
                      }}
                    />
                  </Card>
                )}
              </Space>
            </TabPane>

            <TabPane tab="SQL Editor" key="sql">
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <MonacoEditor
                  height="300px"
                  language="sql"
                  theme="vs-light"
                  value={sqlQuery}
                  onChange={(value) => setSqlQuery(value || '')}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                  }}
                />
                <Space>
                  <Button 
                    type="primary" 
                    icon={<PlayCircleOutlined />}
                    onClick={handleSQLQuery}
                    loading={loading}
                  >
                    Execute SQL
                  </Button>
                  <Button 
                    icon={<ClearOutlined />}
                    onClick={() => {
                      setSqlQuery('')
                      setQueryResults(null)
                    }}
                  >
                    Clear
                  </Button>
                </Space>
              </Space>
            </TabPane>
          </Tabs>
        </Space>
      </Card>

      <Card 
        title="Query Results" 
        style={{ marginTop: 24 }}
        extra={
          queryResults && (
            <Space>
              <Button 
                icon={<DownloadOutlined />} 
                onClick={() => handleExport('csv')}
              >
                Export CSV
              </Button>
              <Button 
                icon={<DownloadOutlined />} 
                onClick={() => handleExport('excel')}
              >
                Export Excel
              </Button>
              <Button 
                icon={<DownloadOutlined />} 
                onClick={() => handleExport('json')}
              >
                Export JSON
              </Button>
            </Space>
          )
        }
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: 50 }}>
            <Spin size="large" />
          </div>
        ) : queryResults && queryResults.length > 0 ? (
          <Table
            columns={getTableColumns()}
            dataSource={queryResults}
            rowKey={(record, index) => index?.toString() || '0'}
            scroll={{ x: true }}
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
              showTotal: (total) => `Total ${total} rows`,
            }}
          />
        ) : (
          <Empty description="No results to display" />
        )}
      </Card>
    </div>
  )
}

export default QueryPage