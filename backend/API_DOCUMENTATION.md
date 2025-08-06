# SQLAI API Documentation

## Overview

SQLAI is an intelligent PostgreSQL database analysis and query assistant that provides:
- Natural language to SQL conversion with Turkish language support
- Real-time schema analysis and relationship mapping
- Async query execution with progress tracking
- Multi-format export capabilities (CSV, Excel, JSON)
- WebSocket-based real-time notifications

**Base URL**: `http://localhost:8000`

## Authentication

Currently, no authentication is required for the API endpoints. In production, implement appropriate authentication and authorization mechanisms.

## API Endpoints

### 1. Health & Status

#### GET /api/health
Get system health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-06T16:30:00.000Z",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "query_executor": "healthy",
    "websocket": "healthy"
  }
}
```

### 2. Database Management

#### GET /api/databases
List all configured database connections.

**Response:**
```json
{
  "databases": [
    {
      "id": "db-uuid-123",
      "name": "Production Database",
      "host": "localhost",
      "database": "myapp",
      "status": "connected",
      "last_connected": "2025-08-06T16:30:00.000Z"
    }
  ]
}
```

#### POST /api/databases
Add a new database connection.

**Request Body:**
```json
{
  "name": "Test Database",
  "host": "localhost",
  "port": 5432,
  "database": "testdb",
  "username": "testuser",
  "password": "testpass",
  "ssl_mode": "prefer"
}
```

**Response:**
```json
{
  "id": "new-db-uuid",
  "message": "Database connection added successfully"
}
```

#### GET /api/databases/{db_id}/test
Test database connection.

**Response:**
```json
{
  "success": true,
  "message": "Connection successful",
  "response_time_ms": 45
}
```

#### DELETE /api/databases/{db_id}
Remove database connection.

**Response:**
```json
{
  "message": "Database connection removed successfully"
}
```

### 3. Schema Analysis

#### GET /api/schema/{db_id}
Get database schema information.

**Query Parameters:**
- `deep_analysis` (boolean, optional): Perform deep schema analysis (default: false)

**Response:**
```json
{
  "database_id": "db-uuid-123",
  "analysis_timestamp": "2025-08-06T16:30:00.000Z",
  "schemas": {
    "public": {
      "tables": [
        {
          "name": "users",
          "columns": [
            {
              "name": "id",
              "type": "integer",
              "nullable": false,
              "is_primary_key": true
            },
            {
              "name": "email",
              "type": "varchar(255)",
              "nullable": false,
              "is_unique": true
            }
          ],
          "row_count": 1500,
          "indexes": [
            {
              "name": "users_pkey",
              "is_primary": true,
              "is_unique": true
            }
          ]
        }
      ],
      "relationships": [
        {
          "from_table": "orders",
          "from_column": "user_id",
          "to_table": "users",
          "to_column": "id",
          "constraint_name": "orders_user_id_fkey"
        }
      ]
    }
  },
  "insights": {
    "total_tables": 15,
    "total_relationships": 23,
    "largest_table": "orders",
    "hub_tables": ["users", "products"]
  }
}
```

#### GET /api/schema/{db_id}/visualization
Get schema visualization data.

**Response:**
```json
{
  "nodes": [
    {
      "id": "public.users",
      "label": "users",
      "schema": "public",
      "size": 10,
      "importance": 0.8,
      "has_pk": true
    }
  ],
  "edges": [
    {
      "source": "public.orders",
      "target": "public.users",
      "from_column": "user_id",
      "to_column": "id",
      "type": "many-to-one"
    }
  ],
  "stats": {
    "total_nodes": 4,
    "total_edges": 3,
    "is_connected": true
  }
}
```

### 4. Query Processing

#### POST /api/query/natural
Execute natural language query.

**Request Body:**
```json
{
  "query": "Show me all customers from Istanbul",
  "database_id": "db-uuid-123",
  "user_id": "user-123"
}
```

**Response:**
```json
{
  "success": true,
  "query_id": "query-uuid-456",
  "sql": "SELECT * FROM customers WHERE city = 'Istanbul'",
  "confidence": 0.92,
  "message": "Query submitted for execution",
  "interpretation": {
    "tables": ["customers"],
    "columns": ["*"],
    "explanation": "Retrieving all customers filtered by city"
  },
  "alternatives": [
    {
      "sql": "SELECT name, email FROM customers WHERE city = 'Istanbul'",
      "confidence": 0.85,
      "explanation": "More specific column selection"
    }
  ]
}
```

**Ambiguous Query Response:**
```json
{
  "success": false,
  "ambiguous": true,
  "message": "Multiple interpretations found. Please clarify:",
  "interpretations": [
    {
      "sql": "SELECT * FROM customers WHERE city = 'Istanbul'",
      "confidence": 0.7,
      "explanation": "Query against customers table"
    },
    {
      "sql": "SELECT * FROM users WHERE city = 'Istanbul'",
      "confidence": 0.6,
      "explanation": "Query against users table"
    }
  ],
  "suggestions": [
    "Specify which table you want to query",
    "Add more specific conditions"
  ]
}
```

#### POST /api/query/execute
Execute SQL query directly.

**Request Body:**
```json
{
  "sql": "SELECT COUNT(*) FROM users WHERE active = true",
  "database_id": "db-uuid-123",
  "user_id": "user-123",
  "stream": false
}
```

**Response:**
```json
{
  "success": true,
  "query_id": "query-uuid-789",
  "sql": "SELECT COUNT(*) FROM users WHERE active = true",
  "message": "Query submitted for execution"
}
```

#### GET /api/query/status/{query_id}
Get query execution status.

**Response:**
```json
{
  "query_id": "query-uuid-456",
  "status": "running",
  "progress": 0.65,
  "rows_processed": 650,
  "start_time": "2025-08-06T16:30:00.000Z",
  "error": null
}
```

**Status Values:**
- `running`: Query is currently executing
- `completed`: Query completed successfully
- `failed`: Query execution failed
- `cancelled`: Query was cancelled by user

#### GET /api/query/results/{query_id}
Get query results with pagination.

**Query Parameters:**
- `offset` (integer, optional): Starting offset (default: 0)
- `limit` (integer, optional): Number of rows to return (default: 1000)

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com",
      "created_at": "2025-01-01T10:00:00.000Z"
    }
  ],
  "total_rows": 1,
  "offset": 0,
  "limit": 1000,
  "truncated": false
}
```

