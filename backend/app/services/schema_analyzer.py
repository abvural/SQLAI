"""
Advanced Schema Analysis Service
Extends PostgresInspector with pattern recognition and metadata extraction
"""
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
import re
from collections import defaultdict, Counter

from app.services.postgres_inspector import PostgresInspector
from app.services.cache_service import CacheService
from app.models import TableCache, ColumnCache, RelationshipCache

logger = logging.getLogger(__name__)

class SchemaAnalyzer:
    """Advanced schema analysis with pattern recognition"""
    
    def __init__(self):
        self.inspector = PostgresInspector()
        self.cache_service = CacheService()
        
        # Common table name patterns
        self.entity_patterns = {
            'user': ['user', 'users', 'kullanici', 'kullanicilar', 'member', 'account'],
            'product': ['product', 'products', 'urun', 'urunler', 'item', 'items'],
            'order': ['order', 'orders', 'siparis', 'siparisler', 'purchase'],
            'customer': ['customer', 'customers', 'musteri', 'musteriler', 'client'],
            'category': ['category', 'categories', 'kategori', 'kategoriler', 'type'],
            'payment': ['payment', 'payments', 'odeme', 'odemeler', 'transaction'],
            'invoice': ['invoice', 'invoices', 'fatura', 'faturalar', 'bill'],
            'supplier': ['supplier', 'suppliers', 'tedarikci', 'tedarikciler', 'vendor'],
            'employee': ['employee', 'employees', 'calisan', 'calisanlar', 'staff'],
            'inventory': ['inventory', 'stock', 'stok', 'envanter', 'warehouse']
        }
        
        # Common column patterns
        self.column_patterns = {
            'id': r'^(id|_id|.*_id)$',
            'name': r'^(name|.*_name|ad|.*_ad|adi|.*_adi)$',
            'email': r'^(email|.*_email|eposta|.*_eposta)$',
            'phone': r'^(phone|.*_phone|telefon|.*_telefon|tel|.*_tel)$',
            'date': r'^(.*_date|.*_at|tarih|.*_tarih|created|updated|modified)$',
            'price': r'^(price|.*_price|fiyat|.*_fiyat|cost|amount|tutar)$',
            'status': r'^(status|.*_status|durum|.*_durum|state|.*_state)$',
            'description': r'^(description|.*_desc|aciklama|.*_aciklama|note|comment)$',
            'address': r'^(address|.*_address|adres|.*_adres|location)$',
            'quantity': r'^(quantity|qty|.*_qty|miktar|.*_miktar|adet|count)$'
        }
        
        # Turkish naming patterns
        self.turkish_patterns = {
            'plural_suffixes': ['lar', 'ler', 'ları', 'leri'],
            'common_words': {
                'tablo': 'table',
                'kayit': 'record',
                'liste': 'list',
                'detay': 'detail',
                'bilgi': 'info',
                'islem': 'transaction',
                'hareket': 'movement',
                'rapor': 'report'
            }
        }
    
    def analyze_database_schema(self, db_id: str, deep_analysis: bool = True) -> Dict[str, Any]:
        """
        Perform comprehensive schema analysis
        
        Args:
            db_id: Database connection ID
            deep_analysis: Whether to perform deep pattern analysis
            
        Returns:
            Complete schema analysis with patterns and insights
        """
        logger.info(f"Starting schema analysis for database {db_id}")
        start_time = datetime.now()
        
        # Get basic schema information
        schema_info = self.inspector.analyze_schema(db_id)
        
        # Enhanced analysis
        analysis_result = {
            **schema_info,
            'analysis_timestamp': datetime.now().isoformat(),
            'patterns': {},
            'statistics': {},
            'insights': [],
            'recommendations': []
        }
        
        if deep_analysis:
            # Analyze patterns
            analysis_result['patterns'] = self._analyze_patterns(schema_info)
            
            # Generate statistics
            analysis_result['statistics'] = self._generate_statistics(schema_info)
            
            # Generate insights
            analysis_result['insights'] = self._generate_insights(schema_info)
            
            # Generate recommendations
            analysis_result['recommendations'] = self._generate_recommendations(schema_info)
        
        # Calculate analysis time
        analysis_time = (datetime.now() - start_time).total_seconds()
        analysis_result['analysis_time_seconds'] = analysis_time
        
        logger.info(f"Schema analysis completed in {analysis_time:.2f} seconds")
        
        # Cache the analysis
        self._cache_analysis_results(db_id, analysis_result)
        
        return analysis_result
    
    def _analyze_patterns(self, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze naming patterns and conventions"""
        patterns = {
            'naming_convention': self._detect_naming_convention(schema_info),
            'entity_types': self._identify_entity_types(schema_info),
            'relationship_patterns': self._analyze_relationship_patterns(schema_info),
            'column_patterns': self._analyze_column_patterns(schema_info),
            'turkish_usage': self._detect_turkish_usage(schema_info)
        }
        
        return patterns
    
    def _detect_naming_convention(self, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """Detect naming conventions used in the database"""
        conventions = {
            'table_naming': 'unknown',
            'column_naming': 'unknown',
            'uses_prefixes': False,
            'uses_suffixes': False,
            'case_style': 'unknown'
        }
        
        table_names = []
        column_names = []
        
        for schema_name, schema_data in schema_info.get('schemas', {}).items():
            for table in schema_data.get('tables', []):
                table_names.append(table['name'])
                for column in table.get('columns', []):
                    column_names.append(column['name'])
        
        if table_names:
            # Check case style
            if all(name.islower() for name in table_names):
                conventions['case_style'] = 'lowercase'
            elif all(name.isupper() for name in table_names):
                conventions['case_style'] = 'uppercase'
            elif all('_' in name for name in table_names):
                conventions['case_style'] = 'snake_case'
            elif all(name[0].isupper() for name in table_names):
                conventions['case_style'] = 'PascalCase'
            
            # Check for common prefixes
            if len(table_names) > 3:
                common_prefix = self._find_common_prefix(table_names)
                if common_prefix and len(common_prefix) > 2:
                    conventions['uses_prefixes'] = True
                    conventions['common_prefix'] = common_prefix
            
            # Check for common suffixes
            common_suffixes = ['_table', '_tbl', '_data', '_info']
            for suffix in common_suffixes:
                if sum(1 for name in table_names if name.endswith(suffix)) > len(table_names) * 0.3:
                    conventions['uses_suffixes'] = True
                    conventions['common_suffix'] = suffix
                    break
            
            # Determine table naming style
            if sum(1 for name in table_names if name.endswith('s')) > len(table_names) * 0.5:
                conventions['table_naming'] = 'plural'
            else:
                conventions['table_naming'] = 'singular'
        
        return conventions
    
    def _identify_entity_types(self, schema_info: Dict[str, Any]) -> Dict[str, List[str]]:
        """Identify entity types from table names"""
        entity_mapping = defaultdict(list)
        
        for schema_name, schema_data in schema_info.get('schemas', {}).items():
            for table in schema_data.get('tables', []):
                table_name_lower = table['name'].lower()
                
                # Check against known patterns
                for entity_type, patterns in self.entity_patterns.items():
                    for pattern in patterns:
                        if pattern in table_name_lower:
                            entity_mapping[entity_type].append(f"{schema_name}.{table['name']}")
                            break
        
        return dict(entity_mapping)
    
    def _analyze_relationship_patterns(self, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze relationship patterns in the database"""
        patterns = {
            'total_relationships': 0,
            'relationship_types': Counter(),
            'most_connected_tables': [],
            'isolated_tables': [],
            'relationship_density': 0.0
        }
        
        table_connections = defaultdict(int)
        total_tables = 0
        
        for schema_name, schema_data in schema_info.get('schemas', {}).items():
            total_tables += len(schema_data.get('tables', []))
            
            for relationship in schema_data.get('relationships', []):
                patterns['total_relationships'] += 1
                patterns['relationship_types'][relationship.get('type', 'unknown')] += 1
                
                from_table = f"{relationship['from_schema']}.{relationship['from_table']}"
                to_table = f"{relationship['to_schema']}.{relationship['to_table']}"
                
                table_connections[from_table] += 1
                table_connections[to_table] += 1
        
        # Find most connected tables
        if table_connections:
            sorted_connections = sorted(table_connections.items(), key=lambda x: x[1], reverse=True)
            patterns['most_connected_tables'] = [
                {'table': table, 'connections': count}
                for table, count in sorted_connections[:5]
            ]
        
        # Find isolated tables
        for schema_name, schema_data in schema_info.get('schemas', {}).items():
            for table in schema_data.get('tables', []):
                full_table_name = f"{schema_name}.{table['name']}"
                if full_table_name not in table_connections:
                    patterns['isolated_tables'].append(full_table_name)
        
        # Calculate relationship density
        if total_tables > 1:
            max_possible_relationships = total_tables * (total_tables - 1)
            patterns['relationship_density'] = patterns['total_relationships'] / max_possible_relationships
        
        return patterns
    
    def _analyze_column_patterns(self, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze column naming and type patterns"""
        patterns = {
            'common_columns': Counter(),
            'data_type_distribution': Counter(),
            'semantic_types': defaultdict(list),
            'nullable_percentage': 0.0,
            'primary_key_types': Counter(),
            'foreign_key_percentage': 0.0
        }
        
        total_columns = 0
        nullable_columns = 0
        foreign_key_columns = 0
        
        for schema_name, schema_data in schema_info.get('schemas', {}).items():
            for table in schema_data.get('tables', []):
                for column in table.get('columns', []):
                    total_columns += 1
                    column_name_lower = column['name'].lower()
                    
                    # Track common column names
                    patterns['common_columns'][column_name_lower] += 1
                    
                    # Track data types
                    patterns['data_type_distribution'][column['type']] += 1
                    
                    # Identify semantic types
                    for semantic_type, pattern in self.column_patterns.items():
                        if re.match(pattern, column_name_lower):
                            patterns['semantic_types'][semantic_type].append(
                                f"{table['name']}.{column['name']}"
                            )
                            break
                    
                    # Track nullable columns
                    if column.get('nullable', False):
                        nullable_columns += 1
                    
                    # Track primary key types
                    if column.get('is_primary_key', False):
                        patterns['primary_key_types'][column['type']] += 1
                    
                    # Track foreign keys
                    if column.get('is_foreign_key', False):
                        foreign_key_columns += 1
        
        # Calculate percentages
        if total_columns > 0:
            patterns['nullable_percentage'] = (nullable_columns / total_columns) * 100
            patterns['foreign_key_percentage'] = (foreign_key_columns / total_columns) * 100
        
        # Get top common columns
        patterns['common_columns'] = dict(patterns['common_columns'].most_common(10))
        patterns['data_type_distribution'] = dict(patterns['data_type_distribution'])
        patterns['semantic_types'] = dict(patterns['semantic_types'])
        patterns['primary_key_types'] = dict(patterns['primary_key_types'])
        
        return patterns
    
    def _detect_turkish_usage(self, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """Detect Turkish language usage in schema"""
        turkish_usage = {
            'uses_turkish': False,
            'turkish_tables': [],
            'turkish_columns': [],
            'mixed_language': False
        }
        
        turkish_chars = set('çğıöşüÇĞİÖŞÜ')
        english_count = 0
        turkish_count = 0
        
        for schema_name, schema_data in schema_info.get('schemas', {}).items():
            for table in schema_data.get('tables', []):
                table_name = table['name']
                
                # Check for Turkish characters
                if any(char in turkish_chars for char in table_name):
                    turkish_usage['turkish_tables'].append(table_name)
                    turkish_count += 1
                
                # Check for Turkish words
                for tr_word in self.turkish_patterns['common_words'].keys():
                    if tr_word in table_name.lower():
                        if table_name not in turkish_usage['turkish_tables']:
                            turkish_usage['turkish_tables'].append(table_name)
                        turkish_count += 1
                        break
                else:
                    # Check if it's English
                    for entity_patterns in self.entity_patterns.values():
                        if any(pattern in table_name.lower() for pattern in entity_patterns if pattern.isascii()):
                            english_count += 1
                            break
                
                # Check columns
                for column in table.get('columns', []):
                    column_name = column['name']
                    if any(char in turkish_chars for char in column_name):
                        turkish_usage['turkish_columns'].append(f"{table_name}.{column_name}")
        
        # Determine language usage
        if turkish_usage['turkish_tables'] or turkish_usage['turkish_columns']:
            turkish_usage['uses_turkish'] = True
        
        if english_count > 0 and turkish_count > 0:
            turkish_usage['mixed_language'] = True
        
        return turkish_usage
    
    def _generate_statistics(self, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate statistical summary of the schema"""
        stats = {
            'total_schemas': len(schema_info.get('schemas', {})),
            'total_tables': schema_info.get('total_tables', 0),
            'total_columns': schema_info.get('total_columns', 0),
            'total_relationships': schema_info.get('total_relationships', 0),
            'avg_columns_per_table': 0,
            'avg_relationships_per_table': 0,
            'largest_tables': [],
            'most_columns_tables': [],
            'data_size_estimate_mb': 0
        }
        
        table_sizes = []
        table_columns = []
        total_size_bytes = 0
        
        for schema_name, schema_data in schema_info.get('schemas', {}).items():
            for table in schema_data.get('tables', []):
                # Track table sizes
                size_bytes = table.get('size_bytes', 0)
                row_count = table.get('row_count', 0)
                column_count = len(table.get('columns', []))
                
                table_sizes.append({
                    'name': f"{schema_name}.{table['name']}",
                    'row_count': row_count,
                    'size_bytes': size_bytes
                })
                
                table_columns.append({
                    'name': f"{schema_name}.{table['name']}",
                    'column_count': column_count
                })
                
                total_size_bytes += size_bytes
        
        # Calculate averages
        if stats['total_tables'] > 0:
            stats['avg_columns_per_table'] = stats['total_columns'] / stats['total_tables']
            stats['avg_relationships_per_table'] = stats['total_relationships'] / stats['total_tables']
        
        # Get largest tables
        table_sizes.sort(key=lambda x: x['row_count'], reverse=True)
        stats['largest_tables'] = table_sizes[:5]
        
        # Get tables with most columns
        table_columns.sort(key=lambda x: x['column_count'], reverse=True)
        stats['most_columns_tables'] = table_columns[:5]
        
        # Estimate total data size
        stats['data_size_estimate_mb'] = total_size_bytes / (1024 * 1024)
        
        return stats
    
    def _generate_insights(self, schema_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights about the schema"""
        insights = []
        
        # Check for missing primary keys
        for schema_name, schema_data in schema_info.get('schemas', {}).items():
            for table in schema_data.get('tables', []):
                if not table.get('has_primary_key', False):
                    insights.append({
                        'type': 'warning',
                        'category': 'structure',
                        'title': 'Missing Primary Key',
                        'description': f"Table {schema_name}.{table['name']} doesn't have a primary key",
                        'impact': 'high',
                        'table': f"{schema_name}.{table['name']}"
                    })
        
        # Check for isolated tables
        isolated_tables = []
        for schema_name, schema_data in schema_info.get('schemas', {}).items():
            relationships = schema_data.get('relationships', [])
            related_tables = set()
            
            for rel in relationships:
                related_tables.add(rel['from_table'])
                related_tables.add(rel['to_table'])
            
            for table in schema_data.get('tables', []):
                if table['name'] not in related_tables:
                    isolated_tables.append(f"{schema_name}.{table['name']}")
        
        if isolated_tables:
            insights.append({
                'type': 'info',
                'category': 'relationships',
                'title': 'Isolated Tables Found',
                'description': f"Found {len(isolated_tables)} tables with no relationships",
                'impact': 'medium',
                'tables': isolated_tables
            })
        
        # Check for large tables without indexes
        for schema_name, schema_data in schema_info.get('schemas', {}).items():
            for table in schema_data.get('tables', []):
                row_count = table.get('row_count', 0)
                index_count = len(table.get('indexes', []))
                
                if row_count > 10000 and index_count < 2:
                    insights.append({
                        'type': 'warning',
                        'category': 'performance',
                        'title': 'Large Table with Few Indexes',
                        'description': f"Table {schema_name}.{table['name']} has {row_count} rows but only {index_count} indexes",
                        'impact': 'high',
                        'table': f"{schema_name}.{table['name']}",
                        'row_count': row_count,
                        'index_count': index_count
                    })
        
        return insights
    
    def _generate_recommendations(self, schema_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate recommendations for schema optimization"""
        recommendations = []
        
        # Recommend indexes for foreign key columns
        for schema_name, schema_data in schema_info.get('schemas', {}).items():
            for table in schema_data.get('tables', []):
                for column in table.get('columns', []):
                    if column.get('is_foreign_key', False):
                        # Check if there's an index on this column
                        has_index = False
                        for index in table.get('indexes', []):
                            if column['name'] in index.get('definition', ''):
                                has_index = True
                                break
                        
                        if not has_index:
                            recommendations.append({
                                'type': 'performance',
                                'priority': 'high',
                                'title': 'Add Index on Foreign Key',
                                'description': f"Consider adding an index on {table['name']}.{column['name']} for better join performance",
                                'sql': f"CREATE INDEX idx_{table['name']}_{column['name']} ON {schema_name}.{table['name']} ({column['name']});",
                                'table': f"{schema_name}.{table['name']}",
                                'column': column['name']
                            })
        
        # Recommend normalization for repeated values
        for schema_name, schema_data in schema_info.get('schemas', {}).items():
            for table in schema_data.get('tables', []):
                for column in table.get('columns', []):
                    # Check for columns that might benefit from normalization
                    column_name_lower = column['name'].lower()
                    if any(pattern in column_name_lower for pattern in ['status', 'type', 'category', 'state']):
                        if column['type'] in ['character varying', 'text', 'varchar']:
                            recommendations.append({
                                'type': 'normalization',
                                'priority': 'medium',
                                'title': 'Consider Normalization',
                                'description': f"Column {table['name']}.{column['name']} might benefit from normalization into a separate lookup table",
                                'table': f"{schema_name}.{table['name']}",
                                'column': column['name']
                            })
                            break  # Only one recommendation per table for this
        
        return recommendations
    
    def _find_common_prefix(self, strings: List[str]) -> str:
        """Find common prefix among strings"""
        if not strings:
            return ""
        
        shortest = min(strings, key=len)
        for i, char in enumerate(shortest):
            for other in strings:
                if other[i] != char:
                    return shortest[:i]
        return shortest
    
    def _cache_analysis_results(self, db_id: str, analysis_result: Dict[str, Any]):
        """Cache the analysis results"""
        try:
            # Save insights as AI insights
            for insight in analysis_result.get('insights', []):
                self.cache_service.save_ai_insight(
                    db_id=db_id,
                    target_type='schema',
                    target_name=insight.get('table', 'database'),
                    insight_type=insight['category'],
                    title=insight['title'],
                    description=insight['description'],
                    severity=insight['type'],
                    confidence=0.85,
                    metadata=insight
                )
            
            logger.info(f"Cached {len(analysis_result.get('insights', []))} insights for database {db_id}")
            
        except Exception as e:
            logger.error(f"Failed to cache analysis results: {e}")
    
    def get_table_importance_scores(self, db_id: str) -> Dict[str, float]:
        """
        Calculate importance scores for tables based on relationships and size
        
        Args:
            db_id: Database connection ID
            
        Returns:
            Dictionary of table names with importance scores (0.0 to 1.0)
        """
        scores = {}
        
        # Get cached tables and relationships
        tables = self.cache_service.get_tables(db_id)
        
        # Get relationships using a fresh session
        from app.models import get_session, RelationshipCache
        with get_session() as session:
            relationships = session.query(RelationshipCache).filter_by(database_id=db_id).all()
            
            # Count connections per table
            connection_count = defaultdict(int)
            for rel in relationships:
                connection_count[rel.from_table] += 1
                connection_count[rel.to_table] += 1
        
        # Calculate scores
        max_connections = max(connection_count.values()) if connection_count else 1
        max_rows = max(t.get('row_count', 0) for t in tables) if tables else 1
        
        for table in tables:
            table_name = table['table_name']
            
            # Connection score (0.5 weight)
            connection_score = connection_count.get(table_name, 0) / max_connections * 0.5
            
            # Size score (0.3 weight)
            size_score = (table.get('row_count', 0) / max_rows) * 0.3 if max_rows > 0 else 0
            
            # Has primary key score (0.2 weight)
            pk_score = 0.2 if table.get('has_primary_key', False) else 0
            
            scores[table_name] = min(connection_score + size_score + pk_score, 1.0)
        
        return scores