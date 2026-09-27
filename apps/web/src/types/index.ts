export interface User {
  id: string;
  email: string;
  full_name?: string;
  role: "ADMIN" | "USER";
  is_active: boolean;
  github_user_id?: string;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  user: User;
  tokens: AuthTokens;
}

export interface Repository {
  id: string;
  owner_id: string;
  name: string;
  full_name: string;
  github_url: string;
  default_branch: string;
  is_private: boolean;
  is_indexed: boolean;
  current_commit_sha?: string;
  index_version: number;
  status: "PENDING" | "QUEUED" | "CLONING" | "PARSING" | "INDEXING" | "INDEXED" | "ACTIVE" | "FAILED";
  created_at: string;
  updated_at: string;
}

export interface Citation {
  file_path: string;
  start_line: number;
  end_line: number;
  symbol_name?: string;
  commit_sha?: string;
  snippet?: string;
}

export interface CodeSymbol {
  id: string;
  name: string;
  symbol_type: "FUNCTION" | "METHOD" | "CLASS" | "INTERFACE" | "ENDPOINT" | "MODEL" | "VARIABLE" | "TYPE_ALIAS";
  signature?: string;
  start_line: number;
  end_line: number;
  file_id?: string;
  parent_symbol_id?: string;
  docstring?: string;
}

export interface RepositoryFile {
  id: string;
  path: string;
  language: string;
  loc?: number;
  size_bytes?: number;
  content_hash?: string;
  symbols?: CodeSymbol[];
}

export interface GraphNode {
  id: string;
  node_key: string;
  node_type: string;
  name: string;
  file_path?: string;
  in_degree?: number;
  out_degree?: number;
  metadata?: Record<string, any>;
}

export interface GraphEdge {
  id?: string;
  source: string;
  target: string;
  edge_type: string;
  metadata?: Record<string, any>;
}

export interface GraphTopologyMetrics {
  total_nodes: number;
  total_edges: number;
  in_degree: number;
  out_degree: number;
  centrality: number;
  node_type_counts: Record<string, number>;
  edge_type_counts: Record<string, number>;
  cycle_count: number;
}

export interface GraphData {
  repository_id: string;
  commit_sha?: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  nodes_count: number;
  edges_count: number;
  metrics?: GraphTopologyMetrics;
}

export interface CircularDependencyCycle {
  cycle_type: "IMPORT_CYCLE" | "CALL_CYCLE" | "MIXED_CYCLE" | string;
  nodes: string[];
  cycle_path: string[];
  length: number;
  participating_files: string[];
  edge_types: string[];
}

export interface CircularDependencyResponse {
  repository_id: string;
  commit_sha?: string;
  total_cycles: number;
  cycles: CircularDependencyCycle[];
}

export interface GraphNodeDetail {
  node: GraphNode;
  in_degree: number;
  out_degree: number;
  centrality: number;
  incoming_callers: GraphNode[];
  outgoing_callees: GraphNode[];
  neighborhood_nodes_count: number;
  neighborhood_edges_count: number;
}

export interface ImpactAnalysis {
  target_node_id: string;
  target_name: string;
  impact_score: number;
  severity?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | string;
  upstream_callers_count: number;
  impacted_files_count: number;
  affected_endpoints: string[];
  affected_endpoints_details?: Array<{
    name: string;
    qualified_name: string;
    file_path?: string;
    http_method?: string;
    route?: string;
  }>;
  impacted_symbols: string[];
  traversal_depth: number;
  score_breakdown?: Record<string, number>;
}

export interface PathAnalysis {
  source_node_id: string;
  target_node_id: string;
  path_exists: boolean;
  path_length: number;
  call_chain: string[];
  nodes: Array<{
    node_id: string;
    name: string;
    node_type: string;
    file_path?: string;
    qualified_name: string;
  }>;
}

export interface IndexJob {
  id: string;
  repository_id: string;
  commit_sha: string;
  status: string;
  current_step: string;
  progress_percent: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
}

export interface SearchHit {
  chunk_id: string;
  repository_id: string;
  file_id: string;
  file_path: string;
  start_line: number;
  end_line: number;
  symbol_name?: string;
  symbol_type?: string;
  content: string;
  score: number;
  lexical_score?: number;
  vector_score?: number;
  rrf_score?: number;
  rerank_score?: number;
}

export interface SearchResponse {
  query: string;
  mode: string;
  total_candidates: number;
  results: SearchHit[];
  execution_time_ms: number;
}

export interface SearchRequest {
  query: string;
  mode?: "hybrid" | "lexical" | "semantic";
  top_k?: number;
  rerank?: boolean;
  symbol_type?: string;
  file_pattern?: string;
}

export type GroundingStatus = "VERIFIED" | "PARTIALLY_VERIFIED" | "UNSUPPORTED";

export interface CitationDTO {
  raw_citation: string;
  file_path: string;
  start_line: number;
  end_line: number;
  file_exists: boolean;
  lines_in_bounds: boolean;
  overlaps_context: boolean;
  symbol_matches: boolean;
  source_chunk_id?: string | null;
  confidence: number;
  validation_reason: string;
  is_valid: boolean;
}

export interface ContextChunkDTO {
  chunk_id: string;
  file_path: string;
  symbol_name?: string | null;
  symbol_type?: string | null;
  start_line: number;
  end_line: number;
  content: string;
  score: number;
  source: string;
}

export interface RetrievalEvidenceDTO {
  candidate_count: number;
  selected_count: number;
  discarded_count: number;
  bm25_scores: number[];
  vector_scores: number[];
  rrf_scores: number[];
  reranker_scores: number[];
  context_tokens: number;
  evidence_threshold_met: boolean;
  threshold_reason: string;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: "USER" | "ASSISTANT" | "SYSTEM";
  content: string;
  grounding_status?: GroundingStatus | null;
  intent?: string | null;
  provider?: string | null;
  is_mock?: boolean;
  citations: CitationDTO[];
  context_chunks: ContextChunkDTO[];
  retrieval_evidence?: RetrievalEvidenceDTO | null;
  tokens_used?: number | null;
  latency_ms?: number | null;
  created_at: string;
}

export interface ChatSession {
  id: string;
  repository_id: string;
  title: string;
  commit_sha?: string | null;
  message_count: number;
  created_at: string;
  updated_at?: string | null;
}

export interface ChatSessionDetail {
  id: string;
  repository_id: string;
  title: string;
  commit_sha?: string | null;
  created_at: string;
  messages: ChatMessage[];
}

