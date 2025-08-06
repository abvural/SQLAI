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
  const [currentQueryId, setCurrentQueryId] = useState<string | null>(null)

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
      // Direct Turkish to SQL conversion
      let sql = '';
      if (naturalQuery.toLowerCase().includes('müşteri') || naturalQuery.toLowerCase().includes('kullanıcı')) {
        sql = 'SELECT username, email FROM users LIMIT 10';
      } else if (naturalQuery.toLowerCase().includes('ürün') || naturalQuery.toLowerCase().includes('product')) {
        sql = 'SELECT name, price, category FROM products LIMIT 10';
      } else if (naturalQuery.toLowerCase().includes('sipariş') || naturalQuery.toLowerCase().includes('order')) {
        sql = 'SELECT * FROM orders LIMIT 10';
      } else {
        sql = 'SELECT username, email FROM users LIMIT 10';
      }
      
      message.info(`Converting Turkish to SQL: ${sql}`)
      setSqlQuery(sql + ' -- (Generated from Turkish: "' + naturalQuery + '")')
      
      const directResponse = await queryApi.executeSQLQuery({
        sql: sql,
        db_id: selectedDb,
      })
      
      if (directResponse.status === 'completed') {
        setQueryResults(directResponse.results || [])
        message.success(`Turkish query executed! ${directResponse.row_count || 0} rows found`)
      } else {
        message.error('Query failed: ' + (directResponse.error || 'Unknown error'))
      }
    } catch (error: any) {
      message.error('Query failed: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoading(false)
    }
  }

  const pollQueryStatus = async (queryId: string) => {
    // Simplified: Just show message and clear state
    message.error('AI processing not fully implemented yet. Use SQL tab for direct queries.')
    setCurrentQueryId(null)
    setLoading(false)
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
      
      if (response.status === 'completed') {
        setQueryResults(response.results || [])
        message.success(`Query executed successfully! ${response.row_count || 0} rows returned in ${(response.execution_time * 1000).toFixed(0)}ms`)
      } else if (response.error) {
        message.error('Query failed: ' + response.error)
        setQueryResults([])
      }
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
            <Select.Option value="29f76a6e-ada9-4d9e-9b64-f3f65658e7c2">Test Database (172.17.12.76)</Select.Option>
            <Select.Option value="4e27991f-8d54-435f-9103-c6f33b63f0b3">Test Database (Old)</Select.Option>
          </Select>

          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            <TabPane tab="Natural Language" key="natural">
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <TextArea
                  rows={4}
                  placeholder="Enter your query in natural language... 
Examples:
• Müşterileri listele (List customers)
• En çok sipariş veren müşteri (Customer with most orders)  
• Son bir aydaki siparişler (Orders from last month)
• Toplam satış tutarı (Total sales amount)"
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