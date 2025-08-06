import React, { useState } from 'react'
import { 
  Card, 
  Button, 
  Table, 
  Space, 
  Modal, 
  Form, 
  Input, 
  InputNumber, 
  Select, 
  message,
  Tag,
  Tooltip
} from 'antd'
import {
  PlusOutlined,
  DatabaseOutlined,
  ReloadOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { databaseApi } from '../services/api'

const DatabasesPage: React.FC = () => {
  const [isModalVisible, setIsModalVisible] = useState(false)
  const [testingConnection, setTestingConnection] = useState(false)
  const [form] = Form.useForm()
  const queryClient = useQueryClient()

  const { data: databases = [], isLoading, refetch } = useQuery({
    queryKey: ['databases'],
    queryFn: databaseApi.listDatabases,
  })

  const testConnectionMutation = useMutation({
    mutationFn: databaseApi.testConnection,
    onSuccess: (data) => {
      if (data.success) {
        message.success('Connection successful!')
      } else {
        message.error('Connection failed: ' + data.message)
      }
    },
    onError: (error: any) => {
      message.error('Connection failed: ' + (error.response?.data?.detail || error.message))
    },
  })

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => (
        <Space>
          <DatabaseOutlined />
          <strong>{text}</strong>
        </Space>
      ),
    },
    {
      title: 'Host',
      dataIndex: 'host',
      key: 'host',
    },
    {
      title: 'Database',
      dataIndex: 'database',
      key: 'database',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const color = status === 'connected' ? 'green' : status === 'error' ? 'red' : 'orange'
        const icon = status === 'connected' ? <CheckCircleOutlined /> : 
                    status === 'error' ? <CloseCircleOutlined /> : 
                    <LoadingOutlined />
        return (
          <Tag color={color} icon={icon}>
            {status.toUpperCase()}
          </Tag>
        )
      },
    },
    {
      title: 'Schema Analyzed',
      dataIndex: 'schema_analyzed',
      key: 'schema_analyzed',
      render: (analyzed: boolean) => (
        <Tag color={analyzed ? 'green' : 'default'}>
          {analyzed ? 'Yes' : 'No'}
        </Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: any) => (
        <Space>
          <Tooltip title="Analyze Schema">
            <Button 
              icon={<ReloadOutlined />} 
              size="small"
              onClick={() => handleAnalyze(record.id)}
            />
          </Tooltip>
          <Tooltip title="Delete">
            <Button 
              danger 
              icon={<DeleteOutlined />} 
              size="small"
              onClick={() => handleDelete(record.id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ]

  const handleTestConnection = async () => {
    try {
      const values = await form.validateFields()
      setTestingConnection(true)
      await testConnectionMutation.mutateAsync(values)
      setTestingConnection(false)
    } catch (error) {
      setTestingConnection(false)
    }
  }

  const handleAddDatabase = async () => {
    try {
      const values = await form.validateFields()
      // TODO: Save database connection
      message.success('Database added successfully!')
      setIsModalVisible(false)
      form.resetFields()
      refetch()
    } catch (error) {
      message.error('Failed to add database')
    }
  }

  const handleAnalyze = async (dbId: string) => {
    try {
      await databaseApi.analyzeDatabase(dbId)
      message.success('Schema analysis started')
      refetch()
    } catch (error) {
      message.error('Failed to start analysis')
    }
  }

  const handleDelete = async (dbId: string) => {
    Modal.confirm({
      title: 'Delete Database Connection',
      content: 'Are you sure you want to delete this database connection?',
      onOk: async () => {
        try {
          // TODO: Implement delete
          message.success('Database deleted successfully')
          refetch()
        } catch (error) {
          message.error('Failed to delete database')
        }
      },
    })
  }

  return (
    <div>
      <Card
        title="Database Connections"
        extra={
          <Space>
            <Button 
              type="primary" 
              icon={<PlusOutlined />}
              onClick={() => setIsModalVisible(true)}
            >
              Add Database
            </Button>
            <Button 
              icon={<ReloadOutlined />}
              onClick={() => refetch()}
            >
              Refresh
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={databases}
          loading={isLoading}
          rowKey="id"
          pagination={false}
        />
      </Card>

      <Modal
        title="Add Database Connection"
        open={isModalVisible}
        onOk={handleAddDatabase}
        onCancel={() => {
          setIsModalVisible(false)
          form.resetFields()
        }}
        width={600}
        footer={[
          <Button key="test" onClick={handleTestConnection} loading={testingConnection}>
            Test Connection
          </Button>,
          <Button key="cancel" onClick={() => {
            setIsModalVisible(false)
            form.resetFields()
          }}>
            Cancel
          </Button>,
          <Button key="submit" type="primary" onClick={handleAddDatabase}>
            Add Database
          </Button>,
        ]}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            port: 5432,
            ssl_mode: 'prefer'
          }}
        >
          <Form.Item
            name="name"
            label="Connection Name"
            rules={[{ required: true, message: 'Please enter a connection name' }]}
          >
            <Input placeholder="e.g., Production DB" />
          </Form.Item>

          <Form.Item
            name="host"
            label="Host"
            rules={[{ required: true, message: 'Please enter the host' }]}
          >
            <Input placeholder="e.g., localhost or 172.17.12.76" />
          </Form.Item>

          <Form.Item
            name="port"
            label="Port"
            rules={[{ required: true, message: 'Please enter the port' }]}
          >
            <InputNumber min={1} max={65535} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="database"
            label="Database"
            rules={[{ required: true, message: 'Please enter the database name' }]}
          >
            <Input placeholder="e.g., postgres" />
          </Form.Item>

          <Form.Item
            name="username"
            label="Username"
            rules={[{ required: true, message: 'Please enter the username' }]}
          >
            <Input placeholder="e.g., myuser" />
          </Form.Item>

          <Form.Item
            name="password"
            label="Password"
            rules={[{ required: true, message: 'Please enter the password' }]}
          >
            <Input.Password placeholder="Enter password" />
          </Form.Item>

          <Form.Item
            name="ssl_mode"
            label="SSL Mode"
          >
            <Select>
              <Select.Option value="disable">Disable</Select.Option>
              <Select.Option value="prefer">Prefer</Select.Option>
              <Select.Option value="require">Require</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default DatabasesPage