#### PUT /api/query/cancel/{query_id}
Cancel a running query.

**Response:**
```json
{
  "message": "Query query-uuid-456 cancellation requested"
}
```

#### GET /api/query/export/{query_id}
Export query results.

**Query Parameters:**
- `format` (string, required): Export format (csv, excel, json)

**Response:**
- Binary data with appropriate Content-Type and Content-Disposition headers
- Filename: `query_results_{query_id}.{extension}`

#### GET /api/query/history
Get query execution history.

**Query Parameters:**
- `user_id` (string, optional): Filter by user ID
- `limit` (integer, optional): Maximum records to return (default: 50)

**Response:**
```json
{
  "history": [
    {
      "query_id": "query-uuid-123",
      "database_id": "db-uuid-456",
      "sql_query": "SELECT * FROM users...",
      "status": "completed",
      "rows_affected": 100,
      "execution_time": 1.23,
      "created_at": "2025-08-06T16:30:00.000Z",
      "error_message": null
    }
  ]
}
```

#### POST /api/query/validate
Validate SQL query.

**Request Body:**
```json
{
  "sql": "SELECT * FROM users WHERE id = ?"
}
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "safe": true
}
```

### 5. Dashboard

#### GET /api/dashboard/overview
Get dashboard overview.

**Response:**
```json
{
  "statistics": {
    "total_databases": 3,
    "active_connections": 2,
    "recent_queries": 15,
    "system_status": "healthy"
  },
  "connections": [
    {
      "id": "db-uuid-123",
      "name": "Production DB",
      "status": "connected"
    }
  ],
  "recent_history": [
    {
      "query_id": "query-uuid-456",
      "sql_query": "SELECT COUNT(*) FROM users",
      "status": "completed"
    }
  ],
  "timestamp": "2025-08-06T16:30:00.000Z"
}
```

#### GET /api/dashboard/database/{db_id}/summary
Get database summary.

