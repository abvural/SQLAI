# SQLAI Production Deployment Guide

## System Requirements

### Minimum Requirements
- **Python**: 3.8+ (3.11+ recommended)
- **RAM**: 4GB (8GB+ recommended for large datasets)
- **CPU**: 2 cores (4+ cores recommended)
- **Storage**: 10GB free space
- **PostgreSQL**: Access to target databases

### Recommended Production Requirements
- **RAM**: 16GB+ 
- **CPU**: 8+ cores
- **Storage**: 50GB+ SSD
- **Network**: Gigabit connection to databases

## Installation Steps

### 1. System Setup

#### Ubuntu/Debian
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-dev -y

# Install system dependencies
sudo apt install postgresql-client build-essential git -y
```

#### CentOS/RHEL
```bash
# Install Python 3.11
sudo dnf install python3.11 python3.11-devel python3.11-pip -y

# Install system dependencies
sudo dnf install postgresql gcc git -y
```

### 2. Application Deployment

#### Clone and Setup
```bash
# Clone repository
git clone <repository-url> sqlai
cd sqlai

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Set up environment
cp backend/.env.example backend/.env
```

#### Environment Configuration
Edit `backend/.env`:
```bash
# Application Settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database Settings
CACHE_DATABASE_URL=sqlite:///./sqlai_cache.db

# Security
SECRET_KEY=your-super-secret-key-here
ENCRYPTION_KEY=your-32-character-encryption-key-here

# Server Settings
HOST=0.0.0.0
PORT=8000

# Performance
MAX_WORKERS=4
QUERY_TIMEOUT=300
MAX_CONNECTIONS_PER_POOL=10
```

### 3. Database Setup

#### Initialize Cache Database
```bash
cd backend
python -c "
from app.models import create_tables
create_tables()
print('Cache database initialized')
"
```

#### Test Database Connections
```bash
# Test PostgreSQL connection
python3 -c "
import psycopg2
conn = psycopg2.connect(
    host='your-db-host',
    user='your-db-user',
    password='your-db-password',
    database='your-db-name'
)
print('PostgreSQL connection successful')
conn.close()
"
```

### 4. Security Configuration

#### SSL/TLS Setup (Nginx)
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/your/cert.pem;
    ssl_certificate_key /path/to/your/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

#### Firewall Configuration
```bash
# Ubuntu/Debian
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 80/tcp    # HTTP (for redirects)
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --reload
```

### 5. Process Management

#### Systemd Service
Create `/etc/systemd/system/sqlai.service`:
```ini
[Unit]
Description=SQLAI Application
After=network.target

[Service]
Type=exec
User=sqlai
Group=sqlai
WorkingDirectory=/opt/sqlai/backend
Environment=PATH=/opt/sqlai/venv/bin
ExecStart=/opt/sqlai/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Service Management
```bash
# Enable and start service
sudo systemctl enable sqlai
sudo systemctl start sqlai

# Check status
sudo systemctl status sqlai

# View logs
sudo journalctl -u sqlai -f
```

### 6. Monitoring Setup

#### Health Check Script
Create `/opt/sqlai/health_check.sh`:
```bash
#!/bin/bash
HEALTH_URL="http://localhost:8000/api/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "SQLAI is healthy"
    exit 0
else
    echo "SQLAI is unhealthy (HTTP: $RESPONSE)"
    exit 1
fi
```

#### Cron Health Checks
```bash
# Add to crontab (every 5 minutes)
*/5 * * * * /opt/sqlai/health_check.sh >> /var/log/sqlai_health.log 2>&1
```

### 7. Logging Configuration

#### Log Rotation
Create `/etc/logrotate.d/sqlai`:
```
/opt/sqlai/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    create 644 sqlai sqlai
    postrotate
        systemctl reload sqlai
    endscript
}
```

#### Rsyslog Configuration
Add to `/etc/rsyslog.d/sqlai.conf`:
```
# SQLAI logs
:programname, isequal, "sqlai" /var/log/sqlai/app.log
& stop
```

### 8. Performance Tuning

#### Python/Uvicorn Settings
```bash
# Production start command
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --access-log \
  --log-config logging.conf \
  --timeout-keep-alive 5
```

#### PostgreSQL Connection Optimization
```python
# In .env or config
CONNECTION_POOL_SIZE=10
CONNECTION_POOL_MAX_OVERFLOW=20
CONNECTION_POOL_TIMEOUT=30
CONNECTION_POOL_RECYCLE=3600
```

#### System Limits
Edit `/etc/security/limits.conf`:
```
sqlai soft nofile 65536
sqlai hard nofile 65536
sqlai soft nproc 32768
sqlai hard nproc 32768
```

### 9. Backup Strategy

