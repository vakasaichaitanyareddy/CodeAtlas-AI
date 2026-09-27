from typing import List, Dict, Set, Optional, Tuple, Any
import networkx as nx
from .models import (
    GraphNodeDTO,
    GraphEdgeDTO,
    ImpactAnalysisResult,
    PathAnalysisResult,
    CycleType,
    CycleResult,
    GraphMetricsDTO,
    SubGraphDTO,
)


class GraphAnalyzer:
    """Graph traversal, cycle detection, and impact analysis algorithms implemented on a directed Code Property Graph."""

    def __init__(self, nodes: List[GraphNodeDTO], edges: List[GraphEdgeDTO]):
        self.node_map: Dict[str, GraphNodeDTO] = {n.node_id: n for n in nodes}
        self.edges = edges
        self.graph = nx.DiGraph()

        # Build NetworkX directed graph
        for node in nodes:
            self.graph.add_node(
                node.node_id,
                name=node.name,
                node_type=node.node_type,
                file_path=node.file_path,
                qualified_name=node.qualified_name,
                line_number=node.line_number,
                metadata=node.metadata,
            )

        for edge in edges:
            self.graph.add_edge(
                edge.source_id,
                edge.target_id,
                edge_type=edge.edge_type,
                weight=edge.weight,
                metadata=edge.metadata,
            )

    def get_upstream_dependencies(self, target_node_id: str, max_depth: int = 5) -> List[GraphNodeDTO]:
        """Reverse BFS: Find all callers and dependent symbols that transitively reach the target."""
        if target_node_id not in self.graph:
            return []

        visited: Set[str] = set()
        queue: List[Tuple[str, int]] = [(target_node_id, 0)]
        upstream_nodes: List[GraphNodeDTO] = []

        while queue:
            current_id, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            # Inward edges = callers / dependents
            for predecessor_id in self.graph.predecessors(current_id):
                if predecessor_id not in visited and predecessor_id != target_node_id:
                    visited.add(predecessor_id)
                    queue.append((predecessor_id, depth + 1))
                    if predecessor_id in self.node_map:
                        upstream_nodes.append(self.node_map[predecessor_id])

        return upstream_nodes

    def get_downstream_dependencies(self, target_node_id: str, max_depth: int = 5) -> List[GraphNodeDTO]:
        """Forward BFS: Find all callees and resources executed transitively by the target."""
        if target_node_id not in self.graph:
            return []

        visited: Set[str] = set()
        queue: List[Tuple[str, int]] = [(target_node_id, 0)]
        downstream_nodes: List[GraphNodeDTO] = []

        while queue:
            current_id, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            for successor_id in self.graph.successors(current_id):
                if successor_id not in visited and successor_id != target_node_id:
                    visited.add(successor_id)
                    queue.append((successor_id, depth + 1))
                    if successor_id in self.node_map:
                        downstream_nodes.append(self.node_map[successor_id])

        return downstream_nodes

    def compute_impact_analysis(self, target_node_id: str) -> ImpactAnalysisResult:
        """Compute the blast radius if the target node is modified or refactored.
        
        Uses deterministic normalized impact scoring:
        score = min(1.0, 0.35 * min(1.0, endpoints/3) + 0.30 * min(1.0, files/5) + 0.20 * min(1.0, callers/10) + 0.15 * min(1.0, depth/5))
        """
        target_node = self.node_map.get(target_node_id)
        if not target_node:
            return ImpactAnalysisResult(
                target_node_id=target_node_id,
                target_name="unknown",
                impact_score=0.0,
                severity="LOW",
                upstream_callers_count=0,
                impacted_files_count=0,
                affected_endpoints=[],
                affected_endpoints_details=[],
                impacted_symbols=[],
                traversal_depth=0,
                score_breakdown={},
            )

        upstream_nodes = self.get_upstream_dependencies(target_node_id, max_depth=6)

        impacted_files: Set[str] = set()
        affected_endpoints: List[str] = []
        affected_endpoints_details: List[Dict[str, Any]] = []
        impacted_symbols: List[str] = []

        for node in upstream_nodes:
            if node.file_path:
                impacted_files.add(node.file_path)
            impacted_symbols.append(node.qualified_name)
            if node.node_type == "ENDPOINT":
                affected_endpoints.append(node.name)
                affected_endpoints_details.append({
                    "name": node.name,
                    "qualified_name": node.qualified_name,
                    "file_path": node.file_path,
                    "http_method": node.metadata.get("http_method") or node.metadata.get("method") or "ANY",
                    "route": node.metadata.get("route") or node.metadata.get("path") or node.name,
                })

        # Determine maximum depth
        max_depth = 0
        for node in upstream_nodes:
            try:
                length = nx.shortest_path_length(self.graph, node.node_id, target_node_id)
                if length > max_depth:
                    max_depth = length
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass

        num_endpoints = len(affected_endpoints)
        num_files = len(impacted_files)
        num_callers = len(upstream_nodes)

        # Deterministic formula components
        endpoints_factor = 0.35 * min(1.0, num_endpoints / 3.0)
        files_factor = 0.30 * min(1.0, num_files / 5.0)
        callers_factor = 0.20 * min(1.0, num_callers / 10.0)
        depth_factor = 0.15 * min(1.0, max_depth / 5.0)

        raw_sum = endpoints_factor + files_factor + callers_factor + depth_factor
        impact_score = round(min(1.0, raw_sum), 4)

        # Deterministic severity mapping
        if impact_score >= 0.75 or num_endpoints >= 2:
            severity = "CRITICAL"
        elif impact_score >= 0.50 or num_endpoints >= 1:
            severity = "HIGH"
        elif impact_score >= 0.25:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        score_breakdown = {
            "endpoints_factor": round(endpoints_factor, 4),
            "files_factor": round(files_factor, 4),
            "callers_factor": round(callers_factor, 4),
            "depth_factor": round(depth_factor, 4),
        }

        return ImpactAnalysisResult(
            target_node_id=target_node_id,
            target_name=target_node.name,
            impact_score=impact_score,
            severity=severity,
            upstream_callers_count=num_callers,
            impacted_files_count=num_files,
            affected_endpoints=affected_endpoints,
            affected_endpoints_details=affected_endpoints_details,
            impacted_symbols=impacted_symbols,
            traversal_depth=max_depth,
            score_breakdown=score_breakdown,
        )

    def find_shortest_path(self, source_node_id: str, target_node_id: str) -> PathAnalysisResult:
        """Find the shortest directed execution chain connecting two nodes."""
        if source_node_id not in self.graph or target_node_id not in self.graph:
            return PathAnalysisResult(
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                path_exists=False,
                path_length=0,
                call_chain=[],
                nodes=[],
            )

        try:
            path_ids = nx.shortest_path(self.graph, source=source_node_id, target=target_node_id)
            nodes = [self.node_map[nid] for nid in path_ids if nid in self.node_map]
            call_chain = [n.qualified_name for n in nodes]
            return PathAnalysisResult(
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                path_exists=True,
                path_length=len(path_ids) - 1,
                call_chain=call_chain,
                nodes=nodes,
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return PathAnalysisResult(
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                path_exists=False,
                path_length=0,
                call_chain=[],
                nodes=[],
            )

    def find_circular_dependencies(self) -> List[CycleResult]:
        """Detect circular dependencies using Tarjan's Strongly Connected Components (SCC) algorithm.
        
        Classifies cycles into IMPORT_CYCLE, CALL_CYCLE, or MIXED_CYCLE.
        Avoids exponential cycle explosion by operating on SCCs directly.
        """
        cycles: List[CycleResult] = []
        sccs = list(nx.strongly_connected_components(self.graph))

        for scc in sccs:
            if len(scc) == 1:
                node = next(iter(scc))
                if self.graph.has_edge(node, node):
                    # Self-loop cycle
                    edge_data = self.graph.get_edge_data(node, node) or {}
                    edge_type = edge_data.get("edge_type", "CALLS")
                    cycle_type = CycleType.IMPORT_CYCLE if edge_type == "IMPORTS" else (
                        CycleType.CALL_CYCLE if edge_type == "CALLS" else CycleType.MIXED_CYCLE
                    )
                    file_path = self.node_map[node].file_path if node in self.node_map else None
                    participating_files = [file_path] if file_path else []
                    node_name = self.node_map[node].qualified_name if node in self.node_map else node

                    cycles.append(
                        CycleResult(
                            cycle_type=cycle_type,
                            nodes=[node_name],
                            cycle_path=[node_name, node_name],
                            length=1,
                            participating_files=participating_files,
                            edge_types=[edge_type],
                        )
                    )
            elif len(scc) > 1:
                # Subgraph is strongly connected: find an elementary directed cycle within this component
                scc_subgraph = self.graph.subgraph(scc)
                try:
                    cycle_edges = nx.find_cycle(scc_subgraph, orientation="original")
                except nx.NetworkXNoCycle:
                    continue

                path_nids = [u for u, v, *rest in cycle_edges] + [cycle_edges[0][0]]
                cycle_nodes = list(dict.fromkeys(path_nids[:-1]))

                edge_types_set = {
                    scc_subgraph.get_edge_data(u, v).get("edge_type", "UNKNOWN")
                    for u, v, *rest in cycle_edges
                }
                edge_types = sorted(list(edge_types_set))

                if edge_types_set == {"IMPORTS"}:
                    cycle_type = CycleType.IMPORT_CYCLE
                elif edge_types_set == {"CALLS"}:
                    cycle_type = CycleType.CALL_CYCLE
                else:
                    cycle_type = CycleType.MIXED_CYCLE

                participating_files_set = {
                    self.node_map[nid].file_path
                    for nid in cycle_nodes
                    if nid in self.node_map and self.node_map[nid].file_path
                }
                participating_files = sorted(list(participating_files_set))

                display_path = [
                    self.node_map[nid].qualified_name if nid in self.node_map else nid
                    for nid in path_nids
                ]
                display_nodes = [
                    self.node_map[nid].qualified_name if nid in self.node_map else nid
                    for nid in cycle_nodes
                ]

                cycles.append(
                    CycleResult(
                        cycle_type=cycle_type,
                        nodes=display_nodes,
                        cycle_path=display_path,
                        length=len(cycle_edges),
                        participating_files=participating_files,
                        edge_types=edge_types,
                    )
                )

        return cycles

    def get_neighborhood_subgraph(
        self, target_node_id: str, depth: int = 2, max_nodes: int = 100
    ) -> SubGraphDTO:
        """Extract a depth-bounded neighborhood subgraph centered around a target node."""
        if target_node_id not in self.graph:
            return SubGraphDTO(nodes=[], edges=[])

        collected: Set[str] = {target_node_id}
        frontier: Set[str] = {target_node_id}

        for _ in range(depth):
            next_frontier: Set[str] = set()
            for nid in frontier:
                # Add successors (callees) and predecessors (callers)
                neighbors = set(self.graph.successors(nid)) | set(self.graph.predecessors(nid))
                for neighbor in neighbors:
                    if neighbor not in collected:
                        next_frontier.add(neighbor)
                        collected.add(neighbor)
                        if len(collected) >= max_nodes:
                            break
                if len(collected) >= max_nodes:
                    break
            frontier = next_frontier
            if len(collected) >= max_nodes:
                break

        sub_nodes = [self.node_map[nid] for nid in collected if nid in self.node_map]

        sub_edges: List[GraphEdgeDTO] = []
        for u in collected:
            for v in collected:
                if self.graph.has_edge(u, v):
                    edge_data = self.graph.get_edge_data(u, v) or {}
                    sub_edges.append(
                        GraphEdgeDTO(
                            source_id=u,
                            target_id=v,
                            edge_type=edge_data.get("edge_type", "DEPENDS_ON"),
                            weight=edge_data.get("weight", 1.0),
                            metadata=edge_data.get("metadata", {}),
                        )
                    )

        return SubGraphDTO(nodes=sub_nodes, edges=sub_edges)

    def get_graph_metrics(self, node_id: Optional[str] = None) -> GraphMetricsDTO:
        """Compute structural metrics for the graph or a specific node."""
        total_nodes = self.graph.number_of_nodes()
        total_edges = self.graph.number_of_edges()

        node_type_counts: Dict[str, int] = {}
        for n in self.node_map.values():
            node_type_counts[n.node_type] = node_type_counts.get(n.node_type, 0) + 1

        edge_type_counts: Dict[str, int] = {}
        for e in self.edges:
            edge_type_counts[e.edge_type] = edge_type_counts.get(e.edge_type, 0) + 1

        cycles = self.find_circular_dependencies()

        if node_id and node_id in self.graph:
            in_deg = self.graph.in_degree(node_id)
            out_deg = self.graph.out_degree(node_id)
            centrality = round(nx.degree_centrality(self.graph).get(node_id, 0.0), 4)
            return GraphMetricsDTO(
                total_nodes=total_nodes,
                total_edges=total_edges,
                in_degree=in_deg,
                out_degree=out_deg,
                centrality=centrality,
                node_type_counts=node_type_counts,
                edge_type_counts=edge_type_counts,
                cycle_count=len(cycles),
            )

        avg_in = round(sum(d for _, d in self.graph.in_degree()) / max(1, total_nodes), 2)
        avg_out = round(sum(d for _, d in self.graph.out_degree()) / max(1, total_nodes), 2)

        return GraphMetricsDTO(
            total_nodes=total_nodes,
            total_edges=total_edges,
            in_degree=int(avg_in),
            out_degree=int(avg_out),
            centrality=0.0,
            node_type_counts=node_type_counts,
            edge_type_counts=edge_type_counts,
            cycle_count=len(cycles),
        )
