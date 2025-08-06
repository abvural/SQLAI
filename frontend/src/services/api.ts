import axios, { AxiosInstance } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  })

  client.interceptors.request.use(
    (config) => {
      return config
    },
    (error) => {
      return Promise.reject(error)
    }
  )

  client.interceptors.response.use(
    (response) => {
      return response
    },
    (error) => {
      if (error.response?.status === 401) {
        // Handle unauthorized
      }
      return Promise.reject(error)
    }
  )

  return client
}

const apiClient = createApiClient()

export const healthApi = {
  checkHealth: async () => {
    const response = await apiClient.get('/health')
    return response.data
  },
  
  getDetailedHealth: async () => {
    const response = await apiClient.get('/health/detailed')
    return response.data
  },
}

export const databaseApi = {
  testConnection: async (connectionData: any) => {
    const response = await apiClient.post('/databases/connect', connectionData)
    return response.data
  },
  
  listDatabases: async () => {
    const response = await apiClient.get('/databases/list')
    return response.data
  },
  
  analyzeDatabase: async (dbId: string) => {
    const response = await apiClient.post(`/databases/analyze/${dbId}`)
    return response.data
  },
  
  getDatabaseStatus: async (dbId: string) => {
    const response = await apiClient.get(`/databases/${dbId}/status`)
    return response.data
  },
}

export const schemaApi = {
  getTables: async (dbId: string) => {
    const response = await apiClient.get(`/schema/${dbId}/tables`)
    return response.data
  },
  
  getRelationships: async (dbId: string) => {
    const response = await apiClient.get(`/schema/${dbId}/relationships`)
    return response.data
  },
  
  getTableDetails: async (dbId: string, tableName: string) => {
    const response = await apiClient.get(`/schema/${dbId}/table/${tableName}`)
    return response.data
  },
  
  getSchemaGraph: async (dbId: string) => {
    const response = await apiClient.get(`/schema/${dbId}/graph`)
    return response.data
  },
}

export const queryApi = {
  executeNaturalQuery: async (data: any) => {
    const response = await apiClient.post('/query/natural', data)
    return response.data
  },
  
  executeSQLQuery: async (data: any) => {
    const response = await apiClient.post('/query/execute', data)
    return response.data
  },
  
  cancelQuery: async (queryId: string) => {
    const response = await apiClient.put(`/query/cancel/${queryId}`)
    return response.data
  },
  
  getQueryProgress: async (queryId: string) => {
    const response = await apiClient.get(`/query/progress/${queryId}`)
    return response.data
  },
  
  getQueryHistory: async (params?: any) => {
    const response = await apiClient.get('/query/history', { params })
    return response.data
  },
  
  exportResults: async (queryId: string, format: string) => {
    const response = await apiClient.post('/query/export', { query_id: queryId, format })
    return response.data
  },
}

export const analyticsApi = {
  getDatabaseInsights: async (dbId: string) => {
    const response = await apiClient.get(`/analytics/database-insights/${dbId}`)
    return response.data
  },
  
  getTableUsage: async (dbId: string, limit?: number) => {
    const response = await apiClient.get(`/analytics/table-usage/${dbId}`, {
      params: { limit }
    })
    return response.data
  },
  
  getSystemHealth: async () => {
    const response = await apiClient.get('/analytics/monitoring/system-health')
    return response.data
  },
  
  getQueryPerformance: async () => {
    const response = await apiClient.get('/analytics/monitoring/query-performance')
    return response.data
  },
}

export default apiClient