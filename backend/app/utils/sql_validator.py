"""
SQL validation and sanitization utilities for preventing SQL injection
"""
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

class SQLOperation(Enum):
    """Allowed SQL operations"""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    
class SQLValidator:
    """SQL validation and sanitization"""
    
    # Dangerous SQL patterns that might indicate injection attempts
    DANGEROUS_PATTERNS = [
        r";\s*DROP\s+",
        r";\s*DELETE\s+FROM\s+",
        r";\s*TRUNCATE\s+",
        r";\s*ALTER\s+",
        r";\s*CREATE\s+",
        r";\s*GRANT\s+",
        r";\s*REVOKE\s+",
        r"--\s*$",  # SQL comment at end
        r"/\*.*\*/",  # Block comments
        r"UNION\s+SELECT",
        r"OR\s+1\s*=\s*1",
        r"OR\s+'[^']*'\s*=\s*'[^']*'",
        r"EXEC\s*\(",
        r"EXECUTE\s+",
        r"xp_cmdshell",
        r"sp_executesql",
        r"WAITFOR\s+DELAY",
        r"BENCHMARK\s*\(",
        r"SLEEP\s*\(",
    ]
    
    # Allowed table/column name pattern
    VALID_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    
    # Maximum lengths for various inputs
    MAX_TABLE_NAME_LENGTH = 63  # PostgreSQL limit
    MAX_COLUMN_NAME_LENGTH = 63
    MAX_QUERY_LENGTH = 100000
    
    @classmethod
    def validate_identifier(cls, identifier: str, identifier_type: str = "identifier") -> bool:
        """
        Validate a database identifier (table name, column name, etc.)
        
        Args:
            identifier: The identifier to validate
            identifier_type: Type of identifier for logging
            
        Returns:
            True if valid, False otherwise
        """
        if not identifier:
            logger.warning(f"Empty {identifier_type}")
            return False
        
        if len(identifier) > cls.MAX_TABLE_NAME_LENGTH:
            logger.warning(f"{identifier_type} too long: {len(identifier)} chars")
            return False
        
        if not cls.VALID_IDENTIFIER.match(identifier):
            logger.warning(f"Invalid {identifier_type} format: {identifier}")
            return False
        
        # Check for SQL keywords used as identifiers
        sql_keywords = {
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE',
            'ALTER', 'GRANT', 'REVOKE', 'UNION', 'WHERE', 'FROM'
        }
        
        if identifier.upper() in sql_keywords:
            logger.warning(f"SQL keyword used as {identifier_type}: {identifier}")
            return False
        
        return True
    
    @classmethod
    def validate_table_name(cls, table_name: str) -> bool:
        """Validate a table name"""
        return cls.validate_identifier(table_name, "table name")
    
    @classmethod
    def validate_column_name(cls, column_name: str) -> bool:
        """Validate a column name"""
        return cls.validate_identifier(column_name, "column name")
    
    @classmethod
    def contains_dangerous_patterns(cls, query: str) -> bool:
        """
        Check if query contains dangerous SQL patterns
        
        Args:
            query: SQL query string
            
        Returns:
            True if dangerous patterns found
        """
        detected = cls.detect_injection_patterns(query)
        return len(detected) > 0
    
    @classmethod
    def detect_dangerous_patterns(cls, query: str) -> List[str]:
        """Alias for detect_injection_patterns for backward compatibility"""
        return cls.detect_injection_patterns(query)
    
    @classmethod
    def detect_injection_patterns(cls, query: str) -> List[str]:
        """
        Detect potential SQL injection patterns
        
        Args:
            query: SQL query to check
            
        Returns:
            List of detected dangerous patterns
        """
        detected = []
        query_upper = query.upper()
        
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, query_upper, re.IGNORECASE):
                detected.append(pattern)
        
        # Check for multiple SQL statements
        if query.count(';') > 1:
            detected.append("Multiple semicolons detected")
        
        # Check for hex encoding attempts
        if re.search(r'0x[0-9a-fA-F]+', query):
            detected.append("Hex encoding detected")
        
        # Check for char() function abuse
        if re.search(r'CHAR\s*\(\s*\d+', query_upper):
            detected.append("CHAR() function detected")
        
        return detected
    
    @classmethod
    def sanitize_string(cls, value: str) -> str:
        """
        Sanitize a string value for safe SQL usage
        
        Args:
            value: String to sanitize
            
        Returns:
            Sanitized string
        """
        if not value:
            return ""
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Escape single quotes (PostgreSQL style)
        value = value.replace("'", "''")
        
        # Remove control characters
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')
        
        return value
    
    @classmethod
    def validate_query(cls, query: str, allowed_operations: Optional[List[SQLOperation]] = None) -> Tuple[bool, str]:
        """
        Validate a SQL query for safety
        
        Args:
            query: SQL query to validate
            allowed_operations: List of allowed SQL operations
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not query:
            return False, "Empty query"
        
        if len(query) > cls.MAX_QUERY_LENGTH:
            return False, f"Query too long: {len(query)} characters"
        
        # Check for dangerous patterns
        dangerous = cls.detect_injection_patterns(query)
        if dangerous:
            logger.warning(f"Dangerous patterns detected: {dangerous}")
            return False, f"Potentially dangerous SQL patterns detected: {', '.join(dangerous)}"
        
        # Check operation type if restricted
        if allowed_operations:
            query_upper = query.strip().upper()
            operation_found = False
            
            for op in allowed_operations:
                if query_upper.startswith(op.value):
                    operation_found = True
                    break
            
            if not operation_found:
                allowed_ops = ", ".join(op.value for op in allowed_operations)
                return False, f"Operation not allowed. Allowed: {allowed_ops}"
        
        return True, ""
    
    @classmethod
    def build_parameterized_query(cls, query_template: str, params: List[Any]) -> Tuple[str, List[Any]]:
        """
        Build a parameterized query
        
        Args:
            query_template: Query template with placeholders
            params: Parameters to bind
            
        Returns:
            Tuple of (query, parameters)
        """
        # For PostgreSQL, we use %s placeholders
        # Params are already a list, just return them
        return query_template, params
    
    @classmethod
    def build_safe_where_clause(cls, conditions: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Build a safe WHERE clause with parameters
        
        Args:
            conditions: Dictionary of column:value conditions
            
        Returns:
            Tuple of (where_clause, parameters)
        """
        if not conditions:
            return "", {}
        
        where_parts = []
        params = {}
        
        for i, (column, value) in enumerate(conditions.items()):
            # Validate column name
            if not cls.validate_column_name(column):
                logger.warning(f"Invalid column name in WHERE clause: {column}")
                continue
            
            param_name = f"param_{i}"
            
            if value is None:
                where_parts.append(f"{column} IS NULL")
            elif isinstance(value, (list, tuple)):
                # Handle IN clause
                placeholders = ", ".join(f":param_{i}_{j}" for j in range(len(value)))
                where_parts.append(f"{column} IN ({placeholders})")
                for j, v in enumerate(value):
                    params[f"param_{i}_{j}"] = v
            else:
                where_parts.append(f"{column} = :{param_name}")
                params[param_name] = value
        
        where_clause = " AND ".join(where_parts)
        return f"WHERE {where_clause}" if where_clause else "", params
    
    @classmethod
    def validate_limit_offset(cls, limit: Optional[int], offset: Optional[int]) -> Tuple[Optional[int], Optional[int]]:
        """
        Validate and sanitize LIMIT and OFFSET values
        
        Args:
            limit: LIMIT value
            offset: OFFSET value
            
        Returns:
            Tuple of (safe_limit, safe_offset)
        """
        safe_limit = None
        safe_offset = None
        
        if limit is not None:
            try:
                safe_limit = int(limit)
                if safe_limit < 0:
                    safe_limit = None
                elif safe_limit > 10000:
                    safe_limit = 10000  # Max limit
            except (ValueError, TypeError):
                safe_limit = None
        
        if offset is not None:
            try:
                safe_offset = int(offset)
                if safe_offset < 0:
                    safe_offset = 0
            except (ValueError, TypeError):
                safe_offset = 0
        
        return safe_limit, safe_offset

