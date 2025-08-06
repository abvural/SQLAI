"""
SQL Query Template System
Provides templates for common query patterns
"""
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Query type enumeration"""
    SELECT = "select"
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MAX = "max"
    MIN = "min"
    GROUP_BY = "group_by"
    JOIN = "join"
    COMPLEX = "complex"

@dataclass
class QueryTemplate:
    """SQL Query Template"""
    name: str
    type: QueryType
    template: str
    parameters: List[str]
    description: str
    example_nl: str
    example_sql: str
    complexity: int  # 1-5 scale

class QueryTemplateSystem:
    """Manages SQL query templates"""
    
    def __init__(self):
        """Initialize query template system"""
        self.templates = self._initialize_templates()
        logger.info(f"Initialized {len(self.templates)} query templates")
    
    def _initialize_templates(self) -> Dict[str, QueryTemplate]:
        """Initialize all query templates"""
        templates = {}
        
        # Simple SELECT template
        templates['simple_select'] = QueryTemplate(
            name='simple_select',
            type=QueryType.SELECT,
            template="SELECT {columns} FROM {table} {where_clause} {order_clause} {limit_clause}",
            parameters=['columns', 'table', 'where_clause', 'order_clause', 'limit_clause'],
            description="Simple SELECT query for retrieving data",
            example_nl="Show all customers",
            example_sql="SELECT * FROM customers",
            complexity=1
        )
        
        # COUNT template
        templates['count'] = QueryTemplate(
            name='count',
            type=QueryType.COUNT,
            template="SELECT COUNT({column}) AS count FROM {table} {where_clause}",
            parameters=['column', 'table', 'where_clause'],
            description="Count rows in a table",
            example_nl="How many customers do we have?",
            example_sql="SELECT COUNT(*) AS count FROM customers",
            complexity=1
        )
        
        # COUNT with GROUP BY
        templates['count_group'] = QueryTemplate(
            name='count_group',
            type=QueryType.COUNT,
            template="SELECT {group_column}, COUNT({count_column}) AS count FROM {table} {where_clause} GROUP BY {group_column} {having_clause} {order_clause}",
            parameters=['group_column', 'count_column', 'table', 'where_clause', 'having_clause', 'order_clause'],
            description="Count rows grouped by a column",
            example_nl="How many orders per customer?",
            example_sql="SELECT customer_id, COUNT(*) AS count FROM orders GROUP BY customer_id",
            complexity=2
        )
        
        # SUM template
        templates['sum'] = QueryTemplate(
            name='sum',
            type=QueryType.SUM,
            template="SELECT SUM({column}) AS total FROM {table} {where_clause}",
            parameters=['column', 'table', 'where_clause'],
            description="Sum values in a column",
            example_nl="What is the total revenue?",
            example_sql="SELECT SUM(amount) AS total FROM orders",
            complexity=1
        )
        
        # SUM with GROUP BY
        templates['sum_group'] = QueryTemplate(
            name='sum_group',
            type=QueryType.SUM,
            template="SELECT {group_column}, SUM({sum_column}) AS total FROM {table} {where_clause} GROUP BY {group_column} {having_clause} {order_clause}",
            parameters=['group_column', 'sum_column', 'table', 'where_clause', 'having_clause', 'order_clause'],
            description="Sum values grouped by a column",
            example_nl="Total sales per category",
            example_sql="SELECT category, SUM(amount) AS total FROM sales GROUP BY category",
            complexity=2
        )
        
        # AVG template
        templates['avg'] = QueryTemplate(
            name='avg',
            type=QueryType.AVG,
            template="SELECT AVG({column}) AS average FROM {table} {where_clause}",
            parameters=['column', 'table', 'where_clause'],
            description="Calculate average of a column",
            example_nl="What is the average order value?",
            example_sql="SELECT AVG(amount) AS average FROM orders",
            complexity=1
        )
        
        # MAX template
        templates['max'] = QueryTemplate(
            name='max',
            type=QueryType.MAX,
            template="SELECT MAX({column}) AS maximum FROM {table} {where_clause}",
            parameters=['column', 'table', 'where_clause'],
            description="Find maximum value in a column",
            example_nl="What is the highest sale amount?",
            example_sql="SELECT MAX(amount) AS maximum FROM sales",
            complexity=1
        )
        
        # MAX with details
        templates['max_details'] = QueryTemplate(
            name='max_details',
            type=QueryType.MAX,
            template="SELECT {columns} FROM {table} WHERE {column} = (SELECT MAX({column}) FROM {table} {inner_where}) {outer_where}",
            parameters=['columns', 'table', 'column', 'inner_where', 'outer_where'],
            description="Find row with maximum value",
            example_nl="Which customer made the biggest purchase?",
            example_sql="SELECT * FROM orders WHERE amount = (SELECT MAX(amount) FROM orders)",
            complexity=3
        )
        
        # MIN template
        templates['min'] = QueryTemplate(
            name='min',
            type=QueryType.MIN,
            template="SELECT MIN({column}) AS minimum FROM {table} {where_clause}",
            parameters=['column', 'table', 'where_clause'],
            description="Find minimum value in a column",
            example_nl="What is the lowest price?",
            example_sql="SELECT MIN(price) AS minimum FROM products",
            complexity=1
        )
        
        # Simple JOIN template
        templates['simple_join'] = QueryTemplate(
            name='simple_join',
            type=QueryType.JOIN,
            template="SELECT {columns} FROM {table1} JOIN {table2} ON {join_condition} {where_clause} {order_clause}",
            parameters=['columns', 'table1', 'table2', 'join_condition', 'where_clause', 'order_clause'],
            description="Join two tables",
            example_nl="Show orders with customer names",
            example_sql="SELECT o.*, c.name FROM orders o JOIN customers c ON o.customer_id = c.id",
            complexity=2
        )
        
        # Multiple JOIN template
        templates['multi_join'] = QueryTemplate(
            name='multi_join',
            type=QueryType.JOIN,
            template="SELECT {columns} FROM {base_table} {join_clauses} {where_clause} {group_clause} {order_clause}",
            parameters=['columns', 'base_table', 'join_clauses', 'where_clause', 'group_clause', 'order_clause'],
            description="Join multiple tables",
            example_nl="Show order details with customer and product information",
            example_sql="SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id JOIN products p ON o.product_id = p.id",
            complexity=3
        )
        
        # Complex aggregation with JOIN
        templates['complex_aggregation'] = QueryTemplate(
            name='complex_aggregation',
            type=QueryType.COMPLEX,
            template="""SELECT {group_columns}, {aggregations}
