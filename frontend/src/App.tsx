import React, { useState, useEffect } from 'react'
import { Layout, Menu, Button, Space, Typography, Spin, Alert } from 'antd'
import {
  DatabaseOutlined,
  CodeOutlined,
  BarChartOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  HeartOutlined,
} from '@ant-design/icons'
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import DatabasesPage from './pages/DatabasesPage'
import QueryPage from './pages/QueryPage'
import SchemaPage from './pages/SchemaPage'
import AnalyticsPage from './pages/AnalyticsPage'
import { healthApi } from './services/api'

const { Header, Sider, Content, Footer } = Layout
const { Title } = Typography

function AppContent() {
  const [collapsed, setCollapsed] = useState(false)
  const [healthStatus, setHealthStatus] = useState<'loading' | 'healthy' | 'error'>('loading')
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  const checkHealth = async () => {
    try {
      const response = await healthApi.checkHealth()
      setHealthStatus(response.status === 'healthy' ? 'healthy' : 'error')
    } catch (error) {
      setHealthStatus('error')
    }
  }

  const menuItems = [
    {
      key: '/databases',
      icon: <DatabaseOutlined />,
      label: 'Databases',
    },
    {
      key: '/query',
      icon: <CodeOutlined />,
      label: 'Query',
    },
    {
      key: '/schema',
      icon: <SettingOutlined />,
      label: 'Schema',
    },
    {
      key: '/analytics',
      icon: <BarChartOutlined />,
      label: 'Analytics',
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed}>
        <div style={{ 
          height: 64, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          color: 'white',
          fontSize: collapsed ? 20 : 24,
          fontWeight: 'bold'
        }}>
          {collapsed ? 'SQL' : 'SQLAI'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ 
          padding: '0 24px', 
          background: '#fff', 
          display: 'flex', 
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <Space>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
            />
            <Title level={4} style={{ margin: 0 }}>
              Intelligent PostgreSQL Database Assistant
            </Title>
          </Space>
          <Space>
            {healthStatus === 'loading' && <Spin size="small" />}
            {healthStatus === 'healthy' && (
              <Space>
                <HeartOutlined style={{ color: '#52c41a' }} />
                <span style={{ color: '#52c41a' }}>Connected</span>
              </Space>
            )}
            {healthStatus === 'error' && (
              <Alert
                message="Backend Disconnected"
                type="error"
                showIcon
                banner
              />
            )}
          </Space>
        </Header>
        <Content style={{ margin: '24px', minHeight: 280 }}>
          <Routes>
            <Route path="/" element={<DatabasesPage />} />
            <Route path="/databases" element={<DatabasesPage />} />
            <Route path="/query" element={<QueryPage />} />
            <Route path="/schema" element={<SchemaPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
          </Routes>
        </Content>
        <Footer style={{ textAlign: 'center' }}>
          SQLAI ©{new Date().getFullYear()} - Intelligent Database Assistant
        </Footer>
      </Layout>
    </Layout>
  )
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  )
}

export default App