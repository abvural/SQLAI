"""
Schema Change Detection Service
Detects and tracks changes in database schema over time
"""
import logging
import hashlib
import json
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from deepdiff import DeepDiff

from app.services.postgres_inspector import PostgresInspector
from app.services.cache_service import CacheService
from app.models import get_session, SchemaSnapshot

logger = logging.getLogger(__name__)

class SchemaChangeDetector:
    """Detect and track schema changes"""
    
    def __init__(self):
        self.inspector = PostgresInspector()
        self.cache_service = CacheService()
    
    def capture_current_schema(self, db_id: str) -> Dict[str, Any]:
        """
        Capture current schema state
        
        Args:
            db_id: Database connection ID
            
        Returns:
            Current schema structure
        """
        logger.info(f"Capturing current schema for database {db_id}")
        
        # Get current schema using inspector
        schema_info = self.inspector.analyze_schema(db_id)
        
        # Create simplified schema structure for comparison
        schema_structure = {
            'timestamp': datetime.utcnow().isoformat(),
            'database_id': db_id,
            'schemas': {}
        }
        
        for schema_name, schema_data in schema_info.get('schemas', {}).items():
            schema_structure['schemas'][schema_name] = {
                'tables': {},
                'relationships': []
            }
            
            # Capture table structures
            for table in schema_data.get('tables', []):
                table_structure = {
                    'columns': {},
                    'indexes': [],
                    'constraints': []
                }
                
                # Capture columns
                for column in table.get('columns', []):
                    table_structure['columns'][column['name']] = {
                        'type': column['type'],
                        'nullable': column.get('nullable', True),
                        'default': column.get('default'),
                        'is_primary_key': column.get('is_primary_key', False),
                        'is_foreign_key': column.get('is_foreign_key', False),
                        'is_unique': column.get('is_unique', False)
                    }
                
                # Capture indexes
                for index in table.get('indexes', []):
                    table_structure['indexes'].append({
                        'name': index['name'],
                        'is_primary': index.get('is_primary', False),
                        'is_unique': index.get('is_unique', False)
                    })
                
                schema_structure['schemas'][schema_name]['tables'][table['name']] = table_structure
            
            # Capture relationships
            for rel in schema_data.get('relationships', []):
                schema_structure['schemas'][schema_name]['relationships'].append({
                    'from_table': rel['from_table'],
                    'from_column': rel['from_column'],
                    'to_table': rel['to_table'],
                    'to_column': rel['to_column'],
                    'constraint_name': rel.get('constraint_name')
                })
        
        return schema_structure
    
    def detect_changes(self, db_id: str) -> Dict[str, Any]:
        """
        Detect changes since last snapshot
        
        Args:
            db_id: Database connection ID
            
        Returns:
            Dictionary of detected changes
        """
        logger.info(f"Detecting schema changes for database {db_id}")
        
        # Get current schema
        current_schema = self.capture_current_schema(db_id)
        
        # Get last snapshot from cache
        with get_session() as session:
            last_snapshot = session.query(SchemaSnapshot).filter_by(
                database_id=db_id
            ).order_by(SchemaSnapshot.created_at.desc()).first()
            
            if not last_snapshot:
                logger.info("No previous snapshot found, creating initial snapshot")
                self._save_snapshot(current_schema)
                return {
                    'has_changes': False,
                    'is_initial': True,
                    'message': 'Initial snapshot created'
                }
            
            # Compare schemas
            changes = self._compare_schemas(last_snapshot.schema_json, current_schema)
            
            # Save new snapshot if there are changes
            if changes['has_changes']:
                self._save_snapshot(current_schema, changes)
            
            return changes
    
    def _compare_schemas(self, old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare two schema structures
        
        Args:
            old_schema: Previous schema structure
            new_schema: Current schema structure
            
        Returns:
            Dictionary of changes
        """
        changes = {
            'has_changes': False,
            'timestamp': datetime.utcnow().isoformat(),
            'tables_added': [],
            'tables_removed': [],
            'tables_modified': [],
            'columns_added': [],
            'columns_removed': [],
            'columns_modified': [],
            'indexes_added': [],
            'indexes_removed': [],
            'relationships_added': [],
            'relationships_removed': [],
            'summary': {}
        }
        
        old_schemas = old_schema.get('schemas', {})
        new_schemas = new_schema.get('schemas', {})
        
        # Check each schema
        all_schema_names = set(old_schemas.keys()) | set(new_schemas.keys())
        
        for schema_name in all_schema_names:
            old_schema_data = old_schemas.get(schema_name, {'tables': {}, 'relationships': []})
            new_schema_data = new_schemas.get(schema_name, {'tables': {}, 'relationships': []})
            
            old_tables = old_schema_data.get('tables', {})
            new_tables = new_schema_data.get('tables', {})
            
            # Find added tables
            added_tables = set(new_tables.keys()) - set(old_tables.keys())
            for table_name in added_tables:
                changes['tables_added'].append(f"{schema_name}.{table_name}")
                changes['has_changes'] = True
            
            # Find removed tables
            removed_tables = set(old_tables.keys()) - set(new_tables.keys())
            for table_name in removed_tables:
                changes['tables_removed'].append(f"{schema_name}.{table_name}")
                changes['has_changes'] = True
            
            # Check modified tables
            common_tables = set(old_tables.keys()) & set(new_tables.keys())
            for table_name in common_tables:
                old_table = old_tables[table_name]
                new_table = new_tables[table_name]
                
                table_changes = self._compare_tables(
                    old_table, new_table, f"{schema_name}.{table_name}"
                )
                
                if table_changes['modified']:
                    changes['tables_modified'].append(f"{schema_name}.{table_name}")
                    changes['columns_added'].extend(table_changes['columns_added'])
                    changes['columns_removed'].extend(table_changes['columns_removed'])
                    changes['columns_modified'].extend(table_changes['columns_modified'])
                    changes['indexes_added'].extend(table_changes['indexes_added'])
                    changes['indexes_removed'].extend(table_changes['indexes_removed'])
                    changes['has_changes'] = True
            
            # Compare relationships
            old_rels = set(json.dumps(r, sort_keys=True) for r in old_schema_data.get('relationships', []))
            new_rels = set(json.dumps(r, sort_keys=True) for r in new_schema_data.get('relationships', []))
            
            added_rels = new_rels - old_rels
            removed_rels = old_rels - new_rels
            
            for rel_json in added_rels:
                rel = json.loads(rel_json)
                changes['relationships_added'].append(rel)
                changes['has_changes'] = True
            
            for rel_json in removed_rels:
                rel = json.loads(rel_json)
                changes['relationships_removed'].append(rel)
                changes['has_changes'] = True
        
        # Generate summary
        if changes['has_changes']:
            changes['summary'] = {
                'total_changes': (
                    len(changes['tables_added']) + len(changes['tables_removed']) +
                    len(changes['tables_modified']) + len(changes['relationships_added']) +
                    len(changes['relationships_removed'])
                ),
                'tables': {
                    'added': len(changes['tables_added']),
                    'removed': len(changes['tables_removed']),
                    'modified': len(changes['tables_modified'])
                },
                'columns': {
                    'added': len(changes['columns_added']),
                    'removed': len(changes['columns_removed']),
                    'modified': len(changes['columns_modified'])
                },
                'indexes': {
                    'added': len(changes['indexes_added']),
                    'removed': len(changes['indexes_removed'])
                },
                'relationships': {
                    'added': len(changes['relationships_added']),
                    'removed': len(changes['relationships_removed'])
                }
            }
        
        return changes
    
    def _compare_tables(self, old_table: Dict, new_table: Dict, table_name: str) -> Dict[str, Any]:
        """
        Compare two table structures
        
        Args:
            old_table: Previous table structure
            new_table: Current table structure
            table_name: Full table name for reporting
            
        Returns:
            Dictionary of table changes
        """
        table_changes = {
            'modified': False,
            'columns_added': [],
            'columns_removed': [],
            'columns_modified': [],
            'indexes_added': [],
            'indexes_removed': []
        }
        
        old_columns = old_table.get('columns', {})
        new_columns = new_table.get('columns', {})
        
        # Check columns
        added_cols = set(new_columns.keys()) - set(old_columns.keys())
        removed_cols = set(old_columns.keys()) - set(new_columns.keys())
        common_cols = set(old_columns.keys()) & set(new_columns.keys())
        
        for col in added_cols:
            table_changes['columns_added'].append(f"{table_name}.{col}")
            table_changes['modified'] = True
        
        for col in removed_cols:
            table_changes['columns_removed'].append(f"{table_name}.{col}")
            table_changes['modified'] = True
        
        for col in common_cols:
            if old_columns[col] != new_columns[col]:
                table_changes['columns_modified'].append({
                    'column': f"{table_name}.{col}",
                    'old': old_columns[col],
                    'new': new_columns[col]
                })
                table_changes['modified'] = True
        
        # Check indexes
        old_indexes = set(json.dumps(idx, sort_keys=True) for idx in old_table.get('indexes', []))
        new_indexes = set(json.dumps(idx, sort_keys=True) for idx in new_table.get('indexes', []))
        
        added_indexes = new_indexes - old_indexes
        removed_indexes = old_indexes - new_indexes
        
        for idx_json in added_indexes:
            idx = json.loads(idx_json)
            table_changes['indexes_added'].append(f"{table_name}.{idx['name']}")
            table_changes['modified'] = True
        
        for idx_json in removed_indexes:
            idx = json.loads(idx_json)
            table_changes['indexes_removed'].append(f"{table_name}.{idx['name']}")
            table_changes['modified'] = True
        
        return table_changes
    
    def _save_snapshot(self, schema_structure: Dict[str, Any], changes: Optional[Dict] = None):
        """
        Save schema snapshot to cache
        
        Args:
            schema_structure: Schema structure to save
            changes: Optional changes dictionary
        """
        # Calculate hash
        schema_json = json.dumps(schema_structure, sort_keys=True)
        schema_hash = hashlib.sha256(schema_json.encode()).hexdigest()
        
        # Extract change counts
        change_counts = {
            'tables_added': 0,
            'tables_removed': 0,
            'tables_modified': 0,
            'columns_added': 0,
            'columns_removed': 0,
            'columns_modified': 0
        }
        
        if changes:
            change_counts['tables_added'] = len(changes.get('tables_added', []))
            change_counts['tables_removed'] = len(changes.get('tables_removed', []))
            change_counts['tables_modified'] = len(changes.get('tables_modified', []))
            change_counts['columns_added'] = len(changes.get('columns_added', []))
            change_counts['columns_removed'] = len(changes.get('columns_removed', []))
            change_counts['columns_modified'] = len(changes.get('columns_modified', []))
        
        # Save to database
        with get_session() as session:
            snapshot = SchemaSnapshot(
                database_id=schema_structure['database_id'],
                snapshot_hash=schema_hash,
                schema_json=schema_structure,
                **change_counts
            )
            session.add(snapshot)
            session.commit()
            
            logger.info(f"Saved schema snapshot for database {schema_structure['database_id']}")
    
    def get_change_history(self, db_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get schema change history
        
        Args:
            db_id: Database connection ID
            limit: Maximum number of snapshots to return
            
        Returns:
            List of change summaries
        """
        history = []
        
        with get_session() as session:
            snapshots = session.query(SchemaSnapshot).filter_by(
                database_id=db_id
            ).order_by(SchemaSnapshot.created_at.desc()).limit(limit).all()
            
            for snapshot in snapshots:
                history.append({
                    'timestamp': snapshot.created_at.isoformat(),
                    'hash': snapshot.snapshot_hash[:16],
                    'changes': {
                        'tables_added': snapshot.tables_added,
                        'tables_removed': snapshot.tables_removed,
                        'tables_modified': snapshot.tables_modified,
                        'columns_added': snapshot.columns_added,
                        'columns_removed': snapshot.columns_removed,
                        'columns_modified': snapshot.columns_modified
                    },
                    'total_changes': (
                        snapshot.tables_added + snapshot.tables_removed +
                        snapshot.tables_modified + snapshot.columns_added +
                        snapshot.columns_removed + snapshot.columns_modified
                    )
                })
        
        return history
    
    def generate_migration_script(self, db_id: str, from_snapshot: Optional[str] = None) -> str:
        """
        Generate SQL migration script for detected changes
        
        Args:
            db_id: Database connection ID
            from_snapshot: Optional snapshot hash to compare from
            
        Returns:
            SQL migration script
        """
        changes = self.detect_changes(db_id)
        
        if not changes['has_changes']:
            return "-- No changes detected\n"
        
        script = []
        script.append("-- Migration script generated at " + datetime.utcnow().isoformat())
        script.append("-- Database: " + db_id)
        script.append("")
        
        # Generate DROP statements for removed tables
        for table in changes.get('tables_removed', []):
            script.append(f"-- Drop table {table}")
            script.append(f"DROP TABLE IF EXISTS {table} CASCADE;")
            script.append("")
        
        # Generate CREATE statements for new tables
        for table in changes.get('tables_added', []):
            script.append(f"-- Create table {table}")
            script.append(f"-- TODO: Add CREATE TABLE statement for {table}")
            script.append("")
        
        # Generate ALTER statements for modified tables
        modified_tables = set()
        
        # Add columns
        for column in changes.get('columns_added', []):
            table_name = '.'.join(column.split('.')[:-1])
            column_name = column.split('.')[-1]
            modified_tables.add(table_name)
            script.append(f"-- Add column {column}")
            script.append(f"ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR(255);")
            script.append("")
        
        # Drop columns
        for column in changes.get('columns_removed', []):
            table_name = '.'.join(column.split('.')[:-1])
            column_name = column.split('.')[-1]
            modified_tables.add(table_name)
            script.append(f"-- Drop column {column}")
            script.append(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {column_name};")
            script.append("")
        
        # Modify columns
        for col_change in changes.get('columns_modified', []):
            if isinstance(col_change, dict):
                column = col_change['column']
                table_name = '.'.join(column.split('.')[:-1])
                column_name = column.split('.')[-1]
                modified_tables.add(table_name)
                script.append(f"-- Modify column {column}")
                script.append(f"-- TODO: Add ALTER COLUMN statement for {column}")
                script.append("")
        
        # Add foreign key constraints
        for rel in changes.get('relationships_added', []):
            script.append(f"-- Add foreign key constraint")
            script.append(f"ALTER TABLE {rel['from_table']} ADD CONSTRAINT fk_{rel['from_table']}_{rel['from_column']}")
            script.append(f"  FOREIGN KEY ({rel['from_column']}) REFERENCES {rel['to_table']}({rel['to_column']});")
            script.append("")
        
        # Drop foreign key constraints
        for rel in changes.get('relationships_removed', []):
            if rel.get('constraint_name'):
                script.append(f"-- Drop foreign key constraint")
                script.append(f"ALTER TABLE {rel['from_table']} DROP CONSTRAINT IF EXISTS {rel['constraint_name']};")
                script.append("")
        
        return '\n'.join(script)