FROM {base_table}
{join_clauses}
{where_clause}
GROUP BY {group_columns}
{having_clause}
{order_clause}
{limit_clause}""",
            parameters=['group_columns', 'aggregations', 'base_table', 'join_clauses', 
                       'where_clause', 'having_clause', 'order_clause', 'limit_clause'],
            description="Complex query with joins and aggregations",
            example_nl="Top 10 customers by total purchase amount last month",
            example_sql="""SELECT c.name, SUM(o.amount) as total
FROM customers c
JOIN orders o ON c.id = o.customer_id
WHERE o.order_date >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month')
GROUP BY c.id, c.name
ORDER BY total DESC
LIMIT 10""",
            complexity=4
        )
        
        # Subquery template
        templates['subquery'] = QueryTemplate(
            name='subquery',
            type=QueryType.COMPLEX,
            template="SELECT {columns} FROM {table} WHERE {column} {operator} (SELECT {sub_column} FROM {sub_table} {sub_where})",
            parameters=['columns', 'table', 'column', 'operator', 'sub_column', 'sub_table', 'sub_where'],
            description="Query with subquery",
            example_nl="Customers who spent more than average",
            example_sql="SELECT * FROM customers WHERE total_spent > (SELECT AVG(total_spent) FROM customers)",
            complexity=3
        )
        
        # Window function template
        templates['window_function'] = QueryTemplate(
            name='window_function',
            type=QueryType.COMPLEX,
            template="SELECT {columns}, {window_function} OVER (PARTITION BY {partition_column} ORDER BY {order_column}) AS {alias} FROM {table} {where_clause}",
            parameters=['columns', 'window_function', 'partition_column', 'order_column', 'alias', 'table', 'where_clause'],
            description="Query with window function",
            example_nl="Rank customers by purchase amount within each category",
            example_sql="SELECT *, RANK() OVER (PARTITION BY category ORDER BY amount DESC) AS rank FROM sales",
            complexity=4
        )
        
        # Date range template
        templates['date_range'] = QueryTemplate(
            name='date_range',
            type=QueryType.SELECT,
            template="SELECT {columns} FROM {table} WHERE {date_column} BETWEEN {start_date} AND {end_date} {additional_where} {order_clause}",
            parameters=['columns', 'table', 'date_column', 'start_date', 'end_date', 'additional_where', 'order_clause'],
            description="Query with date range filter",
            example_nl="Orders from last month",
            example_sql="SELECT * FROM orders WHERE order_date BETWEEN '2024-01-01' AND '2024-01-31'",
            complexity=2
        )
        
        # DISTINCT template
        templates['distinct'] = QueryTemplate(
            name='distinct',
            type=QueryType.SELECT,
            template="SELECT DISTINCT {columns} FROM {table} {where_clause} {order_clause}",
            parameters=['columns', 'table', 'where_clause', 'order_clause'],
            description="Select distinct values",
            example_nl="List all unique categories",
            example_sql="SELECT DISTINCT category FROM products",
            complexity=1
        )
        
        # EXISTS template
        templates['exists'] = QueryTemplate(
            name='exists',
            type=QueryType.SELECT,
            template="SELECT {columns} FROM {table1} t1 WHERE EXISTS (SELECT 1 FROM {table2} t2 WHERE {exists_condition})",
            parameters=['columns', 'table1', 'table2', 'exists_condition'],
            description="Query with EXISTS clause",
            example_nl="Customers who have placed orders",
            example_sql="SELECT * FROM customers c WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id)",
            complexity=3
        )
        
        # UNION template
        templates['union'] = QueryTemplate(
            name='union',
            type=QueryType.COMPLEX,
            template="({query1}) UNION {union_type} ({query2}) {order_clause}",
            parameters=['query1', 'query2', 'union_type', 'order_clause'],
            description="Combine results from multiple queries",
            example_nl="All customers and suppliers",
            example_sql="(SELECT name, 'customer' as type FROM customers) UNION (SELECT name, 'supplier' as type FROM suppliers)",
            complexity=3
        )
        
        # TOP N template
        templates['top_n'] = QueryTemplate(
            name='top_n',
            type=QueryType.SELECT,
            template="SELECT {columns} FROM {table} {where_clause} ORDER BY {order_column} {order_direction} LIMIT {limit}",
            parameters=['columns', 'table', 'where_clause', 'order_column', 'order_direction', 'limit'],
            description="Get top N records",
            example_nl="Top 5 best selling products",
            example_sql="SELECT * FROM products ORDER BY sales_count DESC LIMIT 5",
            complexity=2
        )
        
        return templates
    
    def get_template(self, name: str) -> Optional[QueryTemplate]:
        """
        Get a specific template by name
        
        Args:
            name: Template name
            
        Returns:
            QueryTemplate or None
        """
        return self.templates.get(name)
    
    def find_matching_templates(self, query_type: QueryType, 
                              complexity_max: int = 5) -> List[QueryTemplate]:
        """
        Find templates matching criteria
        
        Args:
            query_type: Type of query
            complexity_max: Maximum complexity level
            
        Returns:
            List of matching templates
        """
        matching = []
        for template in self.templates.values():
            if template.type == query_type and template.complexity <= complexity_max:
                matching.append(template)
        
        return sorted(matching, key=lambda t: t.complexity)
    
    def suggest_template(self, intent: str, needs_join: bool = False, 
                        needs_aggregation: bool = False) -> Optional[QueryTemplate]:
        """
        Suggest best template based on intent
        
        Args:
            intent: Primary intent (select, count, sum, etc.)
            needs_join: Whether join is needed
            needs_aggregation: Whether aggregation is needed
            
        Returns:
            Suggested template or None
        """
        # Map intent to query type
        intent_map = {
            'select': QueryType.SELECT,
            'count': QueryType.COUNT,
            'sum': QueryType.SUM,
            'avg': QueryType.AVG,
            'max': QueryType.MAX,
            'min': QueryType.MIN
        }
        
        query_type = intent_map.get(intent, QueryType.SELECT)
        
        # Find best matching template
        if needs_join and needs_aggregation:
            return self.templates.get('complex_aggregation')
        elif needs_join:
            return self.templates.get('simple_join')
        elif needs_aggregation and query_type == QueryType.COUNT:
            return self.templates.get('count_group')
        elif needs_aggregation and query_type == QueryType.SUM:
            return self.templates.get('sum_group')
        elif query_type == QueryType.MAX:
            return self.templates.get('max_details')
        else:
            # Find simplest template for the query type
            templates = self.find_matching_templates(query_type, complexity_max=2)
            return templates[0] if templates else None
    
    def fill_template(self, template: QueryTemplate, parameters: Dict[str, Any]) -> str:
        """
        Fill template with parameters
        
        Args:
            template: Query template
            parameters: Parameter values
            
        Returns:
            Filled SQL query
        """
        query = template.template
        
        for param in template.parameters:
            value = parameters.get(param, '')
            if value:
                # Handle special formatting
                if param.endswith('_clause') and not value.strip().startswith(('WHERE', 'GROUP', 'ORDER', 'HAVING', 'LIMIT')):
                    # Add appropriate keyword
                    if 'where' in param:
                        value = f"WHERE {value}"
                    elif 'group' in param:
                        value = f"GROUP BY {value}"
                    elif 'order' in param:
                        value = f"ORDER BY {value}"
                    elif 'having' in param:
                        value = f"HAVING {value}"
                    elif 'limit' in param:
                        value = f"LIMIT {value}"
                
                query = query.replace(f"{{{param}}}", value)
            else:
                # Remove empty placeholders
                query = query.replace(f"{{{param}}}", '')
        
        # Clean up extra spaces
        query = ' '.join(query.split())
        
        return query
    
    def get_template_examples(self, complexity_max: int = 3) -> List[Dict[str, str]]:
        """
        Get template examples for learning
        
        Args:
            complexity_max: Maximum complexity to include
            
        Returns:
            List of examples
        """
        examples = []
        for template in self.templates.values():
            if template.complexity <= complexity_max:
                examples.append({
                    'name': template.name,
                    'natural_language': template.example_nl,
                    'sql': template.example_sql,
                    'complexity': template.complexity,
                    'type': template.type.value
                })
        
        return sorted(examples, key=lambda e: e['complexity'])