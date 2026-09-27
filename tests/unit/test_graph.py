import pytest
from packages.parser import PythonParser
from packages.graph import GraphBuilder, GraphAnalyzer


def test_dependency_and_call_graph_resolution():
    model_code = '''
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class UserModel(Base):
    __tablename__ = "users"
    def get_id(self):
        return 1
'''

    service_code = '''
from models import UserModel

class UserService:
    def verify_credentials(self, username, pwd):
        user = UserModel()
        return user.get_id()
'''

    api_code = '''
from services import UserService

@router.post("/api/v1/login")
def login_endpoint(payload):
    svc = UserService()
    return svc.verify_credentials("admin", "pwd")
'''

    parser = PythonParser()
    file_models = parser.parse_file("models.py", model_code)
    file_services = parser.parse_file("services.py", service_code)
    file_api = parser.parse_file("api.py", api_code)

    builder = GraphBuilder()
    nodes, edges = builder.build_graph([file_models, file_services, file_api])

    assert len(nodes) > 0
    assert len(edges) > 0

    node_types = {n.node_type for n in nodes}
    assert "FILE" in node_types
    assert "MODEL" in node_types or "CLASS" in node_types
    assert "ENDPOINT" in node_types

    edge_types = {e.edge_type for e in edges}
    assert "IMPORTS" in edge_types
    assert "CALLS" in edge_types or "DEPENDS_ON" in edge_types

    # Initialize GraphAnalyzer
    analyzer = GraphAnalyzer(nodes, edges)

    # 1. Test Upstream Analysis on verify_credentials
    target_node = next(n for n in nodes if "verify_credentials" in n.name)
    upstream = analyzer.get_upstream_dependencies(target_node.node_id)
    upstream_names = [u.name for u in upstream]
    assert "login_endpoint" in upstream_names or any("login" in name for name in upstream_names)

    # 2. Test Blast-Radius Impact Analysis on verify_credentials
    impact = analyzer.compute_impact_analysis(target_node.node_id)
    assert impact.upstream_callers_count >= 1
    assert impact.impact_score > 0.0
    assert any("login_endpoint" in ep for ep in impact.affected_endpoints) or len(impact.impacted_symbols) >= 1

    # 3. Test Shortest Path from endpoint to service method
    endpoint_node = next(n for n in nodes if n.name == "login_endpoint")
    path_res = analyzer.find_shortest_path(endpoint_node.node_id, target_node.node_id)
    assert path_res.path_exists is True
    assert path_res.path_length >= 1
    assert endpoint_node.qualified_name in path_res.call_chain
    assert target_node.qualified_name in path_res.call_chain
