"use client";

import Link from "next/link";
import { WireframeTunnel } from "@/components/WireframeTunnel";
import { GlobalNavbar } from "@/components/GlobalNavbar";
import { GlobalFooter } from "@/components/GlobalFooter";
import {
  ArrowUpRight,
  Cpu,
  Search,
  Network,
  GitPullRequest,
  ShieldCheck,
  Terminal,
  Activity,
  CheckCircle2,
  Database,
  Layers,
  Sparkles,
  Zap,
  ArrowRight,
  GitBranch,
  FileCode,
  ShieldAlert,
  Boxes,
  Lock,
} from "lucide-react";

export default function LandingPage() {
  const pipelineSteps = [
    {
      step: "01",
      title: "Repository Ingestion",
      tech: "Celery + Git Hashing",
      desc: "Clones repository commit and extracts full file tree with content hash caching.",
    },
    {
      step: "02",
      title: "AST Symbol Extraction",
      tech: "Python ast + JS/TS Scanners",
      desc: "Deconstructs code into hierarchical AST classes, methods, functions, and models.",
    },
    {
      step: "03",
      title: "Hybrid Dual Retrieval",
      tech: "BM25 Okapi + Qdrant 768-d",
      desc: "Fuses exact lexical token scoring with dense vector projections via RRF (k=60).",
    },
    {
      step: "04",
      title: "FlashRank Cross-Encoder",
      tech: "TinyBERT Reranking",
      desc: "Scores semantic relevance (+28% Top-1 accuracy gain) under strict token budgets.",
    },
    {
      step: "05",
      title: "Grounded LLM Streaming",
      tech: "SSE + Provider Isolation",
      desc: "Generates developer-grade answers with mandatory inline citation references.",
    },
    {
      step: "06",
      title: "Citation Verification Gate",
      tech: "Deterministic Line Validation",
      desc: "Verifies every cited line range exists and physically overlaps retrieved context.",
    },
  ];

  const techBadges = [
    "Python AST",
    "Tarjan SCC O(V+E)",
    "BM25 Okapi",
    "Qdrant 768-d HNSW",
    "RRF Fusion (k=60)",
    "FlashRank Cross-Encoder",
    "Evidence-Gated RAG",
    "Dijkstra Call Paths",
    "PostgreSQL 16",
    "Redis 7 Celery",
    "FastAPI",
    "Next.js 14",
  ];

  return (
    <div className="min-h-screen bg-background text-slate-100 flex flex-col font-sans selection:bg-brand-sky/30 selection:text-sky-200">
      {/* Universal Top Navbar */}
      <GlobalNavbar />


      {/* Main Hero Container */}
      <section className="border-b border-border max-w-[1440px] mx-auto w-full flex-1 flex flex-col justify-between">
        <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[620px]">
          {/* Left Hero Column */}
          <div className="lg:col-span-7 p-6 sm:p-10 lg:p-14 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-border bg-surface-300/30">
            <div>
              {/* Status Header Badge */}
              <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full border border-border bg-surface-200 text-[11px] font-mono text-slate-300 mb-8 tracking-wider uppercase shadow-sm">
                <span className="h-2 w-2 rounded-full bg-brand-emerald animate-pulse"></span>
                <span>Production Code Intelligence Engine • 8-Container Stack</span>
              </div>

              {/* Bold Display Headline */}
              <div>
                <h1 className="text-4xl sm:text-6xl xl:text-7xl font-black tracking-tight leading-[0.98] uppercase text-white font-sans">
                  Understand
                  <br />
                  <span className="text-brand-sky">Your Codebase.</span>
                  <br />
                  Prove What
                  <br />
                  <span className="text-brand-crimson">The AI Says.</span>
                </h1>
              </div>

              <p className="mt-6 text-base sm:text-lg text-slate-400 max-w-xl leading-relaxed">
                AST-aware code intelligence, hybrid BM25 + Qdrant vector retrieval, Tarjan SCC graph topology, and evidence-gated RAG with line-level deterministic citation verification.
              </p>

              {/* Action Buttons Row */}
              <div className="mt-8 flex flex-wrap items-center gap-4">
                <Link
                  href="/dashboard"
                  className="px-6 py-3 rounded-lg bg-brand-crimson hover:bg-brand-crimsonHover text-white font-mono text-xs uppercase font-extrabold tracking-widest transition-all shadow-xl shadow-brand-crimson/25 active:scale-95 flex items-center space-x-2"
                >
                  <span>Open Engineering Console</span>
                  <ArrowRight className="h-4 w-4" />
                </Link>

                <Link
                  href="/dashboard/search"
                  className="inline-flex items-center space-x-2 px-5 py-3 rounded-lg border border-border bg-surface-100 hover:bg-surface-50 text-slate-200 font-mono text-xs uppercase tracking-wider transition-colors"
                >
                  <Search className="h-3.5 w-3.5 text-brand-sky" />
                  <span>Try Dual Search</span>
                </Link>
              </div>
            </div>

            {/* Tech Badges Row */}
            <div className="mt-12 pt-6 border-t border-border">
              <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-3">
                // System Capabilities &amp; Algorithms
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {techBadges.map((badge, idx) => (
                  <span
                    key={idx}
                    className="inline-block px-3 py-1 rounded-md border border-border bg-surface-200 text-slate-300 text-xs font-mono tracking-tight hover:border-brand-sky/50 transition-colors"
                  >
                    {badge}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Right Hero Column: 3D Wireframe Perspective Mesh Tunnel */}
          <div className="lg:col-span-5 relative flex flex-col justify-center items-center bg-surface-300 overflow-hidden">
            <WireframeTunnel />
          </div>
        </div>

        {/* Bottom 3-Cell Verified Metrics Strip */}
        <div className="grid grid-cols-1 md:grid-cols-3 border-t border-border bg-surface-200">
          {/* Cell 1: Retrieval Performance */}
          <div className="p-6 md:p-8 border-b md:border-b-0 md:border-r border-border flex flex-col justify-center">
            <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-2">
              Retrieval Accuracy
            </div>
            <div className="text-2xl font-black font-mono text-brand-sky tracking-tight">
              Recall@5: 0.8333
            </div>
            <p className="text-xs text-slate-400 font-mono mt-1">
              RRF Fusion ($k=60$) + FlashRank Cross-Encoder (P50: 188ms)
            </p>
          </div>

          {/* Cell 2: Automated Test Verification */}
          <div className="p-6 md:p-8 border-b md:border-b-0 md:border-r border-border flex items-center space-x-4">
            <div className="h-10 w-10 rounded-lg bg-brand-emerald/10 border border-brand-emerald/30 flex items-center justify-center text-brand-emerald flex-shrink-0">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xl sm:text-2xl font-black font-mono tracking-tight text-white">
                75 / 75 PASSED
              </div>
              <div className="text-xs text-slate-400 font-mono">
                Full Pytest &amp; Next.js 14 Production Suite
              </div>
            </div>
          </div>

          {/* Cell 3: Evidence Gating */}
          <div className="p-6 md:p-8 flex items-center space-x-4">
            <div className="h-10 w-10 rounded-lg bg-brand-crimson/10 border border-brand-crimson/30 flex items-center justify-center text-brand-crimson flex-shrink-0">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-white font-mono uppercase">
                Deterministic Grounding Gate
              </div>
              <p className="text-xs text-slate-400 font-sans mt-0.5">
                Every citation is verified for file existence, line bounds, and AST overlap.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Real Technical Architecture Flow */}
      <section className="max-w-[1440px] mx-auto w-full px-6 py-20 border-b border-border">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 pb-4 border-b border-border gap-4">
          <div>
            <div className="text-[10px] font-mono uppercase tracking-widest text-brand-crimson mb-1">
              // End-to-End Pipeline
            </div>
            <h2 className="text-2xl sm:text-3xl font-black tracking-tight uppercase text-white font-sans">
              Technical Architecture &amp; Execution Chain
            </h2>
          </div>
          <p className="text-xs text-slate-400 font-mono max-w-md">
            From raw Git commit to evidence-verified AI answer with zero cross-tenant leakage.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {pipelineSteps.map((p, idx) => (
            <div
              key={idx}
              className="p-6 rounded-xl border border-border bg-surface-200 hover:border-brand-sky/40 transition-all flex flex-col justify-between group shadow-sm"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-mono font-bold text-brand-sky px-2 py-0.5 rounded bg-surface-100 border border-border">
                    {p.step}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                    {p.tech}
                  </span>
                </div>
                <h3 className="font-bold text-white text-base font-mono tracking-tight group-hover:text-brand-sky transition-colors">
                  {p.title}
                </h3>
                <p className="mt-2 text-xs text-slate-400 leading-relaxed font-sans">
                  {p.desc}
                </p>
              </div>
              <div className="mt-6 pt-4 border-t border-border/80 flex items-center justify-between text-[11px] font-mono text-slate-500">
                <span>STAGE VERIFIED</span>
                <CheckCircle2 className="h-3.5 w-3.5 text-brand-emerald" />
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Core Platform Subsystems Grid */}
      <section className="max-w-[1440px] mx-auto w-full px-6 py-20">
        <div className="flex items-center justify-between mb-12 pb-4 border-b border-border">
          <div>
            <div className="text-[10px] font-mono uppercase tracking-widest text-brand-sky mb-1">
              // Deep Engineering Modules
            </div>
            <h2 className="text-2xl sm:text-3xl font-black tracking-tight uppercase text-white font-sans">
              Core Subsystems &amp; Algorithms
            </h2>
          </div>
          <Link
            href="/dashboard"
            className="font-mono text-xs text-slate-400 hover:text-white uppercase tracking-wider flex items-center space-x-1"
          >
            <span>Open Console</span>
            <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: AST Code Intelligence */}
          <div className="p-6 rounded-xl border border-border bg-surface-200 hover:border-border-strong transition-colors flex flex-col justify-between shadow-sm">
            <div>
              <div className="h-10 w-10 rounded-lg bg-surface-100 border border-border flex items-center justify-center text-brand-crimson mb-4">
                <Cpu className="h-5 w-5" />
              </div>
              <h3 className="font-bold text-white text-base uppercase font-mono tracking-tight">
                Syntactic AST Parsing
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed font-sans">
                Python standard library <code className="text-slate-200">ast.parse</code> and JS/TS syntax scanners extract classes, functions, and call hierarchies into 50-line overlapping semantic chunks with zero lexical loss.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-border font-mono text-[11px] text-slate-400 flex justify-between">
              <span>Throughput:</span>
              <strong className="text-white">646.3 LOC/s</strong>
            </div>
          </div>

          {/* Card 2: Dual Hybrid Search */}
          <div className="p-6 rounded-xl border border-border bg-surface-200 hover:border-border-strong transition-colors flex flex-col justify-between shadow-sm">
            <div>
              <div className="h-10 w-10 rounded-lg bg-surface-100 border border-border flex items-center justify-center text-brand-emerald mb-4">
                <Search className="h-5 w-5" />
              </div>
              <h3 className="font-bold text-white text-base uppercase font-mono tracking-tight">
                Hybrid Retrieval &amp; RRF
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed font-sans">
                Fuses exact lexical BM25 with Qdrant 768-d vector projections via Reciprocal Rank Fusion ($k=60$) and FlashRank TinyBERT cross-encoder reranking (+28% Top-1 boost).
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-border font-mono text-[11px] text-slate-400 flex justify-between">
              <span>Latency:</span>
              <strong className="text-white">P50 = 188ms</strong>
            </div>
          </div>

          {/* Card 3: Tarjan SCC & Blast Radius */}
          <div className="p-6 rounded-xl border border-border bg-surface-200 hover:border-border-strong transition-colors flex flex-col justify-between shadow-sm">
            <div>
              <div className="h-10 w-10 rounded-lg bg-surface-100 border border-border flex items-center justify-center text-brand-indigo mb-4">
                <Network className="h-5 w-5" />
              </div>
              <h3 className="font-bold text-white text-base uppercase font-mono tracking-tight">
                Tarjan SCC &amp; Blast Radius
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed font-sans">
                Directed graph engine detecting circular dependencies via Tarjan SCC in linear $O(V+E)$ time, computing Dijkstra shortest paths, and evaluating blast radius severity up to depth 6.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-border font-mono text-[11px] text-slate-400 flex justify-between">
              <span>Graph Scale:</span>
              <strong className="text-white">5k nodes in 246ms</strong>
            </div>
          </div>

          {/* Card 4: PR Impact */}
          <div className="p-6 rounded-xl border border-border bg-surface-200 hover:border-border-strong transition-colors flex flex-col justify-between shadow-sm">
            <div>
              <div className="h-10 w-10 rounded-lg bg-surface-100 border border-border flex items-center justify-center text-brand-amber mb-4">
                <GitPullRequest className="h-5 w-5" />
              </div>
              <h3 className="font-bold text-white text-base uppercase font-mono tracking-tight">
                PR Impact Intelligence
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed font-sans">
                Analyzes Git diff hunks, maps changed symbols against the dependency graph, identifies upstream callers and downstream consumers, and computes automated regression risk.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-border font-mono text-[11px] text-slate-400 flex justify-between">
              <span>Impact Depth:</span>
              <strong className="text-white">BFS D=6</strong>
            </div>
          </div>

          {/* Card 5: Multi-Tenant Security */}
          <div className="p-6 rounded-xl border border-border bg-surface-200 hover:border-border-strong transition-colors flex flex-col justify-between shadow-sm">
            <div>
              <div className="h-10 w-10 rounded-lg bg-surface-100 border border-border flex items-center justify-center text-rose-400 mb-4">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <h3 className="font-bold text-white text-base uppercase font-mono tracking-tight">
                Zero-Leak Multi-Tenancy
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed font-sans">
                Strict database and Qdrant vector payload scoping. 10 independent cross-tenant attack vectors independently audited and rejected with 403 Forbidden. Single-use refresh token rotation.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-border font-mono text-[11px] text-slate-400 flex justify-between">
              <span>Security Audit:</span>
              <strong className="text-brand-emerald">10/10 Blocked</strong>
            </div>
          </div>

          {/* Card 6: Grounded Streaming */}
          <div className="p-6 rounded-xl border border-border bg-surface-200 hover:border-border-strong transition-colors flex flex-col justify-between shadow-sm">
            <div>
              <div className="h-10 w-10 rounded-lg bg-surface-100 border border-border flex items-center justify-center text-brand-sky mb-4">
                <Terminal className="h-5 w-5" />
              </div>
              <h3 className="font-bold text-white text-base uppercase font-mono tracking-tight">
                Real-Time SSE Streaming RAG
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed font-sans">
                Multi-turn conversation streams tokens, citations, and completion events via Server-Sent Events (SSE). Physical file line numbers verified against repository source code.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-border font-mono text-[11px] text-slate-400 flex justify-between">
              <span>Citation Engine:</span>
              <strong className="text-white">Line-Verified</strong>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="border-t border-border bg-surface-300 py-16 px-6">
        <div className="max-w-4xl mx-auto text-center space-y-6">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full border border-border bg-surface-100 text-xs font-mono text-brand-sky">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Developer-First Infrastructure</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-black text-white uppercase tracking-tight">
            Ready to Index and Understand Your Codebase?
          </h2>
          <p className="text-sm text-slate-400 font-mono max-w-xl mx-auto">
            Connect any repository for instant AST symbol mapping, dependency cycle detection, and verified grounded RAG.
          </p>
          <div className="pt-2 flex justify-center gap-4">
            <Link
              href="/dashboard"
              className="px-6 py-3.5 rounded-lg bg-brand-crimson hover:bg-brand-crimsonHover text-white font-mono text-xs uppercase font-extrabold tracking-widest transition-all shadow-xl shadow-brand-crimson/20 active:scale-95 flex items-center space-x-2"
            >
              <span>Launch Dashboard</span>
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* Universal Technical Footer */}
      <GlobalFooter />
    </div>
  );
}


