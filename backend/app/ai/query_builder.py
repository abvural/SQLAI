"""
AI-Powered SQL Query Builder
Combines NLP, templates, and graph analysis to generate SQL queries
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json

from app.ai.nlp_processor import NLPProcessor
from app.ai.query_templates import QueryTemplateSystem, QueryType
from app.services.relationship_graph import RelationshipGraphBuilder
from app.services.schema_analyzer import SchemaAnalyzer
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

@dataclass
class QueryInterpretation:
    """Represents a possible interpretation of a natural language query"""
    query: str
    confidence: float
    tables: List[str]
    columns: List[str]
    joins: List[Dict[str, str]]
    conditions: List[Dict[str, Any]]
    aggregations: List[str]
    grouping: List[str]
    ordering: List[Tuple[str, str]]
    limit: Optional[int]
    explanation: str

class SQLQueryBuilder:
    """Build SQL queries from natural language"""
    
    def __init__(self):
        """Initialize query builder"""
        self.nlp_processor = NLPProcessor()
        self.template_system = QueryTemplateSystem()
        self.graph_builder = RelationshipGraphBuilder()
        self.schema_analyzer = SchemaAnalyzer()
        self.cache_service = CacheService()
        
        logger.info("SQL Query Builder initialized")
    
    def build_query(self, natural_query: str, db_id: str) -> Dict[str, Any]:
        """
        Build SQL query from natural language
        
        Args:
            natural_query: Natural language query
            db_id: Database connection ID
            
        Returns:
            Query result with SQL, confidence, and explanations
        """
        logger.info(f"Building query for: {natural_query}")
        
        # Get schema information
        schema_info = self._get_schema_info(db_id)
        if not schema_info:
            return {
                'success': False,
                'error': 'Could not retrieve schema information',
                'query': None
            }
        
        # Process natural language
        keywords = self.nlp_processor.extract_keywords(natural_query)
        query_classification = self.nlp_processor.classify_query_type(natural_query)
        
        # Match tables and columns
        matches = self.nlp_processor.match_tables_columns(natural_query, schema_info)
        
        # Generate interpretations
        interpretations = self._generate_interpretations(
            natural_query, keywords, query_classification, matches, schema_info
        )
        
        if not interpretations:
            return {
                'success': False,
                'error': 'Could not understand the query',
                'suggestions': self._generate_suggestions(natural_query, schema_info)
            }
        
        # Select best interpretation
        best_interpretation = max(interpretations, key=lambda i: i.confidence)
        
        # Handle ambiguity
        if best_interpretation.confidence < 0.5 or len(interpretations) > 1:
            return self._handle_ambiguous_query(interpretations, natural_query)
        
        # Build SQL from interpretation
        sql = self._build_sql_from_interpretation(best_interpretation)
        
        return {
            'success': True,
            'sql': sql,
            'confidence': best_interpretation.confidence,
            'interpretation': {
                'tables': best_interpretation.tables,
                'columns': best_interpretation.columns,
                'explanation': best_interpretation.explanation
            },
            'alternatives': [
                {
                    'sql': self._build_sql_from_interpretation(interp),
                    'confidence': interp.confidence,
                    'explanation': interp.explanation
                }
                for interp in interpretations[1:3]  # Top 3 alternatives
            ] if len(interpretations) > 1 else []
        }
    
    def _get_schema_info(self, db_id: str) -> Optional[Dict[str, Any]]:
        """Get cached schema information"""
        cache_key = f"schema_analysis_{db_id}"
        cached = self.cache_service.get_cache(cache_key, 'schema')
        
        if cached:
            return cached
        
        # Analyze schema if not cached
        schema_info = self.schema_analyzer.analyze_database_schema(db_id)
        if schema_info:
            self.cache_service.set_cache(cache_key, schema_info, 'schema', ttl=3600)
        
        return schema_info
    
    def _generate_interpretations(self, natural_query: str, keywords: Dict,
                                 classification: Dict, matches: Dict,
                                 schema_info: Dict) -> List[QueryInterpretation]:
        """
        Generate possible query interpretations
        
        Args:
            natural_query: Original natural language query
            keywords: Extracted keywords
            classification: Query classification
            matches: Table/column matches
            schema_info: Database schema
            
        Returns:
            List of possible interpretations
        """
        interpretations = []
        
        # Get matched tables
        if not matches['tables']:
            # Try to find tables from keywords
            for entity in keywords['entities']:
                # Find similar tables
                for schema_name, schema_data in schema_info.get('schemas', {}).items():
                    for table in schema_data.get('tables', []):
                        similarity = self.nlp_processor.calculate_similarity(
                            entity, table['name']
                        )
                        if similarity > 0.3:
                            matches['tables'].append({
                                'table': f"{schema_name}.{table['name']}",
                                'confidence': similarity
                            })
        
        if not matches['tables']:
            return interpretations
        
        # Generate interpretation for each matched table combination
        for table_match in matches['tables']:
            interpretation = self._create_interpretation(
                natural_query, table_match, keywords, classification, matches, schema_info
            )
            if interpretation:
                interpretations.append(interpretation)
        
        # Sort by confidence
        interpretations.sort(key=lambda i: i.confidence, reverse=True)
        
        return interpretations
    
    def _create_interpretation(self, natural_query: str, table_match: Dict,
                              keywords: Dict, classification: Dict,
                              matches: Dict, schema_info: Dict) -> Optional[QueryInterpretation]:
        """Create a single query interpretation"""
        table_name = table_match['table']
        base_confidence = table_match['confidence']
        
        # Extract table info
        schema_name, table = table_name.split('.')
        table_info = self._get_table_info(schema_name, table, schema_info)
        if not table_info:
            return None
        
        # Determine columns to select
        columns = self._determine_columns(natural_query, table_info, matches, keywords)
        
        # Determine if joins are needed
        joins = []
        if classification['needs_join'] or len(keywords['entities']) > 1:
            joins = self._determine_joins(table_name, keywords['entities'], schema_info)
        
        # Extract conditions
        conditions = self.nlp_processor.extract_filter_conditions(natural_query)
        
        # Determine aggregations
        aggregations = self._determine_aggregations(keywords, classification)
        
        # Determine grouping
        grouping = self._determine_grouping(natural_query, columns, aggregations)
        
        # Determine ordering
        ordering = self._determine_ordering(keywords, columns)
        
        # Determine limit
        limit = self._extract_limit(natural_query)
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            base_confidence, columns, joins, conditions, aggregations
        )
        
        # Generate SQL
        sql = self._generate_sql(
            table_name, columns, joins, conditions, 
            aggregations, grouping, ordering, limit
        )
        
        # Create explanation
        explanation = self._generate_explanation(
            table_name, columns, joins, conditions, 
            aggregations, grouping, ordering, limit
        )
        
        return QueryInterpretation(
            query=sql,
            confidence=confidence,
            tables=[table_name] + [j['to_table'] for j in joins],
            columns=columns,
            joins=joins,
            conditions=conditions,
            aggregations=aggregations,
            grouping=grouping,
            ordering=ordering,
            limit=limit,
            explanation=explanation
        )
    
    def _get_table_info(self, schema_name: str, table_name: str, 
                       schema_info: Dict) -> Optional[Dict]:
        """Get table information from schema"""
        schema_data = schema_info.get('schemas', {}).get(schema_name, {})
        for table in schema_data.get('tables', []):
            if table['name'] == table_name:
                return table
        return None
    
    def _determine_columns(self, query: str, table_info: Dict, 
                          matches: Dict, keywords: Dict) -> List[str]:
        """Determine which columns to select"""
        columns = []
        
        # Check for specific column matches
        for col_match in matches.get('columns', []):
            if col_match['confidence'] > 0.4:
                columns.append(col_match['column'])
        
        # If no specific columns, check aggregations
        if not columns and keywords.get('aggregates'):
            # For aggregations, typically need specific columns
            for column in table_info.get('columns', []):
                col_type = column['type'].lower()
                if 'count' in keywords['aggregates']:
                    columns.append('*')
                    break
                elif any(agg in keywords['aggregates'] for agg in ['sum', 'avg', 'max', 'min']):
                    if any(t in col_type for t in ['int', 'decimal', 'numeric', 'float']):
                        columns.append(column['name'])
                        break
        
        # Default to all columns if none specified
        if not columns:
            columns = ['*']
        
        return columns
    
    def _determine_joins(self, base_table: str, entities: List[str], 
                        schema_info: Dict) -> List[Dict[str, str]]:
        """Determine necessary joins"""
        joins = []
        
        # Find tables for other entities
        target_tables = []
        for entity in entities:
            for schema_name, schema_data in schema_info.get('schemas', {}).items():
                for table in schema_data.get('tables', []):
                    if self.nlp_processor.calculate_similarity(entity, table['name']) > 0.3:
                        full_name = f"{schema_name}.{table['name']}"
                        if full_name != base_table:
                            target_tables.append(full_name)
        
        # Find join paths
        for target in target_tables:
            try:
                path = self.graph_builder.find_join_path(
                    base_table.split('.')[-1], 
                    target.split('.')[-1]
                )
                if path:
                    for step in path:
                        joins.append({
                            'from_table': step['from_table'],
                            'to_table': step['to_table'],
                            'from_column': step['from_column'],
                            'to_column': step['to_column'],
                            'type': 'INNER JOIN'
                        })
            except Exception as e:
                logger.warning(f"Could not find join path: {e}")
        
        return joins
    
    def _determine_aggregations(self, keywords: Dict, 
                               classification: Dict) -> List[str]:
        """Determine aggregation functions"""
        aggregations = []
        
        if classification['needs_aggregation']:
            for agg in keywords.get('aggregates', []):
                aggregations.append(agg)
        
        return aggregations
    
    def _determine_grouping(self, query: str, columns: List[str], 
                          aggregations: List[str]) -> List[str]:
        """Determine GROUP BY columns"""
        grouping = []
        
        if aggregations and columns != ['*']:
            # Need to group by non-aggregated columns
            for col in columns:
                if not any(agg in col for agg in ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN']):
                    grouping.append(col)
        
        return grouping
    
    def _determine_ordering(self, keywords: Dict, columns: List[str]) -> List[Tuple[str, str]]:
        """Determine ORDER BY clause"""
        ordering = []
        
        if keywords.get('ordering'):
            direction = keywords['ordering'][0]
            # Order by first numeric column or first column
            order_col = columns[0] if columns and columns != ['*'] else None
            if order_col:
                ordering.append((order_col, direction))
        
        return ordering
    
    def _extract_limit(self, query: str) -> Optional[int]:
        """Extract LIMIT value from query"""
        import re
        
        # Common patterns for limit
        patterns = [
            r'ilk (\d+)',
            r'top (\d+)',
            r'(\d+) tane',
            r'(\d+) adet'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                return int(match.group(1))
        
        return None
    
    def _calculate_confidence(self, base_confidence: float, columns: List[str],
                            joins: List[Dict], conditions: List[Dict],
                            aggregations: List[str]) -> float:
        """Calculate overall confidence score"""
        confidence = base_confidence
        
        # Adjust based on query complexity
        if columns == ['*']:
            confidence *= 0.9  # Slight penalty for not specific columns
        
        if joins:
            confidence *= 0.95 ** len(joins)  # Penalty for each join
        
        if conditions:
            confidence *= 1.05  # Bonus for specific conditions
        
        if aggregations:
            confidence *= 1.05  # Bonus for clear aggregation intent
        
        # Ensure confidence is between 0 and 1
        return min(max(confidence, 0.0), 1.0)
    
    def _generate_sql(self, table: str, columns: List[str], joins: List[Dict],
                     conditions: List[Dict], aggregations: List[str],
                     grouping: List[str], ordering: List[Tuple[str, str]],
                     limit: Optional[int]) -> str:
        """Generate SQL query from components"""
        # Start with SELECT
        if aggregations:
            select_parts = []
            for agg in aggregations:
                if agg == 'COUNT':
                    select_parts.append(f"COUNT(*) AS count")
                else:
                    # Find numeric column for aggregation
                    for col in columns:
                        if col != '*':
                            select_parts.append(f"{agg}({col}) AS {agg.lower()}_{col}")
                            break
            
            if grouping:
                select_parts = grouping + select_parts
            
            sql = f"SELECT {', '.join(select_parts)}"
        else:
            sql = f"SELECT {', '.join(columns)}"
        
        # FROM clause
        sql += f" FROM {table}"
        
        # JOIN clauses
        for join in joins:
            sql += f" {join['type']} {join['to_table']}"
            sql += f" ON {join['from_table']}.{join['from_column']} = {join['to_table']}.{join['to_column']}"
        
        # WHERE clause
        if conditions:
            where_parts = []
            for cond in conditions:
                if cond['type'] == 'status':
                    where_parts.append(cond['condition'])
                elif cond['type'] == 'numeric':
                    where_parts.append(f"value {cond['operator']} {cond['value']}")
                elif cond['type'] == 'date':
                    where_parts.append(f"date_column {cond['operator']} {cond['value']}")
            
            if where_parts:
                sql += f" WHERE {' AND '.join(where_parts)}"
        
        # GROUP BY clause
        if grouping:
            sql += f" GROUP BY {', '.join(grouping)}"
        
        # ORDER BY clause
        if ordering:
            order_parts = [f"{col} {direction}" for col, direction in ordering]
            sql += f" ORDER BY {', '.join(order_parts)}"
        
        # LIMIT clause
        if limit:
            sql += f" LIMIT {limit}"
        
        return sql
    
    def _generate_explanation(self, table: str, columns: List[str], joins: List[Dict],
                            conditions: List[Dict], aggregations: List[str],
                            grouping: List[str], ordering: List[Tuple[str, str]],
                            limit: Optional[int]) -> str:
        """Generate human-readable explanation"""
        parts = []
        
        if aggregations:
            parts.append(f"Calculating {', '.join(aggregations)}")
        else:
            parts.append("Retrieving data")
        
        parts.append(f"from {table}")
        
        if joins:
            parts.append(f"with {len(joins)} join(s)")
        
        if conditions:
            parts.append(f"filtered by {len(conditions)} condition(s)")
        
        if grouping:
            parts.append(f"grouped by {', '.join(grouping)}")
        
        if ordering:
            parts.append("sorted")
        
        if limit:
            parts.append(f"limited to {limit} results")
        
        return " ".join(parts)
    
    def _build_sql_from_interpretation(self, interpretation: QueryInterpretation) -> str:
        """Build SQL from interpretation object"""
        return interpretation.query
    
    def _handle_ambiguous_query(self, interpretations: List[QueryInterpretation],
                               natural_query: str) -> Dict[str, Any]:
        """Handle queries with multiple interpretations"""
        return {
            'success': False,
            'ambiguous': True,
            'message': 'Multiple interpretations found. Please clarify:',
            'interpretations': [
                {
                    'sql': interp.query,
                    'confidence': interp.confidence,
                    'explanation': interp.explanation,
                    'tables': interp.tables
                }
                for interp in interpretations[:3]  # Top 3 interpretations
            ],
            'original_query': natural_query,
            'suggestions': [
                'Specify which table you want to query',
                'Add more specific conditions',
                'Clarify the columns you need'
            ]
        }
    
    def _generate_suggestions(self, query: str, schema_info: Dict) -> List[str]:
        """Generate query suggestions"""
        suggestions = []
        
        # Get available tables
        tables = []
        for schema_name, schema_data in schema_info.get('schemas', {}).items():
            for table in schema_data.get('tables', []):
                tables.append(table['name'])
        
        suggestions.append(f"Available tables: {', '.join(tables[:5])}")
        suggestions.append("Try being more specific about what data you need")
        suggestions.append("Examples: 'Show all customers', 'Count orders by status'")
        
        return suggestions
    
    def validate_query(self, sql: str) -> Dict[str, Any]:
        """
        Validate generated SQL query
        
        Args:
            sql: SQL query to validate
            
        Returns:
            Validation result
        """
        from app.utils.sql_validator import SQLValidator
        
        validator = SQLValidator()
        is_valid, errors = validator.validate_query(sql)
        
        return {
            'valid': is_valid,
            'errors': errors,
            'safe': not validator.contains_dangerous_patterns(sql)
        }