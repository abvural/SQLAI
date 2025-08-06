# SQLAI Frontend

Modern React frontend for SQLAI - AI-Powered PostgreSQL Database Assistant

## 🚀 Features

- **Natural Language Queries**: Ask questions in Turkish and English
- **Database Management**: Connect and manage multiple PostgreSQL databases
- **Schema Visualization**: Explore database relationships and structure
- **Real-time Results**: Live query execution with progress tracking
- **Export Options**: CSV, JSON, Excel export formats
- **Modern UI**: Ant Design components with responsive layout

## 🛠️ Tech Stack

- **React 18** + **TypeScript**
- **Ant Design** - UI Component Library
- **Vite** - Build Tool and Dev Server
- **React Query** - Server State Management
- **Monaco Editor** - SQL Code Editor
- **Recharts** - Data Visualization
- **Axios** - HTTP Client

## 📋 Prerequisites

- Node.js 16+
- npm 7+
- SQLAI Backend running on port 8000

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 🔧 Configuration

### Environment Variables (.env)

```env
VITE_API_URL=http://localhost:8000/api
VITE_APP_TITLE=SQLAI - Intelligent PostgreSQL Database Assistant
VITE_APP_VERSION=1.0.0
```

### Development Server

- **Port**: 3000
- **Proxy**: `/api` → `http://localhost:8000`
- **Hot Reload**: Enabled

## 🏗️ Project Structure

```
src/
├── components/          # Reusable React components
├── pages/              # Page components
│   ├── DatabasesPage.tsx
│   ├── QueryPage.tsx
│   ├── SchemaPage.tsx
│   └── AnalyticsPage.tsx
├── services/           # API service functions
│   └── api.ts
├── types/              # TypeScript type definitions
├── hooks/              # Custom React hooks
├── utils/              # Utility functions
├── App.tsx             # Main App component
└── main.tsx            # Application entry point
```

## 🎯 Key Components

### QueryPage
- Natural language query interface
- SQL editor with Monaco
- Query history and results display
- Turkish/English examples

### DatabasesPage
- Database connection management
- Connection testing
- Schema analysis triggers

### SchemaPage
- Database schema visualization
- Table relationships
- Entity-Relationship diagrams

### AnalyticsPage
- System health monitoring
- Query performance metrics
- Database insights

## 📱 Usage Examples

### Natural Language Queries
```
• Müşterileri listele
• En çok sipariş veren müşteri
• Son bir aydaki siparişler
• Toplam satış tutarı
```

### Database Connection
1. Navigate to "Databases" page
2. Click "Add Database"
3. Enter connection details
4. Test connection
5. Add to system

### Query Execution
1. Select database
2. Enter natural language or SQL query
3. Click "Execute"
4. View results and export if needed

## 🔄 API Integration

Frontend communicates with SQLAI backend via REST API:

- **Health**: `/api/health`
- **Databases**: `/api/databases/*`
- **Queries**: `/api/query/*`
- **Schema**: `/api/schema/*`
- **Analytics**: `/api/analytics/*`

## 🎨 Styling & Theme

- Ant Design theme configuration
- Primary color: `#1890ff`
- Border radius: `8px`
- Responsive design for mobile/desktop

## 🚦 Scripts

```bash
npm run dev       # Development server (port 3000)
npm run build     # Production build
npm run preview   # Preview production build
npm run lint      # ESLint code checking
npm run format    # Prettier code formatting
```

## 🔗 Backend Integration

Ensure SQLAI backend is running:

```bash
cd ../backend
uvicorn app.main:app --reload --port 8000
```

Backend should be accessible at `http://localhost:8000`

## 📊 Features in Action

### Turkish Language Support
- Natural language processing in Turkish
- Turkish examples and placeholders
- Bilingual interface elements

### Real-time Features
- Live query progress tracking
- Connection status monitoring
- Auto-refresh system health

### Export & Download
- Multiple format support (CSV, JSON, Excel)
- Streaming for large datasets
- Download progress indication

## 🐛 Troubleshooting

### Backend Connection Issues
```bash
# Check backend status
curl http://localhost:8000/api/health

# Check CORS configuration
# Ensure backend allows frontend origin
```

### Build Issues
```bash
# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### API Proxy Issues
```bash
# Check vite.config.ts proxy settings
# Ensure backend URL is correct in .env
```

## 🔄 Development Workflow

1. Start backend server (port 8000)
2. Start frontend dev server (port 3000)  
3. Make changes - hot reload is enabled
4. Test features using browser at localhost:3000
5. Build and deploy when ready

## 📝 License

Part of SQLAI project - AI-Powered PostgreSQL Database Assistant

## 👥 Contributing

This frontend is designed to work with the SQLAI backend API. For features or bugs, ensure both frontend and backend are considered.

---

**SQLAI Frontend - Making database queries as simple as asking a question!** 🚀