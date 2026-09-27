"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  MessageSquare,
  Network,
  GitBranch,
  Activity,
  FileCode,
  ShieldCheck,
  BarChart3,
  Settings,
  ArrowRight,
  Sparkles,
} from "lucide-react";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  currentRepoName?: string;
}

export function CommandPalette({ isOpen, onClose, currentRepoName }: CommandPaletteProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");

  const commands = [
    {
      label: "Dual Hybrid Code Search",
      description: "BM25 lexical + Qdrant 768-d vector search with cross-encoder reranking",
      href: "/dashboard/search",
      icon: Search,
      category: "Code Intelligence",
      shortcut: "S",
    },
    {
      label: "Grounded AI Chat",
      description: "Ask codebase questions with line-level verified citation gate",
      href: "/dashboard/chat",
      icon: MessageSquare,
      category: "AI & RAG",
      shortcut: "C",
    },
    {
      label: "Dependency Graph Topology",
      description: "Interactive AST graph with caller/callee inspection",
      href: "/dashboard/graph?tab=topology",
      icon: Network,
      category: "Graph Engine",
      shortcut: "G",
    },
    {
      label: "Blast Radius & Impact Analysis",
      description: "Calculate ripple effect, affected routes, and severity score",
      href: "/dashboard/graph?tab=impact",
      icon: Activity,
      category: "Graph Engine",
      shortcut: "B",
    },
    {
      label: "Shortest Execution Call Path",
      description: "Dijkstra directed call chain between two functions or endpoints",
      href: "/dashboard/graph?tab=path",
      icon: GitBranch,
      category: "Graph Engine",
      shortcut: "P",
    },
    {
      label: "Architectural Cycles (Tarjan SCC)",
      description: "Detect strongly connected circular import and call cycles",
      href: "/dashboard/graph?tab=cycles",
      icon: Network,
      category: "Architecture",
      shortcut: "Y",
    },
    {
      label: "AST Code Explorer",
      description: "Browse parsed repository files and AST symbol registry",
      href: "/dashboard/explorer",
      icon: FileCode,
      category: "Code Intelligence",
      shortcut: "E",
    },
    {
      label: "Repository Management",
      description: "Connect GitHub repos and trigger background Celery indexing",
      href: "/dashboard/repositories",
      icon: GitBranch,
      category: "Workspace",
      shortcut: "R",
    },
    {
      label: "Telemetry & Analytics",
      description: "Retrieval evaluation, Recall@K, and Prometheus telemetry",
      href: "/dashboard/analytics",
      icon: BarChart3,
      category: "Observability",
      shortcut: "A",
    },
    {
      label: "Multi-Tenant Security",
      description: "Inspect zero-leak tenant isolation and audit logs",
      href: "/dashboard/security",
      icon: ShieldCheck,
      category: "Security",
      shortcut: "X",
    },
    {
      label: "Workspace Settings",
      description: "API keys, model providers, and environment configuration",
      href: "/dashboard/settings",
      icon: Settings,
      category: "Settings",
      shortcut: ",",
    },
  ];

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        if (isOpen) onClose();
        else {
          // Open
          setQuery("");
        }
      }
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const filtered = commands.filter(
    (c) =>
      c.label.toLowerCase().includes(query.toLowerCase()) ||
      c.description.toLowerCase().includes(query.toLowerCase()) ||
      c.category.toLowerCase().includes(query.toLowerCase())
  );

  const handleSelect = (href: string) => {
    onClose();
    router.push(href);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-start justify-center pt-24 px-4 animate-fade-in font-sans">
      <div
        className="w-full max-w-2xl bg-surface-200 border border-border rounded-xl shadow-2xl overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input */}
        <div className="p-4 border-b border-border flex items-center space-x-3 bg-surface-300">
          <Search className="h-5 w-5 text-brand-sky flex-shrink-0" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`Jump to feature, tool, or analysis in ${currentRepoName || "CodeAtlas"}...`}
            className="flex-1 bg-transparent text-sm text-slate-100 placeholder-slate-500 font-mono outline-none"
          />
          <kbd className="kbd-badge">ESC</kbd>
        </div>

        {/* Results List */}
        <div className="max-h-96 overflow-y-auto p-2 space-y-1">
          {filtered.length === 0 ? (
            <div className="p-8 text-center text-xs font-mono text-slate-500">
              No matching commands or tools found for &quot;{query}&quot;
            </div>
          ) : (
            filtered.map((item, idx) => {
              const Icon = item.icon;
              return (
                <div
                  key={idx}
                  onClick={() => handleSelect(item.href)}
                  className="p-3 rounded-lg border border-transparent hover:border-border hover:bg-surface-100/80 cursor-pointer flex items-center justify-between group transition-colors"
                >
                  <div className="flex items-center space-x-3 min-w-0 pr-3">
                    <div className="h-8 w-8 rounded-lg bg-surface-300 border border-border flex items-center justify-center text-brand-sky group-hover:text-white group-hover:border-brand-sky/50 transition-colors flex-shrink-0">
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-bold text-slate-200 group-hover:text-white font-mono">
                          {item.label}
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-300 text-slate-400 border border-border/60">
                          {item.category}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 truncate mt-0.5 font-sans">
                        {item.description}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2 flex-shrink-0">
                    <kbd className="kbd-badge opacity-0 group-hover:opacity-100 transition-opacity">
                      {item.shortcut}
                    </kbd>
                    <ArrowRight className="h-3.5 w-3.5 text-slate-500 group-hover:text-brand-sky transition-colors" />
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="p-2.5 px-4 bg-surface-300 border-t border-border flex items-center justify-between text-[11px] font-mono text-slate-500">
          <div className="flex items-center space-x-3">
            <span>Navigation: <kbd className="kbd-badge">↑</kbd> <kbd className="kbd-badge">↓</kbd></span>
            <span>Select: <kbd className="kbd-badge">↵</kbd></span>
          </div>
          <span className="text-brand-sky font-semibold">CodeAtlas Core Platform</span>
        </div>
      </div>
    </div>
  );
}
