import React, { useState, useEffect } from 'react'
import { 
  Card, 
  Select, 
  Table, 
  Space, 
  Button,
  Descriptions,
  Tag,
  Empty,
  Spin,
  message
} from 'antd'
import {
  TableOutlined,
  NodeIndexOutlined,
  ReloadOutlined
} from '@ant-design/icons'
import { schemaApi } from '../services/api'

const SchemaPage: React.FC = () => {
  const [selectedDb, setSelectedDb] = useState<string>('29f76a6e-ada9-4d9e-9b64-f3f65658e7c2')
  const [selectedTable, setSelectedTable] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [tables, setTables] = useState<any[]>([])
  const [columns, setColumns] = useState<any[]>([])
  const [tableDetails, setTableDetails] = useState<any>(null)

  // Load tables when database is selected
  useEffect(() => {
    if (selectedDb) {
      loadTables()
    }
  }, [selectedDb])

  // Load table details when table is selected
  useEffect(() => {
    if (selectedDb && selectedTable) {
      loadTableDetails()
    }
  }, [selectedDb, selectedTable])

  const loadTables = async () => {
    setLoading(true)
    try {
      const response = await schemaApi.getTables(selectedDb)
      setTables(response)
      message.success(`Loaded ${response.length} tables`)
    } catch (error: any) {
      message.error('Failed to load tables: ' + (error.response?.data?.detail || error.message))
      setTables([])
    } finally {
      setLoading(false)
    }
  }

  const loadTableDetails = async () => {
    try {
      const response = await schemaApi.getTableDetails(selectedDb, selectedTable)
      setTableDetails(response)
      setColumns(response.columns || [])
    } catch (error: any) {
      message.error('Failed to load table details: ' + (error.response?.data?.detail || error.message))
      setColumns([])
    }
  }

  const tableColumns = [
    {
      title: 'Table Name',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => (
        <Space>
          <TableOutlined />
          <a onClick={() => setSelectedTable(text)}>{text}</a>
        </Space>
      ),
    },
    {
      title: 'Schema',
      dataIndex: 'schema',
      key: 'schema',
    },
    {
      title: 'Row Count',
      dataIndex: 'row_count',
      key: 'row_count',
    },
    {
      title: 'Size',
      dataIndex: 'size',
      key: 'size',
    },
  ]

  const columnColumns = [
    {
      title: 'Column Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Data Type',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: 'Nullable',
      dataIndex: 'nullable',
      key: 'nullable',
      render: (nullable: boolean) => (
        <Tag color={nullable ? 'orange' : 'green'}>
          {nullable ? 'YES' : 'NO'}
        </Tag>
      ),
    },
    {
      title: 'Key',
      key: 'key',
      render: (record: any) => {
        if (record.primary_key) return <Tag color="blue">PK</Tag>
        if (record.foreign_key) return <Tag color="purple">FK</Tag>
        return null
      },
    },
    {
      title: 'Default',
      dataIndex: 'default_value',
      key: 'default_value',
    },
  ]

  return (
    <div>
      <Card title="Schema Explorer">
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

          {selectedDb && (
            <>
              <Card 
                title="Tables" 
                size="small"
                extra={
                  <Button 
                    icon={<ReloadOutlined />} 
                    size="small"
                    onClick={loadTables}
                    loading={loading}
                  >
                    Refresh
                  </Button>
                }
              >
                {loading ? (
                  <div style={{ textAlign: 'center', padding: 50 }}>
                    <Spin />
                  </div>
                ) : tables.length > 0 ? (
                  <Table
                    columns={tableColumns}
                    dataSource={tables}
                    rowKey="name"
                    pagination={false}
                    size="small"
                  />
                ) : (
                  <Empty description="No tables found" />
                )}
              </Card>

              {selectedTable && tableDetails && (
                <Card title={`Table: ${selectedTable}`} size="small">
                  <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    <Descriptions bordered size="small">
                      <Descriptions.Item label="Schema">{tableDetails.schema || 'public'}</Descriptions.Item>
                      <Descriptions.Item label="Row Count">{tableDetails.row_count || 0}</Descriptions.Item>
                      <Descriptions.Item label="Size">{tableDetails.size || '0 KB'}</Descriptions.Item>
                      <Descriptions.Item label="Indexes">{tableDetails.indexes?.length || 0}</Descriptions.Item>
                      <Descriptions.Item label="Constraints">{tableDetails.constraints?.length || 0}</Descriptions.Item>
                    </Descriptions>

                    <div>
                      <h4>Columns</h4>
                      {columns.length > 0 ? (
                        <Table
                          columns={columnColumns}
                          dataSource={columns}
                          rowKey="name"
                          pagination={false}
                          size="small"
                        />
                      ) : (
                        <Empty description="No columns found" />
                      )}
                    </div>
                  </Space>
                </Card>
              )}
            </>
          )}
        </Space>
      </Card>

      <Card title="Schema Visualization" style={{ marginTop: 24 }}>
        <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Empty description="Select a database to view schema visualization" />
        </div>
      </Card>
    </div>
  )
}

export default SchemaPage