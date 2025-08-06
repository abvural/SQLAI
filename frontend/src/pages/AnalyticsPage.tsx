import React, { useState } from 'react'
import { 
  Card, 
  Row, 
  Col, 
  Statistic, 
  Progress,
  Table,
  Select,
  Empty
} from 'antd'
import {
  DatabaseOutlined,
  TableOutlined,
  LinkOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  BarChartOutlined
} from '@ant-design/icons'
import { 
  BarChart, 
  Bar, 
  LineChart, 
  Line, 
  PieChart, 
  Pie, 
  Cell,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from 'recharts'

const AnalyticsPage: React.FC = () => {
  const [selectedDb, setSelectedDb] = useState<string>('')

  // Mock data - will be replaced with API calls
  const queryPerformanceData = [
    { time: '00:00', queries: 45 },
    { time: '04:00', queries: 30 },
    { time: '08:00', queries: 120 },
    { time: '12:00', queries: 180 },
    { time: '16:00', queries: 150 },
    { time: '20:00', queries: 80 },
  ]

  const tableUsageData = [
    { name: 'users', usage: 450 },
    { name: 'orders', usage: 380 },
    { name: 'products', usage: 320 },
    { name: 'categories', usage: 180 },
    { name: 'reviews', usage: 150 },
  ]

  const queryTypeData = [
    { name: 'SELECT', value: 60, color: '#0088FE' },
    { name: 'INSERT', value: 20, color: '#00C49F' },
    { name: 'UPDATE', value: 15, color: '#FFBB28' },
    { name: 'DELETE', value: 5, color: '#FF8042' },
  ]

  const slowQueries = [
    { query: 'SELECT * FROM orders JOIN ...', time: 5.2, count: 12 },
    { query: 'UPDATE products SET ...', time: 3.8, count: 8 },
    { query: 'SELECT COUNT(*) FROM ...', time: 2.5, count: 15 },
  ]

  return (
    <div>
      <Card title="Analytics Dashboard">
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

          {selectedDb ? (
            <>
              <Row gutter={16}>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="Total Tables"
                      value={0}
                      prefix={<TableOutlined />}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="Total Columns"
                      value={0}
                      prefix={<DatabaseOutlined />}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="Relationships"
                      value={0}
                      prefix={<LinkOutlined />}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="Avg Query Time"
                      value={0}
                      suffix="ms"
                      prefix={<ClockCircleOutlined />}
                    />
                  </Card>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={12}>
                  <Card title="Query Performance Over Time">
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={queryPerformanceData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="time" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey="queries" stroke="#8884d8" />
                      </LineChart>
                    </ResponsiveContainer>
                  </Card>
                </Col>
                <Col span={12}>
                  <Card title="Most Used Tables">
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={tableUsageData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="usage" fill="#82ca9d" />
                      </BarChart>
                    </ResponsiveContainer>
                  </Card>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Card title="Query Types Distribution">
                    <ResponsiveContainer width="100%" height={300}>
                      <PieChart>
                        <Pie
                          data={queryTypeData}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={(entry) => `${entry.name}: ${entry.value}%`}
                          outerRadius={80}
                          fill="#8884d8"
                          dataKey="value"
                        >
                          {queryTypeData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </Card>
                </Col>
                <Col span={16}>
                  <Card title="Slow Queries">
                    <Table
                      dataSource={slowQueries}
                      columns={[
                        {
                          title: 'Query',
                          dataIndex: 'query',
                          key: 'query',
                          ellipsis: true,
                        },
                        {
                          title: 'Avg Time (s)',
                          dataIndex: 'time',
                          key: 'time',
                          width: 120,
                          render: (time: number) => (
                            <span style={{ color: time > 3 ? 'red' : 'orange' }}>
                              {time}s
                            </span>
                          ),
                        },
                        {
                          title: 'Count',
                          dataIndex: 'count',
                          key: 'count',
                          width: 80,
                        },
                      ]}
                      pagination={false}
                      size="small"
                    />
                  </Card>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={24}>
                  <Card title="System Health">
                    <Row gutter={16}>
                      <Col span={6}>
                        <div style={{ textAlign: 'center' }}>
                          <Progress type="dashboard" percent={75} />
                          <p>CPU Usage</p>
                        </div>
                      </Col>
                      <Col span={6}>
                        <div style={{ textAlign: 'center' }}>
                          <Progress type="dashboard" percent={60} />
                          <p>Memory Usage</p>
                        </div>
                      </Col>
                      <Col span={6}>
                        <div style={{ textAlign: 'center' }}>
                          <Progress type="dashboard" percent={45} />
                          <p>Connection Pool</p>
                        </div>
                      </Col>
                      <Col span={6}>
                        <div style={{ textAlign: 'center' }}>
                          <Progress type="dashboard" percent={85} status="success" />
                          <p>Cache Hit Rate</p>
                        </div>
                      </Col>
                    </Row>
                  </Card>
                </Col>
              </Row>
            </>
          ) : (
            <Empty description="Select a database to view analytics" />
          )}
        </Space>
      </Card>
    </div>
  )
}

export default AnalyticsPage