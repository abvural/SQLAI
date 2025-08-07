"""
Schema Learner Service
Continuously learns from successful queries and improves understanding
"""
import os
import logging
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import hashlib
from collections import defaultdict

logger = logging.getLogger(__name__)

class SchemaLearnerService:
    """Service that learns from query patterns and improves over time"""
    
    def __init__(self, db_id: str):
        """
        Initialize schema learner service
        
        Args:
            db_id: Database connection ID
        """
        self.db_id = db_id
        self.learning_enabled = os.getenv('ENABLE_LEARNING', 'true').lower() == 'true'
        
        # Learning data structures
        self.query_patterns = defaultdict(list)  # Pattern -> List of (query, sql, success_rate)
        self.table_relationships = defaultdict(set)  # Table -> Set of related tables
        self.column_usage = defaultdict(int)  # Column -> Usage count
        self.turkish_mappings = {}  # Turkish term -> English/SQL mapping
        self.successful_queries = []  # History of successful queries
        
        # Initialize services
        self.llm_service = None
        self.schema_context = None
        
        if os.getenv('USE_LOCAL_LLM', 'false').lower() == 'true':
            try:
                from app.services.llm_service import LocalLLMService
                from app.services.schema_context_service import SchemaContextService
                
                self.llm_service = LocalLLMService()
                self.schema_context = SchemaContextService(db_id)
                logger.info(f"Schema Learner initialized with LLM for database: {db_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM for learning: {e}")
        
        # Load previous learning data
        self._load_learning_data()
        
        logger.info(f"Schema Learner Service initialized for database: {db_id}")
    
    def learn_from_query(self, natural_query: str, sql: str, 
                        result_count: int, execution_time: float,
                        success: bool = True):
        """
        Learn from a query execution
        
        Args:
            natural_query: Original natural language query
            sql: Generated SQL query
            result_count: Number of results returned
            execution_time: Query execution time in seconds
            success: Whether query was successful
        """
        if not self.learning_enabled:
            return
        
        try:
            # Record query pattern
            pattern = self._extract_pattern(natural_query)
            self.query_patterns[pattern].append({
                'query': natural_query,
                'sql': sql,
                'success': success,
                'result_count': result_count,
                'execution_time': execution_time,
                'timestamp': datetime.now().isoformat()
            })
            
            if success:
                # Learn from successful query
                self._learn_from_successful_query(natural_query, sql)
                
                # Update schema context if available
                if self.schema_context:
                    self.schema_context.update_with_query_results(
                        natural_query, sql, success
                    )
                
                # Analyze with LLM if available
                if self.llm_service:
                    asyncio.create_task(
                        self._analyze_with_llm(natural_query, sql)
                    )
            
            # Save learning data periodically
            if len(self.successful_queries) % 10 == 0:
                self._save_learning_data()
            
        except Exception as e:
            logger.error(f"Error learning from query: {e}")
    
    def _extract_pattern(self, query: str) -> str:
        """Extract pattern from natural language query"""
        # Remove specific values and normalize
        import re
        
        pattern = query.lower()
        
        # Replace numbers with placeholders
        pattern = re.sub(r'\b\d+\b', '[NUMBER]', pattern)
        
        # Replace quoted strings with placeholders
        pattern = re.sub(r'["\'].*?["\']', '[STRING]', pattern)
        
        # Replace names with placeholders
        pattern = re.sub(r'\b[A-Z][a-z]+\b', '[NAME]', pattern)
        
        # Remove extra spaces
        pattern = ' '.join(pattern.split())
        
        return pattern
    
    def _learn_from_successful_query(self, natural_query: str, sql: str):
        """Learn patterns from successful query"""
        import re
        
        # Extract tables from SQL
        tables = re.findall(r'FROM\s+([^\s,]+)', sql, re.IGNORECASE)
        tables.extend(re.findall(r'JOIN\s+([^\s]+)', sql, re.IGNORECASE))
        
        # Learn table relationships
        if len(tables) > 1:
            for i, table1 in enumerate(tables):
                for table2 in tables[i+1:]:
                    self.table_relationships[table1].add(table2)
                    self.table_relationships[table2].add(table1)
        
        # Extract and count column usage
        columns = re.findall(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE)
        if columns:
            for col_list in columns:
                for col in col_list.split(','):
                    col = col.strip().split('.')[-1]  # Get column name only
                    if col and col != '*':
                        self.column_usage[col] += 1
        
        # Learn Turkish mappings
        self._learn_turkish_mappings(natural_query, sql)
        
        # Add to successful queries
        self.successful_queries.append({
            'query': natural_query,
            'sql': sql,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only recent queries (last 1000)
        if len(self.successful_queries) > 1000:
            self.successful_queries = self.successful_queries[-1000:]
    
    def _learn_turkish_mappings(self, natural_query: str, sql: str):
        """Learn Turkish to SQL mappings"""
        import re
        
        # Common Turkish patterns and their SQL equivalents
        patterns = [
            (r'en (fazla|çok)', 'MAX'),
            (r'en az', 'MIN'),
            (r'toplam', 'SUM'),
            (r'ortalama', 'AVG'),
            (r'kaç|sayı', 'COUNT'),
            (r'listele|göster', 'SELECT'),
            (r'grupla|göre', 'GROUP BY'),
            (r'sırala', 'ORDER BY')
        ]
        
        query_lower = natural_query.lower()
        sql_upper = sql.upper()
        
        for pattern, sql_keyword in patterns:
            if re.search(pattern, query_lower) and sql_keyword in sql_upper:
                for match in re.finditer(pattern, query_lower):
                    turkish_term = match.group()
                    self.turkish_mappings[turkish_term] = sql_keyword
    
    async def _analyze_with_llm(self, natural_query: str, sql: str):
        """Analyze query with LLM to extract insights"""
        if not self.llm_service:
            return
        
        try:
            # Analyze the query pattern
            analysis = await self.llm_service.analyze_schema({
                'query': natural_query,
                'sql': sql,
                'tables': list(self.table_relationships.keys()),
                'common_columns': [col for col, count in 
                                 sorted(self.column_usage.items(), 
                                       key=lambda x: x[1], reverse=True)[:10]]
            })
            
            # Store insights
            if analysis:
                logger.info(f"LLM analysis insights: {analysis}")
                
        except Exception as e:
            logger.error(f"Error analyzing with LLM: {e}")
    
    def get_suggestions(self, partial_query: str) -> List[Dict[str, Any]]:
        """
        Get query suggestions based on learned patterns
        
        Args:
            partial_query: Partial natural language query
            
        Returns:
            List of suggestions with confidence scores
        """
        suggestions = []
        pattern = self._extract_pattern(partial_query)
        
        # Find similar patterns
        for stored_pattern, queries in self.query_patterns.items():
            if pattern in stored_pattern or stored_pattern.startswith(pattern):
                successful = [q for q in queries if q['success']]
                if successful:
                    # Calculate confidence based on success rate
                    success_rate = len(successful) / len(queries)
                    
                    # Get most recent successful query
                    recent = max(successful, key=lambda x: x['timestamp'])
                    
                    suggestions.append({
                        'suggestion': recent['query'],
                        'sql': recent['sql'],
                        'confidence': success_rate,
                        'usage_count': len(successful)
                    })
        
        # Sort by confidence and usage
        suggestions.sort(key=lambda x: (x['confidence'], x['usage_count']), reverse=True)
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def get_related_tables(self, table_name: str) -> List[str]:
        """
        Get tables related to a given table
        
        Args:
            table_name: Table name
            
        Returns:
            List of related table names
        """
        return list(self.table_relationships.get(table_name, set()))
    
    def get_popular_columns(self, limit: int = 20) -> List[Tuple[str, int]]:
        """
        Get most frequently used columns
        
        Args:
            limit: Maximum number of columns to return
            
        Returns:
            List of (column_name, usage_count) tuples
        """
        return sorted(self.column_usage.items(), 
                     key=lambda x: x[1], reverse=True)[:limit]
    
    def get_turkish_mappings(self) -> Dict[str, str]:
        """Get learned Turkish to SQL mappings"""
        return self.turkish_mappings.copy()
    
    def export_learning_data(self) -> Dict[str, Any]:
        """
        Export all learning data
        
        Returns:
            Dictionary containing all learned patterns and relationships
        """
        return {
            'db_id': self.db_id,
            'query_patterns': dict(self.query_patterns),
            'table_relationships': {k: list(v) for k, v in self.table_relationships.items()},
            'column_usage': dict(self.column_usage),
            'turkish_mappings': self.turkish_mappings,
            'successful_queries': self.successful_queries[-100:],  # Last 100
            'export_time': datetime.now().isoformat()
        }
    
    def import_learning_data(self, data: Dict[str, Any]):
        """
        Import learning data from export
        
        Args:
            data: Learning data dictionary
        """
        if data.get('db_id') != self.db_id:
            logger.warning(f"Database ID mismatch: {data.get('db_id')} != {self.db_id}")
            return
        
        # Import patterns
        for pattern, queries in data.get('query_patterns', {}).items():
            self.query_patterns[pattern].extend(queries)
        
        # Import relationships
        for table, related in data.get('table_relationships', {}).items():
            self.table_relationships[table].update(related)
        
        # Import column usage
        for column, count in data.get('column_usage', {}).items():
            self.column_usage[column] += count
        
        # Import Turkish mappings
        self.turkish_mappings.update(data.get('turkish_mappings', {}))
        
        # Import successful queries
        self.successful_queries.extend(data.get('successful_queries', []))
        
        logger.info(f"Imported learning data for database: {self.db_id}")
    
    def _save_learning_data(self):
        """Save learning data to cache"""
        try:
            from app.services.cache_service import CacheService
            cache = CacheService()
            
            cache_key = f"learning_data_{self.db_id}"
            cache.set_cache(
                cache_key,
                self.export_learning_data(),
                category='learning',
                ttl=86400  # 24 hours
            )
            
            logger.info("Learning data saved to cache")
            
        except Exception as e:
            logger.error(f"Error saving learning data: {e}")
    
    def _load_learning_data(self):
        """Load learning data from cache"""
        try:
            from app.services.cache_service import CacheService
            cache = CacheService()
            
            cache_key = f"learning_data_{self.db_id}"
            data = cache.get_cache(cache_key, category='learning')
            
            if data:
                self.import_learning_data(data)
                logger.info("Learning data loaded from cache")
                
        except Exception as e:
            logger.error(f"Error loading learning data: {e}")
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """
        Get statistics about learned patterns
        
        Returns:
            Dictionary with learning statistics
        """
        total_patterns = len(self.query_patterns)
        total_queries = sum(len(queries) for queries in self.query_patterns.values())
        successful_queries = sum(
            len([q for q in queries if q['success']])
            for queries in self.query_patterns.values()
        )
        
        return {
            'total_patterns': total_patterns,
            'total_queries': total_queries,
            'successful_queries': successful_queries,
            'success_rate': successful_queries / total_queries if total_queries > 0 else 0,
            'tables_learned': len(self.table_relationships),
            'columns_tracked': len(self.column_usage),
            'turkish_terms': len(self.turkish_mappings),
            'recent_queries': len(self.successful_queries)
        }