"""
Local LLM Service using Ollama
Handles Turkish understanding with Mistral and SQL generation with SQLCoder
"""
import os
import logging
import json
import asyncio
from typing import Dict, Any, Optional, List
import ollama
from ollama import AsyncClient
import re
from app.services.adaptive_learning_service import AdaptiveLearningService

logger = logging.getLogger(__name__)

class LocalLLMService:
    """Service for interacting with local LLM models via Ollama"""
    
    def __init__(self, db_id: Optional[str] = None):
        """Initialize LLM service with Ollama client and adaptive learning"""
        self.db_id = db_id
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.mistral_model = os.getenv('MISTRAL_MODEL', 'mistral:7b-instruct-q4_K_M')
        self.sqlcoder_model = os.getenv('SQLCODER_MODEL', 'sqlcoder')
        self.timeout = int(os.getenv('LLM_TIMEOUT', '30'))
        self.temperature = float(os.getenv('LLM_TEMPERATURE', '0.1'))
        self.top_p = float(os.getenv('LLM_TOP_P', '0.95'))
        
        # Initialize clients
        self.client = ollama.Client(host=self.ollama_host)
        self.async_client = AsyncClient(host=self.ollama_host)
        
        # Initialize adaptive learning if db_id provided
        self.adaptive_learning = None
        if db_id:
            self.adaptive_learning = AdaptiveLearningService(db_id)
            # Inject self to avoid circular import
            self.adaptive_learning.llm_client = self
            logger.info(f"🧠 Adaptive learning enabled for database: {db_id}")
        
        # Check if models are available
        self._check_models()
        
        logger.info(f"LLM Service initialized with Mistral: {self.mistral_model}, SQLCoder: {self.sqlcoder_model}")
    
    def _check_models(self):
        """Check if required models are available"""
        try:
            models = self.client.list()
            available_models = [m['name'] for m in models.get('models', [])]
            
            if self.mistral_model not in available_models:
                logger.warning(f"Mistral model {self.mistral_model} not found. Available: {available_models}")
            
            if self.sqlcoder_model not in available_models:
                logger.warning(f"SQLCoder model {self.sqlcoder_model} not found. Available: {available_models}")
                
        except Exception as e:
            logger.error(f"Could not check models: {e}")
    
    async def understand_turkish(self, query: str) -> Dict[str, Any]:
        """
        Use Mistral to understand Turkish query and extract intent
        
        Args:
            query: Turkish natural language query
            
        Returns:
            Dictionary with extracted intent, entities, and metrics
        """
        try:
            # Get adaptive learning context if available
            adaptive_context = ""
            if self.adaptive_learning:
                adaptive_context = self.adaptive_learning.get_adaptive_context_for_query(query)
                logger.info(f"🧠 Using adaptive context: {adaptive_context[:100]}...")
            
            # Build enhanced prompt with adaptive context
            context_section = f"\n{adaptive_context}\n" if adaptive_context else ""
            
            # Basit ve etkili prompt - template'leri kaldıralım
            prompt = f"""Sorgu: "{query}"
{context_section}
Analiz:
"kullanıcı sayısı" -> {{"intent":"count","entities":["kullanıcı"],"filters":[]}}
"ahmet isimli kullanıcılar" -> {{"intent":"select","entities":["kullanıcı"],"filters":["name=ahmet"]}}
"tüm ürünler" -> {{"intent":"select","entities":["ürün"],"filters":[]}}

Yanıt (sadece JSON):"""

            response = await self.async_client.generate(
                model=self.mistral_model,
                prompt=prompt,
                options={
                    'temperature': self.temperature,
                    'top_p': self.top_p,
                    'num_predict': 200
                }
            )
            
            # Parse JSON from response
            try:
                result_text = response['response'].strip()
                logger.debug(f"Mistral raw response: {repr(result_text)}")
                
                # Extract JSON from response - improved parsing
                # Try multiple JSON extraction patterns
                json_patterns = [
                    r'\{[^{}]*"intent"[^{}]*\}',  # Look for intent field specifically
                    r'\{[^{}]+\}',                # Simple JSON
                    r'\{.*?\}(?=\s*$)',          # JSON at end of string
                ]
                
                intent_data = None
                for pattern in json_patterns:
                    json_match = re.search(pattern, result_text, re.DOTALL)
                    if json_match:
                        try:
                            intent_data = json.loads(json_match.group())
                            if 'intent' in intent_data:  # Valid response
                                logger.info(f"Successfully parsed Mistral JSON: {intent_data}")
                                break
                        except json.JSONDecodeError:
                            continue
                
                if not intent_data:
                    logger.warning(f"No valid JSON found in Mistral response: {result_text}")
                    intent_data = self._parse_intent_fallback(query)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e} - Response: {result_text}")
                intent_data = self._parse_intent_fallback(query)
            
            # Post-process: Add name and date filters if we detect them
            if not intent_data.get('filters'):
                intent_data['filters'] = []
            
            # Add name filters
            detected_name_filters = self._detect_name_filters(query)
            if detected_name_filters:
                intent_data['filters'].extend(detected_name_filters)
                logger.info(f"Added detected name filters: {detected_name_filters}")
            
            # Add date filters
            detected_date_filters = self._detect_date_filters(query)
            if detected_date_filters:
                intent_data['filters'].extend(detected_date_filters)
                logger.info(f"Added detected date filters: {detected_date_filters}")
            
            # Add complex JOIN pattern detection
            complex_patterns = self._detect_complex_join_patterns(query)
            if complex_patterns:
                # Add to metadata for SQL generation context
                if 'metadata' not in intent_data:
                    intent_data['metadata'] = {}
                intent_data['metadata']['join_patterns'] = complex_patterns
                logger.info(f"Detected complex JOIN patterns: {complex_patterns}")
            
            # Add conversational pattern detection
            conversational = self._detect_conversational_patterns(query)
            if conversational['context_dependent'] or conversational['follow_up_type']:
                if 'metadata' not in intent_data:
                    intent_data['metadata'] = {}
                intent_data['metadata']['conversational'] = conversational
                
                # Update query with expanded context if needed
                if conversational['expanded_query'] != query:
                    intent_data['expanded_query'] = conversational['expanded_query']
                
                logger.info(f"Detected conversational patterns: {conversational}")
            
            # Add business intelligence pattern detection
            bi_patterns = self._detect_business_intelligence_patterns(query)
            if bi_patterns:
                if 'metadata' not in intent_data:
                    intent_data['metadata'] = {}
                intent_data['metadata']['bi_patterns'] = bi_patterns
                
                # Mark as complex analytics query
                intent_data['query_complexity'] = 'advanced_analytics'
                logger.info(f"Detected BI patterns: {bi_patterns}")
            
            logger.info(f"Turkish understanding result: {intent_data}")
            return intent_data
            
        except Exception as e:
            logger.error(f"Error understanding Turkish query: {e}")
            return self._parse_intent_fallback(query)
    
    def _parse_intent_fallback(self, query: str) -> Dict[str, Any]:
        """Fallback intent parsing using simple patterns"""
        query_lower = query.lower()
        
        intent = "select"
        if any(word in query_lower for word in ["kaç", "sayı", "count", "adet", "tane"]):
            intent = "count"
        elif any(word in query_lower for word in ["toplam", "sum"]):
            intent = "sum"
        elif any(word in query_lower for word in ["ortalama", "avg", "average"]):
            intent = "avg"
        elif any(word in query_lower for word in ["en fazla", "en çok", "max", "maksimum"]):
            intent = "max"
        elif any(word in query_lower for word in ["en az", "min", "minimum"]):
            intent = "min"
        
        # Extract entities (simple approach)
        entities = []
        entity_keywords = {
            "kullanıcı": ["kullanıcı", "user", "users"],
            "bayi": ["bayi", "dealer", "distributor"],
            "satış": ["satış", "sale", "sales"],
            "ürün": ["ürün", "product", "products"],
            "müşteri": ["müşteri", "customer", "client"]
        }
        
        for entity, keywords in entity_keywords.items():
            if any(kw in query_lower for kw in keywords):
                entities.append(entity)
        
        return {
            "intent": intent,
            "entities": entities,
            "metrics": [],
            "filters": [],
            "aggregation": None,
            "ordering": None,
            "limit": None
        }
    
    async def generate_sql(self, intent: Dict[str, Any], schema_context: str, query: str = "") -> str:
        """
        Use SQLCoder to generate SQL from intent and schema with adaptive learning enhancement
        
        Args:
            intent: Parsed intent from Turkish understanding
            schema_context: Relevant database schema information
            query: Original natural language query for learning context
            
        Returns:
            Generated SQL query
        """
        try:
            # Get adaptive context for SQL generation if available
            adaptive_sql_context = ""
            if self.adaptive_learning and query:
                adaptive_sql_context = self.adaptive_learning.get_adaptive_context_for_query(query)
            
            # Build enhanced prompt for SQLCoder with adaptive context
            prompt = self._build_sql_prompt(intent, schema_context, adaptive_sql_context)
            
            response = await self.async_client.generate(
                model=self.sqlcoder_model,
                prompt=prompt,
                options={
                    'temperature': 0.0,  # Very low temperature for deterministic SQL
                    'top_p': 0.9,
                    'num_predict': 100,  # Shorter for focused output
                    'stop': [';', '\n\n', 'Schema:', 'Task:', 'Write']  # Stop at semicolon
                }
            )
            
            sql = response['response'].strip()
            
            # Clean up SQL
            sql = self._clean_sql(sql)
            
            logger.info(f"Generated SQL with adaptive learning: {repr(sql)}")
            logger.info(f"Raw SQLCoder response: {repr(response['response'])}")
            return sql
            
        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            # Fallback to template-based generation
            return self._generate_sql_fallback(intent, schema_context)
    
    def _build_sql_prompt(self, intent: Dict[str, Any], schema_context: str, adaptive_context: str = "") -> str:
        """Build optimized prompt for SQLCoder model with adaptive learning context"""
        intent_type = intent.get('intent', 'select')
        entities = intent.get('entities', [])
        
        # Map Turkish entities to English table names
        entity_map = {
            'kullanıcı': 'users',
            'kullanıcılar': 'users', 
            'müşteri': 'customer_segments',
            'müşteriler': 'customer_segments',
            'sipariş': 'orders',
            'siparişler': 'orders',
            'satış': 'sales_targets',
            'satışlar': 'sales_targets',
            'segment': 'customer_segments',
            'gelir': 'revenue'
        }
        
        # Extract filters for better context
        filters = intent.get('filters', [])
        
        # Check for complex JOIN patterns in metadata
        join_patterns = intent.get('metadata', {}).get('join_patterns', [])
        has_complex_joins = len(join_patterns) > 0
        
        # Build specific query instruction based on intent and complexity
        if has_complex_joins:
            # Handle complex JOIN queries
            pattern_info = join_patterns[0]  # Use first detected pattern
            if 'max_aggregation' in pattern_info:
                instruction = "Write a SQL query with JOINs to find the entity with maximum value (use GROUP BY and ORDER BY DESC LIMIT 1)"
            elif 'per_group_aggregation' in pattern_info:
                instruction = "Write a SQL query with JOINs and GROUP BY to calculate aggregated values per group"
            elif 'segment_analysis' in pattern_info:
                instruction = "Write a SQL query joining customer_segments with related tables to analyze by segments"
            elif 'performance_analysis' in pattern_info:
                instruction = "Write a SQL query with multiple JOINs to calculate performance metrics across related tables"
            elif 'revenue_source' in pattern_info:
                instruction = "Write a SQL query joining multiple tables to analyze revenue sources and calculate totals"
            else:
                instruction = f"Write a complex SQL query with JOINs based on pattern: {pattern_info}"
        elif intent_type == 'count':
            table_name = 'users'  # default
            for entity in entities:
                if entity.lower() in entity_map:
                    table_name = entity_map[entity.lower()]
                    break
            
            if filters:
                instruction = f"Write a SQL query to count records in the {table_name} table with filters: {', '.join(filters)}"
            else:
                instruction = f"Write a SQL query to count all records in the {table_name} table"
            
        elif intent_type == 'max' or intent_type == 'select':
            table_name = 'users'  # default
            for entity in entities:
                if entity.lower() in entity_map:
                    table_name = entity_map[entity.lower()]
                    break
            
            if filters:
                # Extract name filters specifically
                filter_conditions = []
                for f in filters:
                    if '=' in f:
                        field, value = f.split('=', 1)
                        if field.strip().lower() in ['name', 'isim', 'ad']:
                            filter_conditions.append(f"username LIKE '%{value.strip()}%'")
                        elif 'LIKE' in f:
                            filter_conditions.append(f)
                        else:
                            filter_conditions.append(f"username = '{value.strip()}'")
                    else:
                        filter_conditions.append(f)
                
                if filter_conditions:
                    instruction = f"Write a SQL query to select records from {table_name} table WHERE {' AND '.join(filter_conditions)}"
                else:
                    instruction = f"Write a SQL query to select records from the {table_name} table with filters: {', '.join(filters)}"
            else:
                # Complex queries for max revenue by segment
                if any('segment' in str(e).lower() or 'müşteri' in str(e).lower() for e in entities):
                    instruction = "Write a SQL query to find which customer segment generates the most revenue by joining customer_segments with orders and grouping by segment_type"
                else:
                    instruction = f"Write a SQL query to select records from the {table_name} table"
        else:
            instruction = f"Write a SQL query for intent: {intent_type}"
        
        # Enhanced prompt with adaptive learning context
        context_section = ""
        if adaptive_context:
            context_section = f"\nAdaptive Learning Context:\n{adaptive_context}\n"
        
        # Build simple, focused prompt for SQLCoder
        if adaptive_context:
            context_section = f"\nContext: {adaptive_context}\n"
        
        # SQLCoder works best with simple, direct prompts
        # Include filter information if available
        filter_info = ""
        if intent.get('filters'):
            filter_info = f"\nFilters to apply: {', '.join(intent['filters'])}"
        
        prompt = f"""{instruction}.

Schema:
{schema_context}{filter_info}
{context_section}
SQL:"""
        
        return prompt
    
    def _clean_sql(self, sql: str) -> str:
        """Clean and validate generated SQL"""
        if not sql or not sql.strip():
            return ""
            
        original_sql = sql
        logger.debug(f"Cleaning SQL: {repr(original_sql)}")
        
        # Remove various prefixes and artifacts
        sql = sql.strip()
        
        # Remove XML-like tags and HTML artifacts
        sql = re.sub(r'<[^>]*>', '', sql)
        
        # Remove markdown code blocks
        sql = re.sub(r'```sql?\s*', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'```\s*$', '', sql, flags=re.IGNORECASE)
        
        # Remove common prefixes
        sql = re.sub(r'^(SQL Query?:\s*|Query:\s*|Answer:\s*|SQL:\s*)', '', sql, flags=re.IGNORECASE)
        
        # Remove leading non-SQL characters
        sql = re.sub(r'^[^A-Za-z]*', '', sql)
        
        # Extract the first valid SQL statement
        lines = sql.split('\n')
        sql_parts = []
        found_sql = False
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('--'):
                continue
                
            # Look for SQL keywords
            line_upper = line.upper()
            if (line_upper.startswith(('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH')) or 
                (found_sql and line)):
                found_sql = True
                sql_parts.append(line)
                
                # Stop at semicolon
                if ';' in line:
                    break
        
        if sql_parts:
            sql = ' '.join(sql_parts)
        else:
            # Fallback: look for any SELECT statement pattern
            select_match = re.search(r'(SELECT\s+.*?)(?:;|$)', sql, re.IGNORECASE | re.DOTALL)
            if select_match:
                sql = select_match.group(1)
            else:
                # Last resort: clean the original
                sql = original_sql.strip()
        
        # Clean up whitespace
        sql = ' '.join(sql.split())
        
        # Ensure it ends with semicolon
        if sql and not sql.endswith(';'):
            sql += ';'
        
        # Remove any remaining artifacts
        sql = re.sub(r'^[^A-Za-z]*', '', sql)
        
        logger.debug(f"Cleaned SQL result: {repr(sql)}")
        
        return sql
    
    def _detect_name_filters(self, query: str) -> List[str]:
        """
        Detect name filters in Turkish queries using pattern matching
        
        Args:
            query: Turkish natural language query
            
        Returns:
            List of detected filters
        """
        filters = []
        query_lower = query.lower()
        
        # Turkish name filter patterns
        import re
        name_patterns = [
            r'(?:ismi|adı)\s+([a-zçğıöşüĞİÖŞÜ]+)(?:\s+(?:olan|geçen))?',
            r'([a-zçğıöşüĞİÖŞÜ]+)\s+(?:ismi|adı)\s+(?:geçen|olan)',
            r'([a-zçğıöşüĞİÖŞÜ]+)\s+(?:isimli|adlı)',
            r'([a-zçğıöşüĞİÖŞÜ]+)\s+ismi\s+geçen'
        ]
        
        # Common Turkish names to look for
        turkish_names = {
            'ahmet', 'mehmet', 'mustafa', 'ali', 'hüseyin', 'hasan', 'ibrahim', 'ismail',
            'fatma', 'ayşe', 'emine', 'hatice', 'zeynep', 'elif', 'merve', 'esra',
            'john', 'jane', 'admin', 'test', 'demo'
        }
        
        for pattern in name_patterns:
            matches = re.findall(pattern, query_lower)
            for match in matches:
                name = match.strip()
                # Check if it's a likely name (length > 2, common name, or contains typical name chars)
                if (len(name) > 2 and 
                    (name in turkish_names or 
                     any(c in name for c in 'çğıöşü') or  # Turkish chars
                     len(name) >= 3)):
                    filters.append(f"name={name}")
                    logger.info(f"Detected name filter: {name}")
        
        return filters
    
    def _detect_date_filters(self, query: str) -> List[str]:
        """
        Detect date/time filters in Turkish queries
        
        Args:
            query: Turkish natural language query
            
        Returns:
            List of detected date filters
        """
        filters = []
        query_lower = query.lower()
        
        # Turkish date patterns
        date_patterns = [
            # Relative dates
            (r'son\s+(\d+)\s+gün', lambda m: f"created_at >= CURRENT_DATE - INTERVAL '{m.group(1)} days'"),
            (r'son\s+(\d+)\s+hafta', lambda m: f"created_at >= CURRENT_DATE - INTERVAL '{m.group(1)} weeks'"),
            (r'son\s+(\d+)\s+ay', lambda m: f"created_at >= CURRENT_DATE - INTERVAL '{m.group(1)} months'"),
            (r'son\s+(\d+)\s+yıl', lambda m: f"created_at >= CURRENT_DATE - INTERVAL '{m.group(1)} years'"),
            
            # Fixed periods
            (r'bugün', lambda m: "DATE(created_at) = CURRENT_DATE"),
            (r'dün', lambda m: "DATE(created_at) = CURRENT_DATE - INTERVAL '1 day'"),
            (r'bu\s+hafta', lambda m: "created_at >= date_trunc('week', CURRENT_DATE)"),
            (r'bu\s+ay', lambda m: "created_at >= date_trunc('month', CURRENT_DATE)"),
            (r'bu\s+yıl', lambda m: "created_at >= date_trunc('year', CURRENT_DATE)"),
            (r'geçen\s+hafta', lambda m: "created_at >= CURRENT_DATE - INTERVAL '1 week' AND created_at < date_trunc('week', CURRENT_DATE)"),
            (r'geçen\s+ay', lambda m: "created_at >= CURRENT_DATE - INTERVAL '1 month' AND created_at < date_trunc('month', CURRENT_DATE)"),
            
            # English equivalents
            (r'last\s+(\d+)\s+days?', lambda m: f"created_at >= CURRENT_DATE - INTERVAL '{m.group(1)} days'"),
            (r'last\s+(\d+)\s+weeks?', lambda m: f"created_at >= CURRENT_DATE - INTERVAL '{m.group(1)} weeks'"),
            (r'this\s+week', lambda m: "created_at >= date_trunc('week', CURRENT_DATE)"),
            (r'this\s+month', lambda m: "created_at >= date_trunc('month', CURRENT_DATE)"),
        ]
        
        for pattern, sql_func in date_patterns:
            match = re.search(pattern, query_lower)
            if match:
                date_filter = sql_func(match)
                filters.append(f"date:{date_filter}")
                logger.info(f"Detected date filter: {date_filter}")
                break  # Only match first pattern
        
        return filters
    
    def _detect_complex_join_patterns(self, query: str) -> List[str]:
        """
        Detect complex queries requiring multi-table JOINs
        
        Args:
            query: Turkish natural language query
            
        Returns:
            List of detected JOIN patterns and requirements
        """
        join_patterns = []
        query_lower = query.lower()
        
        # Complex aggregation patterns requiring JOINs
        complex_patterns = [
            # Turkish patterns
            (r'en\s+(fazla|çok)\s+(\w+)\s+(yapan|olan|veren)\s+(\w+)', 
             lambda m: f"max_aggregation:Find {m.group(4)} with highest {m.group(2)} - requires JOIN"),
            
            (r'(\w+)\s+başına\s+(ortalama|toplam)\s+(\w+)', 
             lambda m: f"per_group_aggregation:{m.group(1)} grouped by {m.group(3)} - requires JOIN and GROUP BY"),
            
            (r'(\w+)\s+segmentine\s+göre\s+(\w+)', 
             lambda m: f"segment_analysis:Analyze {m.group(2)} by {m.group(1)} segments - requires JOIN"),
            
            (r'(\w+)\s+ile\s+(\w+)\s+arasındaki\s+ilişki', 
             lambda m: f"relationship_analysis:Analyze relationship between {m.group(1)} and {m.group(2)} - requires JOIN"),
            
            # Business intelligence patterns
            (r'en\s+karlı\s+(\w+)', 
             lambda m: f"profitability_analysis:Most profitable {m.group(1)} - requires revenue calculation JOINs"),
            
            (r'(\w+)\s+performans\s+analizi', 
             lambda m: f"performance_analysis:{m.group(1)} performance metrics - requires multiple JOINs"),
            
            (r'aylık\s+(\w+)\s+raporu', 
             lambda m: f"monthly_report:Monthly {m.group(1)} report - requires date grouping and JOINs"),
            
            # Customer analysis patterns
            (r'müşteri\s+davranış\s+analizi', 
             lambda m: "customer_behavior:Customer behavior analysis - requires orders, customers JOIN"),
            
            (r'segment\s+bazında\s+(\w+)', 
             lambda m: f"segment_based:{m.group(1)} by customer segments - requires segment JOIN"),
            
            # Revenue and sales patterns
            (r'gelir\s+kaynağı\s+analizi', 
             lambda m: "revenue_source:Revenue source analysis - requires multiple table JOINs"),
            
            (r'satış\s+hedefi\s+(karşılaştırma|analizi)', 
             lambda m: "sales_target:Sales target vs actual - requires targets and sales JOIN")
        ]
        
        for pattern, analysis_func in complex_patterns:
            match = re.search(pattern, query_lower)
            if match:
                join_requirement = analysis_func(match)
                join_patterns.append(join_requirement)
                logger.info(f"Detected complex JOIN pattern: {join_requirement}")
        
        return join_patterns
    
    def _detect_conversational_patterns(self, query: str, conversation_context: str = "") -> Dict[str, Any]:
        """
        Detect conversational query patterns and implicit references
        
        Args:
            query: Current Turkish natural language query
            conversation_context: Previous query context (optional)
            
        Returns:
            Dictionary with conversational elements and context expansions
        """
        conversational_elements = {
            'implicit_references': [],
            'follow_up_type': None,
            'context_dependent': False,
            'expanded_query': query
        }
        
        query_lower = query.lower()
        
        # Detect implicit references (pronouns, demonstratives)
        implicit_patterns = [
            (r'\b(bunlar|bunları|bunların|onlar|onları|onların)\b', 'previous_results'),
            (r'\b(şu|bu)\b(?!\s+(hafta|ay|yıl|gün))', 'demonstrative_reference'),
            (r'\b(aynı|benzer)\b', 'similarity_reference'),
            (r'\b(diğer|başka)\b', 'alternative_reference')
        ]
        
        for pattern, ref_type in implicit_patterns:
            if re.search(pattern, query_lower):
                conversational_elements['implicit_references'].append(ref_type)
                conversational_elements['context_dependent'] = True
        
        # Detect follow-up question types
        follow_up_patterns = [
            (r'\b(peki|tamam)\b.*?(ya\s+)?(nasıl|ne|kim|nerede)', 'follow_up_question'),
            (r'\b(bunun\s+)?(detayı|detayları|ayrıntısı)\b', 'detail_request'),
            (r'\b(daha\s+)?(fazla|çok)\s+(bilgi|detay)\b', 'more_information'),
            (r'\b(grafiği|tablosu|raporu)\s+(göster|hazırla)\b', 'visualization_request'),
            (r'\b(karşılaştır|karşılaştırma|fark)\b', 'comparison_request'),
            (r'\b(neden|sebep|nedeni)\b', 'explanation_request'),
            (r'\b(trend|eğilim|değişim)\b', 'trend_analysis'),
            (r'\b(önceki|geçen)\s+(ile|göre)\s+(karşılaştır|fark)\b', 'temporal_comparison')
        ]
        
        for pattern, follow_type in follow_up_patterns:
            if re.search(pattern, query_lower):
                conversational_elements['follow_up_type'] = follow_type
                break
        
        # Context expansion patterns
        expansion_patterns = [
            # Add missing table context based on conversation
            (r'\b(sayısı|adedi|kaç)\b(?!\s+\w+\s+(var|sayısı))', 
             lambda m: f"{query} (referring to the previously mentioned entity)"),
            
            (r'\b(onların|bunların)\s+(\w+)\b', 
             lambda m: f"Previous results' {m.group(2)} (expand with context)"),
            
            (r'\b(bu|şu)\s+(\w+)\b(?!\s+(hafta|ay|yıl|gün))', 
             lambda m: f"{query} (this {m.group(2)} refers to context)"),
            
            # Incomplete queries that need expansion
            (r'^(daha\s+)?(fazla|çok|az|yüksek|düşük)$', 
             lambda m: f"{query} (incomplete comparison - needs context)")
        ]
        
        for pattern, expansion_func in expansion_patterns:
            match = re.search(pattern, query_lower)
            if match:
                conversational_elements['expanded_query'] = expansion_func(match)
                conversational_elements['context_dependent'] = True
                break
        
        # Detect question modifiers that change intent
        intent_modifiers = []
        modifier_patterns = [
            (r'\b(yaklaşık|tahmini|ortalama)\b', 'approximation'),
            (r'\b(kesinlikle|mutlaka|sadece)\b', 'certainty'),
            (r'\b(hızlıca|çabuk|basit)\b', 'simplification'),
            (r'\b(detaylı|kapsamlı|tam)\b', 'detailed'),
            (r'\b(son\s+durum|güncel|şu\s+anki)\b', 'current_state')
        ]
        
        for pattern, modifier in modifier_patterns:
            if re.search(pattern, query_lower):
                intent_modifiers.append(modifier)
        
        conversational_elements['intent_modifiers'] = intent_modifiers
        
        if conversational_elements['context_dependent'] or conversational_elements['follow_up_type']:
            logger.info(f"Detected conversational query: {conversational_elements}")
        
        return conversational_elements
    
    def _detect_business_intelligence_patterns(self, query: str) -> List[str]:
        """
        Detect business intelligence and advanced analytics query patterns
        
        Args:
            query: Turkish natural language query
            
        Returns:
            List of detected BI patterns and SQL generation hints
        """
        bi_patterns = []
        query_lower = query.lower()
        
        # Customer Analytics Patterns
        customer_patterns = [
            (r'müşteri\s+(yaşam\s+değeri|lifetime\s+value|ltv)', 
             lambda m: "customer_ltv:Calculate Customer Lifetime Value using cohort analysis"),
            
            (r'(churn|kayıp|terk\s+eden)\s+müşteri', 
             lambda m: "churn_analysis:Customer churn rate and prediction analysis"),
            
            (r'müşteri\s+(segment|segmentasyon|gruplama)', 
             lambda m: "customer_segmentation:RFM analysis and customer segmentation"),
            
            (r'(retention|elde\s+tutma)\s+(oranı|rate)', 
             lambda m: "retention_rate:Customer retention rate over time periods"),
            
            (r'cohort\s+analiz|kohort\s+analizi', 
             lambda m: "cohort_analysis:Cohort analysis for customer behavior tracking")
        ]
        
        # Sales Analytics Patterns
        sales_patterns = [
            (r'satış\s+(hunisi|funnel|kanalı)', 
             lambda m: "sales_funnel:Sales funnel conversion rates by stage"),
            
            (r'(konversiyon|dönüşüm)\s+(oranı|rate)', 
             lambda m: "conversion_rate:Conversion rate analysis across different stages"),
            
            (r'(pipeline|satış\s+hattı)\s+analiz', 
             lambda m: "pipeline_analysis:Sales pipeline health and forecasting"),
            
            (r'(quota|kota|hedef)\s+(performans|başarı)', 
             lambda m: "quota_performance:Sales quota achievement and performance tracking"),
            
            (r'(seasonality|mevsimsellik)\s+analiz', 
             lambda m: "seasonality:Seasonal trend analysis for sales patterns")
        ]
        
        # Revenue Analytics Patterns
        revenue_patterns = [
            (r'(mrr|monthly\s+recurring|aylık\s+yinelenen)\s+gelir', 
             lambda m: "mrr_analysis:Monthly Recurring Revenue tracking and growth"),
            
            (r'(arr|annual\s+recurring|yıllık\s+yinelenen)\s+gelir', 
             lambda m: "arr_analysis:Annual Recurring Revenue analysis"),
            
            (r'gelir\s+(cohort|kohort)', 
             lambda m: "revenue_cohort:Revenue cohort analysis by customer acquisition date"),
            
            (r'(price|fiyat)\s+(elasticity|esneklik)', 
             lambda m: "price_elasticity:Price elasticity analysis and optimization"),
            
            (r'unit\s+economics|birim\s+ekonomi', 
             lambda m: "unit_economics:Unit economics analysis (CAC, LTV, payback period)")
        ]
        
        # Product Analytics Patterns
        product_patterns = [
            (r'(feature|özellik)\s+(adoption|benimsenme|kullanım)', 
             lambda m: "feature_adoption:Feature adoption rates and user engagement"),
            
            (r'(activation|etkinleştirme)\s+(rate|oranı)', 
             lambda m: "activation_rate:User activation rate and onboarding success"),
            
            (r'(engagement|katılım)\s+(metrics|metrikleri)', 
             lambda m: "engagement_metrics:User engagement metrics and trends"),
            
            (r'(usage\s+pattern|kullanım\s+deseni)', 
             lambda m: "usage_patterns:User behavior patterns and product usage analytics"),
            
            (r'(stickiness|yapışkanlık)\s+analiz', 
             lambda m: "stickiness_analysis:Product stickiness and user retention analysis")
        ]
        
        # Time Series and Forecasting Patterns
        forecasting_patterns = [
            (r'(forecast|tahmin|projeksiyon)', 
             lambda m: "forecasting:Time series forecasting using historical trends"),
            
            (r'(trend\s+analiz|eğilim\s+analizi)', 
             lambda m: "trend_analysis:Statistical trend analysis with seasonality"),
            
            (r'(growth\s+rate|büyüme\s+oranı)', 
             lambda m: "growth_rate:Growth rate calculation (MoM, YoY, CAGR)"),
            
            (r'(anomaly|anormallik)\s+(detection|tespit)', 
             lambda m: "anomaly_detection:Statistical anomaly detection in metrics"),
            
            (r'(moving\s+average|hareketli\s+ortalama)', 
             lambda m: "moving_average:Moving averages for trend smoothing")
        ]
        
        # Combine all patterns
        all_patterns = (customer_patterns + sales_patterns + 
                       revenue_patterns + product_patterns + 
                       forecasting_patterns)
        
        for pattern, analysis_func in all_patterns:
            match = re.search(pattern, query_lower)
            if match:
                bi_pattern = analysis_func(match)
                bi_patterns.append(bi_pattern)
                logger.info(f"Detected BI pattern: {bi_pattern}")
        
        return bi_patterns
    
    def _generate_sql_fallback(self, intent: Dict[str, Any], schema_context: str) -> str:
        """Fallback SQL generation using templates"""
        intent_type = intent.get('intent', 'select')
        entities = intent.get('entities', [])
        
        # Map Turkish entities to likely table names
        table_mapping = {
            'kullanıcı': 'users',
            'bayi': 'dealers',
            'satış': 'sales',
            'ürün': 'products',
            'müşteri': 'customers'
        }
        
        tables = [table_mapping.get(e, e) for e in entities]
        
        if not tables:
            tables = ['users']  # Default table
        
        # Generate based on intent
        if intent_type == 'count':
            return f"SELECT COUNT(*) as count FROM {tables[0]};"
        elif intent_type == 'sum':
            return f"SELECT SUM(amount) as total FROM {tables[0]};"
        elif intent_type == 'avg':
            return f"SELECT AVG(amount) as average FROM {tables[0]};"
        elif intent_type == 'max':
            if len(tables) > 1:
                return f"""SELECT d.*, MAX(s.amount) as max_amount 
FROM {tables[0]} d 
JOIN {tables[1]} s ON d.id = s.dealer_id 
GROUP BY d.id 
ORDER BY max_amount DESC 
LIMIT 10;"""
            else:
                return f"SELECT MAX(amount) as maximum FROM {tables[0]};"
        elif intent_type == 'min':
            return f"SELECT MIN(amount) as minimum FROM {tables[0]};"
        else:
            return f"SELECT * FROM {tables[0]} LIMIT 100;"
    
    async def analyze_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze database schema and extract patterns
        
        Args:
            schema: Database schema information
            
        Returns:
            Analysis results with patterns and insights
        """
        try:
            # Prepare schema summary
            schema_summary = self._summarize_schema(schema)
            
            prompt = f"""Analyze this database schema and identify:
