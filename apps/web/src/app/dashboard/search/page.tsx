"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import {
  Search,
  Sparkles,
  Zap,
  FileCode,
  Filter,
  ArrowRight,
  Layers,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Cpu,
} from "lucide-react";
import { api } from "@/lib/api";
import { Repository, SearchHit, SearchResponse } from "@/types";
import { StatusBadge } from "@/components/StatusBadge";
import { CodeViewer } from "@/components/CodeViewer";

export default function SearchPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>("");
  const [query, setQuery] = useState<string>("");
  const [mode, setMode] = useState<"hybrid" | "lexical" | "semantic">("hybrid");
  const [topK, setTopK] = useState<number>(10);
  const [rerank, setRerank] = useState<boolean>(true);
  const [symbolType, setSymbolType] = useState<string>("");
  const [filePattern, setFilePattern] = useState<string>("");
  const [showAdvancedFilters, setShowAdvancedFilters] = useState<boolean>(false);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadRepositories();
  }, []);

  // Keyboard shortcut to focus search bar
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "/" && document.activeElement !== searchInputRef.current) {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  async function loadRepositories() {
    try {
      const repos = await api.listRepositories();
      setRepositories(repos);
      if (repos.length > 0) {
        setSelectedRepoId(repos[0].id);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load repositories");
    }
  }

  async function handleSearch(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!selectedRepoId || !query.trim()) return;

    try {
      setLoading(true);
      setError(null);
      const res = await api.searchRepository(selectedRepoId, {
        query: query.trim(),
        mode,
        top_k: topK,
        rerank,
        symbol_type: symbolType || undefined,
        file_pattern: filePattern || undefined,
      });
      setSearchResponse(res);
    } catch (err: any) {
      setError(err.message || "Search failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 font-sans">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-border gap-4">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-brand-sky mb-1 flex items-center space-x-1.5">
            <Sparkles className="h-3.5 w-3.5" />
            <span>AST Lexical &amp; Vector Dual Retrieval</span>
          </div>
          <h1 className="text-2xl font-black uppercase tracking-tight text-white font-sans">
            Code Search &amp; Discovery Engine
          </h1>
          <p className="mt-1 text-xs text-slate-400 font-mono">
            Execute hybrid BM25 + Qdrant 768-d vector search with Reciprocal Rank Fusion ($k=60$) and FlashRank TinyBERT cross-encoder reranking.
          </p>
        </div>

        {/* Repository Selector */}
        <select
          value={selectedRepoId}
          onChange={(e) => setSelectedRepoId(e.target.value)}
          className="bg-surface-300 border border-border text-slate-200 text-xs rounded-lg px-3.5 py-2 font-mono focus:border-brand-sky focus:outline-none shadow-sm"
        >
          {repositories.map((repo) => (
            <option key={repo.id} value={repo.id}>
              {repo.full_name || repo.name} ({repo.default_branch})
            </option>
          ))}
        </select>
      </div>

      {/* Main Search Command Console */}
      <form onSubmit={handleSearch} className="space-y-4">
        {/* Large Search Bar */}
        <div className="relative">
          <Search className="h-5 w-5 absolute left-4 top-3.5 text-brand-sky" />
          <input
            ref={searchInputRef}
            type="text"
            placeholder="Search code by symbol, identifier, or natural language query (e.g. 'verify_jwt_token', 'dispatch_request', 'handle incoming webhook')..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-surface-200 border border-border rounded-xl pl-12 pr-32 py-3.5 text-sm font-mono text-slate-100 placeholder-slate-500 focus:border-brand-sky focus:outline-none focus:ring-1 focus:ring-brand-sky transition shadow-inner"
          />
          <div className="absolute right-2.5 top-2 flex items-center space-x-2">
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="px-4 py-1.5 bg-brand-sky hover:bg-brand-skyHover text-slate-950 font-extrabold rounded-lg text-xs font-mono disabled:opacity-50 transition flex items-center space-x-1.5 shadow-sm active:scale-95"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
              <span>{loading ? "Searching..." : "Search"}</span>
            </button>
          </div>
        </div>

        {/* Retrieval Mode Toolbar */}
        <div className="p-4 rounded-xl border border-border bg-surface-200 flex flex-wrap items-center justify-between gap-4 text-xs font-mono">
          {/* Mode Selector Tabs */}
          <div className="flex items-center space-x-1 bg-surface-300 p-1 rounded-lg border border-border">
            <button
              type="button"
              onClick={() => setMode("hybrid")}
              className={`px-3 py-1.5 rounded-md transition ${
                mode === "hybrid"
                  ? "bg-surface-100 text-brand-sky font-bold border border-border shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Hybrid (RRF + Reranker)
            </button>
            <button
              type="button"
              onClick={() => setMode("lexical")}
              className={`px-3 py-1.5 rounded-md transition ${
                mode === "lexical"
                  ? "bg-surface-100 text-brand-sky font-bold border border-border shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Lexical (BM25 Okapi)
            </button>
            <button
              type="button"
              onClick={() => setMode("semantic")}
              className={`px-3 py-1.5 rounded-md transition ${
                mode === "semantic"
                  ? "bg-surface-100 text-brand-sky font-bold border border-border shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Semantic (Qdrant Vector)
            </button>
          </div>

          {/* Quick Filters */}
          <div className="flex items-center space-x-3">
            <label className="flex items-center space-x-2 cursor-pointer select-none text-slate-300">
              <input
                type="checkbox"
                checked={rerank}
                onChange={(e) => setRerank(e.target.checked)}
                className="rounded border-border bg-surface-300 text-brand-sky focus:ring-0"
              />
              <span className="text-[11px]">Cross-Encoder Rerank</span>
            </label>

            <div className="flex items-center space-x-1.5 text-slate-400 text-[11px]">
              <span>Top K:</span>
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="bg-surface-300 border border-border text-slate-200 rounded px-2 py-1 focus:border-brand-sky focus:outline-none text-[11px]"
              >
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={30}>30</option>
                <option value={50}>50</option>
              </select>
            </div>

            <button
              type="button"
              onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
              className={`p-1.5 rounded-lg border text-slate-400 hover:text-white transition flex items-center space-x-1 ${
                showAdvancedFilters ? "bg-surface-100 border-brand-sky/40 text-brand-sky" : "bg-surface-300 border-border"
              }`}
              title="Toggle Advanced Filters"
            >
              <Filter className="h-3.5 w-3.5" />
              <span className="text-[11px]">Filters</span>
            </button>
          </div>
        </div>

        {/* Advanced Filters Drawer */}
        {showAdvancedFilters && (
          <div className="p-4 rounded-xl border border-border bg-surface-300 grid grid-cols-1 sm:grid-cols-2 gap-4 font-mono text-xs animate-fade-in">
            <div>
              <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1.5">
                AST Symbol Type Filter
              </label>
              <select
                value={symbolType}
                onChange={(e) => setSymbolType(e.target.value)}
                className="w-full bg-surface-200 border border-border text-slate-200 rounded-lg px-3 py-2 focus:border-brand-sky focus:outline-none"
              >
                <option value="">All Symbol Types (Classes, Functions, Endpoints, Models)</option>
                <option value="FUNCTION">FUNCTION</option>
                <option value="METHOD">METHOD</option>
                <option value="CLASS">CLASS</option>
                <option value="MODEL">MODEL</option>
                <option value="ENDPOINT">ENDPOINT</option>
                <option value="INTERFACE">INTERFACE</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1.5">
                File Path Glob Pattern (Optional)
              </label>
              <input
                type="text"
                placeholder="e.g. src/flask/**, apps/api/**, *.py"
                value={filePattern}
                onChange={(e) => setFilePattern(e.target.value)}
                className="w-full bg-surface-200 border border-border text-slate-200 rounded-lg px-3 py-2 focus:border-brand-sky focus:outline-none placeholder-slate-600"
              />
            </div>
          </div>
        )}
      </form>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-400 text-xs font-mono flex items-center space-x-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && (
        <div className="space-y-4">
          <div className="p-6 rounded-xl border border-border bg-surface-200 animate-pulse space-y-4">
            <div className="h-4 bg-surface-100 rounded w-1/3"></div>
            <div className="h-3 bg-surface-100 rounded w-1/4"></div>
            <div className="h-24 bg-surface-300 rounded"></div>
          </div>
          <div className="p-6 rounded-xl border border-border bg-surface-200 animate-pulse space-y-4">
            <div className="h-4 bg-surface-100 rounded w-2/5"></div>
            <div className="h-3 bg-surface-100 rounded w-1/3"></div>
            <div className="h-24 bg-surface-300 rounded"></div>
          </div>
        </div>
      )}

      {/* Search Stats Bar */}
      {searchResponse && !loading && (
        <div className="flex items-center justify-between text-xs font-mono text-slate-400 border-b border-border pb-3">
          <div className="flex items-center space-x-3">
            <span>
              Retrieved <strong className="text-white">{searchResponse.results.length}</strong> top chunks from {searchResponse.total_candidates} candidates
            </span>
            <span>•</span>
            <span className="text-brand-sky font-bold flex items-center space-x-1">
              <Clock className="h-3.5 w-3.5" />
              <span>{searchResponse.execution_time_ms} ms latency</span>
            </span>
          </div>
          <span className="uppercase px-2.5 py-0.5 rounded bg-surface-300 text-slate-300 border border-border text-[10px] font-bold">
            Mode: {searchResponse.mode}
          </span>
        </div>
      )}

      {/* Results List */}
      {!loading && (
        <div className="space-y-5">
          {searchResponse && searchResponse.results.length === 0 && (
            <div className="p-12 text-center text-slate-400 font-mono text-xs rounded-xl border border-border bg-surface-200/50 space-y-2">
              <p className="font-bold text-white">No matching code chunks found.</p>
              <p className="text-slate-500">Try broadening your query tokens or switching retrieval mode to Hybrid.</p>
            </div>
          )}

          {searchResponse?.results.map((hit, idx) => (
            <div
              key={hit.chunk_id || idx}
              className="p-5 rounded-xl border border-border bg-surface-200 space-y-3.5 hover:border-border-strong transition-all shadow-sm"
            >
              {/* Result Card Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/80 pb-3 font-mono">
                <div className="flex items-center space-x-2.5 truncate">
                  <span className="text-xs font-bold text-brand-sky">#{idx + 1}</span>
                  <FileCode className="h-4 w-4 text-brand-sky flex-shrink-0" />
                  <span className="text-xs text-white font-bold truncate">{hit.file_path}</span>
                  <span className="text-xs text-slate-500">
                    :L{hit.start_line}-{hit.end_line}
                  </span>
                </div>

                <div className="flex items-center space-x-2 text-xs flex-shrink-0">
                  {hit.symbol_name && (
                    <span className="text-xs text-brand-sky font-semibold px-2 py-0.5 rounded bg-surface-300 border border-border">
                      {hit.symbol_name}
                    </span>
                  )}
                  {hit.symbol_type && (
                    <StatusBadge type="nodeType" value={hit.symbol_type} size="sm" />
                  )}
                  <div className="px-2 py-0.5 rounded bg-brand-sky/10 text-brand-sky border border-brand-sky/30 text-[10px] font-bold">
                    Score: {hit.score.toFixed(4)}
                  </div>
                </div>
              </div>

              {/* Score Breakdown Pills */}
              <div className="flex flex-wrap gap-2 text-[10px] font-mono">
                {hit.rrf_score !== undefined && hit.rrf_score !== null && (
                  <span className="px-2 py-0.5 rounded bg-surface-300 border border-border text-slate-300">
                    RRF Fusion: <strong className="text-white">{hit.rrf_score.toFixed(6)}</strong>
                  </span>
                )}
                {hit.lexical_score !== undefined && hit.lexical_score !== null && (
                  <span className="px-2 py-0.5 rounded bg-surface-300 border border-border text-slate-300">
                    BM25 Lexical: <strong className="text-white">{hit.lexical_score.toFixed(3)}</strong>
                  </span>
                )}
                {hit.vector_score !== undefined && hit.vector_score !== null && (
                  <span className="px-2 py-0.5 rounded bg-surface-300 border border-border text-slate-300">
                    Vector Cosine: <strong className="text-white">{hit.vector_score.toFixed(3)}</strong>
                  </span>
                )}
                {hit.rerank_score !== undefined && hit.rerank_score !== null && (
                  <span className="px-2 py-0.5 rounded bg-brand-indigo/10 text-brand-indigo border border-brand-indigo/30 font-bold">
                    Reranker (TinyBERT): {hit.rerank_score.toFixed(4)}
                  </span>
                )}
              </div>

              {/* Syntax-Highlighted Code Preview */}
              <CodeViewer
                code={hit.content}
                filePath={hit.file_path}
                startLine={hit.start_line}
                endLine={hit.end_line}
                symbolName={hit.symbol_name}
                symbolType={hit.symbol_type}
                maxHeight="max-h-72"
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

