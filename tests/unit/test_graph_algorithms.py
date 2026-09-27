import pytest
from packages.graph.models import GraphNodeDTO, GraphEdgeDTO, CycleType
from packages.graph.algorithms import GraphAnalyzer


def test_tarjan_scc_no_cycles():
    """Verify DAG with no cycles returns an empty circular dependencies list."""
    nodes = [
        GraphNodeDTO(node_id="a", node_type="FUNCTION", name="func_a", qualified_name="mod::func_a", file_path="a.py"),
        GraphNodeDTO(node_id="b", node_type="FUNCTION", name="func_b", qualified_name="mod::func_b", file_path="b.py"),
        GraphNodeDTO(node_id="c", node_type="FUNCTION", name="func_c", qualified_name="mod::func_c", file_path="c.py"),
    ]
    edges = [
        GraphEdgeDTO(source_id="a", target_id="b", edge_type="CALLS"),
        GraphEdgeDTO(source_id="b", target_id="c", edge_type="CALLS"),
    ]
    analyzer = GraphAnalyzer(nodes, edges)
    cycles = analyzer.find_circular_dependencies()
    assert len(cycles) == 0


def test_tarjan_scc_self_loop():
    """Verify self-loop cycle is detected and classified correctly."""
    nodes = [
        GraphNodeDTO(node_id="self_rec", node_type="FUNCTION", name="recursive_fn", qualified_name="mod::recursive_fn", file_path="recurse.py"),
    ]
    edges = [
        GraphEdgeDTO(source_id="self_rec", target_id="self_rec", edge_type="CALLS"),
    ]
    analyzer = GraphAnalyzer(nodes, edges)
    cycles = analyzer.find_circular_dependencies()
    assert len(cycles) == 1
    assert cycles[0].cycle_type == CycleType.CALL_CYCLE
    assert cycles[0].length == 1
    assert "recurse.py" in cycles[0].participating_files


def test_tarjan_scc_import_cycle():
    """Verify multi-node import cycle is detected as IMPORT_CYCLE."""
    nodes = [
        GraphNodeDTO(node_id="file_a", node_type="FILE", name="a.py", qualified_name="pkg/a.py", file_path="pkg/a.py"),
        GraphNodeDTO(node_id="file_b", node_type="FILE", name="b.py", qualified_name="pkg/b.py", file_path="pkg/b.py"),
        GraphNodeDTO(node_id="file_c", node_type="FILE", name="c.py", qualified_name="pkg/c.py", file_path="pkg/c.py"),
    ]
    edges = [
        GraphEdgeDTO(source_id="file_a", target_id="file_b", edge_type="IMPORTS"),
        GraphEdgeDTO(source_id="file_b", target_id="file_c", edge_type="IMPORTS"),
        GraphEdgeDTO(source_id="file_c", target_id="file_a", edge_type="IMPORTS"),
    ]
    analyzer = GraphAnalyzer(nodes, edges)
    cycles = analyzer.find_circular_dependencies()
    assert len(cycles) == 1
    assert cycles[0].cycle_type == CycleType.IMPORT_CYCLE
    assert cycles[0].length == 3
    assert set(cycles[0].participating_files) == {"pkg/a.py", "pkg/b.py", "pkg/c.py"}
    assert cycles[0].cycle_path[0] == cycles[0].cycle_path[-1]  # Loop closed


def test_tarjan_scc_mixed_cycle():
    """Verify cycle with mixed IMPORTS and CALLS is classified as MIXED_CYCLE."""
    nodes = [
        GraphNodeDTO(node_id="x", node_type="FUNCTION", name="fn_x", qualified_name="pkg::fn_x", file_path="x.py"),
        GraphNodeDTO(node_id="y", node_type="FUNCTION", name="fn_y", qualified_name="pkg::fn_y", file_path="y.py"),
    ]
    edges = [
        GraphEdgeDTO(source_id="x", target_id="y", edge_type="IMPORTS"),
        GraphEdgeDTO(source_id="y", target_id="x", edge_type="CALLS"),
    ]
    analyzer = GraphAnalyzer(nodes, edges)
    cycles = analyzer.find_circular_dependencies()
    assert len(cycles) == 1
    assert cycles[0].cycle_type == CycleType.MIXED_CYCLE
    assert cycles[0].length == 2


def test_upstream_and_downstream_dependencies():
    """Verify reverse BFS upstream and forward BFS downstream traversals."""
    nodes = [
        GraphNodeDTO(node_id="ep", node_type="ENDPOINT", name="login_endpoint", qualified_name="api::login_endpoint", file_path="api.py"),
        GraphNodeDTO(node_id="svc", node_type="FUNCTION", name="authenticate", qualified_name="service::authenticate", file_path="service.py"),
        GraphNodeDTO(node_id="repo", node_type="FUNCTION", name="get_user_by_email", qualified_name="repo::get_user_by_email", file_path="repo.py"),
        GraphNodeDTO(node_id="db", node_type="MODEL", name="UserModel", qualified_name="models::UserModel", file_path="models.py"),
    ]
    edges = [
        GraphEdgeDTO(source_id="ep", target_id="svc", edge_type="CALLS"),
        GraphEdgeDTO(source_id="svc", target_id="repo", edge_type="CALLS"),
        GraphEdgeDTO(source_id="repo", target_id="db", edge_type="QUERIES"),
    ]
    analyzer = GraphAnalyzer(nodes, edges)

    # Upstream of UserModel
    upstream = analyzer.get_upstream_dependencies("db")
    upstream_ids = {n.node_id for n in upstream}
    assert upstream_ids == {"repo", "svc", "ep"}

    # Downstream of login_endpoint
    downstream = analyzer.get_downstream_dependencies("ep")
    downstream_ids = {n.node_id for n in downstream}
    assert downstream_ids == {"svc", "repo", "db"}

    # Depth bounded
    shallow_upstream = analyzer.get_upstream_dependencies("db", max_depth=1)
    assert len(shallow_upstream) == 1
    assert shallow_upstream[0].node_id == "repo"


