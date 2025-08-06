import React, { useState } from 'react'
import { 
  Card, 
  Select, 
  Table, 
  Space, 
  Button,
  Descriptions,
  Tag,
  Empty,
  Spin
} from 'antd'
import {
  TableOutlined,
  NodeIndexOutlined,
  ReloadOutlined
} from '@ant-design/icons'

const SchemaPage: React.FC = () => {
  const [selectedDb, setSelectedDb] = useState<string>('')
  const [selectedTable, setSelectedTable] = useState<string>('')
  const [loading, setLoading] = useState(false)

  // Mock data - will be replaced with API calls
  const tables = []
  const columns = []

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
      dataIndex: 'data_type',
      key: 'data_type',
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
            {/* TODO: Load databases dynamically */}
            <Select.Option value="db1">Test Database</Select.Option>
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
                    onClick={() => {/* TODO: Refresh tables */}}
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

              {selectedTable && (
                <Card title={`Table: ${selectedTable}`} size="small">
                  <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    <Descriptions bordered size="small">
                      <Descriptions.Item label="Schema">public</Descriptions.Item>
                      <Descriptions.Item label="Row Count">0</Descriptions.Item>
                      <Descriptions.Item label="Size">0 KB</Descriptions.Item>
                      <Descriptions.Item label="Created">-</Descriptions.Item>
                      <Descriptions.Item label="Modified">-</Descriptions.Item>
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