**Response:**
```json
{
  "connection": {
    "id": "db-uuid-123",
    "name": "Production Database",
    "host": "localhost",
    "database": "myapp",
    "status": "connected"
  },
  "schema_stats": {
    "total_schemas": 1,
    "total_tables": 15,
    "total_columns": 120,
    "total_relationships": 23,
    "largest_table": "orders",
    "most_connected_table": "users"
  },
  "analysis_timestamp": "2025-08-06T16:30:00.000Z"
}
```

#### GET /api/dashboard/health
Get system health status.

**Response:**
```json
{
  "status": "healthy",
  "connections": {
    "total": 3,
    "healthy": 3,
    "unhealthy": 0
  },
  "system": {
    "memory_usage_percent": 45.2,
    "timestamp": "2025-08-06T16:30:00.000Z"
  }
}
```

#### GET /api/dashboard/analytics
Get usage analytics.

**Response:**
```json
{
  "query_statistics": {
    "total_queries": 150,
    "successful_queries": 142,
    "failed_queries": 8,
    "success_rate": 94.67,
    "average_execution_time": 1.23
  },
  "database_usage": {
    "most_used": [
      ["db-uuid-123", 45],
      ["db-uuid-456", 30]
    ]
  },
  "generated_at": "2025-08-06T16:30:00.000Z"
}
```

### 6. WebSocket Endpoints

#### WS /api/query/progress/{query_id}
Real-time query progress updates.

**Messages Received:**
```json
{
  "query_id": "query-uuid-456",
  "status": "running",
  "progress": 0.45,
  "rows_processed": 450,
  "timestamp": "2025-08-06T16:30:00.000Z"
}
```

#### WS /api/notifications
System notifications and alerts.

**Messages Received:**
```json
{
  "type": "system_notification",
  "notification_type": "connection_lost",
  "message": "Database connection lost",
  "severity": "warning",
  "timestamp": "2025-08-06T16:30:00.000Z"
}
```

## Error Responses

All API endpoints return consistent error responses:

```json
{
  "error": "Error description",
  "error_code": "VALIDATION_ERROR",
  "details": {
    "field": "Additional error details"
  },
  "timestamp": "2025-08-06T16:30:00.000Z"
}
```

### Common HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict
- `422 Unprocessable Entity`: Validation failed
- `500 Internal Server Error`: Server error

## Rate Limiting

Currently, no rate limiting is implemented. In production, consider implementing rate limiting based on:
- API key/user
- IP address
- Endpoint type

## Performance Considerations

- **Pagination**: Use `offset` and `limit` parameters for large result sets
- **Streaming**: Use `stream=true` for large query results
- **Caching**: Schema analysis results are cached for 1 hour
- **Memory**: Large exports are limited to prevent memory issues

## Turkish Language Support

Natural language queries support Turkish keywords:
- "En çok" → MAX aggregation
- "Toplam" → SUM aggregation  
- "Sayı" → COUNT aggregation
- "Ortalama" → AVG aggregation
- "Listele" → SELECT operation

Example:
```json
{
  "query": "En çok sipariş veren müşteriyi bul",
  "database_id": "db-uuid-123"
}
```

## Security Notes

1. **SQL Injection**: All queries are validated and parameterized
2. **Credential Storage**: Database credentials are encrypted
3. **Query Validation**: Dangerous SQL patterns are blocked
4. **Input Sanitization**: All user inputs are validated

## Examples

### Complete Workflow Example

1. **Add Database:**
```bash
curl -X POST http://localhost:8000/api/databases \
  -H "Content-Type: application/json" \
  -d '{"name":"Test DB","host":"localhost","database":"test","username":"user","password":"pass"}'
```

2. **Analyze Schema:**
```bash
curl http://localhost:8000/api/schema/{db_id}
```

3. **Execute Natural Language Query:**
```bash
curl -X POST http://localhost:8000/api/query/natural \
  -H "Content-Type: application/json" \
  -d '{"query":"Show all users","database_id":"{db_id}"}'
```

4. **Get Results:**
```bash
curl http://localhost:8000/api/query/results/{query_id}
```

5. **Export Results:**
```bash
curl http://localhost:8000/api/query/export/{query_id}?format=csv
```