def test_normalized_impact_scoring_and_severity():
    """Verify deterministic normalized impact formula and severity mapping."""
    nodes = [
        GraphNodeDTO(node_id="ep1", node_type="ENDPOINT", name="post_login", qualified_name="api::post_login", file_path="auth_api.py", metadata={"http_method": "POST", "route": "/api/v1/login"}),
        GraphNodeDTO(node_id="ep2", node_type="ENDPOINT", name="post_register", qualified_name="api::post_register", file_path="auth_api.py", metadata={"http_method": "POST", "route": "/api/v1/register"}),
        GraphNodeDTO(node_id="svc", node_type="FUNCTION", name="hash_password", qualified_name="security::hash_password", file_path="security.py"),
        GraphNodeDTO(node_id="util", node_type="FUNCTION", name="crypto_digest", qualified_name="crypto::crypto_digest", file_path="crypto.py"),
    ]
    edges = [
        GraphEdgeDTO(source_id="ep1", target_id="svc", edge_type="CALLS"),
        GraphEdgeDTO(source_id="ep2", target_id="svc", edge_type="CALLS"),
        GraphEdgeDTO(source_id="svc", target_id="util", edge_type="CALLS"),
    ]
    analyzer = GraphAnalyzer(nodes, edges)

    impact = analyzer.compute_impact_analysis("util")
    assert impact.target_node_id == "util"
    assert impact.upstream_callers_count == 3
    assert impact.impacted_files_count == 2
    assert len(impact.affected_endpoints) == 2
    assert "post_login" in impact.affected_endpoints
    assert "post_register" in impact.affected_endpoints

    # Check endpoints detail enrichment
    assert len(impact.affected_endpoints_details) == 2
    methods = {d["http_method"] for d in impact.affected_endpoints_details}
    assert "POST" in methods

    # Because endpoints >= 2, severity MUST be CRITICAL
    assert impact.severity == "CRITICAL"
    assert 0.0 < impact.impact_score <= 1.0

    # Score breakdown verified
    assert "endpoints_factor" in impact.score_breakdown
    assert "files_factor" in impact.score_breakdown
    assert "callers_factor" in impact.score_breakdown
    assert "depth_factor" in impact.score_breakdown


def test_dijkstra_shortest_path():
    """Verify shortest path finding between nodes."""
    nodes = [
        GraphNodeDTO(node_id="a", node_type="FUNCTION", name="fn_a", qualified_name="m::fn_a"),
        GraphNodeDTO(node_id="b", node_type="FUNCTION", name="fn_b", qualified_name="m::fn_b"),
        GraphNodeDTO(node_id="c", node_type="FUNCTION", name="fn_c", qualified_name="m::fn_c"),
        GraphNodeDTO(node_id="isolated", node_type="FUNCTION", name="fn_iso", qualified_name="m::fn_iso"),
    ]
    edges = [
        GraphEdgeDTO(source_id="a", target_id="b", edge_type="CALLS"),
        GraphEdgeDTO(source_id="b", target_id="c", edge_type="CALLS"),
    ]
    analyzer = GraphAnalyzer(nodes, edges)

    path_ac = analyzer.find_shortest_path("a", "c")
    assert path_ac.path_exists is True
    assert path_ac.path_length == 2
    assert path_ac.call_chain == ["m::fn_a", "m::fn_b", "m::fn_c"]
    assert len(path_ac.nodes) == 3

    path_iso = analyzer.find_shortest_path("a", "isolated")
    assert path_iso.path_exists is False
    assert path_iso.path_length == 0
    assert len(path_iso.call_chain) == 0


def test_neighborhood_subgraph_extraction():
    """Verify depth-bounded neighborhood subgraph extraction."""
    nodes = [
        GraphNodeDTO(node_id=f"node_{i}", node_type="FUNCTION", name=f"fn_{i}", qualified_name=f"m::fn_{i}")
        for i in range(10)
    ]
    # Chain: 0 -> 1 -> 2 -> 3 -> 4 -> 5 ...
    edges = [
        GraphEdgeDTO(source_id=f"node_{i}", target_id=f"node_{i+1}", edge_type="CALLS")
        for i in range(9)
    ]
    analyzer = GraphAnalyzer(nodes, edges)

    # Neighborhood around node_3 with depth 1 (should include 2, 3, 4)
    subgraph = analyzer.get_neighborhood_subgraph("node_3", depth=1, max_nodes=50)
    sub_node_ids = {n.node_id for n in subgraph.nodes}
    assert sub_node_ids == {"node_2", "node_3", "node_4"}
    assert len(subgraph.edges) == 2

    # Test max_nodes bounding
    subgraph_capped = analyzer.get_neighborhood_subgraph("node_3", depth=3, max_nodes=3)
    assert len(subgraph_capped.nodes) <= 3