class QueryBuilder:
    """Safe SQL query builder"""
    
    @staticmethod
    def build_select(
        table: str,
        columns: Optional[List[str]] = None,
        conditions: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build a safe SELECT query
        
        Args:
            table: Table name
            columns: List of column names
            conditions: WHERE conditions
            order_by: ORDER BY column
            limit: LIMIT value
            offset: OFFSET value
            
        Returns:
            Tuple of (query, parameters)
        """
        # Validate table name
        if not SQLValidator.validate_table_name(table):
            raise ValueError(f"Invalid table name: {table}")
        
        # Validate columns
        if columns:
            for col in columns:
                if not SQLValidator.validate_column_name(col):
                    raise ValueError(f"Invalid column name: {col}")
            column_str = ", ".join(columns)
        else:
            column_str = "*"
        
        # Build query
        query = f"SELECT {column_str} FROM {table}"
        
        # Add WHERE clause
        where_clause, params = SQLValidator.build_safe_where_clause(conditions or {})
        if where_clause:
            query += f" {where_clause}"
        
        # Add ORDER BY
        if order_by:
            if SQLValidator.validate_column_name(order_by.replace(" DESC", "").replace(" ASC", "")):
                query += f" ORDER BY {order_by}"
        
        # Add LIMIT/OFFSET
        safe_limit, safe_offset = SQLValidator.validate_limit_offset(limit, offset)
        if safe_limit is not None:
            query += f" LIMIT {safe_limit}"
        if safe_offset is not None:
            query += f" OFFSET {safe_offset}"
        
        return query, params
    
    @staticmethod
    def build_insert(table: str, data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Build a safe INSERT query
        
        Args:
            table: Table name
            data: Data to insert
            
        Returns:
            Tuple of (query, parameters)
        """
        if not SQLValidator.validate_table_name(table):
            raise ValueError(f"Invalid table name: {table}")
        
        if not data:
            raise ValueError("No data to insert")
        
        columns = []
        placeholders = []
        params = {}
        
        for i, (column, value) in enumerate(data.items()):
            if not SQLValidator.validate_column_name(column):
                raise ValueError(f"Invalid column name: {column}")
            
            columns.append(column)
            param_name = f"param_{i}"
            placeholders.append(f":{param_name}")
            params[param_name] = value
        
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        
        return query, params

def validate_user_input(input_value: Any, input_type: str = "string", max_length: int = 1000) -> Tuple[bool, Any, str]:
    """
    Validate and sanitize user input
    
    Args:
        input_value: User input value
        input_type: Expected type (string, integer, float, boolean)
        max_length: Maximum length for strings
        
    Returns:
        Tuple of (is_valid, sanitized_value, error_message)
    """
    if input_value is None:
        return True, None, ""
    
    try:
        if input_type == "string":
            if not isinstance(input_value, str):
                input_value = str(input_value)
            
            if len(input_value) > max_length:
                return False, None, f"Input too long: {len(input_value)} characters"
            
            sanitized = SQLValidator.sanitize_string(input_value)
            return True, sanitized, ""
        
        elif input_type == "integer":
            sanitized = int(input_value)
            return True, sanitized, ""
        
        elif input_type == "float":
            sanitized = float(input_value)
            return True, sanitized, ""
        
        elif input_type == "boolean":
            if isinstance(input_value, bool):
                return True, input_value, ""
            if isinstance(input_value, str):
                if input_value.lower() in ('true', '1', 'yes'):
                    return True, True, ""
                elif input_value.lower() in ('false', '0', 'no'):
                    return True, False, ""
            return False, None, "Invalid boolean value"
        
        else:
            return False, None, f"Unknown input type: {input_type}"
    
    except (ValueError, TypeError) as e:
        return False, None, f"Invalid {input_type}: {str(e)}"