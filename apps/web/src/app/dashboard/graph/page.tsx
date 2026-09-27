"use client";

import { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Network,
  Search,
  Activity,
  GitBranch,
  FileCode,
  ShieldAlert,
  ArrowRight,
  Boxes,
  Zap,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Layers,
  ArrowUpRight,
} from "lucide-react";
import { api } from "@/lib/api";
import {
  Repository,
  GraphData,
  ImpactAnalysis,
  PathAnalysis,
  CircularDependencyResponse,
  GraphNodeDetail,
  GraphNode,
} from "@/types";
import { StatusBadge } from "@/components/StatusBadge";

export default function GraphPage() {
  return (
    <Suspense
      fallback={
        <div className="p-12 text-center text-xs font-mono text-slate-400 border border-border bg-surface-200 rounded-xl space-y-2">
          <Loader2 className="h-6 w-6 animate-spin mx-auto text-brand-sky" />
          <div>Initializing Graph &amp; Impact Engine...</div>
        </div>
      }
    >
      <GraphPageContent />
    </Suspense>
  );
}

function GraphPageContent() {
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get("tab") as any) || "topology";

  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>("");
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Active Tab: topology | impact | path | cycles
  const [activeTab, setActiveTab] = useState<"topology" | "impact" | "path" | "cycles">(initialTab);

  // Filter state for topology
  const [nodeTypeFilter, setNodeTypeFilter] = useState<string>("ALL");
  const [searchFilter, setSearchFilter] = useState<string>("");
  const [selectedNodeDetail, setSelectedNodeDetail] = useState<GraphNodeDetail | null>(null);
  const [loadingNodeDetail, setLoadingNodeDetail] = useState<boolean>(false);

  // Blast Radius State
  const [targetSymbol, setTargetSymbol] = useState<string>("");
  const [impactResult, setImpactResult] = useState<ImpactAnalysis | null>(null);
  const [analyzingImpact, setAnalyzingImpact] = useState<boolean>(false);

  // Path Analysis State
  const [sourceSymbol, setSourceSymbol] = useState<string>("");
  const [destinationSymbol, setDestinationSymbol] = useState<string>("");
  const [pathResult, setPathResult] = useState<PathAnalysis | null>(null);
  const [analyzingPath, setAnalyzingPath] = useState<boolean>(false);

  // Cycles State
  const [cyclesData, setCyclesData] = useState<CircularDependencyResponse | null>(null);
  const [loadingCycles, setLoadingCycles] = useState<boolean>(false);

  useEffect(() => {
    loadRepositories();
  }, []);

  useEffect(() => {
    if (selectedRepoId) {
      setImpactResult(null);
      setPathResult(null);
      setSelectedNodeDetail(null);
      setTargetSymbol("");
      setSourceSymbol("");
      setDestinationSymbol("");
      loadGraph(selectedRepoId);
      loadCycles(selectedRepoId);
    }
  }, [selectedRepoId]);

  async function loadRepositories() {
    try {
      setLoading(true);
      const repos = await api.listRepositories();
      setRepositories(repos);
      if (repos.length > 0) {
        setSelectedRepoId(repos[0].id);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load repositories");
    } finally {
      setLoading(false);
    }
  }

  async function loadGraph(repoId: string, nodeType?: string) {
    try {
      setLoading(true);
      setError(null);
      const opts = nodeType && nodeType !== "ALL" ? { node_type: nodeType } : undefined;
      const data = await api.getRepositoryGraph(repoId, opts);
      setGraphData(data);

      if (data.nodes.length > 0) {
        if (!targetSymbol) setTargetSymbol(data.nodes[0].name);
        if (!sourceSymbol) setSourceSymbol(data.nodes[0].name);
        if (!destinationSymbol && data.nodes.length > 1) {
          setDestinationSymbol(data.nodes[data.nodes.length - 1].name);
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to load graph data");
    } finally {
      setLoading(false);
    }
  }

  async function loadCycles(repoId: string) {
    try {
      setLoadingCycles(true);
      const data = await api.getRepositoryCycles(repoId);
      setCyclesData(data);
    } catch {
      // Optional cycle metrics
    } finally {
      setLoadingCycles(false);
    }
  }

  async function handleComputeImpact(symbolToAnalyze?: string) {
    const sym = symbolToAnalyze || targetSymbol;
    if (!selectedRepoId || !sym) return;
    try {
      setAnalyzingImpact(true);
      setError(null);
      const res = await api.getGraphImpact(selectedRepoId, sym);
      setImpactResult(res);
      if (symbolToAnalyze) setTargetSymbol(symbolToAnalyze);
    } catch (err: any) {
      setError(err.message || "Failed to analyze blast radius");
    } finally {
      setAnalyzingImpact(false);
    }
  }

  async function handleFindPath() {
    if (!selectedRepoId || !sourceSymbol || !destinationSymbol) return;
    try {
      setAnalyzingPath(true);
      setError(null);
      const res = await api.getGraphPath(selectedRepoId, sourceSymbol, destinationSymbol);
      setPathResult(res);
    } catch (err: any) {
      setError(err.message || "Failed to find execution path");
    } finally {
      setAnalyzingPath(false);
    }
  }

  async function inspectNode(nodeKey: string) {
    if (!selectedRepoId) return;
    try {
      setLoadingNodeDetail(true);
      const detail = await api.getGraphNodeDetails(selectedRepoId, nodeKey);
      setSelectedNodeDetail(detail);
    } catch (err: any) {
      setError(err.message || "Failed to load symbol details");
    } finally {
      setLoadingNodeDetail(false);
    }
  }

  const filteredNodes = (graphData?.nodes || []).filter((n) => {
    const matchesType = nodeTypeFilter === "ALL" || n.node_type === nodeTypeFilter;
    const matchesSearch =
      !searchFilter ||
      n.name.toLowerCase().includes(searchFilter.toLowerCase()) ||
      (n.file_path && n.file_path.toLowerCase().includes(searchFilter.toLowerCase()));
    return matchesType && matchesSearch;
  });

  return (
    <div className="max-w-7xl mx-auto space-y-6 font-sans">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-border gap-4">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-brand-indigo mb-1 flex items-center space-x-1.5">
            <Network className="h-3.5 w-3.5" />
            <span>AST Directed Graph &amp; Graph Algorithms</span>
          </div>
          <h1 className="text-2xl font-black uppercase tracking-tight text-white font-sans">
            Dependency Graph &amp; Impact Engine
          </h1>
          <p className="mt-1 text-xs text-slate-400 font-mono">
            Directly trace call paths, compute Tarjan strongly connected components (SCC), and model transitively affected API blast radii.
          </p>
        </div>

        {/* Repository Selector */}
        <select
          value={selectedRepoId}
          onChange={(e) => setSelectedRepoId(e.target.value)}
          className="bg-surface-300 border border-border text-slate-200 text-xs rounded-lg px-3.5 py-2 font-mono focus:border-brand-indigo focus:outline-none shadow-sm"
        >
          {repositories.map((repo) => (
            <option key={repo.id} value={repo.id}>
              {repo.full_name || repo.name} ({repo.default_branch})
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-400 text-xs font-mono flex items-center space-x-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Metrics Header Strip */}
      {graphData && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div className="p-4 rounded-xl border border-border bg-surface-200 font-mono shadow-sm">
            <div className="text-[10px] text-slate-500 uppercase font-semibold">GRAPH NODES</div>
            <div className="text-2xl font-bold text-white mt-1">{graphData.nodes_count}</div>
          </div>
          <div className="p-4 rounded-xl border border-border bg-surface-200 font-mono shadow-sm">
            <div className="text-[10px] text-slate-500 uppercase font-semibold">DIRECTED EDGES</div>
            <div className="text-2xl font-bold text-brand-sky mt-1">{graphData.edges_count}</div>
          </div>
          <div className="p-4 rounded-xl border border-border bg-surface-200 font-mono shadow-sm">
            <div className="text-[10px] text-slate-500 uppercase font-semibold">API ENDPOINTS</div>
            <div className="text-2xl font-bold text-brand-amber mt-1">
              {graphData.nodes.filter((n) => n.node_type === "ENDPOINT").length}
            </div>
          </div>
          <div className="p-4 rounded-xl border border-border bg-surface-200 font-mono shadow-sm">
            <div className="text-[10px] text-slate-500 uppercase font-semibold">DATA MODELS</div>
            <div className="text-2xl font-bold text-brand-purple mt-1">
              {graphData.nodes.filter((n) => n.node_type === "MODEL").length}
            </div>
          </div>
          <div className="p-4 rounded-xl border border-border bg-surface-200 font-mono shadow-sm">
            <div className="text-[10px] text-slate-500 uppercase font-semibold">CIRCULAR CYCLES</div>
            <div
              className={`text-2xl font-bold mt-1 ${
                cyclesData && cyclesData.total_cycles > 0 ? "text-brand-crimson" : "text-brand-emerald"
              }`}
            >
              {cyclesData ? cyclesData.total_cycles : 0}
            </div>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-border space-x-6 text-xs font-mono">
        <button
          onClick={() => setActiveTab("topology")}
          className={`pb-3 flex items-center space-x-2 transition ${
            activeTab === "topology"
              ? "text-brand-indigo border-b-2 border-brand-indigo font-bold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Boxes className="h-4 w-4" />
          <span>Topology &amp; Inspection</span>
        </button>

        <button
          onClick={() => setActiveTab("impact")}
          className={`pb-3 flex items-center space-x-2 transition ${
            activeTab === "impact"
              ? "text-brand-indigo border-b-2 border-brand-indigo font-bold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Activity className="h-4 w-4" />
          <span>Blast Radius Analysis</span>
        </button>

        <button
          onClick={() => setActiveTab("path")}
          className={`pb-3 flex items-center space-x-2 transition ${
            activeTab === "path"
              ? "text-brand-indigo border-b-2 border-brand-indigo font-bold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <GitBranch className="h-4 w-4" />
          <span>Shortest Call Path</span>
        </button>

        <button
          onClick={() => setActiveTab("cycles")}
          className={`pb-3 flex items-center space-x-2 transition ${
            activeTab === "cycles"
              ? "text-brand-indigo border-b-2 border-brand-indigo font-bold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <ShieldAlert className="h-4 w-4" />
          <span>Architectural Cycles ({cyclesData ? cyclesData.total_cycles : 0})</span>
        </button>
      </div>

      {/* Tab 1: Topology & Symbol Inspector */}
      {activeTab === "topology" && graphData && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="p-4 rounded-xl border border-border bg-surface-200 flex flex-col md:flex-row items-center justify-between gap-4 font-mono text-xs shadow-sm">
            {/* Search */}
            <div className="relative w-full md:w-80">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
              <input
                type="text"
                placeholder="Filter symbols or files..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="w-full bg-surface-300 border border-border text-slate-200 pl-9 pr-3 py-2 rounded-lg text-xs font-mono focus:border-brand-indigo focus:outline-none"
              />
            </div>

            {/* Type Filters */}
            <div className="flex flex-wrap items-center gap-1.5 w-full md:w-auto">
              {["ALL", "FUNCTION", "METHOD", "CLASS", "ENDPOINT", "MODEL", "FILE"].map((t) => (
                <button
                  key={t}
                  onClick={() => setNodeTypeFilter(t)}
                  className={`px-3 py-1.5 rounded-lg text-[11px] font-semibold transition ${
                    nodeTypeFilter === t
                      ? "bg-brand-indigo text-white font-bold shadow-sm"
                      : "bg-surface-300 text-slate-400 hover:text-slate-200 border border-border"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Nodes List */}
            <div className="lg:col-span-7 p-5 rounded-xl border border-border bg-surface-200 space-y-3 shadow-sm">
              <div className="text-xs font-mono font-bold text-slate-300 border-b border-border pb-2 flex justify-between items-center">
                <span>Filtered AST Symbols ({filteredNodes.length})</span>
                <span className="text-[11px] text-slate-500 font-normal">Click a node to inspect callers &amp; callees</span>
              </div>
              <div className="space-y-2 max-h-[540px] overflow-y-auto pr-1">
                {filteredNodes.map((n) => {
                  const isSelected = selectedNodeDetail?.node.node_key === n.node_key;
                  return (
                    <div
                      key={n.id}
                      onClick={() => inspectNode(n.node_key)}
                      className={`p-3 rounded-xl border flex items-center justify-between text-xs font-mono cursor-pointer transition ${
                        isSelected
                          ? "bg-surface-100 border-brand-indigo text-brand-indigo shadow-sm"
                          : "bg-surface-300 border-border hover:border-border-strong hover:bg-surface-100/50"
                      }`}
                    >
                      <div className="truncate mr-3 min-w-0">
                        <div className="text-slate-100 font-bold truncate">{n.name}</div>
                        {n.file_path && (
                          <div className="text-[10px] text-slate-500 truncate mt-0.5">{n.file_path}</div>
                        )}
                      </div>
                      <div className="flex items-center space-x-2 shrink-0">
                        {n.in_degree !== undefined && (
                          <span className="text-[10px] text-slate-400 px-1.5 py-0.5 rounded bg-surface-200 border border-border">
                            in:{n.in_degree}
                          </span>
                        )}
                        {n.out_degree !== undefined && (
                          <span className="text-[10px] text-slate-400 px-1.5 py-0.5 rounded bg-surface-200 border border-border">
                            out:{n.out_degree}
                          </span>
                        )}
                        <StatusBadge type="nodeType" value={n.node_type} size="sm" />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Symbol Inspector Panel */}
            <div className="lg:col-span-5 p-5 rounded-xl border border-border bg-surface-200 space-y-4 shadow-sm">
              <div className="text-xs font-mono font-bold text-white border-b border-border pb-2 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Boxes className="h-4 w-4 text-brand-indigo" />
                  <span>Symbol Structural Inspector</span>
                </div>
                {selectedNodeDetail && (
                  <StatusBadge type="nodeType" value={selectedNodeDetail.node.node_type} size="sm" />
                )}
              </div>

              {loadingNodeDetail ? (
                <div className="py-16 flex justify-center items-center">
                  <Loader2 className="h-6 w-6 text-brand-indigo animate-spin" />
                </div>
              ) : selectedNodeDetail ? (
                <div className="space-y-4 font-mono text-xs">
                  <div>
                    <div className="text-slate-500 text-[10px] uppercase font-semibold">Symbol Identity</div>
                    <div className="text-white font-bold text-base mt-0.5">{selectedNodeDetail.node.name}</div>
                    <div className="text-[11px] text-slate-400 break-all mt-1 p-2 rounded bg-surface-300 border border-border">
                      {selectedNodeDetail.node.node_key}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div className="p-3 rounded-lg bg-surface-300 border border-border space-y-0.5">
                      <span className="text-slate-500 block text-[10px] uppercase">Incoming In-Degree:</span>
                      <span className="text-brand-sky font-bold text-base">{selectedNodeDetail.in_degree}</span>
                    </div>
                    <div className="p-3 rounded-lg bg-surface-300 border border-border space-y-0.5">
                      <span className="text-slate-500 block text-[10px] uppercase">Outgoing Out-Degree:</span>
                      <span className="text-brand-indigo font-bold text-base">{selectedNodeDetail.out_degree}</span>
                    </div>
                  </div>

                  {/* Incoming Callers */}
                  <div className="space-y-1.5 pt-2 border-t border-border">
                    <div className="text-[11px] font-bold text-slate-300">
                      Incoming Callers ({selectedNodeDetail.incoming_callers.length})
                    </div>
                    {selectedNodeDetail.incoming_callers.length > 0 ? (
                      <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
                        {selectedNodeDetail.incoming_callers.map((c, i) => (
                          <div
                            key={i}
                            onClick={() => inspectNode(c.node_key)}
                            className="p-2 rounded-lg bg-surface-300 border border-border text-[11px] text-slate-300 truncate cursor-pointer hover:border-brand-indigo hover:text-white transition"
                          >
                            {c.name}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-[10px] text-slate-500 p-2 rounded bg-surface-300">No incoming callers detected</div>
                    )}
                  </div>

                  {/* Outgoing Callees */}
                  <div className="space-y-1.5 pt-2 border-t border-border">
                    <div className="text-[11px] font-bold text-slate-300">
                      Outgoing Callees ({selectedNodeDetail.outgoing_callees.length})
                    </div>
                    {selectedNodeDetail.outgoing_callees.length > 0 ? (
                      <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
                        {selectedNodeDetail.outgoing_callees.map((c, i) => (
                          <div
                            key={i}
                            onClick={() => inspectNode(c.node_key)}
                            className="p-2 rounded-lg bg-surface-300 border border-border text-[11px] text-slate-300 truncate cursor-pointer hover:border-brand-indigo hover:text-white transition"
                          >
                            {c.name}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-[10px] text-slate-500 p-2 rounded bg-surface-300">No outgoing callees detected</div>
                    )}
                  </div>

                  <div className="pt-2">
                    <button
                      onClick={() => {
                        setTargetSymbol(selectedNodeDetail.node.name);
                        setActiveTab("impact");
                        handleComputeImpact(selectedNodeDetail.node.name);
                      }}
                      className="w-full py-2.5 bg-brand-indigo hover:bg-brand-indigo/90 text-white rounded-lg text-xs font-mono font-bold transition shadow-sm"
                    >
                      Calculate Blast Radius for {selectedNodeDetail.node.name}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="py-16 text-center text-xs text-slate-500 font-mono space-y-2">
                  <Boxes className="h-8 w-8 text-slate-600 mx-auto" />
                  <p>Select any node in the list to view architectural connections and degree metrics.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Blast Radius Impact Analysis */}
      {activeTab === "impact" && (
        <div className="space-y-6">
          <div className="p-6 rounded-xl border border-border bg-surface-200 space-y-4 shadow-sm">
            <div>
              <h2 className="text-sm font-bold font-mono text-white flex items-center space-x-2">
                <Activity className="h-4 w-4 text-brand-amber" />
                <span>Blast Radius &amp; Transitive Regression Analysis</span>
              </h2>
              <p className="text-xs font-mono text-slate-400 mt-1">
                Calculate the ripple effect across API endpoints, consumer services, and upstream callers if a symbol is refactored.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                placeholder="Target symbol name (e.g. as_view, dispatch_request, verify_jwt_token)..."
                value={targetSymbol}
                onChange={(e) => setTargetSymbol(e.target.value)}
                className="flex-1 bg-surface-300 border border-border text-slate-200 text-xs rounded-lg px-4 py-2.5 font-mono focus:border-brand-amber focus:outline-none"
              />
              <button
                onClick={() => handleComputeImpact()}
                disabled={analyzingImpact || !targetSymbol}
                className="px-6 py-2.5 bg-brand-amber hover:bg-amber-600 text-slate-950 font-extrabold rounded-lg text-xs font-mono disabled:opacity-50 transition flex items-center justify-center space-x-2 shadow-sm active:scale-95"
              >
                <Zap className={`h-4 w-4 ${analyzingImpact ? "animate-spin" : ""}`} />
                <span>{analyzingImpact ? "Computing Blast Radius..." : "Analyze Blast Radius"}</span>
              </button>
            </div>
          </div>

          {impactResult && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Score Card */}
              <div className="lg:col-span-4 rounded-xl border border-brand-amber/30 bg-surface-200 p-6 space-y-4 font-mono shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Impact Score</div>
                  {impactResult.severity && (
                    <StatusBadge type="severity" value={impactResult.severity} />
                  )}
                </div>
                <div className="flex items-baseline space-x-2">
                  <span className="text-5xl font-black text-brand-amber">
                    {impactResult.impact_score.toFixed(3)}
                  </span>
                  <span className="text-xs text-slate-500 font-bold">/ 1.000</span>
                </div>
                <div className="text-xs text-slate-300">
                  Target Symbol: <strong className="text-white">{impactResult.target_name}</strong>
                </div>

                <div className="pt-4 border-t border-border space-y-2.5 text-xs">
                  <div className="flex justify-between text-slate-400">
                    <span>Upstream Callers:</span>
                    <span className="text-white font-bold">{impactResult.upstream_callers_count}</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Impacted Files:</span>
                    <span className="text-white font-bold">{impactResult.impacted_files_count}</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Max Traversal Depth:</span>
                    <span className="text-brand-sky font-bold">{impactResult.traversal_depth} hops</span>
                  </div>
                </div>

                {impactResult.score_breakdown && Object.keys(impactResult.score_breakdown).length > 0 && (
                  <div className="pt-4 border-t border-border space-y-2 text-[11px] text-slate-400">
                    <div className="font-bold text-slate-200 uppercase text-[10px]">Factor Breakdown:</div>
                    <div className="flex justify-between">
                      <span>Endpoints factor:</span>
                      <span className="text-white font-mono">{impactResult.score_breakdown.endpoints_factor ?? 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Files factor:</span>
                      <span className="text-white font-mono">{impactResult.score_breakdown.files_factor ?? 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Callers factor:</span>
                      <span className="text-white font-mono">{impactResult.score_breakdown.callers_factor ?? 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Depth factor:</span>
                      <span className="text-white font-mono">{impactResult.score_breakdown.depth_factor ?? 0}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Affected Endpoints & Impacted Symbols */}
              <div className="lg:col-span-8 rounded-xl border border-border bg-surface-200 p-6 space-y-6 shadow-sm">
                <div>
                  <div className="text-xs font-mono font-bold text-brand-amber uppercase tracking-wider mb-3 flex items-center space-x-2">
                    <ShieldAlert className="h-4 w-4" />
                    <span>Affected HTTP API Endpoints ({impactResult.affected_endpoints.length})</span>
                  </div>
                  {impactResult.affected_endpoints_details && impactResult.affected_endpoints_details.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {impactResult.affected_endpoints_details.map((ep, idx) => (
                        <div
                          key={idx}
                          className="px-3.5 py-2.5 rounded-lg bg-surface-300 border border-border text-xs font-mono flex items-center justify-between"
                        >
                          <div className="truncate mr-2">
                            <span className="font-bold text-slate-200">{ep.name}</span>
                            <div className="text-[10px] text-slate-500 truncate">{ep.route}</div>
                          </div>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-brand-amber/10 text-brand-amber uppercase font-bold border border-brand-amber/30">
                            {ep.http_method || "ANY"}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : impactResult.affected_endpoints.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {impactResult.affected_endpoints.map((ep, idx) => (
                        <span
                          key={idx}
                          className="px-2.5 py-1 rounded bg-brand-amber/10 text-brand-amber border border-brand-amber/30 text-xs font-mono font-semibold"
                        >
                          {ep}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 font-mono">No direct HTTP endpoints affected.</p>
                  )}
                </div>

                <div>
                  <div className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider mb-3">
                    Transitively Impacted Symbols ({impactResult.impacted_symbols.length})
                  </div>
                  <div className="space-y-1.5 max-h-[320px] overflow-y-auto pr-1">
                    {impactResult.impacted_symbols.map((sym, idx) => (
                      <div
                        key={idx}
                        className="px-3 py-2 rounded-lg bg-surface-300 border border-border font-mono text-xs text-slate-300 flex items-center justify-between hover:border-border-strong transition"
                      >
                        <span className="truncate mr-2 font-mono">{sym}</span>
                        <button
                          onClick={() => {
                            const nameOnly = sym.split("::").pop() || sym;
                            handleComputeImpact(nameOnly);
                          }}
                          className="text-[11px] text-brand-sky hover:underline font-bold shrink-0"
                        >
                          Focus Blast Radius
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Shortest Call Path */}
      {activeTab === "path" && (
        <div className="space-y-6">
          <div className="p-6 rounded-xl border border-border bg-surface-200 space-y-4 shadow-sm">
            <div>
              <h2 className="text-sm font-bold font-mono text-white flex items-center space-x-2">
                <GitBranch className="h-4 w-4 text-brand-sky" />
                <span>Shortest Call Path Discovery (Dijkstra Traversal)</span>
              </h2>
              <p className="text-xs font-mono text-slate-400 mt-1">
                Trace the directed call and dependency path connecting two symbols across classes, functions, and endpoints.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <input
                type="text"
                placeholder="Source Symbol (e.g. handle_request, get_user_route)..."
                value={sourceSymbol}
                onChange={(e) => setSourceSymbol(e.target.value)}
                className="bg-surface-300 border border-border text-slate-200 text-xs rounded-lg px-4 py-2.5 font-mono focus:border-brand-sky focus:outline-none"
              />
              <input
                type="text"
                placeholder="Target Symbol (e.g. dispatch_request, fetch_profile)..."
                value={destinationSymbol}
                onChange={(e) => setDestinationSymbol(e.target.value)}
                className="bg-surface-300 border border-border text-slate-200 text-xs rounded-lg px-4 py-2.5 font-mono focus:border-brand-sky focus:outline-none"
              />
            </div>

            <button
              onClick={handleFindPath}
              disabled={analyzingPath || !sourceSymbol || !destinationSymbol}
              className="px-6 py-2.5 bg-brand-sky hover:bg-brand-skyHover text-slate-950 font-extrabold rounded-lg text-xs font-mono disabled:opacity-50 transition flex items-center justify-center space-x-2 shadow-sm active:scale-95"
            >
              {analyzingPath ? <Loader2 className="h-4 w-4 animate-spin" /> : <GitBranch className="h-4 w-4" />}
              <span>{analyzingPath ? "Finding Shortest Path..." : "Find Execution Path"}</span>
            </button>
          </div>

          {pathResult && (
            <div className="p-6 rounded-xl border border-border bg-surface-200 space-y-4 font-mono shadow-sm">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <span className="text-xs font-bold text-white">
                  {pathResult.path_exists ? `Execution Path Resolved: ${pathResult.path_length} hops` : "No Directed Execution Path"}
                </span>
                <span className="text-xs text-slate-400">
                  <code className="text-brand-sky">{pathResult.source_node_id}</code> &rarr; <code className="text-brand-emerald">{pathResult.target_node_id}</code>
                </span>
              </div>

              {pathResult.path_exists ? (
                <div className="space-y-4 pt-2">
                  <div className="text-xs text-slate-400 uppercase font-semibold">Hop-by-Hop Call Chain:</div>
                  <div className="flex flex-wrap items-center gap-3">
                    {pathResult.nodes && pathResult.nodes.length > 0 ? (
                      pathResult.nodes.map((stepNode, idx) => (
                        <div key={idx} className="flex items-center space-x-3">
                          <div className="p-3 rounded-xl bg-surface-300 border border-border text-xs space-y-1 shadow-sm">
                            <div className="flex items-center space-x-2">
                              <span className="text-[10px] font-bold text-brand-sky px-1.5 py-0.2 rounded bg-surface-100 border border-border">
                                Step #{idx + 1}
                              </span>
                              <span className="font-bold text-white">{stepNode.name}</span>
                            </div>
                            {stepNode.file_path && (
                              <div className="text-[10px] text-slate-400 truncate max-w-[220px]">
                                {stepNode.file_path}
                              </div>
                            )}
                          </div>
                          {idx < (pathResult.nodes?.length ?? 0) - 1 && (
                            <ArrowRight className="h-4 w-4 text-brand-sky flex-shrink-0" />
                          )}
                        </div>
                      ))
                    ) : (
                      pathResult.call_chain.map((step, idx) => (
                        <div key={idx} className="flex items-center space-x-3">
                          <span className="px-3 py-2 rounded-lg bg-surface-300 border border-border text-xs text-slate-200 font-bold">
                            {step}
                          </span>
                          {idx < pathResult.call_chain.length - 1 && (
                            <ArrowRight className="h-4 w-4 text-brand-sky flex-shrink-0" />
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ) : (
                <div className="py-8 text-center text-xs text-slate-500">
                  No directed execution path exists between {sourceSymbol} and {destinationSymbol}.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Architectural Cycles */}
      {activeTab === "cycles" && (
        <div className="space-y-6">
          <div className="p-6 rounded-xl border border-border bg-surface-200 space-y-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold font-mono text-white flex items-center space-x-2">
                  <ShieldAlert className="h-4 w-4 text-brand-crimson" />
                  <span>Circular Dependency Analysis (Tarjan Strongly Connected Components)</span>
                </h2>
                <p className="text-xs font-mono text-slate-400 mt-1">
                  Circular dependencies introduce tight architectural coupling and cause runtime initialization failures.
                </p>
              </div>
              <button
                onClick={() => selectedRepoId && loadCycles(selectedRepoId)}
                className="px-3 py-1.5 rounded-lg border border-border hover:bg-surface-100 bg-surface-300 text-slate-300 text-xs font-mono flex items-center space-x-1.5 transition"
              >
                <Loader2 className={`h-3.5 w-3.5 ${loadingCycles ? "animate-spin text-brand-sky" : ""}`} />
                <span>Refresh SCC</span>
              </button>
            </div>
          </div>

          {loadingCycles ? (
            <div className="p-16 text-center text-xs font-mono text-slate-400 border border-border bg-surface-200/50 rounded-xl">
              <Loader2 className="h-6 w-6 animate-spin mx-auto text-brand-indigo mb-2" />
              <span>Analyzing strongly connected components via Tarjan SCC...</span>
            </div>
          ) : cyclesData && cyclesData.cycles.length > 0 ? (
            <div className="space-y-4">
              {cyclesData.cycles.map((cycle, idx) => (
                <div
                  key={idx}
                  className="p-5 rounded-xl border border-rose-500/30 bg-surface-200 space-y-3 font-mono text-xs shadow-sm"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 font-bold text-[10px] uppercase border border-rose-500/30">
                        {cycle.cycle_type}
                      </span>
                      <span className="text-white font-bold">Cycle #{idx + 1} ({cycle.length} hops)</span>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-surface-300 border border-border space-y-2">
                    <div className="text-[10px] text-slate-500 uppercase font-bold">Cycle Execution Ring:</div>
                    <div className="flex flex-wrap items-center gap-2 text-slate-200">
                      {cycle.cycle_path.map((p, pIdx) => (
                        <span key={pIdx} className="flex items-center space-x-2">
                          <code className="text-brand-sky">{p}</code>
                          {pIdx < cycle.cycle_path.length - 1 && <span className="text-slate-600">&rarr;</span>}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-1">
                    <span className="text-slate-500 text-[10px] uppercase font-bold">Participating Files:</span>
                    <div className="flex flex-wrap gap-2 pt-1">
                      {cycle.participating_files.map((f, fIdx) => (
                        <span key={fIdx} className="px-2 py-0.5 rounded bg-surface-300 border border-border text-slate-300 text-[11px]">
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-12 text-center text-xs font-mono text-slate-400 border border-border bg-surface-200 rounded-xl space-y-2">
              <CheckCircle2 className="h-8 w-8 text-brand-emerald mx-auto" />
              <div className="text-sm font-bold text-white">Zero Circular Dependencies Detected</div>
              <p className="text-slate-500">The dependency graph forms a clean Directed Acyclic Graph (DAG).</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
