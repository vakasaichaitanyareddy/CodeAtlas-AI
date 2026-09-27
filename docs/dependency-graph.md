# Dependency & Call Graph Architecture

## Overview
CodeAtlas builds a directed code relationship graph representing files, modules, classes, functions, API endpoints, and database models as nodes, connected by typed directed edges (`IMPORTS`, `CALLS`, `INHERITS`, `IMPLEMENTS`, `DEPENDS_ON`, `EXPOSES`, `QUERIES`).

The graph engine empowers engineers and architects to:
1. Trace upstream callers and blast radiuses before modifying code.
2. Find shortest execution call chains connecting ingress endpoints to persistence models.
3. Detect architectural cycles and circular imports using Tarjan's Strongly Connected Components (SCC).
4. Inspect symbol neighborhoods with depth-bounded subgraphs and degree metrics.

---

## 1. Graph Node & Edge Taxonomy

### Node Types
- `FILE`: Physical source file in the repository.
- `MODULE`: Logical namespace or package.
- `CLASS`: Object-oriented class declaration.
- `FUNCTION`: Standalone function or procedure.
- `METHOD`: Class member function.
- `ENDPOINT`: HTTP route / API endpoint (e.g. `POST /api/v1/checkout`).
- `MODEL`: Relational or ORM model entity (e.g. `OrderModel`).

### Edge Types
- `IMPORTS`: Source file/module imports target module/symbol.
- `CALLS`: Source function/method invokes target function/method.
- `INHERITS`: Subclass derives from parent class.
- `IMPLEMENTS`: Class implements interface/protocol.
- `DEPENDS_ON`: Component relies on another module/service.
- `EXPOSES`: Controller/handler exposes an HTTP endpoint.
- `QUERIES`: Function performs database operations against a model.

---

## 2. Graph Algorithms & Traversals

### 2.1 Upstream Analysis (Reverse BFS)
Finds all callers, controllers, and tests that transitively rely on a given symbol up to a configured depth limit (default: 6 hops).

$$\text{Upstream}(u) = \{ v \in V \mid v \xrightarrow{*} u \}$$

### 2.2 Downstream Analysis (Forward BFS)
Finds all callees, persistence models, and external resources executed transitively by a target symbol.

$$\text{Downstream}(u) = \{ v \in V \mid u \xrightarrow{*} v \}$$

### 2.3 Normalized Impact Score & Blast Radius Analysis
Evaluates the architectural risk of modifying a symbol using a bounded, deterministic formula yielding a normalized score in $[0.0, 1.0]$:

$$\text{score} = \min\left(1.0, 0.35 \times \min\left(1.0, \frac{\text{endpoints}}{3}\right) + 0.30 \times \min\left(1.0, \frac{\text{files}}{5}\right) + 0.20 \times \min\left(1.0, \frac{\text{callers}}{10}\right) + 0.15 \times \min\left(1.0, \frac{\text{depth}}{5}\right)\right)$$

#### Deterministic Severity Mapping:
- **`CRITICAL`**: $\text{score} \ge 0.75$ or $\text{endpoints} \ge 2$
- **`HIGH`**: $\text{score} \ge 0.50$ or $\text{endpoints} \ge 1$
- **`MEDIUM`**: $\text{score} \ge 0.25$
- **`LOW`**: $\text{score} < 0.25$

### 2.4 Circular Dependency Detection (Tarjan's SCC)
Uses Tarjan's Strongly Connected Components (SCC) algorithm to detect feedback loops without exponential cycle enumeration:
- **Self-Loops**: $|S| = 1$ with directed edge $(u, u)$.
- **Multi-Node SCCs**: $|S| > 1$, where an elementary cycle is identified in $O(V+E)$ time.
- **Cycle Classification**:
  - `IMPORT_CYCLE`: All edges in the cycle loop are `IMPORTS`.
  - `CALL_CYCLE`: All edges in the cycle loop are `CALLS`.
  - `MIXED_CYCLE`: Cycle contains a combination of imports, calls, or dependencies.

### 2.5 Depth-Bounded Neighborhood Subgraph Extraction
Extracts a focused subgraph centered at target node $u$ with radius $d \le 2$ and capped at $N \le 500$ nodes, ensuring responsive frontend rendering and low API payload latency.

### 2.6 Shortest Call Path Analysis
Dijkstra shortest path search finding the sequence of calls and transitions linking an ingress endpoint to a persistence model or target symbol.

---

## 3. REST API Specification

### `GET /api/v1/repositories/{id}/graph`
Returns repository topology nodes, edges, degree counts, and summary metrics.
- **Query Filters**: `node_type`, `file_path`, `max_nodes` (default 500), `focus_symbol`, `commit_sha`.
- **Response**: `GraphTopologyResponse` (`repository_id`, `commit_sha`, `nodes`, `edges`, `nodes_count`, `edges_count`, `metrics`).

### `GET /api/v1/repositories/{id}/graph/cycles`
Returns all architectural cycles detected via Tarjan's SCC algorithm.
- **Response**: `CircularDependencyResponse` (`repository_id`, `total_cycles`, `cycles: [{ cycle_type, nodes, cycle_path, length, participating_files, edge_types }]`).

### `GET /api/v1/repositories/{id}/graph/nodes/{node_key}`
Returns detailed node metrics, incoming callers, outgoing callees, and bounded neighborhood.
- **Response**: `GraphNodeDetailResponse`.

### `GET /api/v1/repositories/{id}/graph/impact?symbol={symbol}`
Computes blast radius impact analysis for a symbol.
- **Response**: `GraphImpactResponse` (`impact_score`, `severity`, `upstream_callers_count`, `impacted_files_count`, `affected_endpoints`, `affected_endpoints_details`, `impacted_symbols`, `traversal_depth`, `score_breakdown`).

### `GET /api/v1/repositories/{id}/graph/path?source_symbol={source}&target_symbol={target}`
Finds shortest directed execution chain connecting two symbols.
- **Response**: `GraphPathResponse` (`path_exists`, `path_length`, `call_chain`, `nodes`).

---

## 4. Multi-Tenant Isolation & Security
All graph queries enforce tenant ownership via `RepositoryService.get_repository_by_id`. Unauthorized cross-tenant graph inspections return `HTTP 403 Forbidden`. All node and edge queries are scoped by repository ID and optional commit SHA.
