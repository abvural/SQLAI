"""
Error Recovery Service
Handles graceful degradation, auto-reconnection, and system recovery
"""
import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import traceback

from app.services.database_service import get_database_service
from app.services.connection_pool import ConnectionPoolManager
from app.services.websocket_manager import connection_manager

logger = logging.getLogger(__name__)

class RecoveryStrategy(Enum):
    """Recovery strategy types"""
    RETRY = "retry"
    FALLBACK = "fallback"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    CIRCUIT_BREAKER = "circuit_breaker"

class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, not trying
    HALF_OPEN = "half_open"  # Testing if recovered

class ErrorRecoveryService:
    """Handles system error recovery and resilience"""
    
    def __init__(self):
        """Initialize error recovery service"""
        self.db_service = get_database_service()
        self.pool_manager = ConnectionPoolManager()
        
        # Recovery configurations
        self.retry_configs = {
            'database_connection': {
                'max_retries': 3,
                'base_delay': 1.0,
                'max_delay': 30.0,
                'backoff_factor': 2.0
            },
            'query_execution': {
                'max_retries': 2,
                'base_delay': 0.5,
                'max_delay': 10.0,
                'backoff_factor': 1.5
            },
            'schema_analysis': {
                'max_retries': 2,
                'base_delay': 2.0,
                'max_delay': 60.0,
                'backoff_factor': 2.0
            }
        }
        
        # Circuit breaker states
        self.circuit_breakers = {}
        
        # Error tracking
        self.error_counts = {}
        self.last_errors = {}
        
        # Recovery callbacks
        self.recovery_callbacks: Dict[str, List[Callable]] = {}
        
        logger.info("Error Recovery Service initialized")
    
    async def execute_with_recovery(self, 
                                   operation_name: str,
                                   operation_func: Callable,
                                   recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETRY,
                                   context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute operation with error recovery
        
        Args:
            operation_name: Name of the operation
            operation_func: Function to execute
            recovery_strategy: Strategy to use for recovery
            context: Additional context for recovery
            
        Returns:
            Operation result with recovery information
        """
        if context is None:
            context = {}
            
        start_time = time.time()
        result = {
            'success': False,
            'result': None,
            'error': None,
            'recovery_attempts': 0,
            'total_time': 0,
            'strategy_used': recovery_strategy.value
        }
        
        try:
            if recovery_strategy == RecoveryStrategy.RETRY:
                result = await self._execute_with_retry(operation_name, operation_func, context)
            elif recovery_strategy == RecoveryStrategy.CIRCUIT_BREAKER:
                result = await self._execute_with_circuit_breaker(operation_name, operation_func, context)
            elif recovery_strategy == RecoveryStrategy.FALLBACK:
                result = await self._execute_with_fallback(operation_name, operation_func, context)
            elif recovery_strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
                result = await self._execute_with_graceful_degradation(operation_name, operation_func, context)
            
        except Exception as e:
            logger.error(f"Recovery execution failed for {operation_name}: {e}")
            result['error'] = str(e)
        
        result['total_time'] = time.time() - start_time
        
        # Track error statistics
        if not result['success']:
            self._track_error(operation_name, result['error'])
        else:
            self._track_success(operation_name)
        
        return result
    
    async def _execute_with_retry(self, 
                                 operation_name: str,
                                 operation_func: Callable,
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute operation with retry logic"""
        config = self.retry_configs.get(operation_name, self.retry_configs['query_execution'])
        
        last_error = None
        for attempt in range(config['max_retries'] + 1):
            try:
                if asyncio.iscoroutinefunction(operation_func):
                    result = await operation_func()
                else:
                    result = operation_func()
                
                return {
                    'success': True,
                    'result': result,
                    'recovery_attempts': attempt
                }
                
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed for {operation_name}: {e}")
                
                if attempt < config['max_retries']:
                    # Calculate delay with exponential backoff
                    delay = min(
                        config['base_delay'] * (config['backoff_factor'] ** attempt),
                        config['max_delay']
                    )
                    
                    logger.info(f"Retrying {operation_name} in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All retry attempts failed for {operation_name}")
        
        return {
            'success': False,
            'error': str(last_error),
            'recovery_attempts': config['max_retries']
        }
    
    async def _execute_with_circuit_breaker(self,
                                          operation_name: str,
                                          operation_func: Callable,
                                          context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute operation with circuit breaker pattern"""
        breaker = self._get_circuit_breaker(operation_name)
        
        # Check circuit breaker state
        if breaker['state'] == CircuitBreakerState.OPEN:
            if time.time() - breaker['opened_at'] < breaker['timeout']:
                return {
                    'success': False,
                    'error': f'Circuit breaker open for {operation_name}',
                    'recovery_attempts': 0
                }
            else:
                # Move to half-open state
                breaker['state'] = CircuitBreakerState.HALF_OPEN
                logger.info(f"Circuit breaker for {operation_name} moved to half-open")
        
        try:
            if asyncio.iscoroutinefunction(operation_func):
                result = await operation_func()
            else:
                result = operation_func()
            
            # Success - reset circuit breaker
            if breaker['state'] == CircuitBreakerState.HALF_OPEN:
                breaker['state'] = CircuitBreakerState.CLOSED
                breaker['failure_count'] = 0
                logger.info(f"Circuit breaker for {operation_name} closed (recovered)")
            
            return {
                'success': True,
                'result': result,
                'recovery_attempts': 0
            }
            
        except Exception as e:
            breaker['failure_count'] += 1
            
            # Check if we should open the circuit breaker
            if breaker['failure_count'] >= breaker['failure_threshold']:
                breaker['state'] = CircuitBreakerState.OPEN
                breaker['opened_at'] = time.time()
                logger.warning(f"Circuit breaker opened for {operation_name} after {breaker['failure_count']} failures")
            
            return {
                'success': False,
                'error': str(e),
                'recovery_attempts': 0
            }
    
    async def _execute_with_fallback(self,
                                   operation_name: str,
                                   operation_func: Callable,
                                   context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute operation with fallback strategy"""
        try:
            # Try primary operation
            if asyncio.iscoroutinefunction(operation_func):
                result = await operation_func()
            else:
                result = operation_func()
            
            return {
                'success': True,
                'result': result,
                'recovery_attempts': 0
            }
            
        except Exception as e:
            logger.warning(f"Primary operation failed for {operation_name}, trying fallback: {e}")
            
            # Try fallback operation
            fallback_func = context.get('fallback_func')
            if fallback_func:
                try:
                    if asyncio.iscoroutinefunction(fallback_func):
                        fallback_result = await fallback_func()
                    else:
                        fallback_result = fallback_func()
                    
                    return {
                        'success': True,
                        'result': fallback_result,
                        'recovery_attempts': 1,
                        'fallback_used': True
                    }
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed for {operation_name}: {fallback_error}")
                    return {
                        'success': False,
                        'error': f"Primary: {str(e)}, Fallback: {str(fallback_error)}",
                        'recovery_attempts': 1
                    }
            else:
                return {
                    'success': False,
                    'error': f"No fallback available for {operation_name}: {str(e)}",
                    'recovery_attempts': 0
                }
    
    async def _execute_with_graceful_degradation(self,
                                               operation_name: str,
                                               operation_func: Callable,
                                               context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute operation with graceful degradation"""
        try:
            if asyncio.iscoroutinefunction(operation_func):
                result = await operation_func()
            else:
                result = operation_func()
            
            return {
                'success': True,
                'result': result,
                'recovery_attempts': 0
            }
            
        except Exception as e:
            logger.warning(f"Operation {operation_name} failed, degrading gracefully: {e}")
            
            # Return degraded result
            degraded_result = context.get('degraded_result', {
                'status': 'degraded',
                'message': f'{operation_name} temporarily unavailable',
                'limited_functionality': True
            })
            
            return {
                'success': True,  # Still successful, just degraded
                'result': degraded_result,
                'recovery_attempts': 0,
                'degraded': True
            }
    
    def _get_circuit_breaker(self, operation_name: str) -> Dict[str, Any]:
        """Get or create circuit breaker for operation"""
        if operation_name not in self.circuit_breakers:
            self.circuit_breakers[operation_name] = {
                'state': CircuitBreakerState.CLOSED,
                'failure_count': 0,
                'failure_threshold': 5,
                'timeout': 60,  # seconds
                'opened_at': None
            }
        
        return self.circuit_breakers[operation_name]
    
    def _track_error(self, operation_name: str, error: str):
        """Track error occurrence"""
        if operation_name not in self.error_counts:
            self.error_counts[operation_name] = 0
        
        self.error_counts[operation_name] += 1
        self.last_errors[operation_name] = {
            'error': error,
            'timestamp': datetime.utcnow(),
            'count': self.error_counts[operation_name]
        }
        
        logger.error(f"Error tracked for {operation_name}: {error} (count: {self.error_counts[operation_name]})")
    
    def _track_success(self, operation_name: str):
        """Track successful operation"""
        # Reset error count on success
        if operation_name in self.error_counts:
            self.error_counts[operation_name] = 0
    
    async def recover_database_connection(self, db_id: str) -> bool:
        """
        Attempt to recover a failed database connection
        
        Args:
            db_id: Database connection ID
            
        Returns:
            True if recovery successful
        """
        logger.info(f"Attempting to recover database connection: {db_id}")
        
        async def reconnect():
            # Remove old pool
            self.pool_manager.remove_pool(db_id)
            
            # Test connection
            if self.db_service.test_connection(db_id):
                # Recreate pool
                self.pool_manager.create_pool(db_id)
                return True
            else:
                raise Exception("Connection test failed")
        
        result = await self.execute_with_recovery(
            f"database_connection_{db_id}",
            reconnect,
            RecoveryStrategy.RETRY
        )
        
        if result['success']:
            logger.info(f"Successfully recovered database connection: {db_id}")
            # Notify via WebSocket
            await connection_manager.send_system_notification(
                'connection_recovered',
                f'Database connection {db_id} recovered',
                'info'
            )
        else:
            logger.error(f"Failed to recover database connection {db_id}: {result['error']}")
        
        return result['success']
    
    async def recover_query_executor(self) -> bool:
        """Attempt to recover query executor"""
        logger.info("Attempting to recover query executor")
        
        async def reset_executor():
            from app.services.query_executor import QueryExecutor
            
            # Create new executor instance
            new_executor = QueryExecutor()
            
            # Clean up old queries
            new_executor.cleanup_old_results(max_age_hours=0)
            
            return new_executor
        
        result = await self.execute_with_recovery(
            "query_executor_recovery",
            reset_executor,
            RecoveryStrategy.RETRY
        )
        
        return result['success']
    
    def register_recovery_callback(self, component: str, callback: Callable):
        """Register a callback to be called when component recovers"""
        if component not in self.recovery_callbacks:
            self.recovery_callbacks[component] = []
        
        self.recovery_callbacks[component].append(callback)
        logger.info(f"Registered recovery callback for {component}")
    
    async def _call_recovery_callbacks(self, component: str):
        """Call recovery callbacks for a component"""
        if component in self.recovery_callbacks:
            for callback in self.recovery_callbacks[component]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"Recovery callback failed for {component}: {e}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            'error_counts': dict(self.error_counts),
            'last_errors': {
                k: {
                    'error': v['error'],
                    'timestamp': v['timestamp'].isoformat(),
                    'count': v['count']
                }
                for k, v in self.last_errors.items()
            },
            'circuit_breakers': {
                k: {
                    'state': v['state'].value,
                    'failure_count': v['failure_count'],
                    'failure_threshold': v['failure_threshold']
                }
                for k, v in self.circuit_breakers.items()
            }
        }
    
    async def run_health_recovery_loop(self, check_interval: int = 300):
        """
        Run continuous health check and recovery loop
        
        Args:
            check_interval: Check interval in seconds (default: 5 minutes)
        """
        logger.info(f"Starting health recovery loop with {check_interval}s interval")
        
        while True:
            try:
                # Check database connections
                connections = self.db_service.list_connections()
                
                for conn in connections:
                    try:
                        if not self.db_service.test_connection(conn['id']):
                            logger.warning(f"Database connection {conn['id']} is down, attempting recovery")
                            await self.recover_database_connection(conn['id'])
                    except Exception as e:
                        logger.error(f"Health check failed for connection {conn['id']}: {e}")
                
                # Reset circuit breakers that have been open too long
                current_time = time.time()
                for name, breaker in self.circuit_breakers.items():
                    if (breaker['state'] == CircuitBreakerState.OPEN and 
                        breaker['opened_at'] and 
                        current_time - breaker['opened_at'] > breaker['timeout'] * 5):  # 5x timeout
                        
                        breaker['state'] = CircuitBreakerState.HALF_OPEN
                        logger.info(f"Reset circuit breaker for {name} to half-open after extended timeout")
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Health recovery loop error: {e}")
                await asyncio.sleep(check_interval)