1. Main entities and their relationships
2. Turkish naming patterns
3. Common query patterns
4. Important metrics and dimensions

Schema:
{schema_summary}

Provide analysis in JSON format:
{{
    "entities": [...],
    "relationships": [...],
    "turkish_mappings": {{...}},
    "common_patterns": [...]
}}

Analysis:"""

            response = await self.async_client.generate(
                model=self.mistral_model,
                prompt=prompt,
                options={
                    'temperature': 0.3,
                    'num_predict': 1000
                }
            )
            
            # Parse response
            analysis_text = response['response']
            
            try:
                json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = {"entities": [], "relationships": []}
            except:
                analysis = {"entities": [], "relationships": []}
            
            logger.info("Schema analysis completed")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing schema: {e}")
            return {"entities": [], "relationships": []}
    
    def _summarize_schema(self, schema: Dict[str, Any]) -> str:
        """Create a concise summary of the schema for LLM context"""
        summary_lines = []
        
        for schema_name, schema_data in schema.get('schemas', {}).items():
            for table in schema_data.get('tables', []):
                table_name = table['name']
                columns = [f"{col['name']} ({col['type']})" for col in table.get('columns', [])][:10]
                summary_lines.append(f"Table: {schema_name}.{table_name}")
                summary_lines.append(f"  Columns: {', '.join(columns)}")
                
                # Add relationships if any
                for rel in schema_data.get('relationships', []):
                    if rel.get('from_table') == table_name:
                        summary_lines.append(f"  FK: {rel['from_column']} -> {rel['to_table']}.{rel['to_column']}")
        
        return '\n'.join(summary_lines[:100])  # Limit to prevent context overflow
    
    async def generate_query_variations(self, base_query: str, count: int = 3) -> List[str]:
        """
        Generate variations of a query for training data
        
        Args:
            base_query: Base Turkish query
            count: Number of variations to generate
            
        Returns:
            List of query variations
        """
        try:
            prompt = f"""Generate {count} variations of this Turkish database query:
"{base_query}"

Variations should:
1. Keep the same meaning
2. Use different Turkish words/phrases
3. Be natural and realistic

Variations:
1."""

            response = await self.async_client.generate(
                model=self.mistral_model,
                prompt=prompt,
                options={
                    'temperature': 0.7,
                    'num_predict': 200
                }
            )
            
            # Parse variations
            variations = [base_query]
            lines = response['response'].split('\n')
            for line in lines:
                if re.match(r'^\d+\.', line):
                    variation = re.sub(r'^\d+\.\s*', '', line).strip()
                    if variation and variation != base_query:
                        variations.append(variation)
            
            return variations[:count + 1]
            
        except Exception as e:
            logger.error(f"Error generating variations: {e}")
            return [base_query]
    
    async def initialize_adaptive_learning(self, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize adaptive learning from schema
        
        Args:
            schema_info: Database schema information
            
        Returns:
            Learning initialization results
        """
        if self.adaptive_learning:
            return await self.adaptive_learning.initialize_schema_learning(schema_info)
        return {}
    
    async def learn_from_success(self, query: str, generated_sql: str, confidence: float, execution_success: bool) -> None:
        """
        Learn from successful query execution
        
        Args:
            query: Original natural language query
            generated_sql: Generated SQL query
            confidence: Query generation confidence
            execution_success: Whether SQL executed successfully
        """
        if self.adaptive_learning:
            await self.adaptive_learning.learn_from_successful_query(
                query, generated_sql, confidence, execution_success
            )
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """
        Get adaptive learning statistics
        
        Returns:
            Learning performance metrics
        """
        if self.adaptive_learning:
            return self.adaptive_learning.get_learning_stats()
        return {'message': 'Adaptive learning not initialized'}
    
    def test_connection(self) -> bool:
        """Test connection to Ollama service"""
        try:
            models = self.client.list()
            return True
        except Exception as e:
            logger.error(f"Ollama connection failed: {e}")
            return False