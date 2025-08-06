"""
Export Service for Query Results
Handles exporting query results in various formats
"""
import logging
import json
import csv
from io import StringIO, BytesIO
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

class ExportService:
    """Service for exporting query results"""
    
    def __init__(self):
        """Initialize export service"""
        logger.info("Export Service initialized")
    
    def export_to_csv(self, data: List[Dict[str, Any]], 
                     filename: Optional[str] = None) -> bytes:
        """
        Export data to CSV format
        
        Args:
            data: Query result data
            filename: Optional filename
            
        Returns:
            CSV data as bytes
        """
        if not data:
            return b""
        
        # Create CSV content
        output = StringIO()
        
        # Get column names from first row
        fieldnames = list(data[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        
        # Write header
        writer.writeheader()
        
        # Write data rows
        for row in data:
            # Convert complex types to strings
            clean_row = {}
            for key, value in row.items():
                if value is None:
                    clean_row[key] = ""
                elif isinstance(value, (dict, list)):
                    clean_row[key] = json.dumps(value, default=str)
                elif isinstance(value, datetime):
                    clean_row[key] = value.isoformat()
                else:
                    clean_row[key] = str(value)
            
            writer.writerow(clean_row)
        
        # Get CSV content
        csv_content = output.getvalue()
        output.close()
        
        return csv_content.encode('utf-8')
    
    def export_to_excel(self, data: List[Dict[str, Any]], 
                       filename: Optional[str] = None,
                       sheet_name: str = "Results") -> bytes:
        """
        Export data to Excel format
        
        Args:
            data: Query result data
            filename: Optional filename
            sheet_name: Excel sheet name
            
        Returns:
            Excel data as bytes
        """
        if not data:
            # Create empty workbook
            df = pd.DataFrame()
        else:
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Clean data for Excel
            for column in df.columns:
                df[column] = df[column].apply(self._clean_value_for_excel)
        
        # Create Excel file in memory
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter', options={'remove_timezone': True}) as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Get workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets[sheet_name]
            
            # Add formatting
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            # Apply header format
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                # Auto-adjust column width
                worksheet.set_column(col_num, col_num, len(str(value)) + 2)
        
        output.seek(0)
        return output.read()
    
    def export_to_json(self, data: List[Dict[str, Any]], 
                      filename: Optional[str] = None,
                      pretty: bool = True) -> bytes:
        """
        Export data to JSON format
        
        Args:
            data: Query result data
            filename: Optional filename
            pretty: Whether to format JSON prettily
            
        Returns:
            JSON data as bytes
        """
        if not data:
            data = []
        
        # Clean data for JSON serialization
        clean_data = []
        for row in data:
            clean_row = {}
            for key, value in row.items():
                clean_row[key] = self._clean_value_for_json(value)
            clean_data.append(clean_row)
        
        # Create JSON
        if pretty:
            json_content = json.dumps(clean_data, indent=2, ensure_ascii=False, default=str)
        else:
            json_content = json.dumps(clean_data, ensure_ascii=False, default=str)
        
        return json_content.encode('utf-8')
    
    def export_to_sql_inserts(self, data: List[Dict[str, Any]], 
                             table_name: str,
                             filename: Optional[str] = None) -> bytes:
        """
        Export data as SQL INSERT statements
        
        Args:
            data: Query result data
            table_name: Target table name
            filename: Optional filename
            
        Returns:
            SQL INSERT statements as bytes
        """
        if not data:
            return b""
        
        # Generate SQL INSERT statements
        sql_statements = []
        
        # Get column names
        columns = list(data[0].keys())
        columns_str = ", ".join(f'"{col}"' for col in columns)
        
        for row in data:
            values = []
            for col in columns:
                value = row[col]
                if value is None:
                    values.append('NULL')
                elif isinstance(value, str):
                    # Escape single quotes
                    escaped_value = value.replace("'", "''")
                    values.append(f"'{escaped_value}'")
                elif isinstance(value, (int, float)):
                    values.append(str(value))
                elif isinstance(value, datetime):
                    values.append(f"'{value.isoformat()}'")
                else:
                    # Convert to string and escape
                    str_value = str(value).replace("'", "''")
                    values.append(f"'{str_value}'")
            
            values_str = ", ".join(values)
            sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});"
            sql_statements.append(sql)
        
        # Join all statements
        sql_content = "\n".join(sql_statements)
        
        return sql_content.encode('utf-8')
    
    def _clean_value_for_excel(self, value: Any) -> Any:
        """Clean value for Excel export"""
        if value is None:
            return ""
        elif isinstance(value, (dict, list)):
            return json.dumps(value, default=str)
        elif isinstance(value, datetime):
            return value
        else:
            return value
    
    def _clean_value_for_json(self, value: Any) -> Any:
        """Clean value for JSON export"""
        if value is None:
            return None
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, (dict, list)):
            return value
        else:
            return value
    
    def get_export_metadata(self, data: List[Dict[str, Any]], 
                           export_format: str) -> Dict[str, Any]:
        """
        Get metadata about the export
        
        Args:
            data: Query result data
            export_format: Export format
            
        Returns:
            Export metadata
        """
        if not data:
            return {
                'row_count': 0,
                'column_count': 0,
                'columns': [],
                'format': export_format,
                'estimated_size_bytes': 0
            }
        
        columns = list(data[0].keys())
        
        # Estimate size based on format
        estimated_size = 0
        if export_format == 'csv':
            # Rough CSV size estimation
            estimated_size = len(data) * (sum(len(str(data[0].get(col, ""))) for col in columns) + len(columns))
        elif export_format == 'json':
            # Rough JSON size estimation
            estimated_size = len(json.dumps(data[:10], default=str)) * (len(data) // 10 + 1)
        elif export_format == 'excel':
            # Excel is typically larger
            estimated_size = len(data) * len(columns) * 20  # Rough estimate
        
        return {
            'row_count': len(data),
            'column_count': len(columns),
            'columns': columns,
            'format': export_format,
            'estimated_size_bytes': estimated_size,
            'data_types': self._analyze_data_types(data)
        }
    
    def _analyze_data_types(self, data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Analyze data types in the result set"""
        if not data:
            return {}
        
        type_analysis = {}
        sample_row = data[0]
        
        for column, value in sample_row.items():
            if value is None:
                type_analysis[column] = 'null'
            elif isinstance(value, bool):
                type_analysis[column] = 'boolean'
            elif isinstance(value, int):
                type_analysis[column] = 'integer'
            elif isinstance(value, float):
                type_analysis[column] = 'float'
            elif isinstance(value, str):
                type_analysis[column] = 'string'
            elif isinstance(value, datetime):
                type_analysis[column] = 'datetime'
            elif isinstance(value, dict):
                type_analysis[column] = 'object'
            elif isinstance(value, list):
                type_analysis[column] = 'array'
            else:
                type_analysis[column] = 'unknown'
        
        return type_analysis
    
    def validate_export_request(self, data_size: int, 
                               export_format: str) -> Dict[str, Any]:
        """
        Validate export request
        
        Args:
            data_size: Number of rows to export
            export_format: Export format
            
        Returns:
            Validation result
        """
        # Define limits
        limits = {
            'csv': 1000000,     # 1M rows
            'excel': 100000,    # 100K rows (Excel limitation)
            'json': 50000,      # 50K rows (memory consideration)
            'sql': 10000        # 10K rows (readability)
        }
        
        max_allowed = limits.get(export_format, 10000)
        
        if data_size > max_allowed:
            return {
                'valid': False,
                'error': f"Export size ({data_size} rows) exceeds limit for {export_format} ({max_allowed} rows)",
                'suggestion': f"Consider using CSV format or limiting your query results"
            }
        
        # Check estimated memory usage
        estimated_memory_mb = data_size * 0.001  # Rough estimate: 1KB per row
        if estimated_memory_mb > 500:  # 500MB limit
            return {
                'valid': False,
                'error': f"Export would use too much memory (~{estimated_memory_mb:.1f}MB)",
                'suggestion': "Use streaming export or reduce result size"
            }
        
        return {
            'valid': True,
            'estimated_memory_mb': estimated_memory_mb,
            'max_allowed_rows': max_allowed
        }