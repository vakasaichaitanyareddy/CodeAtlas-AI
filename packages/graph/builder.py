import os
from typing import List, Dict, Tuple, Optional, Set
from packages.parser.models import NormalizedFile, NormalizedSymbol, SymbolType
from .models import GraphNodeDTO, GraphEdgeDTO


class GraphBuilder:
    """Builds a normalized, directed Code Property Graph from parsed repository files."""

    def __init__(self):
        self.nodes: Dict[str, GraphNodeDTO] = {}
        self.edges: List[GraphEdgeDTO] = []
        self._symbol_lookup: Dict[str, GraphNodeDTO] = {} # unqualified name -> candidate nodes
        self._qualified_symbol_lookup: Dict[str, GraphNodeDTO] = {} # qualified name -> node
        self._file_path_map: Dict[str, str] = {} # normalized module/file path lookup

    def build_graph(self, parsed_files: List[NormalizedFile]) -> Tuple[List[GraphNodeDTO], List[GraphEdgeDTO]]:
        """Construct graph nodes and directed relationship edges from a collection of parsed files."""
        self.nodes.clear()
        self.edges.clear()
        self._symbol_lookup.clear()
        self._qualified_symbol_lookup.clear()
        self._file_path_map.clear()

        # Step 1: Create File and Symbol nodes & build lookup indexes
        for file in parsed_files:
            file_node_id = f"file::{file.file_path}"
            norm_path = file.file_path.replace("\\", "/").lower()
            self._file_path_map[norm_path] = file_node_id

            # Also index without extension for module import matching
            stem_path = os.path.splitext(norm_path)[0]
            self._file_path_map[stem_path] = file_node_id
            module_dot_path = stem_path.replace("/", ".")
            self._file_path_map[module_dot_path] = file_node_id

            file_node = GraphNodeDTO(
                node_id=file_node_id,
                node_type="FILE",
                name=os.path.basename(file.file_path),
                qualified_name=file.file_path,
                file_path=file.file_path,
                line_number=1,
                metadata={"loc": file.lines_of_code, "language": file.language},
            )
            self._add_node(file_node)

            for sym in file.symbols:
                node_type = sym.symbol_type.value
                node_id = f"{node_type.lower()}::{file.file_path}::{sym.qualified_name}"
                sym_node = GraphNodeDTO(
                    node_id=node_id,
                    node_type=node_type,
                    name=sym.name,
                    qualified_name=f"{file.file_path}::{sym.qualified_name}",
                    file_path=file.file_path,
                    line_number=sym.start_line,
                    metadata={
                        "end_line": sym.end_line,
                        "signature": sym.signature,
                        "parent_name": sym.parent_name,
                        **sym.metadata,
                    },
                )
                self._add_node(sym_node)

                # Index for resolution
                self._qualified_symbol_lookup[sym.qualified_name] = sym_node
                if sym.name not in self._symbol_lookup:
                    self._symbol_lookup[sym.name] = sym_node

                # Containment edge: file contains top-level symbol
                if not sym.parent_name:
                    edge_type = "EXPOSES" if sym.symbol_type == SymbolType.ENDPOINT else "DEPENDS_ON"
                    self._add_edge(file_node_id, node_id, edge_type=edge_type)
                else:
                    # Class contains method
                    parent_node_id = f"class::{file.file_path}::{sym.parent_name}"
                    if parent_node_id in self.nodes:
                        self._add_edge(parent_node_id, node_id, edge_type="DEPENDS_ON")

        # Step 2: Resolve Import edges
        for file in parsed_files:
            source_file_id = f"file::{file.file_path}"
            for imp in file.imports:
                target_file_id = self._resolve_import_to_file_node(imp.module, file.file_path)
                if target_file_id and target_file_id != source_file_id:
                    self._add_edge(
                        source_file_id,
                        target_file_id,
                        edge_type="IMPORTS",
                        metadata={"module": imp.module, "imported_symbols": imp.imported_symbols},
                    )

        # Step 3: Resolve Inheritance (INHERITS) edges
        for file in parsed_files:
            for sym in file.symbols:
                if sym.symbol_type in (SymbolType.CLASS, SymbolType.MODEL, SymbolType.INTERFACE):
                    subclass_node_id = f"{sym.symbol_type.value.lower()}::{file.file_path}::{sym.qualified_name}"
                    bases = sym.metadata.get("bases", [])
                    base_class = sym.metadata.get("base_class")
                    all_bases = list(bases) + ([base_class] if base_class else [])

                    for base_name in all_bases:
                        target_node = self._symbol_lookup.get(base_name)
                        if target_node and target_node.node_id != subclass_node_id:
                            self._add_edge(subclass_node_id, target_node.node_id, edge_type="INHERITS")

        # Step 4: Resolve Call edges (CALLS) and Queries (QUERIES)
        for file in parsed_files:
            for sym in file.symbols:
                caller_node_id = f"{sym.symbol_type.value.lower()}::{file.file_path}::{sym.qualified_name}"
                for call in sym.calls:
                    target_node = self._resolve_call_target(call.callee_name, file)
                    if target_node and target_node.node_id != caller_node_id:
                        edge_type = "QUERIES" if target_node.node_type == "MODEL" else "CALLS"
                        self._add_edge(
                            caller_node_id,
                            target_node.node_id,
                            edge_type=edge_type,
                            metadata={"call_line": call.line_number},
                        )

        return list(self.nodes.values()), self.edges

    def _resolve_import_to_file_node(self, module_str: str, current_file: str) -> Optional[str]:
        if not module_str:
            return None

        clean_mod = module_str.lstrip(".").replace(".", "/").lower()
        if clean_mod in self._file_path_map:
            return self._file_path_map[clean_mod]

        # Check relative resolution
        if module_str.startswith("."):
            curr_dir = os.path.dirname(current_file).replace("\\", "/").lower()
            rel_path = os.path.normpath(os.path.join(curr_dir, clean_mod)).replace("\\", "/").lower()
            if rel_path in self._file_path_map:
                return self._file_path_map[rel_path]

        # Partial match
        for key, node_id in self._file_path_map.items():
            if key.endswith(clean_mod):
                return node_id
        return None

    def _resolve_call_target(self, callee_name: str, current_file: NormalizedFile) -> Optional[GraphNodeDTO]:
        # 1. Check if callee is defined in the same file
        for sym in current_file.symbols:
            if sym.name == callee_name:
                target_id = f"{sym.symbol_type.value.lower()}::{current_file.file_path}::{sym.qualified_name}"
                if target_id in self.nodes:
                    return self.nodes[target_id]

        # 2. Check globally in symbol lookup
        if callee_name in self._symbol_lookup:
            return self._symbol_lookup[callee_name]

        return None

    def _add_node(self, node: GraphNodeDTO):
        if node.node_id not in self.nodes:
            self.nodes[node.node_id] = node

    def _add_edge(self, source_id: str, target_id: str, edge_type: str, weight: float = 1.0, metadata: Optional[dict] = None):
        if source_id in self.nodes and target_id in self.nodes:
            edge = GraphEdgeDTO(
                source_id=source_id,
                target_id=target_id,
                edge_type=edge_type,
                weight=weight,
                metadata=metadata or {},
            )
            self.edges.append(edge)