#### Database Backup Script
Create `/opt/sqlai/backup.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/opt/sqlai/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup cache database
cp /opt/sqlai/backend/sqlai_cache.db $BACKUP_DIR/sqlai_cache_$DATE.db

# Backup configuration
cp /opt/sqlai/backend/.env $BACKUP_DIR/env_$DATE.backup

# Compress old backups
find $BACKUP_DIR -name "*.db" -mtime +7 -exec gzip {} \;

# Remove old backups (keep 30 days)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

#### Scheduled Backups
```bash
# Daily backup at 2 AM
0 2 * * * /opt/sqlai/backup.sh >> /var/log/sqlai_backup.log 2>&1
```

### 10. Security Hardening

#### File Permissions
```bash
# Set proper ownership
sudo chown -R sqlai:sqlai /opt/sqlai

# Secure configuration files
chmod 600 /opt/sqlai/backend/.env

# Secure log files
chmod 640 /opt/sqlai/logs/*.log
```

#### Network Security
```bash
# Limit connections (iptables example)
sudo iptables -A INPUT -p tcp --dport 8000 -s 127.0.0.1 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8000 -s 10.0.0.0/8 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8000 -j DROP
```

### 11. Docker Deployment (Alternative)

#### Dockerfile
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash sqlai

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set ownership
RUN chown -R sqlai:sqlai /app

# Switch to app user
USER sqlai

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose
```yaml
version: '3.8'

services:
  sqlai:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    depends_on:
      - cache-db

  cache-db:
    image: postgres:14
    environment:
      - POSTGRES_DB=sqlai_cache
      - POSTGRES_USER=sqlai
      - POSTGRES_PASSWORD=your-password
    volumes:
      - cache_data:/var/lib/postgresql/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - sqlai
    restart: unless-stopped

volumes:
  cache_data:
```

### 12. Monitoring and Alerting

#### Prometheus Metrics (Optional)
```python
# Add to requirements.txt
prometheus-client==0.17.1

# Add to main.py
from prometheus_client import Counter, Histogram, generate_latest
```

#### Basic Monitoring Script
```bash
#!/bin/bash
# /opt/sqlai/monitor.sh

LOG_FILE="/var/log/sqlai_monitor.log"
ALERT_EMAIL="admin@yourcompany.com"

check_service() {
    if ! systemctl is-active --quiet sqlai; then
        echo "$(date): SQLAI service is down" >> $LOG_FILE
        echo "SQLAI service is down" | mail -s "SQLAI Alert" $ALERT_EMAIL
        systemctl restart sqlai
    fi
}

check_memory() {
    MEMORY_USAGE=$(ps aux | grep uvicorn | grep -v grep | awk '{sum+=$6} END {print sum/1024}')
    if (( $(echo "$MEMORY_USAGE > 2048" | bc -l) )); then
        echo "$(date): High memory usage: ${MEMORY_USAGE}MB" >> $LOG_FILE
    fi
}

check_service
check_memory
```

### 13. Troubleshooting

#### Common Issues

1. **Port Already in Use**
```bash
# Find process using port 8000
sudo netstat -tlnp | grep :8000
sudo kill -9 <PID>
```

2. **Permission Denied**
```bash
# Fix ownership
sudo chown -R sqlai:sqlai /opt/sqlai
```

3. **Database Connection Issues**
```bash
# Test connection
psql -h host -U user -d database -c "SELECT version();"
```

4. **High Memory Usage**
```bash
# Check memory usage
ps aux | grep uvicorn
free -h

# Restart service
sudo systemctl restart sqlai
```

#### Log Locations
- Application logs: `/opt/sqlai/logs/`
- System logs: `/var/log/sqlai/`
- Service logs: `journalctl -u sqlai`

### 14. Updates and Maintenance

#### Update Procedure
```bash
# Stop service
sudo systemctl stop sqlai

# Backup current version
cp -r /opt/sqlai /opt/sqlai.backup.$(date +%Y%m%d)

# Pull updates
cd /opt/sqlai
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r backend/requirements.txt

# Run any migrations
python backend/migrate.py

# Start service
sudo systemctl start sqlai

# Verify
curl http://localhost:8000/api/health
```

#### Maintenance Tasks
```bash
# Weekly maintenance script
#!/bin/bash
# Clean old logs
find /opt/sqlai/logs -name "*.log" -mtime +30 -delete

# Clean old query results
python3 -c "
from backend.app.services.query_executor import QueryExecutor
executor = QueryExecutor()
executor.cleanup_old_results(max_age_hours=168)  # 1 week
"

# Vacuum cache database
sqlite3 /opt/sqlai/backend/sqlai_cache.db "VACUUM;"

echo "Maintenance completed: $(date)"
```

This deployment guide provides a comprehensive setup for production SQLAI deployment with security, monitoring, and maintenance considerations.