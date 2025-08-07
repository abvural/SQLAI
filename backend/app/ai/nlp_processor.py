"""
Enhanced Natural Language Processor with spaCy and TF-IDF
Handles Turkish language processing and semantic similarity
Now with optional Local LLM support via Ollama
"""
import logging
import re
import unicodedata
import os
import asyncio
from typing import Dict, List, Optional, Tuple, Any
# from sentence_transformers import SentenceTransformer  # DISABLED: Keras 3 compatibility issue
import numpy as np
from functools import lru_cache
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
try:
    import spacy
    from spacy.lang.tr import Turkish
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logging.warning("spaCy not available. Using basic Turkish processing.")

logger = logging.getLogger(__name__)

class NLPProcessor:
    """Natural Language Processing for SQL query generation"""
    
    def __init__(self, model_name: str = "tr_core_news_sm", db_id: Optional[str] = None):
        """
        Initialize enhanced NLP processor with spaCy Turkish model and optional LLM
        
        Args:
            model_name: spaCy Turkish model name
            db_id: Database ID for schema context (optional)
        """
        logger.info(f"Initializing enhanced lightweight NLP processor with Turkish AI")
        
        # Check if LLM is enabled
        self.use_llm = os.getenv('USE_LOCAL_LLM', 'false').lower() == 'true'
        self.llm_service = None
        self.schema_context = None
        self.db_id = db_id
        
        if self.use_llm:
            try:
                from app.services.llm_service import LocalLLMService
                from app.services.schema_context_service import SchemaContextService
                
                self.llm_service = LocalLLMService(db_id)
                if self.db_id:
                    self.schema_context = SchemaContextService(self.db_id)
                    logger.info(f"LLM integration enabled with database: {self.db_id}")
                else:
                    logger.info("LLM integration enabled without specific database context")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM service: {e}")
                self.use_llm = False
        
        # Initialize spaCy Turkish model
        self.nlp = None
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load(model_name)
                logger.info(f"Loaded spaCy Turkish model: {model_name}")
            except OSError:
                logger.warning(f"Turkish model {model_name} not found. Using basic Turkish nlp.")
                try:
                    self.nlp = Turkish()
                    logger.info("Loaded basic Turkish language class")
                except Exception as e:
                    logger.warning(f"Failed to load basic Turkish class: {e}")
                    self.nlp = None
        
        # Initialize TF-IDF vectorizer for semantic similarity
        self.tfidf_vectorizer = TfidfVectorizer(
            analyzer='word',
            token_pattern=r'\b[a-zA-Z\u011f\u00fc\u015f\u0131\u00f6\u00e7\u011e\u00dc\u015eI\u00d6\u00c7]+\b',  # Turkish character support
            stop_words=self._get_turkish_stop_words(),
            max_features=1000,
            ngram_range=(1, 2),  # Use 1-2 grams for better context
            lowercase=True
        )
        
        # Knowledge base for query patterns and their SQL templates
        self.query_templates = {}
        
        # Turkish character mapping
        self.turkish_chars = {
            'ı': 'i', 'İ': 'I',
            'ğ': 'g', 'Ğ': 'G',
            'ü': 'u', 'Ü': 'U',
            'ş': 's', 'Ş': 'S',
            'ö': 'o', 'Ö': 'O',
            'ç': 'c', 'Ç': 'C'
        }
        
        # Turkish keywords to SQL functions
        self.turkish_keywords = {
            'en çok': 'MAX',
            'en az': 'MIN',
            'toplam': 'SUM',
            'ortalama': 'AVG',
            'sayı': 'COUNT',
            'sayısı': 'COUNT',
            'adet': 'COUNT',
            'miktar': 'COUNT',
            'ilk': 'FIRST',
            'son': 'LAST',
            'bugün': 'CURRENT_DATE',
            'dün': 'CURRENT_DATE - INTERVAL \'1 day\'',
            'geçen ay': 'CURRENT_DATE - INTERVAL \'1 month\'',
            'bu ay': 'date_trunc(\'month\', CURRENT_DATE)',
            'bu yıl': 'date_trunc(\'year\', CURRENT_DATE)',
            'geçen yıl': 'CURRENT_DATE - INTERVAL \'1 year\''
        }
        
        # Intent patterns
        self.intent_patterns = {
            'select': ['listele', 'göster', 'getir', 'bul', 'ara', 'seç', 'liste', 'kim', 'hangi', 'nedir', 'neler'],
            'count': ['kaç', 'sayısı', 'adet', 'toplam sayı', 'miktar'],
            'sum': ['toplam', 'toplamı', 'toplam tutar', 'ne kadar'],
            'avg': ['ortalama', 'ortalamasi', 'ortalama değer'],
            'max': ['en çok', 'en fazla', 'en yüksek', 'maksimum', 'en büyük'],
            'min': ['en az', 'en düşük', 'minimum', 'en küçük'],
            'group': ['grupla', 'gruplara göre', 'kategorilere göre', 'göre'],
            'order': ['sırala', 'sıralı', 'büyükten küçüğe', 'küçükten büyüğe', 'azalan', 'artan'],
            'filter': ['sadece', 'yalnız', 'filtrele', 'şartlı', 'koşullu', 'olan', 'olmayan'],
            'join': ['ile birlikte', 'dahil', 'ilişkili', 'bağlantılı'],
            'distinct': ['benzersiz', 'tekil', 'farklı', 'unique']
        }
        
        # Common table name variations (Turkish/English)
        self.table_synonyms = {
            'kullanici': ['user', 'users', 'kullanici', 'kullanicilar', 'uye', 'uyeler'],
            'musteri': ['customer', 'customers', 'musteri', 'musteriler', 'client', 'alici'],
            'urun': ['product', 'products', 'urun', 'urunler', 'item', 'mal'],
            'siparis': ['order', 'orders', 'siparis', 'siparisler'],
            'kategori': ['category', 'categories', 'kategori', 'kategoriler'],
            'tedarikci': ['supplier', 'suppliers', 'tedarikci', 'tedarikciler', 'saglayici']
        }
        
        # Initialize knowledge base
        self._initialize_query_knowledge_base()
        
        logger.info("Enhanced NLP Processor with Turkish AI initialized successfully")
    
    def _get_turkish_stop_words(self) -> List[str]:
        """Get Turkish stop words"""
        return [
            've', 'ile', 'bir', 'bu', 'şu', 'o', 'olan', 'olarak', 've', 'veya', 'ya', 'ki', 
            'de', 'da', 'den', 'dan', 'deki', 'daki', 'nin', 'nın', 'nun', 'nün',
            'için', 'gibi', 'kadar', 'daha', 'en', 'çok', 'az', 'var', 'yok'
        ]
    
    def _initialize_query_knowledge_base(self):
        """Initialize knowledge base with query patterns and templates"""
        self.query_templates = {
            # User queries
            'list_users': {
                'patterns': ['kullanıcılar', 'kullanıcı listesi', 'tüm kullanıcılar', 'users', 'list users'],
                'sql_template': 'SELECT * FROM users',
                'confidence_base': 0.9
            },
            'count_users': {
                'patterns': ['kaç kullanıcı', 'kullanıcı sayısı', 'count users', 'user count'],
                'sql_template': 'SELECT COUNT(*) as user_count FROM users',
                'confidence_base': 0.9
            },
            'user_by_name': {
                'patterns': ['ismi {} olan', 'adı {} olan', '{} isimli', '{} adlı', 'named {}', 'user {}'],
                'sql_template': 'SELECT * FROM users WHERE username = \'{}\'',
                'confidence_base': 0.95
            },
            'user_search': {
                'patterns': ['{} içeren', '{} olan kullanıcılar', 'find {}', 'search {}'],
                'sql_template': 'SELECT username, email FROM users WHERE username LIKE \'%{}%\' LIMIT 10',
                'confidence_base': 0.85
            },
            # Product queries
            'list_products': {
                'patterns': ['ürünler', 'ürün listesi', 'tüm ürünler', 'products', 'list products'],
                'sql_template': 'SELECT * FROM products',
                'confidence_base': 0.9
            },
            # Order queries
            'list_orders': {
                'patterns': ['siparişler', 'sipariş listesi', 'orders', 'list orders'],
                'sql_template': 'SELECT * FROM orders',
                'confidence_base': 0.9
            }
        }
    
    def normalize_turkish(self, text: str) -> str:
        """
        Enhanced Turkish text normalization using spaCy if available
        
        Args:
            text: Input text with Turkish characters
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower().strip()
        
        # Use spaCy with fallback to basic normalization
        try:
            if self.nlp and hasattr(self.nlp, '__call__'):
                doc = self.nlp(text)
                # Extract tokens carefully - Turkish class has issues with is_stop
                tokens = []
                stop_words = set(self._get_turkish_stop_words())
                for token in doc:
                    token_text = token.text.strip().lower()
                    # Use our own stop word list instead of spaCy's which may not work for Turkish
                    if (token_text not in stop_words and not token.is_punct and 
                        not token.is_space and len(token_text) > 1):
                        tokens.append(token.lemma_ if hasattr(token, 'lemma_') and token.lemma_ else token_text)
                normalized = ' '.join(tokens) if tokens else text
            else:
                raise Exception("spaCy not available")
        except Exception as e:
            # Reliable fallback normalization
            stop_words = set(self._get_turkish_stop_words())
            words = text.split()
            filtered_words = [word for word in words if word not in stop_words and len(word) > 1]
            normalized = ' '.join(filtered_words) if filtered_words else text
        
        # Replace Turkish keywords with SQL equivalents
        for turkish, sql in self.turkish_keywords.items():
            if turkish in normalized:
                normalized = normalized.replace(turkish, f"[{sql}]")
        
        # Remove extra spaces
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def extract_keywords(self, text: str) -> Dict[str, List[str]]:
        """
        Extract keywords and intents from text
        
        Args:
            text: Input query text
            
        Returns:
            Dictionary of extracted keywords by category
        """
        normalized = self.normalize_turkish(text)
        keywords = {
            'intents': [],
            'entities': [],
            'filters': [],
            'aggregates': [],
            'ordering': []
        }
        
        # Extract intents
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in normalized:
                    keywords['intents'].append(intent)
                    break
        
        # Extract entities (potential table/column names)
        words = normalized.split()
        for word in words:
            # Check if word might be a table name
            for entity_type, synonyms in self.table_synonyms.items():
                if word in [self.normalize_turkish(s) for s in synonyms]:
                    keywords['entities'].append(entity_type)
        
        # Extract SQL function indicators
        if any(word in normalized for word in ['max', 'en cok', '[MAX]']):
            keywords['aggregates'].append('MAX')
        if any(word in normalized for word in ['min', 'en az', '[MIN]']):
            keywords['aggregates'].append('MIN')
        if any(word in normalized for word in ['sum', 'toplam', '[SUM]']):
            keywords['aggregates'].append('SUM')
        if any(word in normalized for word in ['avg', 'ortalama', '[AVG]']):
            keywords['aggregates'].append('AVG')
        if any(word in normalized for word in ['count', 'sayi', 'kac', '[COUNT]']):
            keywords['aggregates'].append('COUNT')
        
        # Extract ordering
        if any(word in normalized for word in ['sirala', 'buyukten', 'azalan']):
            keywords['ordering'].append('DESC')
        elif any(word in normalized for word in ['kucukten', 'artan']):
            keywords['ordering'].append('ASC')
        
        return keywords
    
    @lru_cache(maxsize=1000)
    def get_embedding(self, text: str) -> np.ndarray:
        """
        Get TF-IDF embedding for text (cached)
        
        Args:
            text: Input text
            
        Returns:
            TF-IDF embedding vector
        """
        normalized = self.normalize_turkish(text)
        if not normalized:
            return np.zeros(100)  # Default empty vector
            
        # Try to use TF-IDF if we have training data
        try:
            # Create a fresh vectorizer for each call to avoid state issues
            vectorizer = TfidfVectorizer(
                analyzer='word',
                token_pattern=r'\b[a-zA-Z\u011f\u00fc\u015f\u0131\u00f6\u00e7\u011e\u00dc\u015eI\u00d6\u00c7]+\b',
                lowercase=True,
                max_features=100,
                ngram_range=(1, 2)
            )
            
            # Combine all template patterns as training data
            all_patterns = []
            for template_info in self.query_templates.values():
                all_patterns.extend(template_info['patterns'])
            
            # Add some basic Turkish words if patterns are empty
            if not all_patterns:
                all_patterns = ['kullanıcı', 'user', 'listele', 'list', 'kaç', 'count']
            
            all_patterns.append(normalized)
            
            # Fit and transform
            tfidf_matrix = vectorizer.fit_transform(all_patterns)
            # Return the last vector (our query)
            result = tfidf_matrix[-1].toarray().flatten()
            return result if len(result) > 0 else np.zeros(100)
            
        except Exception as e:
            logger.warning(f"TF-IDF embedding failed, using fallback: {e}")
            # Fallback: simple hash-based embedding with better distribution
            import hashlib
            text_hash = int(hashlib.md5(normalized.encode()).hexdigest(), 16)
            # Create a better distributed vector
            vector = []
            for i in range(10):
                vector.append((text_hash >> (i * 4)) & 0xFF)
            return np.array(vector, dtype=float)
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts using improved methods
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1)
        """
        # Normalize both texts
        norm1 = self.normalize_turkish(text1)
        norm2 = self.normalize_turkish(text2)
        
        if not norm1 or not norm2:
            return 0.0
        
        # Use multiple similarity metrics and combine them
        similarities = []
        
        # 1. Exact word match ratio
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        if words1 and words2:
            word_similarity = len(words1 & words2) / max(len(words1), len(words2))
            similarities.append(word_similarity * 0.4)  # 40% weight
        
        # 2. TF-IDF cosine similarity
        try:
            tfidf_matrix = self.tfidf_vectorizer.fit_transform([norm1, norm2])
            cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            similarities.append(cosine_sim * 0.4)  # 40% weight
        except:
            similarities.append(0.0)
        
        # 3. Character-level similarity for names
        import difflib
        char_similarity = difflib.SequenceMatcher(None, norm1, norm2).ratio()
        similarities.append(char_similarity * 0.2)  # 20% weight
        
        return float(sum(similarities))
    
    async def generate_sql_with_llm(self, query: str, schema_info: Dict[str, Any] = None) -> Tuple[Optional[str], float]:
        """
        Generate SQL using Local LLM (Mistral + SQLCoder)
        
        Args:
            query: Natural language query
            schema_info: Database schema information (optional)
            
        Returns:
            Tuple of (generated_sql, confidence_score)
        """
        if not self.llm_service:
            logger.warning("LLM service not available, falling back to pattern matching")
            return self.generate_intelligent_sql_pattern(query, schema_info)
        
        try:
            # Get relevant schema context
            schema_context = ""
            if self.schema_context and schema_info:
                # Index schema if not already indexed
                self.schema_context.index_schema(schema_info)
                # Get relevant context for the query
                schema_context = self.schema_context.get_relevant_context(query, limit=20)
            elif schema_info:
                # Build basic context without ChromaDB
                schema_context = self._build_basic_schema_context(schema_info)
            
            # Step 1: Understand Turkish query using Mistral
            intent = await self.llm_service.understand_turkish(query)
            logger.info(f"LLM Turkish understanding: {intent}")
            
            # Step 2: Generate SQL using SQLCoder with adaptive learning context
            sql = await self.llm_service.generate_sql(intent, schema_context, query)
            
            # Step 3: Calculate confidence based on intent clarity
            confidence = 0.95  # High confidence for LLM
            if intent.get('intent') == 'select' and not intent.get('filters'):
                confidence = 0.85  # Lower confidence for vague queries
            elif not intent.get('entities'):
                confidence = 0.75  # Even lower if no entities detected
            
            # Step 4: Update schema context with successful query
            if sql and self.schema_context:
                self.schema_context.update_with_query_results(query, sql, True)
            
            # Step 5: Store successful result for adaptive learning
            if sql and confidence > 0.7:
                await self.llm_service.learn_from_success(query, sql, confidence, True)
            
            return sql, confidence
            
        except Exception as e:
            logger.error(f"Error generating SQL with LLM: {e}")
            # Fallback to pattern matching
            return self.generate_intelligent_sql_pattern(query, schema_info)
    
    def generate_intelligent_sql(self, query: str, schema_info: Dict[str, Any] = None) -> Tuple[Optional[str], float]:
        """
        Generate SQL using intelligent pattern matching and semantic similarity or LLM
        
        Args:
            query: Natural language query
            schema_info: Database schema information (optional)
            
        Returns:
            Tuple of (generated_sql, confidence_score)
        """
        # Use LLM if available
        if self.use_llm and self.llm_service:
            try:
                # Check if we're already in an event loop
                try:
                    loop = asyncio.get_running_loop()
                    # We're in an async context, create a task
                    import threading
                    import concurrent.futures
                    
                    def run_in_thread():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(self.generate_sql_with_llm(query, schema_info))
                        finally:
                            new_loop.close()
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_in_thread)
                        result = future.result(timeout=30)
                    return result
                    
                except RuntimeError:
                    # No running loop, safe to create new one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(self.generate_sql_with_llm(query, schema_info))
                        return result
                    finally:
                        loop.close()
                        
            except Exception as e:
                logger.error(f"Error with LLM generation: {e}")
                # Return empty result instead of falling back to patterns
                return None, 0.0
        
        # If LLM is not available, return empty result
        logger.warning("LLM not available and pattern matching disabled")
        return None, 0.0
    
    def generate_intelligent_sql_pattern(self, query: str, schema_info: Dict[str, Any] = None) -> Tuple[Optional[str], float]:
        """
        Generate SQL using intelligent pattern matching and semantic similarity (original method)
        
        Args:
            query: Natural language query
            schema_info: Database schema information (optional)
            
        Returns:
            Tuple of (generated_sql, confidence_score)
        """
        normalized_query = self.normalize_turkish(query)
        best_match = None
        best_confidence = 0.0
        best_sql = None
        
        # Extract potential entity names from query
        query_words = normalized_query.split()
        potential_names = []
        
        # Look for Turkish name patterns
        import re
        name_patterns = [
            r'ismi\s+([a-zA-ZğüşıöçĞÜŞIÖÇ_]+)',
            r'adı\s+([a-zA-ZğüşıöçĞÜŞIÖÇ_]+)', 
            r'([a-zA-ZğüşıöçĞÜŞIÖÇ_]+)\s+(?:isimli|adlı)',
            r'named\s+([a-zA-Z_]+)',
            r'user\s+([a-zA-Z_]+)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, query.lower())
            if match:
                potential_names.append(match.group(1))
        
        # Match against query templates
        for template_key, template_info in self.query_templates.items():
            for pattern in template_info['patterns']:
                # Handle parameterized patterns
                if '{}' in pattern:
                    if potential_names:
                        for name in potential_names:
                            filled_pattern = pattern.format(name)
                            similarity = self.calculate_similarity(normalized_query, filled_pattern)
                            confidence = similarity * template_info['confidence_base']
                            
                            if confidence > best_confidence:
                                best_confidence = confidence
                                best_match = template_key
                                best_sql = template_info['sql_template'].format(name)
                else:
                    # Direct pattern matching
                    similarity = self.calculate_similarity(normalized_query, pattern)
                    confidence = similarity * template_info['confidence_base']
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = template_key
                        best_sql = template_info['sql_template']
        
        # If no good match, try fuzzy matching with basic patterns
        if best_confidence < 0.5:
            basic_patterns = {
                'kullanıcı': ('SELECT * FROM users', 0.7),
                'user': ('SELECT * FROM users', 0.7),
                'ürün': ('SELECT * FROM products', 0.7),
                'product': ('SELECT * FROM products', 0.7),
                'sipariş': ('SELECT * FROM orders', 0.7),
                'order': ('SELECT * FROM orders', 0.7)
            }
            
            for pattern, (sql, base_conf) in basic_patterns.items():
                if pattern in normalized_query:
                    return sql, base_conf
        
        return best_sql, best_confidence
    
    def find_best_match(self, query: str, candidates: List[str], 
                       threshold: float = 0.3) -> Tuple[Optional[str], float]:
        """
        Find best matching candidate for query
        
        Args:
            query: Query text
            candidates: List of candidate strings
            threshold: Minimum similarity threshold
            
        Returns:
            Tuple of (best_match, similarity_score)
        """
        if not candidates:
            return None, 0.0
        
        query_embedding = self.get_embedding(query)
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            candidate_embedding = self.get_embedding(candidate)
            similarity = np.dot(query_embedding, candidate_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(candidate_embedding)
            )
            
            if similarity > best_score and similarity >= threshold:
                best_score = similarity
                best_match = candidate
        
        return best_match, best_score
    
    def match_tables_columns(self, query: str, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Match query to tables and columns using semantic similarity
        
        Args:
            query: Natural language query
            schema_info: Database schema information
            
        Returns:
            Matched tables and columns with confidence scores
        """
        keywords = self.extract_keywords(query)
        matches = {
            'tables': [],
            'columns': [],
            'relationships': [],
            'confidence': 0.0
        }
        
        # Extract all table names from schema
        all_tables = []
        all_columns = []
        
        for schema_name, schema_data in schema_info.get('schemas', {}).items():
            for table in schema_data.get('tables', []):
                table_full_name = f"{schema_name}.{table['name']}"
                all_tables.append({
                    'full_name': table_full_name,
                    'name': table['name'],
                    'schema': schema_name
                })
                
                for column in table.get('columns', []):
                    all_columns.append({
                        'table': table_full_name,
                        'name': column['name'],
                        'type': column['type']
                    })
        
        # Match tables based on keywords and similarity
        for entity in keywords['entities']:
            # Find tables matching this entity
            for table_info in all_tables:
                similarity = self.calculate_similarity(entity, table_info['name'])
                if similarity > 0.3:
                    matches['tables'].append({
                        'table': table_info['full_name'],
                        'confidence': similarity,
                        'matched_entity': entity
                    })
        
        # If no direct entity match, try semantic matching with query
        if not matches['tables'] and all_tables:
            table_names = [t['name'] for t in all_tables]
            best_table, score = self.find_best_match(query, table_names)
            if best_table:
                table_info = next(t for t in all_tables if t['name'] == best_table)
                matches['tables'].append({
                    'table': table_info['full_name'],
                    'confidence': score,
                    'matched_entity': 'semantic'
                })
        
        # Match columns based on query context
        query_words = query.lower().split()
        for column_info in all_columns:
            # Check if column is relevant to any matched table
            if any(column_info['table'] == t['table'] for t in matches['tables']):
                # Check column relevance
                for word in query_words:
                    similarity = self.calculate_similarity(word, column_info['name'])
                    if similarity > 0.4:
                        matches['columns'].append({
                            'table': column_info['table'],
                            'column': column_info['name'],
                            'type': column_info['type'],
                            'confidence': similarity
                        })
        
        # Calculate overall confidence
        if matches['tables']:
            table_confidences = [t['confidence'] for t in matches['tables']]
            column_confidences = [c['confidence'] for c in matches['columns']] if matches['columns'] else [0.5]
            matches['confidence'] = np.mean(table_confidences + column_confidences)
        
        return matches
    
    def classify_query_type(self, query: str) -> Dict[str, Any]:
        """
        Classify the type of SQL query needed
        
        Args:
            query: Natural language query
            
        Returns:
            Query type classification
        """
        keywords = self.extract_keywords(query)
        
        classification = {
            'primary_intent': 'select',
            'needs_aggregation': False,
            'needs_grouping': False,
            'needs_ordering': False,
            'needs_filtering': False,
            'needs_join': False,
            'complexity': 'simple'
        }
        
        # Determine primary intent
        if 'count' in keywords['intents']:
            classification['primary_intent'] = 'count'
            classification['needs_aggregation'] = True
        elif keywords['aggregates']:
            classification['primary_intent'] = keywords['aggregates'][0].lower()
            classification['needs_aggregation'] = True
        
        # Check for grouping
        if 'group' in keywords['intents'] or 'göre' in query.lower():
            classification['needs_grouping'] = True
        
        # Check for ordering
        if keywords['ordering'] or 'order' in keywords['intents']:
            classification['needs_ordering'] = True
        
        # Check for filtering
        if 'filter' in keywords['intents'] or any(word in query.lower() for word in ['sadece', 'yalnız', 'olan']):
            classification['needs_filtering'] = True
        
        # Check for joins (multiple entities)
        if len(keywords['entities']) > 1 or 'join' in keywords['intents']:
            classification['needs_join'] = True
        
        # Determine complexity
        complexity_score = sum([
            classification['needs_aggregation'],
            classification['needs_grouping'],
            classification['needs_ordering'],
            classification['needs_filtering'],
            classification['needs_join']
        ])
        
        if complexity_score <= 1:
            classification['complexity'] = 'simple'
        elif complexity_score <= 3:
            classification['complexity'] = 'moderate'
        else:
            classification['complexity'] = 'complex'
        
        return classification
    
    def extract_filter_conditions(self, query: str) -> List[Dict[str, Any]]:
        """
        Extract filter conditions from natural language
        
        Args:
            query: Natural language query
            
        Returns:
            List of filter conditions
        """
        conditions = []
        query_lower = query.lower()
        
        # Name-based filters (Turkish specific patterns)
        import re
        name_patterns = [
            (r'ismi\s+([a-zA-ZğüşıöçĞÜŞIÖÇ]+)\s+olan', '='),
            (r'adı\s+([a-zA-ZğüşıöçĞÜŞIÖÇ]+)\s+olan', '='),
            (r'ismi\s+([a-zA-ZğüşıöçĞÜŞIÖÇ]+)', '='),
            (r'adı\s+([a-zA-ZğüşıöçĞÜŞIÖÇ]+)', '='),
            (r'([a-zA-ZğüşıöçĞÜŞIÖÇ]+)\s+isimli', '='),
            (r'([a-zA-ZğüşıöçĞÜŞIÖÇ]+)\s+adlı', '='),
            (r'name\s*=\s*["\']([^"\']+)["\']', '='),
            (r'name\s+is\s+([a-zA-Z]+)', '=')
        ]
        
        for pattern, operator in name_patterns:
            match = re.search(pattern, query_lower)
            if match:
                name_value = match.group(1).strip()
                conditions.append({
                    'type': 'name',
                    'field': 'name',  # Default field name
                    'operator': operator,
                    'value': name_value.title(),  # Capitalize name
                    'raw_value': f"'{name_value.title()}'"
                })
                break  # Only match the first name pattern
        
        # Date filters
        if 'bugün' in query_lower:
            conditions.append({
                'type': 'date',
                'operator': '=',
                'value': 'CURRENT_DATE'
            })
        elif 'dün' in query_lower:
            conditions.append({
                'type': 'date',
                'operator': '=',
                'value': "CURRENT_DATE - INTERVAL '1 day'"
            })
        elif 'geçen ay' in query_lower:
            conditions.append({
                'type': 'date',
                'operator': '>=',
                'value': "CURRENT_DATE - INTERVAL '1 month'"
            })
        elif 'bu ay' in query_lower:
            conditions.append({
                'type': 'date',
                'operator': '>=',
                'value': "date_trunc('month', CURRENT_DATE)"
            })
        
        # Numeric filters
        numeric_patterns = [
            (r'(\d+)\s*dan\s+fazla', '>'),
            (r'(\d+)\s*den\s+fazla', '>'),
            (r'(\d+)\s*dan\s+az', '<'),
            (r'(\d+)\s*den\s+az', '<'),
            (r'en\s+az\s+(\d+)', '>='),
            (r'en\s+fazla\s+(\d+)', '<='),
            (r'(\d+)\s+ve\s+üzeri', '>='),
            (r'(\d+)\s+ve\s+altı', '<=')
        ]
        
        for pattern, operator in numeric_patterns:
            match = re.search(pattern, query_lower)
            if match:
                conditions.append({
                    'type': 'numeric',
                    'operator': operator,
                    'value': int(match.group(1))
                })
        
        # Status filters
        status_keywords = {
            'aktif': "status = 'active'",
            'pasif': "status = 'inactive'",
            'beklemede': "status = 'pending'",
            'tamamlandı': "status = 'completed'",
            'iptal': "status = 'cancelled'"
        }
        
        for keyword, condition in status_keywords.items():
            if keyword in query_lower:
                conditions.append({
                    'type': 'status',
                    'condition': condition
                })
        
        return conditions
    
    def _build_basic_schema_context(self, schema_info: Dict[str, Any]) -> str:
        """
        Build basic schema context string without ChromaDB
        
        Args:
            schema_info: Database schema information
            
        Returns:
            Formatted schema context string
        """
        lines = ["Database Schema:", "=" * 50]
        
        for schema_name, schema_data in schema_info.get('schemas', {}).items():
            # Add tables
            for table in schema_data.get('tables', [])[:20]:  # Limit to 20 tables
                lines.append(f"\nTable: {schema_name}.{table['name']}")
                lines.append("Columns:")
                
                # Add columns
                for column in table.get('columns', [])[:15]:  # Limit to 15 columns per table
                    col_type = column['type']
                    constraints = []
                    if column.get('is_primary_key'):
                        constraints.append('PK')
                    if column.get('is_foreign_key'):
                        constraints.append('FK')
                    if not column.get('nullable', True):
                        constraints.append('NOT NULL')
                    
                    constraint_str = f" [{', '.join(constraints)}]" if constraints else ""
                    lines.append(f"  - {column['name']} ({col_type}){constraint_str}")
                
                # Add row count if available
                if table.get('row_count'):
                    lines.append(f"Row Count: {table['row_count']}")
            
            # Add relationships
            relationships = schema_data.get('relationships', [])[:10]  # Limit to 10 relationships
            if relationships:
                lines.append("\nRelationships:")
                for rel in relationships:
                    lines.append(f"  - {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']}")
        
        return "\n".join(lines)