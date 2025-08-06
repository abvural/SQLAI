"""
Relationship Graph Builder using NetworkX
Builds and analyzes database relationship graphs for query path finding
"""
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
import networkx as nx
import json
from collections import defaultdict

from app.services.cache_service import CacheService
from app.models import get_session, RelationshipCache, TableCache

logger = logging.getLogger(__name__)

class RelationshipGraphBuilder:
    """Build and analyze database relationship graphs"""
    
    def __init__(self):
        self.cache_service = CacheService()
        self.graph = None
        self.db_id = None
    
    def build_graph(self, db_id: str) -> nx.DiGraph:
        """
        Build a directed graph of database relationships
        
        Args:
            db_id: Database connection ID
            
        Returns:
            NetworkX directed graph
        """
        logger.info(f"Building relationship graph for database {db_id}")
        
        self.db_id = db_id
        self.graph = nx.DiGraph()
        
        # Get tables and relationships from cache
        with get_session() as session:
            # Add tables as nodes
            tables = session.query(TableCache).filter_by(database_id=db_id).all()
            for table in tables:
                self.graph.add_node(
                    f"{table.schema_name}.{table.table_name}",
                    schema=table.schema_name,
                    table=table.table_name,
                    row_count=table.row_count or 0,
                    has_primary_key=table.has_primary_key,
                    column_count=table.column_count,
                    importance_score=table.importance_score or 0.5
                )
            
            # Add relationships as edges
            relationships = session.query(RelationshipCache).filter_by(database_id=db_id).all()
            for rel in relationships:
                from_node = f"{rel.from_schema}.{rel.from_table}"
                to_node = f"{rel.to_schema}.{rel.to_table}"
                
                # Add edge with relationship metadata
                self.graph.add_edge(
                    from_node,
                    to_node,
                    from_column=rel.from_column,
                    to_column=rel.to_column,
                    relationship_type=rel.relationship_type,
                    constraint_name=rel.constraint_name,
                    is_inferred=rel.is_inferred or False,
                    weight=1.0 if not rel.is_inferred else 2.0  # Prefer explicit relationships
                )
        
        logger.info(f"Graph built with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
        return self.graph
    
    def find_join_path(self, from_table: str, to_table: str, max_hops: int = 4) -> List[Dict[str, Any]]:
        """
        Find the shortest join path between two tables
        
        Args:
            from_table: Starting table name
            to_table: Target table name
            max_hops: Maximum number of joins allowed
            
        Returns:
            List of join steps with details
        """
        if not self.graph:
            raise ValueError("Graph not built. Call build_graph() first")
        
        # Normalize table names (add schema if not present)
        from_table = self._normalize_table_name(from_table)
        to_table = self._normalize_table_name(to_table)
        
        if from_table not in self.graph:
            raise ValueError(f"Table {from_table} not found in graph")
        if to_table not in self.graph:
            raise ValueError(f"Table {to_table} not found in graph")
        
        try:
            # Find shortest path
            path = nx.shortest_path(self.graph, from_table, to_table, weight='weight')
            
            if len(path) - 1 > max_hops:
                logger.warning(f"Path from {from_table} to {to_table} requires {len(path)-1} hops, exceeds max {max_hops}")
                return []
            
            # Build join steps
            join_steps = []
            for i in range(len(path) - 1):
                edge_data = self.graph[path[i]][path[i+1]]
                join_steps.append({
                    'from_table': path[i],
                    'to_table': path[i+1],
                    'from_column': edge_data['from_column'],
                    'to_column': edge_data['to_column'],
                    'join_type': 'INNER JOIN',  # Default, can be customized
                    'relationship_type': edge_data.get('relationship_type', 'unknown'),
                    'is_inferred': edge_data.get('is_inferred', False)
                })
            
            logger.info(f"Found join path from {from_table} to {to_table} with {len(join_steps)} joins")
            return join_steps
            
        except nx.NetworkXNoPath:
            logger.warning(f"No path found from {from_table} to {to_table}")
            return []
    
    def find_related_tables(self, table_name: str, depth: int = 1) -> Dict[str, List[str]]:
        """
        Find all tables related to a given table up to specified depth
        
        Args:
            table_name: Table to find relations for
            depth: How many hops to explore
            
        Returns:
            Dictionary with 'directly_related' and 'indirectly_related' tables
        """
        if not self.graph:
            raise ValueError("Graph not built. Call build_graph() first")
        
        table_name = self._normalize_table_name(table_name)
        
        if table_name not in self.graph:
            raise ValueError(f"Table {table_name} not found in graph")
        
        directly_related = set()
        indirectly_related = set()
        
        # Get directly connected tables
        directly_related.update(self.graph.predecessors(table_name))
        directly_related.update(self.graph.successors(table_name))
        
        # Get indirectly connected tables up to specified depth
        if depth > 1:
            for node in nx.single_source_shortest_path_length(self.graph.to_undirected(), table_name, cutoff=depth):
                if node != table_name and node not in directly_related:
                    indirectly_related.add(node)
        
        return {
            'directly_related': list(directly_related),
            'indirectly_related': list(indirectly_related)
        }
    
    def find_hub_tables(self, top_n: int = 5) -> List[Tuple[str, int]]:
        """
        Find hub tables (tables with most connections)
        
        Args:
            top_n: Number of top hub tables to return
            
        Returns:
            List of (table_name, connection_count) tuples
        """
        if not self.graph:
            raise ValueError("Graph not built. Call build_graph() first")
        
        # Calculate degree (in + out connections) for each node
        degree_dict = dict(self.graph.degree())
        
        # Sort by degree and get top N
        sorted_tables = sorted(degree_dict.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_tables[:top_n]
    
    def find_isolated_tables(self) -> List[str]:
        """
        Find tables with no relationships
        
        Returns:
            List of isolated table names
        """
        if not self.graph:
            raise ValueError("Graph not built. Call build_graph() first")
        
        isolated = []
        for node in self.graph.nodes():
            if self.graph.degree(node) == 0:
                isolated.append(node)
        
        return isolated
    
    def analyze_graph_metrics(self) -> Dict[str, Any]:
        """
        Analyze graph metrics for insights
        
        Returns:
            Dictionary of graph metrics
        """
        if not self.graph:
            raise ValueError("Graph not built. Call build_graph() first")
        
        metrics = {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'is_connected': nx.is_weakly_connected(self.graph),
            'number_of_components': nx.number_weakly_connected_components(self.graph),
            'average_degree': sum(dict(self.graph.degree()).values()) / self.graph.number_of_nodes() if self.graph.number_of_nodes() > 0 else 0,
            'density': nx.density(self.graph),
            'hub_tables': self.find_hub_tables(),
            'isolated_tables': self.find_isolated_tables()
        }
        
        # Find strongly connected components (cycles)
        sccs = list(nx.strongly_connected_components(self.graph))
        metrics['has_cycles'] = any(len(scc) > 1 for scc in sccs)
        metrics['largest_cycle_size'] = max(len(scc) for scc in sccs) if sccs else 0
        
        # Calculate centrality metrics for important tables
        if self.graph.number_of_nodes() > 0:
            try:
                betweenness = nx.betweenness_centrality(self.graph)
                top_betweenness = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:5]
                metrics['most_central_tables'] = [(table, score) for table, score in top_betweenness]
            except:
                metrics['most_central_tables'] = []
        
        return metrics
    
    def get_join_complexity(self, tables: List[str]) -> Dict[str, Any]:
        """
        Calculate complexity of joining multiple tables
        
        Args:
            tables: List of table names to join
            
        Returns:
            Dictionary with complexity metrics
        """
        if not self.graph:
            raise ValueError("Graph not built. Call build_graph() first")
        
        if len(tables) < 2:
            return {'complexity': 'trivial', 'join_count': 0}
        
        # Normalize table names
        tables = [self._normalize_table_name(t) for t in tables]
        
        # Find minimum spanning tree for the tables
        subgraph_nodes = set(tables)
        
        # Add intermediate nodes if needed
        for i in range(len(tables)):
            for j in range(i+1, len(tables)):
                try:
                    path = nx.shortest_path(self.graph, tables[i], tables[j])
                    subgraph_nodes.update(path)
                except nx.NetworkXNoPath:
                    pass
        
        if len(subgraph_nodes) == len(tables):
            # All tables are connected directly
            complexity = 'simple'
        elif len(subgraph_nodes) <= len(tables) * 1.5:
            complexity = 'moderate'
        else:
            complexity = 'complex'
        
        return {
            'complexity': complexity,
            'tables_involved': len(subgraph_nodes),
            'join_count': len(subgraph_nodes) - 1,
            'original_tables': len(tables),
            'intermediate_tables': len(subgraph_nodes) - len(tables)
        }
    
    def suggest_join_order(self, tables: List[str]) -> List[str]:
        """
        Suggest optimal join order for multiple tables
        
        Args:
            tables: List of table names to join
            
        Returns:
            Ordered list of tables for optimal joining
        """
        if not self.graph:
            raise ValueError("Graph not built. Call build_graph() first")
        
        if len(tables) <= 2:
            return tables
        
        # Normalize table names
        tables = [self._normalize_table_name(t) for t in tables]
        
        # Start with the table that has most connections to other tables in the list
        connection_counts = {}
        for table in tables:
            count = 0
            for other in tables:
                if table != other:
                    if self.graph.has_edge(table, other) or self.graph.has_edge(other, table):
                        count += 1
            connection_counts[table] = count
        
        # Sort by connection count (descending) and then by row count (ascending)
        ordered = sorted(tables, key=lambda t: (
            -connection_counts[t],
            self.graph.nodes[t].get('row_count', 0)
        ))
        
        return ordered
    
    def export_graph(self, format: str = 'json') -> str:
        """
        Export graph in specified format
        
        Args:
            format: Export format ('json', 'gexf', 'graphml')
            
        Returns:
            Serialized graph data
        """
        if not self.graph:
            raise ValueError("Graph not built. Call build_graph() first")
        
        if format == 'json':
            # Convert to node-link format for D3.js visualization
            data = nx.node_link_data(self.graph)
            return json.dumps(data, indent=2)
        elif format == 'gexf':
            # GEXF format for Gephi
            import io
            stream = io.StringIO()
            nx.write_gexf(self.graph, stream)
            return stream.getvalue()
        elif format == 'graphml':
            # GraphML format
            import io
            stream = io.StringIO()
            nx.write_graphml(self.graph, stream)
            return stream.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _normalize_table_name(self, table_name: str) -> str:
        """
        Normalize table name by adding schema if not present
        
        Args:
            table_name: Table name with or without schema
            
        Returns:
            Normalized table name (schema.table)
        """
        if '.' in table_name:
            return table_name
        
        # Default to public schema
        return f"public.{table_name}"
    
    def visualize_graph_stats(self) -> Dict[str, Any]:
        """
        Generate statistics for graph visualization
        
        Returns:
            Dictionary with visualization data
        """
        if not self.graph:
            raise ValueError("Graph not built. Call build_graph() first")
        
        # Prepare data for visualization
        viz_data = {
            'nodes': [],
            'edges': [],
            'stats': self.analyze_graph_metrics()
        }
        
        # Add nodes with metadata
        for node, data in self.graph.nodes(data=True):
            viz_data['nodes'].append({
                'id': node,
                'label': node.split('.')[-1],  # Just table name for label
                'schema': data.get('schema', 'public'),
                'size': max(10, min(50, data.get('row_count', 0) / 100)),  # Size based on row count
                'importance': data.get('importance_score', 0.5),
                'has_pk': data.get('has_primary_key', False),
                'degree': self.graph.degree(node)
            })
        
        # Add edges with metadata  
        for source, target, data in self.graph.edges(data=True):
            viz_data['edges'].append({
                'source': source,
                'target': target,
                'from_column': data.get('from_column'),
                'to_column': data.get('to_column'),
                'type': data.get('relationship_type', 'unknown'),
                'is_inferred': data.get('is_inferred', False)
            })
        
        return viz_data