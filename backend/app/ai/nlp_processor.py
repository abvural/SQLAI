"""
Natural Language Processor with Sentence Transformers
Handles semantic similarity and text embeddings
"""
import logging
import re
import unicodedata
from typing import Dict, List, Optional, Tuple, Any
from sentence_transformers import SentenceTransformer
import numpy as np
from functools import lru_cache

logger = logging.getLogger(__name__)

class NLPProcessor:
    """Natural Language Processing for SQL query generation"""
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Initialize NLP processor with multilingual model
        
        Args:
            model_name: Sentence transformer model (supports Turkish)
        """
        logger.info(f"Loading sentence transformer model: {model_name}")
        self.model = SentenceTransformer(model_name)
        
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
        
        logger.info("NLP Processor initialized successfully")
    
    def normalize_turkish(self, text: str) -> str:
        """
        Normalize Turkish text for better matching
        
        Args:
            text: Input text with Turkish characters
            
        Returns:
            Normalized text
        """
        # Convert to lowercase
        text = text.lower()
        
        # Replace Turkish keywords with SQL equivalents
        for turkish, sql in self.turkish_keywords.items():
            if turkish in text:
                text = text.replace(turkish, f"[{sql}]")
        
        # Normalize Turkish characters for matching (but keep originals for display)
        normalized = text
        for tr_char, latin_char in self.turkish_chars.items():
            normalized = normalized.replace(tr_char, latin_char)
        
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
        Get sentence embedding for text (cached)
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector
        """
        normalized = self.normalize_turkish(text)
        return self.model.encode(normalized, convert_to_numpy=True)
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1)
        """
        embedding1 = self.get_embedding(text1)
        embedding2 = self.get_embedding(text2)
        
        # Cosine similarity
        similarity = np.dot(embedding1, embedding2) / (
            np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
        )
        
        return float(similarity)
    
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