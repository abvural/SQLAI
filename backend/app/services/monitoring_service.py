"""
System Monitoring Service
Health checks, metrics collection, and system monitoring
"""
import logging
import psutil
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass

from app.services.database_service import get_database_service
from app.services.query_executor import QueryExecutor
from app.services.websocket_manager import connection_manager
from app.models import get_session, SystemMetric

logger = logging.getLogger(__name__)

@dataclass
class HealthStatus:
    """System health status"""
    component: str
    status: str  # healthy, warning, critical, down
    message: str
    last_check: datetime
    response_time_ms: Optional[float] = None

@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_percent: float
    active_connections: int
    active_queries: int
    
class MonitoringService:
    """System monitoring and health checks"""
    
    def __init__(self):
        """Initialize monitoring service"""
        self.db_service = get_database_service()
        self.query_executor = QueryExecutor()
        
        # Health check thresholds
        self.thresholds = {
            'memory_warning': 75,      # 75% memory usage
            'memory_critical': 90,     # 90% memory usage
            'cpu_warning': 80,         # 80% CPU usage
            'cpu_critical': 95,        # 95% CPU usage
            'disk_warning': 85,        # 85% disk usage
            'disk_critical': 95,       # 95% disk usage
            'response_time_warning': 5000,  # 5 seconds
            'response_time_critical': 10000  # 10 seconds
        }
        
        # Metrics history
        self.metrics_history: List[SystemMetrics] = []
        self.max_history_size = 1440  # 24 hours of minute-by-minute data
        
        logger.info("Monitoring Service initialized")
    
    async def get_system_health(self) -> Dict[str, Any]:
        """
        Get overall system health status
        
        Returns:
            System health report
        """
        health_checks = [
            await self._check_database_connections(),
            await self._check_system_resources(),
            await self._check_query_executor(),
            await self._check_websocket_manager(),
            await self._check_memory_usage()
        ]
        
        # Determine overall status
        statuses = [check.status for check in health_checks]
        if 'critical' in statuses or 'down' in statuses:
            overall_status = 'critical'
        elif 'warning' in statuses:
            overall_status = 'warning'
        else:
            overall_status = 'healthy'
        
        return {
            'overall_status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'components': [
                {
                    'component': check.component,
                    'status': check.status,
                    'message': check.message,
                    'response_time_ms': check.response_time_ms,
                    'last_check': check.last_check.isoformat()
                }
                for check in health_checks
            ],
            'system_metrics': self._get_current_metrics()
        }
    
    async def _check_database_connections(self) -> HealthStatus:
        """Check database connections health"""
        start_time = time.time()
        
        try:
            connections = self.db_service.list_connections()
            healthy_connections = 0
            total_connections = len(connections)
            
            for conn in connections:
                try:
                    if self.db_service.test_connection(conn['id']):
                        healthy_connections += 1
                except:
                    pass
            
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            if total_connections == 0:
                status = 'warning'
                message = 'No database connections configured'
            elif healthy_connections == total_connections:
                status = 'healthy'
                message = f'All {total_connections} database connections healthy'
            elif healthy_connections > 0:
                status = 'warning'
                message = f'{healthy_connections}/{total_connections} database connections healthy'
            else:
                status = 'critical'
                message = 'All database connections failed'
            
            return HealthStatus(
                component='Database Connections',
                status=status,
                message=message,
                last_check=datetime.utcnow(),
                response_time_ms=response_time
            )
            
        except Exception as e:
            return HealthStatus(
                component='Database Connections',
                status='down',
                message=f'Database connection check failed: {str(e)}',
                last_check=datetime.utcnow(),
                response_time_ms=(time.time() - start_time) * 1000
            )
    
    async def _check_system_resources(self) -> HealthStatus:
        """Check system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine status based on thresholds
            issues = []
            status = 'healthy'
            
            if cpu_percent >= self.thresholds['cpu_critical']:
                status = 'critical'
                issues.append(f'CPU usage critical: {cpu_percent:.1f}%')
            elif cpu_percent >= self.thresholds['cpu_warning']:
                status = 'warning'
                issues.append(f'CPU usage high: {cpu_percent:.1f}%')
            
            if memory.percent >= self.thresholds['memory_critical']:
                status = 'critical'
                issues.append(f'Memory usage critical: {memory.percent:.1f}%')
            elif memory.percent >= self.thresholds['memory_warning']:
                if status == 'healthy':
                    status = 'warning'
                issues.append(f'Memory usage high: {memory.percent:.1f}%')
            
            if disk.percent >= self.thresholds['disk_critical']:
                status = 'critical'
                issues.append(f'Disk usage critical: {disk.percent:.1f}%')
            elif disk.percent >= self.thresholds['disk_warning']:
                if status == 'healthy':
                    status = 'warning'
                issues.append(f'Disk usage high: {disk.percent:.1f}%')
            
            if status == 'healthy':
                message = f'Resources normal (CPU: {cpu_percent:.1f}%, Memory: {memory.percent:.1f}%, Disk: {disk.percent:.1f}%)'
            else:
                message = '; '.join(issues)
            
            return HealthStatus(
                component='System Resources',
                status=status,
                message=message,
                last_check=datetime.utcnow()
            )
            
        except Exception as e:
            return HealthStatus(
                component='System Resources',
                status='down',
                message=f'Resource check failed: {str(e)}',
                last_check=datetime.utcnow()
            )
    
    async def _check_query_executor(self) -> HealthStatus:
        """Check query executor health"""
        try:
            active_queries = len(self.query_executor.active_queries)
            completed_queries = sum(1 for q in self.query_executor.active_queries.values() 
                                  if q['status'] == 'completed')
            failed_queries = sum(1 for q in self.query_executor.active_queries.values() 
                               if q['status'] == 'failed')
            
            if active_queries > 100:  # Too many active queries
                status = 'warning'
                message = f'High query load: {active_queries} active queries'
            elif failed_queries > completed_queries * 0.2:  # More than 20% failure rate
                status = 'warning'
                message = f'High query failure rate: {failed_queries} failed out of {active_queries}'
            else:
                status = 'healthy'
                message = f'Query executor healthy: {active_queries} active queries'
            
            return HealthStatus(
                component='Query Executor',
                status=status,
                message=message,
                last_check=datetime.utcnow()
            )
            
        except Exception as e:
            return HealthStatus(
                component='Query Executor',
                status='down',
                message=f'Query executor check failed: {str(e)}',
                last_check=datetime.utcnow()
            )
    
    async def _check_websocket_manager(self) -> HealthStatus:
        """Check WebSocket manager health"""
        try:
            stats = connection_manager.get_connection_stats()
            total_connections = stats['total_connections']
            
            if total_connections > 1000:  # Too many connections
                status = 'warning'
                message = f'High WebSocket load: {total_connections} connections'
            else:
                status = 'healthy'
                message = f'WebSocket manager healthy: {total_connections} connections'
            
            return HealthStatus(
                component='WebSocket Manager',
                status=status,
                message=message,
                last_check=datetime.utcnow()
            )
            
        except Exception as e:
            return HealthStatus(
                component='WebSocket Manager',
                status='down',
                message=f'WebSocket manager check failed: {str(e)}',
                last_check=datetime.utcnow()
            )
    
    async def _check_memory_usage(self) -> HealthStatus:
        """Check application memory usage"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # Check for memory leaks (simplified)
            if memory_mb > 1000:  # More than 1GB
                status = 'critical'
                message = f'High memory usage: {memory_mb:.1f}MB'
            elif memory_mb > 500:  # More than 500MB
                status = 'warning'
                message = f'Elevated memory usage: {memory_mb:.1f}MB'
            else:
                status = 'healthy'
                message = f'Memory usage normal: {memory_mb:.1f}MB'
            
            return HealthStatus(
                component='Application Memory',
                status=status,
                message=message,
                last_check=datetime.utcnow()
            )
            
        except Exception as e:
            return HealthStatus(
                component='Application Memory',
                status='down',
                message=f'Memory check failed: {str(e)}',
                last_check=datetime.utcnow()
            )
    
    def _get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            process = psutil.Process()
            app_memory = process.memory_info().rss / 1024 / 1024
            
            # Get connection stats
            ws_stats = connection_manager.get_connection_stats()
            query_stats = {
                'active_queries': len(self.query_executor.active_queries),
                'completed_queries': sum(1 for q in self.query_executor.active_queries.values() 
                                       if q['status'] == 'completed'),
                'failed_queries': sum(1 for q in self.query_executor.active_queries.values() 
                                    if q['status'] == 'failed')
            }
            
            return {
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available_mb': memory.available / 1024 / 1024,
                    'disk_percent': disk.percent,
                    'disk_free_gb': disk.free / 1024 / 1024 / 1024
                },
                'application': {
                    'memory_mb': app_memory,
                    'websocket_connections': ws_stats['total_connections'],
                    'database_connections': len(self.db_service.list_connections())
                },
                'queries': query_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get current metrics: {e}")
            return {}
    
    def collect_metrics(self):
        """Collect and store system metrics"""
        try:
            current_time = datetime.utcnow()
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            process = psutil.Process()
            app_memory = process.memory_info().rss / 1024 / 1024
            
            # Get connection counts
            ws_stats = connection_manager.get_connection_stats()
            active_queries = len(self.query_executor.active_queries)
            
            metrics = SystemMetrics(
                timestamp=current_time,
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_mb=app_memory,
                disk_percent=disk.percent,
                active_connections=ws_stats['total_connections'],
                active_queries=active_queries
            )
            
            # Add to history
            self.metrics_history.append(metrics)
            
            # Trim history if too long
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history = self.metrics_history[-self.max_history_size:]
            
            # Store in database
            self._store_metrics_in_db(metrics)
            
            logger.debug(f"Collected metrics: CPU={cpu_percent:.1f}%, Memory={memory.percent:.1f}%, Queries={active_queries}")
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
    
    def _store_metrics_in_db(self, metrics: SystemMetrics):
        """Store metrics in database"""
        try:
            with get_session() as session:
                metric_record = SystemMetric(
                    timestamp=metrics.timestamp,
                    metric_type='system_performance',
                    metric_name='combined_metrics',
                    metric_value=metrics.cpu_percent,  # Primary value
                    additional_data={
                        'cpu_percent': metrics.cpu_percent,
                        'memory_percent': metrics.memory_percent,
                        'memory_mb': metrics.memory_mb,
                        'disk_percent': metrics.disk_percent,
                        'active_connections': metrics.active_connections,
                        'active_queries': metrics.active_queries
                    }
                )
                session.add(metric_record)
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to store metrics in database: {e}")
    
    def get_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get metrics history
        
        Args:
            hours: Number of hours of history to return
            
        Returns:
            List of historical metrics
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Filter in-memory history
        recent_metrics = [
            {
                'timestamp': m.timestamp.isoformat(),
                'cpu_percent': m.cpu_percent,
                'memory_percent': m.memory_percent,
                'memory_mb': m.memory_mb,
                'disk_percent': m.disk_percent,
                'active_connections': m.active_connections,
                'active_queries': m.active_queries
            }
            for m in self.metrics_history
            if m.timestamp >= cutoff_time
        ]
        
        return recent_metrics
    
    async def run_continuous_monitoring(self, interval_seconds: int = 60):
        """
        Run continuous monitoring loop
        
        Args:
            interval_seconds: Monitoring interval in seconds
        """
        logger.info(f"Starting continuous monitoring with {interval_seconds}s interval")
        
        while True:
            try:
                # Collect metrics
                self.collect_metrics()
                
                # Check health and send alerts if needed
                health = await self.get_system_health()
                
                if health['overall_status'] in ['warning', 'critical']:
                    await self._send_health_alert(health)
                
                # Wait for next interval
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(interval_seconds)
    
    async def _send_health_alert(self, health: Dict[str, Any]):
        """Send health alert via WebSocket"""
        try:
            alert_message = {
                'type': 'health_alert',
                'status': health['overall_status'],
                'timestamp': health['timestamp'],
                'components': [
                    c for c in health['components'] 
                    if c['status'] in ['warning', 'critical', 'down']
                ]
            }
            
            await connection_manager.send_system_notification(
                'health_alert',
                f"System health status: {health['overall_status']}",
                health['overall_status']
            )
            
        except Exception as e:
            logger.error(f"Failed to send health alert: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics"""
        if not self.metrics_history:
            return {'message': 'No metrics data available'}
        
        recent_metrics = self.metrics_history[-60:]  # Last hour
        
        return {
            'time_range': {
                'start': recent_metrics[0].timestamp.isoformat(),
                'end': recent_metrics[-1].timestamp.isoformat(),
                'samples': len(recent_metrics)
            },
            'averages': {
                'cpu_percent': sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
                'memory_percent': sum(m.memory_percent for m in recent_metrics) / len(recent_metrics),
                'memory_mb': sum(m.memory_mb for m in recent_metrics) / len(recent_metrics),
                'active_queries': sum(m.active_queries for m in recent_metrics) / len(recent_metrics)
            },
            'peaks': {
                'max_cpu': max(m.cpu_percent for m in recent_metrics),
                'max_memory': max(m.memory_percent for m in recent_metrics),
                'max_queries': max(m.active_queries for m in recent_metrics)
            }
        }