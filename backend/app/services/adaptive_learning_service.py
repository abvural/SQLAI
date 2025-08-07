"""
Adaptive Learning Service for Self-Training Query Understanding System
Automatically learns from schema and successful queries to improve understanding
"""

import logging
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re

from app.services.schema_context_service import SchemaContextService
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class AdaptiveLearningService:
    """
    Self-learning system that adapts to database schema and user queries
    """
    
    def __init__(self, db_id: str):
        self.db_id = db_id
        self.schema_context = SchemaContextService(db_id)
        self.cache = CacheService()
        
        # LLM client reference - to be injected later to avoid circular import
        self.llm_client = None
        
        # Learning storage
        self.query_patterns = defaultdict(list)
        self.successful_mappings = defaultdict(dict)
        self.schema_vocabulary = set()
        self.turkish_english_mappings = {}
        
        # Performance tracking
        self.query_success_rate = defaultdict(float)
        self.learning_metrics = {
            'total_queries': 0,
            'successful_queries': 0,
            'learned_patterns': 0,
            'vocabulary_size': 0
        }
        
    async def initialize_schema_learning(self, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize learning from database schema
        """
        logger.info(f"🧠 Starting adaptive learning for database: {self.db_id}")
        
        try:
            # 1. Extract vocabulary from schema
            vocabulary = self._extract_schema_vocabulary(schema_info)
            
            # 2. Generate Turkish-English mappings automatically
            mappings = await self._generate_language_mappings(vocabulary)
            
            # 3. Create domain-specific context
            domain_context = await self._infer_domain_context(schema_info)
            
            # 4. Generate query patterns from schema relationships
            query_patterns = self._generate_query_patterns_from_schema(schema_info)
            
            # 5. Store learned knowledge
            learning_data = {
                'vocabulary': vocabulary,
                'language_mappings': mappings,
                'domain_context': domain_context,
                'query_patterns': query_patterns,
                'timestamp': datetime.now().isoformat(),
                'schema_hash': self._calculate_schema_hash(schema_info)
            }
            
            self._store_learning_data(learning_data)
            
            logger.info(f"✅ Schema learning completed: {len(vocabulary)} terms, {len(mappings)} mappings")
            return learning_data
            
        except Exception as e:
            logger.error(f"Error in schema learning: {e}")
            return {}
    
    def _extract_schema_vocabulary(self, schema_info: Dict[str, Any]) -> List[str]:
        """
        Extract all meaningful terms from database schema
        """
        vocabulary = set()
        
        if 'schemas' in schema_info:
            for schema_name, schema_data in schema_info['schemas'].items():
                if 'tables' in schema_data:
                    for table in schema_data['tables']:
                        # Table names
                        vocabulary.add(table['name'])
                        
                        # Column names
                        if 'columns' in table:
                            for column in table['columns']:
                                vocabulary.add(column['name'])
                                
                        # Extract meaningful words from names
                        table_words = self._extract_words(table['name'])
                        vocabulary.update(table_words)
                        
                        if 'columns' in table:
                            for column in table['columns']:
                                column_words = self._extract_words(column['name'])
                                vocabulary.update(column_words)
        
        return list(vocabulary)
    
    def _extract_words(self, name: str) -> List[str]:
        """
        Extract meaningful words from table/column names
        """
        # Handle snake_case, camelCase, PascalCase
        words = []
        
        # Split by underscore
        parts = name.split('_')
        for part in parts:
            # Split camelCase/PascalCase
            camel_words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', part)
            words.extend(camel_words)
        
        # Filter meaningful words (length > 2)
        return [word.lower() for word in words if len(word) > 2]
    
    async def _generate_language_mappings(self, vocabulary: List[str]) -> Dict[str, str]:
        """
        Generate Turkish-English mappings using LLM
        """
        mappings = {}
        
        try:
            # Common database terms
            common_terms = [
                'user', 'users', 'customer', 'customers', 'order', 'orders',
                'product', 'products', 'sale', 'sales', 'department', 'employee',
                'segment', 'revenue', 'target', 'inventory', 'category'
            ]
            
            # Filter vocabulary for database-related terms
            db_terms = [term for term in vocabulary if term.lower() in common_terms or len(term) > 3]
            
            if db_terms and self.llm_client:
                prompt = f"""
Sen bir veritabanı terminolojisi uzmanısın. Aşağıdaki İngilizce veritabanı terimlerinin Türkçe karşılıklarını JSON formatında ver:

Terimler: {', '.join(db_terms[:20])}  # Limit to avoid token overflow

JSON formatında yanıt ver:
{{
    "english_term": "turkish_equivalent",
    ...
}}

Örnek:
{{
    "users": "kullanıcılar",
    "user": "kullanıcı", 
    "customers": "müşteriler",
    "customer": "müşteri",
    "orders": "siparişler",
    "order": "sipariş",
    "products": "ürünler",
    "product": "ürün",
    "sales": "satışlar",
    "sale": "satış"
}}

JSON:"""
                
                response = await self.llm_client.async_client.generate(
                    model=self.llm_client.mistral_model,
                    prompt=prompt,
                    options={'temperature': 0.1, 'num_predict': 300}
                )
                
                # Parse JSON response
                try:
                    json_match = re.search(r'\{.*\}', response['response'], re.DOTALL)
                    if json_match:
                        mappings = json.loads(json_match.group())
                        logger.info(f"Generated {len(mappings)} language mappings")
                except json.JSONDecodeError:
                    logger.warning("Could not parse LLM language mapping response")
                    
        except Exception as e:
            logger.error(f"Error generating language mappings: {e}")
            
        # If LLM client not available, skip LLM-based mapping generation
        if not self.llm_client:
            logger.info("LLM client not available, using default mappings only")
        
        # Add some default mappings if LLM failed
        default_mappings = {
            'users': 'kullanıcılar',
            'user': 'kullanıcı',
            'customers': 'müşteriler', 
            'customer': 'müşteri',
            'orders': 'siparişler',
            'order': 'sipariş',
            'products': 'ürünler',
            'product': 'ürün',
            'sales': 'satışlar',
            'sale': 'satış',
            'count': 'sayı',
            'total': 'toplam',
            'amount': 'miktar'
        }
        
        mappings.update(default_mappings)
        return mappings
    
    async def _infer_domain_context(self, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Infer business domain from schema structure
        """
        context = {
            'domain_type': 'general',
            'key_entities': [],
            'business_processes': [],
            'metrics': []
        }
        
        try:
            tables = []
            if 'schemas' in schema_info:
                for schema_data in schema_info['schemas'].values():
                    if 'tables' in schema_data:
                        tables.extend([t['name'] for t in schema_data['tables']])
            
            # Infer domain type from table names
            if any(t in ['orders', 'customers', 'products', 'sales'] for t in tables):
                context['domain_type'] = 'ecommerce'
                context['key_entities'] = ['customer', 'order', 'product', 'sale']
                context['business_processes'] = ['ordering', 'sales_analysis', 'customer_segmentation']
                context['metrics'] = ['revenue', 'order_count', 'customer_count', 'product_performance']
                
            elif any(t in ['employees', 'departments', 'payroll', 'hr'] for t in tables):
                context['domain_type'] = 'hr'
                context['key_entities'] = ['employee', 'department', 'payroll']
                context['business_processes'] = ['employee_management', 'payroll_processing']
                context['metrics'] = ['employee_count', 'salary_analysis', 'department_size']
                
            elif any(t in ['users', 'posts', 'comments', 'likes'] for t in tables):
                context['domain_type'] = 'social'
                context['key_entities'] = ['user', 'post', 'comment']
                context['business_processes'] = ['user_engagement', 'content_analysis']
                context['metrics'] = ['user_activity', 'post_engagement', 'comment_count']
                
            logger.info(f"Inferred domain: {context['domain_type']} with {len(context['key_entities'])} key entities")
            return context
            
        except Exception as e:
            logger.error(f"Error inferring domain context: {e}")
            return context
    
    def _generate_query_patterns_from_schema(self, schema_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate common query patterns based on schema relationships
        """
        patterns = []
        
        try:
            # Extract relationships and generate patterns
            if 'schemas' in schema_info:
                for schema_data in schema_info['schemas'].values():
                    if 'tables' in schema_data:
                        tables = schema_data['tables']
                        
                        for table in tables:
                            table_name = table['name']
                            
                            # COUNT patterns
                            patterns.append({
                                'pattern_type': 'count',
                                'table': table_name,
                                'sql_template': f"SELECT COUNT(*) as {table_name}_count FROM {table_name}",
                                'turkish_variants': [
                                    f"{table_name} sayısı",
                                    f"kaç {table_name} var",
                                    f"kaç tane {table_name}",
                                    f"{table_name} adedi"
                                ]
                            })
                            
                            # SELECT ALL patterns  
                            patterns.append({
                                'pattern_type': 'select_all',
                                'table': table_name,
                                'sql_template': f"SELECT * FROM {table_name}",
                                'turkish_variants': [
                                    f"{table_name} listesi",
                                    f"tüm {table_name}",
                                    f"{table_name} göster"
                                ]
                            })
            
            logger.info(f"Generated {len(patterns)} query patterns from schema")
            return patterns
            
        except Exception as e:
            logger.error(f"Error generating query patterns: {e}")
            return patterns
    
    async def learn_from_successful_query(self, query: str, generated_sql: str, confidence: float, execution_success: bool) -> None:
        """
        Learn from successful query execution
        """
        if execution_success and confidence > 0.7:
            try:
                # Store successful pattern
                learning_entry = {
                    'query': query,
                    'sql': generated_sql,
                    'confidence': confidence,
                    'timestamp': datetime.now().isoformat(),
                    'success': execution_success
                }
                
                # Extract pattern from successful query
                pattern = await self._extract_pattern_from_query(query, generated_sql)
                if pattern:
                    self.query_patterns[pattern['type']].append(pattern)
                    
                # Update success metrics
                self.learning_metrics['total_queries'] += 1
                if execution_success:
                    self.learning_metrics['successful_queries'] += 1
                    
                # Store in cache for future reference
                cache_key = f"successful_query_{self.db_id}_{hash(query)}"
                self.cache.set_cache(cache_key, learning_entry, 'learning', ttl=86400*7)  # 7 days
                
                logger.info(f"✅ Learned from successful query: {query[:50]}...")
                
            except Exception as e:
                logger.error(f"Error learning from successful query: {e}")
    
    async def _extract_pattern_from_query(self, query: str, sql: str) -> Optional[Dict[str, Any]]:
        """
        Extract reusable pattern from successful query
        """
        try:
            query_lower = query.lower()
            sql_upper = sql.upper()
            
            pattern = {
                'original_query': query,
                'sql_template': sql,
                'confidence': 0.9,  # High confidence for learned patterns
                'type': 'learned'
            }
            
            # Detect pattern type
            if 'COUNT' in sql_upper:
                pattern['type'] = 'count'
                pattern['turkish_keywords'] = [word for word in ['kaç', 'sayı', 'adet', 'tane'] if word in query_lower]
                
            elif 'SELECT *' in sql_upper:
                pattern['type'] = 'select_all'
                pattern['turkish_keywords'] = [word for word in ['listele', 'göster', 'tüm'] if word in query_lower]
                
            elif 'GROUP BY' in sql_upper:
                pattern['type'] = 'aggregation'
                pattern['turkish_keywords'] = [word for word in ['en fazla', 'en çok', 'toplam'] if word in query_lower]
            
            return pattern
            
        except Exception as e:
            logger.error(f"Error extracting pattern: {e}")
            return None
    
    def get_adaptive_context_for_query(self, query: str) -> str:
        """
        Generate adaptive context based on learned patterns and schema
        """
        try:
            # Load learning data
            learning_data = self._load_learning_data()
            
            if not learning_data:
                return ""
                
            # Build dynamic context
            context_parts = []
            
            # Add schema vocabulary
            if 'vocabulary' in learning_data:
                vocab_sample = learning_data['vocabulary'][:20]
                context_parts.append(f"Database Terms: {', '.join(vocab_sample)}")
            
            # Add language mappings relevant to query
            if 'language_mappings' in learning_data:
                relevant_mappings = {}
                query_words = query.lower().split()
                
                for eng, tur in learning_data['language_mappings'].items():
                    if any(word in query.lower() for word in [tur, eng]):
                        relevant_mappings[tur] = eng
                        
                if relevant_mappings:
                    mappings_str = ', '.join([f"{tur}={eng}" for tur, eng in relevant_mappings.items()])
                    context_parts.append(f"Turkish Mappings: {mappings_str}")
            
            # Add learned query patterns
            similar_patterns = self._find_similar_learned_patterns(query)
            if similar_patterns:
                patterns_str = '; '.join([f"{p['original_query']} -> {p['sql_template'][:50]}..." for p in similar_patterns[:3]])
                context_parts.append(f"Similar Patterns: {patterns_str}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error generating adaptive context: {e}")
            return ""
    
    def _find_similar_learned_patterns(self, query: str) -> List[Dict[str, Any]]:
        """
        Find learned patterns similar to current query
        """
        similar = []
        query_words = set(query.lower().split())
        
        try:
            # Load stored patterns
            for pattern_list in self.query_patterns.values():
                for pattern in pattern_list:
                    pattern_words = set(pattern['original_query'].lower().split())
                    similarity = len(query_words & pattern_words) / len(query_words | pattern_words)
                    
                    if similarity > 0.3:  # 30% similarity threshold
                        pattern['similarity'] = similarity
                        similar.append(pattern)
            
            # Sort by similarity
            similar.sort(key=lambda x: x['similarity'], reverse=True)
            return similar[:5]
            
        except Exception as e:
            logger.error(f"Error finding similar patterns: {e}")
            return []
    
    def _calculate_schema_hash(self, schema_info: Dict[str, Any]) -> str:
        """
        Calculate hash of schema for change detection
        """
        import hashlib
        schema_str = json.dumps(schema_info, sort_keys=True)
        return hashlib.md5(schema_str.encode()).hexdigest()
    
    def _store_learning_data(self, data: Dict[str, Any]) -> None:
        """
        Store learning data in cache
        """
        cache_key = f"adaptive_learning_{self.db_id}"
        self.cache.set_cache(cache_key, data, 'learning', ttl=86400*30)  # 30 days
    
    def _load_learning_data(self) -> Dict[str, Any]:
        """
        Load learning data from cache
        """
        cache_key = f"adaptive_learning_{self.db_id}"
        return self.cache.get_cache(cache_key, 'learning') or {}
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """
        Get learning performance statistics
        """
        success_rate = 0
        if self.learning_metrics['total_queries'] > 0:
            success_rate = self.learning_metrics['successful_queries'] / self.learning_metrics['total_queries']
        
        return {
            'total_queries': self.learning_metrics['total_queries'],
            'successful_queries': self.learning_metrics['successful_queries'],
            'success_rate': success_rate,
            'learned_patterns': len(self.query_patterns),
            'vocabulary_size': len(self.schema_vocabulary),
            'last_learning_update': datetime.now().isoformat()
        }