"""
Schema Context Service using ChromaDB
Manages schema embeddings and retrieval for LLM context
"""
import os
import logging
import json
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import hashlib
from datetime import datetime

from app.services.relationship_graph import RelationshipGraphBuilder
from app.services.schema_analyzer import SchemaAnalyzer
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

class SchemaContextService:
    """Service for managing schema context with vector embeddings"""
    
    def __init__(self, db_id: str):
        """
        Initialize schema context service for a specific database
        
        Args:
            db_id: Database connection ID
        """
        self.db_id = db_id
        
        # Initialize ChromaDB
        persist_path = os.getenv('CHROMA_PERSIST_PATH', './chroma_db')
        collection_prefix = os.getenv('CHROMA_COLLECTION_PREFIX', 'sqlai_')
        
        self.client = chromadb.PersistentClient(
            path=persist_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create or get collection for this database
        collection_name = f"{collection_prefix}{db_id[:8]}"  # Use first 8 chars of UUID
        
        # Use default embedding function (all-MiniLM-L6-v2)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_fn
            )
            logger.info(f"Using existing collection: {collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_fn,
                metadata={"database_id": db_id}
            )
            logger.info(f"Created new collection: {collection_name}")
        
        # Initialize related services
        self.graph_builder = RelationshipGraphBuilder()
        self.schema_analyzer = SchemaAnalyzer()
        self.cache_service = CacheService()
        
        # Build graph for this database
        try:
            self.graph_builder.build_graph(db_id)
        except Exception as e:
            logger.warning(f"Could not build relationship graph: {e}")
    
    def index_schema(self, schema_data: Dict[str, Any], force_reindex: bool = False):
        """
        Index database schema into vector database
        
        Args:
            schema_data: Complete schema information
            force_reindex: Force reindexing even if already indexed
        """
        if not force_reindex and self._is_indexed(schema_data):
            logger.info("Schema already indexed and unchanged")
            return
        
        # Clear existing data if reindexing
        if force_reindex:
            try:
                self.collection.delete(where={})
                logger.info("Cleared existing schema index")
            except:
                pass
        
        documents = []
        metadatas = []
        ids = []
        
        # Index tables
        for schema_name, schema_info in schema_data.get('schemas', {}).items():
            for table in schema_info.get('tables', []):
                # Create searchable document for table
                doc = self._table_to_document(table, schema_name)
                documents.append(doc)
                
                # Metadata for filtering and context
                metadata = {
                    'type': 'table',
                    'schema': schema_name,
                    'table_name': table['name'],
                    'full_name': f"{schema_name}.{table['name']}",
                    'row_count': table.get('row_count', 0),
                    'column_count': len(table.get('columns', [])),
                    'has_primary_key': table.get('has_primary_key', False)
                }
                metadatas.append(metadata)
                
                # Unique ID for this table
                ids.append(f"table_{schema_name}_{table['name']}")
                
                # Also index columns individually for fine-grained search
                for column in table.get('columns', []):
                    col_doc = self._column_to_document(column, table['name'], schema_name)
                    documents.append(col_doc)
                    
                    col_metadata = {
                        'type': 'column',
                        'schema': schema_name,
                        'table_name': table['name'],
                        'column_name': column['name'],
                        'data_type': column['type'],
                        'is_primary_key': column.get('is_primary_key', False),
                        'is_foreign_key': column.get('is_foreign_key', False)
                    }
                    metadatas.append(col_metadata)
                    
                    ids.append(f"column_{schema_name}_{table['name']}_{column['name']}")
        
        # Index relationships
        for schema_name, schema_info in schema_data.get('schemas', {}).items():
            for rel in schema_info.get('relationships', []):
                rel_doc = self._relationship_to_document(rel)
                documents.append(rel_doc)
                
                rel_metadata = {
                    'type': 'relationship',
                    'from_table': f"{rel['from_schema']}.{rel['from_table']}",
                    'to_table': f"{rel['to_schema']}.{rel['to_table']}",
                    'from_column': rel['from_column'],
                    'to_column': rel['to_column'],
                    'relationship_type': rel.get('type', 'foreign_key')
                }
                metadatas.append(rel_metadata)
                
                ids.append(f"rel_{rel['from_table']}_{rel['from_column']}_{rel['to_table']}_{rel['to_column']}")
        
        # Add to ChromaDB in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_end = min(i + batch_size, len(documents))
            self.collection.add(
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end],
                ids=ids[i:batch_end]
            )
        
        logger.info(f"Indexed {len(documents)} schema elements")
        
        # Store index metadata
        self._save_index_metadata(schema_data)
    
    def get_relevant_context(self, query: str, limit: int = 20) -> str:
        """
        Get relevant schema context for a query
        
        Args:
            query: Natural language query
            limit: Maximum number of results to retrieve
            
        Returns:
            Formatted schema context string
        """
        try:
            # Search for relevant schema elements
            results = self.collection.query(
                query_texts=[query],
                n_results=min(limit, self.collection.count()),
                include=['metadatas', 'documents', 'distances']
            )
            
            if not results['ids'][0]:
                return self._get_default_context()
            
            # Organize results by relevance and type
            tables = set()
            columns = {}
            relationships = []
            
            for i, metadata in enumerate(results['metadatas'][0]):
                distance = results['distances'][0][i]
                
                # Only include highly relevant results (distance < 1.0)
                if distance < 1.0:
                    if metadata['type'] == 'table':
                        tables.add(metadata['full_name'])
                    elif metadata['type'] == 'column':
                        table_key = f"{metadata['schema']}.{metadata['table_name']}"
                        if table_key not in columns:
                            columns[table_key] = []
                        columns[table_key].append({
                            'name': metadata['column_name'],
                            'type': metadata['data_type'],
                            'is_pk': metadata.get('is_primary_key', False),
                            'is_fk': metadata.get('is_foreign_key', False)
                        })
                    elif metadata['type'] == 'relationship':
                        relationships.append({
                            'from': f"{metadata['from_table']}.{metadata['from_column']}",
                            'to': f"{metadata['to_table']}.{metadata['to_column']}"
                        })
            
            # Find additional related tables through relationships
            if tables and self.graph_builder.graph:
                for table in list(tables):
                    try:
                        related = self.graph_builder.find_related_tables(
                            table.split('.')[-1], 
                            depth=1
                        )
                        for rel_table in related.get('directly_related', []):
                            if '.' not in rel_table:
                                rel_table = f"public.{rel_table}"
                            tables.add(rel_table)
                    except:
                        pass
            
            # Build context string
            context = self._build_context_string(tables, columns, relationships)
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting relevant context: {e}")
            return self._get_default_context()
    
    def _table_to_document(self, table: Dict[str, Any], schema_name: str) -> str:
        """Convert table information to searchable document"""
        columns_str = ", ".join([f"{col['name']} {col['type']}" for col in table.get('columns', [])])
        
        # Include Turkish variations if applicable
        turkish_hints = self._get_turkish_hints(table['name'])
        
        doc = f"""Table: {schema_name}.{table['name']}
Columns: {columns_str}
Row Count: {table.get('row_count', 'unknown')}
{turkish_hints}
Description: Table {table['name']} with {len(table.get('columns', []))} columns"""
        
        return doc
    
    def _column_to_document(self, column: Dict[str, Any], table_name: str, schema_name: str) -> str:
        """Convert column information to searchable document"""
        constraints = []
        if column.get('is_primary_key'):
            constraints.append('PRIMARY KEY')
        if column.get('is_foreign_key'):
            constraints.append('FOREIGN KEY')
        if not column.get('nullable', True):
            constraints.append('NOT NULL')
        
        constraints_str = f" ({', '.join(constraints)})" if constraints else ""
        
        doc = f"""Column: {column['name']} in table {schema_name}.{table_name}
Type: {column['type']}{constraints_str}
Description: Column {column['name']} of type {column['type']} in {table_name}"""
        
        return doc
    
    def _relationship_to_document(self, rel: Dict[str, Any]) -> str:
        """Convert relationship information to searchable document"""
        doc = f"""Relationship: {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']}
Type: {rel.get('type', 'foreign_key')}
Description: Foreign key relationship from {rel['from_table']} to {rel['to_table']}"""
        
        return doc
    
    def _get_turkish_hints(self, name: str) -> str:
        """Get Turkish language hints for a name"""
        hints = []
        
        # Common Turkish mappings
        mappings = {
            'users': 'kullanıcılar',
            'user': 'kullanıcı',
            'customers': 'müşteriler',
            'customer': 'müşteri',
            'products': 'ürünler',
            'product': 'ürün',
            'orders': 'siparişler',
            'order': 'sipariş',
            'sales': 'satışlar',
            'sale': 'satış',
            'dealers': 'bayiler',
            'dealer': 'bayi'
        }
        
        name_lower = name.lower()
        for eng, tr in mappings.items():
            if eng in name_lower:
                hints.append(f"Turkish: {tr}")
                break
        
        return " ".join(hints)
    
    def _build_context_string(self, tables: set, columns: Dict, relationships: List) -> str:
        """Build formatted context string for LLM"""
        lines = ["Database Schema Context:", "=" * 50]
        
        # Add tables with columns
        for table in sorted(tables):
            lines.append(f"\nTable: {table}")
            
            if table in columns:
                lines.append("Columns:")
                for col in columns[table][:15]:  # Limit columns to prevent overflow
                    pk = " [PK]" if col['is_pk'] else ""
                    fk = " [FK]" if col['is_fk'] else ""
                    lines.append(f"  - {col['name']} ({col['type']}){pk}{fk}")
        
        # Add relationships
        if relationships:
            lines.append("\nRelationships:")
            for rel in relationships[:10]:  # Limit relationships
                lines.append(f"  - {rel['from']} -> {rel['to']}")
        
        # Add join hints if multiple tables
        if len(tables) > 1:
            lines.append("\nJoin Hints:")
            # Try to find join paths
            table_list = list(tables)
            for i in range(len(table_list) - 1):
                try:
                    if self.graph_builder.graph:
                        path = self.graph_builder.find_join_path(
                            table_list[i].split('.')[-1],
                            table_list[i + 1].split('.')[-1],
                            max_hops=3
                        )
                        if path:
                            lines.append(f"  - {table_list[i]} can join {table_list[i + 1]}")
                except:
                    pass
        
        return "\n".join(lines)
    
    def _get_default_context(self) -> str:
        """Get default context when no specific match found"""
        try:
            # Get some common tables
            results = self.collection.query(
                query_texts=["users customers products orders sales"],
                n_results=10,
                where={"type": "table"}
            )
            
            if results['metadatas'][0]:
                tables = [m['full_name'] for m in results['metadatas'][0]]
                return f"Available tables: {', '.join(tables)}"
        except:
            pass
        
        return "Database schema information not available. Common tables: users, products, orders, customers"
    
    def _is_indexed(self, schema_data: Dict[str, Any]) -> bool:
        """Check if schema is already indexed"""
        try:
            # Generate hash of current schema
            schema_json = json.dumps(schema_data, sort_keys=True)
            current_hash = hashlib.sha256(schema_json.encode()).hexdigest()
            
            # Check stored hash
            stored_hash = self._get_stored_hash()
            
            return current_hash == stored_hash
        except:
            return False
    
    def _save_index_metadata(self, schema_data: Dict[str, Any]):
        """Save metadata about indexed schema"""
        try:
            schema_json = json.dumps(schema_data, sort_keys=True)
            schema_hash = hashlib.sha256(schema_json.encode()).hexdigest()
            
            # Store in ChromaDB metadata
            self.client.persist()
            
            # Also save to cache
            self.cache_service.set_cache(
                f"schema_index_hash_{self.db_id}",
                schema_hash,
                category='schema_index'
            )
            
            logger.info(f"Saved index metadata with hash: {schema_hash[:8]}...")
        except Exception as e:
            logger.error(f"Error saving index metadata: {e}")
    
    def _get_stored_hash(self) -> Optional[str]:
        """Get stored schema hash"""
        try:
            return self.cache_service.get_cache(
                f"schema_index_hash_{self.db_id}",
                category='schema_index'
            )
        except:
            return None
    
    def update_with_query_results(self, query: str, sql: str, success: bool):
        """
        Update context based on query execution results
        
        Args:
            query: Natural language query
            sql: Generated SQL
            success: Whether query was successful
        """
        if success:
            try:
                # Extract tables from SQL for better relevance
                import re
                tables = re.findall(r'FROM\s+([^\s,]+)', sql, re.IGNORECASE)
                tables.extend(re.findall(r'JOIN\s+([^\s]+)', sql, re.IGNORECASE))
                
                # Add successful query pattern to collection
                doc_id = f"query_{hashlib.md5(query.encode()).hexdigest()[:8]}"
                
                self.collection.add(
                    documents=[f"Successful query: {query}\nSQL: {sql}\nTables: {', '.join(tables)}"],
                    metadatas=[{
                        'type': 'query_pattern',
                        'query': query,
                        'sql': sql[:500],  # Limit SQL length
                        'success': True
                    }],
                    ids=[doc_id]
                )
                
                logger.info(f"Added successful query pattern to context")
                
            except Exception as e:
                logger.error(f"Error updating context with query results: {e}")
    
    def get_similar_queries(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        """
        Find similar successful queries
        
        Args:
            query: Natural language query
            limit: Maximum number of results
            
        Returns:
            List of similar queries with their SQL
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where={"type": "query_pattern", "success": True}
            )
            
            similar_queries = []
            for i, metadata in enumerate(results['metadatas'][0]):
                similar_queries.append({
                    'query': metadata.get('query', ''),
                    'sql': metadata.get('sql', ''),
                    'distance': results['distances'][0][i]
                })
            
            return similar_queries
            
        except Exception as e:
            logger.error(f"Error finding similar queries: {e}")
            return []