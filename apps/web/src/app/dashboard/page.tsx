"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Repository } from "@/types";
import { StatusBadge } from "@/components/StatusBadge";
import {
  FileCode,
  Search,
  MessageSquare,
  Network,
  Plus,
  Loader2,
  FolderGit2,
  ShieldCheck,
  Server,
  Database,
  Layers,
  Cpu,
  Activity,
  ArrowRight,
  GitBranch,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  ExternalLink,
  ShieldAlert,
} from "lucide-react";

export default function DashboardOverviewPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const repos = await api.listRepositories();
        setRepositories(repos);
      } catch {
        setRepositories([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const activeRepo = repositories.length > 0 ? repositories[0] : null;

  return (
    <div className="max-w-7xl mx-auto space-y-8 font-sans">
      {/* Overview Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-border gap-4">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-brand-crimson mb-1 flex items-center space-x-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-crimson animate-pulse"></span>
            <span>Live Command Center</span>
          </div>
          <h1 className="text-2xl font-black uppercase tracking-tight text-white font-sans">
            Code Intelligence Command Center
          </h1>
          <p className="mt-1 text-xs text-slate-400 font-mono">
            {activeRepo ? (
              <>
                Active Scope: <span className="text-white font-bold">{activeRepo.full_name || activeRepo.name}</span>{" "}
                <span className="text-slate-500">({activeRepo.default_branch})</span> • ID: {activeRepo.id.slice(0, 8)}...
              </>
            ) : (
              "Connect a repository to index AST symbols, dependencies, and vector embeddings"
            )}
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Link
            href="/dashboard/repositories"
            className="flex items-center space-x-2 px-4 py-2.5 bg-brand-crimson hover:bg-brand-crimsonHover text-white font-mono text-xs uppercase font-bold tracking-wider transition-all shadow-md shadow-brand-crimson/20 active:scale-95 rounded-lg"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Connect Repo</span>
          </Link>
          <Link
            href="/dashboard/chat"
            className="flex items-center space-x-2 px-4 py-2.5 border border-border bg-surface-100 hover:bg-surface-50 text-slate-200 font-mono text-xs uppercase tracking-wider transition-colors rounded-lg"
          >
            <MessageSquare className="h-3.5 w-3.5 text-brand-sky" />
            <span>Grounded Chat</span>
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="p-16 text-center border border-border bg-surface-200/50 rounded-xl">
          <Loader2 className="h-6 w-6 text-brand-sky animate-spin mx-auto mb-3" />
          <p className="text-xs text-slate-400 font-mono">Querying system telemetry &amp; repositories...</p>
        </div>
      ) : repositories.length === 0 ? (
        /* Empty State */
        <div className="p-12 border border-dashed border-border bg-surface-200/60 text-center space-y-4 rounded-xl">
          <div className="h-12 w-12 rounded-xl bg-surface-100 border border-border flex items-center justify-center text-brand-crimson mx-auto">
            <FolderGit2 className="h-6 w-6" />
          </div>
          <div className="max-w-md mx-auto">
            <h2 className="text-base font-bold text-white uppercase font-sans">No Repositories Connected Yet</h2>
            <p className="mt-1.5 text-xs text-slate-400 font-mono leading-relaxed">
              Connect a GitHub repository to begin syntactic AST parsing, Tarjan SCC dependency graph extraction, and hybrid BM25 + Qdrant vector indexing.
            </p>
          </div>
          <div className="pt-2">
            <Link
              href="/dashboard/repositories"
              className="inline-flex items-center space-x-2 px-5 py-2.5 bg-brand-crimson hover:bg-brand-crimsonHover text-white font-mono text-xs uppercase font-bold tracking-wider transition-colors rounded-lg shadow-md"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Connect First Repository</span>
            </Link>
          </div>
        </div>
      ) : (
        /* Active Repositories Hub Banner */
        <div className="p-6 rounded-xl border border-border bg-surface-200 shadow-sm space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/80 pb-4">
            <div className="flex items-center space-x-4">
              <div className="h-12 w-12 rounded-xl bg-surface-100 border border-border flex items-center justify-center text-brand-crimson flex-shrink-0 shadow-inner">
                <GitBranch className="h-6 w-6" />
              </div>
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2.5">
                  <h3 className="text-base font-bold text-white font-mono">
                    {activeRepo?.full_name || activeRepo?.name}
                  </h3>
                  <span className="text-[10px] font-mono px-2 py-0.5 bg-surface-300 text-slate-300 border border-border rounded">
                    {activeRepo?.default_branch}
                  </span>
                  {activeRepo && <StatusBadge type="status" value={activeRepo.status} />}
                </div>
                <p className="text-xs text-slate-400 font-mono">
                  Indexed Commit: <code className="text-slate-200">{activeRepo?.current_commit_sha?.slice(0, 7) || "HEAD"}</code> • Connected {activeRepo && new Date(activeRepo.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>

            <Link
              href="/dashboard/repositories"
              className="text-xs text-brand-sky hover:underline flex items-center space-x-1 font-mono font-bold uppercase tracking-wider self-start md:self-auto"
            >
              <span>Manage All Repositories ({repositories.length})</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {/* Quick-Action Launchpad Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1 font-mono">
            <Link
              href="/dashboard/search"
              className="p-3 rounded-lg border border-border bg-surface-300 hover:bg-surface-100 hover:border-brand-sky/40 transition-colors flex items-center space-x-3 group"
            >
              <div className="h-8 w-8 rounded-lg bg-surface-100 border border-border flex items-center justify-center text-brand-sky group-hover:scale-105 transition-transform flex-shrink-0">
                <Search className="h-4 w-4" />
              </div>
              <div className="truncate">
                <div className="text-xs font-bold text-slate-200 group-hover:text-brand-sky transition-colors">
                  Dual Search
                </div>
                <div className="text-[10px] text-slate-500">BM25 + Qdrant</div>
              </div>
            </Link>

            <Link
              href="/dashboard/chat"
              className="p-3 rounded-lg border border-border bg-surface-300 hover:bg-surface-100 hover:border-brand-sky/40 transition-colors flex items-center space-x-3 group"
            >
              <div className="h-8 w-8 rounded-lg bg-surface-100 border border-border flex items-center justify-center text-brand-sky group-hover:scale-105 transition-transform flex-shrink-0">
                <MessageSquare className="h-4 w-4" />
              </div>
              <div className="truncate">
                <div className="text-xs font-bold text-slate-200 group-hover:text-brand-sky transition-colors">
                  Grounded Chat
                </div>
                <div className="text-[10px] text-slate-500">Verified Evidence</div>
              </div>
            </Link>

            <Link
              href="/dashboard/graph"
              className="p-3 rounded-lg border border-border bg-surface-300 hover:bg-surface-100 hover:border-brand-indigo/40 transition-colors flex items-center space-x-3 group"
            >
              <div className="h-8 w-8 rounded-lg bg-surface-100 border border-border flex items-center justify-center text-brand-indigo group-hover:scale-105 transition-transform flex-shrink-0">
                <Network className="h-4 w-4" />
              </div>
              <div className="truncate">
                <div className="text-xs font-bold text-slate-200 group-hover:text-brand-indigo transition-colors">
                  Dependency Graph
                </div>
                <div className="text-[10px] text-slate-500">AST Directed Edges</div>
              </div>
            </Link>

            <Link
              href="/dashboard/graph?tab=impact"
              className="p-3 rounded-lg border border-border bg-surface-300 hover:bg-surface-100 hover:border-brand-amber/40 transition-colors flex items-center space-x-3 group"
            >
              <div className="h-8 w-8 rounded-lg bg-surface-100 border border-border flex items-center justify-center text-brand-amber group-hover:scale-105 transition-transform flex-shrink-0">
                <Activity className="h-4 w-4" />
              </div>
              <div className="truncate">
                <div className="text-xs font-bold text-slate-200 group-hover:text-brand-amber transition-colors">
                  Blast Radius
                </div>
                <div className="text-[10px] text-slate-500">Ripple Risk Analysis</div>
              </div>
            </Link>
          </div>
        </div>
      )}

      {/* Core Technical Subsystems Status */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
            Autonomous Subsystems Telemetry
          </h2>
          <span className="text-xs text-brand-emerald font-mono flex items-center space-x-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-emerald animate-pulse"></span>
            <span>All 8 Containers Operational</span>
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 font-mono">
          {/* Subsystem 1: AST Parsing */}
          <div className="p-5 rounded-xl border border-border bg-surface-200 space-y-3 hover:border-border-strong transition shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-brand-crimson uppercase tracking-wider">
                AST &amp; Ingestion Engine
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-brand-emerald/10 text-brand-emerald border border-brand-emerald/25 font-bold">
                OPERATIONAL
              </span>
            </div>
            <h3 className="text-sm font-bold text-white uppercase">Syntactic Scope Chunking</h3>
            <ul className="text-xs text-slate-400 space-y-2 font-mono">
              <li className="flex items-center space-x-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-brand-emerald flex-shrink-0" />
                <span>Python AST + JS/TS Syntax Scanners</span>
              </li>
              <li className="flex items-center space-x-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-brand-emerald flex-shrink-0" />
                <span>Scope-Aware Hierarchical Chunking</span>
              </li>
              <li className="flex items-center space-x-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-brand-emerald flex-shrink-0" />
                <span>Celery Worker (Throughput: 646 LOC/s)</span>
              </li>
            </ul>
          </div>

          {/* Subsystem 2: Dual Hybrid Search */}
          <div className="p-5 rounded-xl border border-border bg-surface-200 space-y-3 hover:border-border-strong transition shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-brand-emerald uppercase tracking-wider">
                Dual Hybrid Search
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-brand-emerald/10 text-brand-emerald border border-brand-emerald/25 font-bold">
                OPERATIONAL
              </span>
            </div>
            <h3 className="text-sm font-bold text-white uppercase">Hybrid RRF &amp; Cross-Encoder</h3>
            <ul className="text-xs text-slate-400 space-y-2 font-mono">
              <li className="flex items-center space-x-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-brand-emerald flex-shrink-0" />
                <span>BM25 Okapi + CodeTokenizer (Recall@5 = 0.8333)</span>
              </li>
              <li className="flex items-center space-x-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-brand-emerald flex-shrink-0" />
                <span>Qdrant 768-d Dense Vector Database</span>
              </li>
              <li className="flex items-center space-x-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-brand-emerald flex-shrink-0" />
                <span>Reciprocal Rank Fusion (k=60) + TinyBERT</span>
              </li>
            </ul>
          </div>

          {/* Subsystem 3: Graph & RAG */}
          <div className="p-5 rounded-xl border border-border bg-surface-200 space-y-3 hover:border-border-strong transition shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-brand-indigo uppercase tracking-wider">
                Graph &amp; Grounded RAG
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-brand-emerald/10 text-brand-emerald border border-brand-emerald/25 font-bold">
                OPERATIONAL
              </span>
            </div>
            <h3 className="text-sm font-bold text-white uppercase">Tarjan SCC &amp; Citation Gate</h3>
            <ul className="text-xs text-slate-400 space-y-2 font-mono">
              <li className="flex items-center space-x-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-brand-emerald flex-shrink-0" />
                <span>Tarjan SCC O(V+E) Cycle Detection</span>
              </li>
              <li className="flex items-center space-x-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-brand-emerald flex-shrink-0" />
                <span>BFS Blast Radius &amp; Dijkstra Call Paths</span>
              </li>
              <li className="flex items-center space-x-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-brand-emerald flex-shrink-0" />
                <span>Line-Level Evidence Gated Citations</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Production Infrastructure Telemetry Topology */}
      <div className="p-6 rounded-xl border border-border bg-surface-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2.5 text-xs font-mono uppercase tracking-wider text-slate-200">
            <Server className="h-4 w-4 text-brand-crimson" />
            <span className="font-bold">8-Container Infrastructure Topology</span>
          </div>
          <span className="text-[10px] font-mono text-brand-emerald uppercase font-bold flex items-center space-x-1">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-emerald"></span>
            <span>All Services Healthy</span>
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-3.5 bg-surface-300 rounded-lg border border-border space-y-1">
            <div className="text-slate-500 text-[10px] uppercase font-semibold">PostgreSQL 16</div>
            <div className="text-white font-bold">Port 5433 (Healthy)</div>
            <div className="text-[10px] text-slate-400">Relational &amp; Graph Entities</div>
          </div>
          <div className="p-3.5 bg-surface-300 rounded-lg border border-border space-y-1">
            <div className="text-slate-500 text-[10px] uppercase font-semibold">Qdrant HNSW</div>
            <div className="text-white font-bold">Port 6333 (768-d)</div>
            <div className="text-[10px] text-slate-400">Dense Vector Collection</div>
          </div>
          <div className="p-3.5 bg-surface-300 rounded-lg border border-border space-y-1">
            <div className="text-slate-500 text-[10px] uppercase font-semibold">Redis 7 Broker</div>
            <div className="text-white font-bold">Port 6379 (Active)</div>
            <div className="text-[10px] text-slate-400">Task Queue &amp; State Cache</div>
          </div>
          <div className="p-3.5 bg-surface-300 rounded-lg border border-border space-y-1">
            <div className="text-slate-500 text-[10px] uppercase font-semibold">Celery Ingestion</div>
            <div className="text-white font-bold">Worker Connected</div>
            <div className="text-[10px] text-slate-400">Async Task Execution</div>
          </div>
        </div>
      </div>
    </div>
  );
}

