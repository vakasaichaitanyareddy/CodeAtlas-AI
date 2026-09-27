"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Repository } from "@/types";
import { StatusBadge } from "@/components/StatusBadge";
import {
  GitBranch,
  Plus,
  Trash2,
  ExternalLink,
  ShieldCheck,
  ShieldAlert,
  Clock,
  Loader2,
  CheckCircle2,
  AlertCircle,
  FolderGit2,
  Network,
  ArrowRight,
  Search,
  MessageSquare,
  Activity,
  Layers,
} from "lucide-react";

export default function RepositoriesPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [indexingId, setIndexingId] = useState<string | null>(null);

  // New repo form state
  const [showModal, setShowModal] = useState(false);
  const [githubUrl, setGithubUrl] = useState("");
  const [defaultBranch, setDefaultBranch] = useState("main");
  const [isPrivate, setIsPrivate] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);

  const fetchRepositories = async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const data = await api.listRepositories();
      setRepositories(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load repositories";
      if (!silent) setError(msg);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchRepositories();
  }, []);

  // Auto-polling when any repository is PENDING, QUEUED, CLONING, PARSING, or INDEXING
  useEffect(() => {
    const hasActiveJob = repositories.some((r) =>
      ["PENDING", "QUEUED", "CLONING", "PARSING", "INDEXING"].includes(r.status)
    );

    if (hasActiveJob) {
      pollTimerRef.current = setInterval(() => {
        fetchRepositories(true);
      }, 3000);
    } else {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    }

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [repositories]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);

    try {
      const newRepo = await api.createRepository(githubUrl, defaultBranch, isPrivate);
      setShowModal(false);
      setGithubUrl("");
      setDefaultBranch("main");
      setIsPrivate(false);

      // Automatically trigger background indexing for seamless UX
      try {
        await api.triggerIndexing(newRepo.id);
      } catch (triggerErr) {
        console.warn("Auto-index trigger deferred:", triggerErr);
      }

      await fetchRepositories();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create repository";
      setFormError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleTriggerIndex = async (id: string) => {
    setIndexingId(id);
    try {
      await api.triggerIndexing(id);
      setRepositories((prev) =>
        prev.map((r) => (r.id === id ? { ...r, status: "INDEXING" } : r))
      );
      await fetchRepositories(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to trigger indexing";
      alert(msg);
    } finally {
      setIndexingId(null);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to disconnect repository "${name}"? All parsed AST symbols and graph nodes will be permanently removed.`)) {
      return;
    }

    try {
      await api.deleteRepository(id);
      setRepositories((prev) => prev.filter((r) => r.id !== id));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to delete repository");
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-border gap-4">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-brand-crimson mb-1">
            // Repository Hub
          </div>
          <h1 className="text-2xl font-black uppercase tracking-tight text-white font-sans">
            Indexed Repositories
          </h1>
          <p className="mt-1 text-xs text-slate-400 font-mono">
            Connect Git repositories for AST symbol parsing, Tarjan SCC dependency graphs, and vector indexing.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="flex items-center space-x-2 px-4 py-2.5 bg-brand-crimson hover:bg-brand-crimsonHover text-white font-mono text-xs uppercase font-bold tracking-wider transition-all shadow-md shadow-brand-crimson/20 active:scale-95 rounded-lg"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>Connect Repository</span>
        </button>
      </div>

      {/* Error notification */}
      {error && (
        <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-xs text-rose-400 font-mono flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => fetchRepositories()}
            className="text-xs underline hover:text-white ml-4 font-mono font-bold"
          >
            Retry
          </button>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="p-16 text-center border border-border bg-surface-200/50 rounded-xl">
          <Loader2 className="h-6 w-6 text-brand-sky animate-spin mx-auto mb-3" />
          <p className="text-xs text-slate-400 font-mono">Querying repository registry...</p>
        </div>
      ) : repositories.length === 0 ? (
        <div className="p-16 text-center border border-dashed border-border bg-surface-200/40 space-y-4 rounded-xl">
          <div className="h-12 w-12 rounded-xl bg-surface-100 border border-border flex items-center justify-center text-brand-crimson mx-auto">
            <FolderGit2 className="h-6 w-6" />
          </div>
          <div className="max-w-md mx-auto">
            <h3 className="text-base font-bold text-white uppercase font-sans">No Repositories Connected</h3>
            <p className="mt-1.5 text-xs text-slate-400 font-mono leading-relaxed">
              Connect a GitHub repository to begin AST symbol indexing, dependency graph extraction, and repository-level AI queries.
            </p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="mt-4 inline-flex items-center space-x-2 px-5 py-2.5 bg-brand-crimson hover:bg-brand-crimsonHover text-white font-mono text-xs uppercase font-bold tracking-wider transition-all shadow-md rounded-lg"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Connect First Repository</span>
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {repositories.map((repo) => {
            const isProcessing =
              indexingId === repo.id ||
              ["INDEXING", "CLONING", "PARSING", "QUEUED"].includes(repo.status);
            const isIndexed = repo.status === "ACTIVE" || repo.status === "INDEXED";

            return (
              <div
                key={repo.id}
                className="p-6 rounded-xl border border-border bg-surface-200 shadow-sm space-y-4 hover:border-border-strong transition-all"
              >
                {/* Top Row: Details & Status */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/80 pb-4">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-3">
                      <a
                        href={repo.github_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-base font-bold text-white hover:text-brand-sky flex items-center space-x-2 group font-mono transition-colors"
                      >
                        <span>{repo.full_name || repo.name}</span>
                        <ExternalLink className="h-3.5 w-3.5 text-slate-500 group-hover:text-brand-sky" />
                      </a>
                      <StatusBadge type="status" value={repo.status} />
                      {repo.is_private ? (
                        <span className="inline-flex items-center space-x-1 text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/25 font-semibold">
                          <ShieldAlert className="h-3 w-3" />
                          <span>PRIVATE REPO</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1 text-[10px] font-mono px-2 py-0.5 rounded bg-surface-300 text-slate-400 border border-border font-semibold">
                          <ShieldCheck className="h-3 w-3" />
                          <span>PUBLIC REPO</span>
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 font-mono">
                      <span className="flex items-center space-x-1 text-slate-300">
                        <GitBranch className="h-3.5 w-3.5 text-brand-sky" />
                        <span>{repo.default_branch}</span>
                      </span>
                      <span>•</span>
                      <span>UUID: <code className="text-slate-200">{repo.id.slice(0, 8)}...</code></span>
                      <span>•</span>
                      <span>Added {new Date(repo.created_at).toLocaleDateString()}</span>
                      {repo.current_commit_sha && (
                        <>
                          <span>•</span>
                          <span>Commit: <code className="text-brand-sky">{repo.current_commit_sha.slice(0, 7)}</code></span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Actions: Index / Delete */}
                  <div className="flex items-center space-x-2.5 flex-shrink-0">
                    <button
                      onClick={() => handleTriggerIndex(repo.id)}
                      disabled={isProcessing}
                      className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono uppercase font-bold tracking-wider transition ${
                        !isIndexed
                          ? "bg-brand-crimson hover:bg-brand-crimsonHover text-white border-brand-crimson/50 shadow-sm"
                          : "border-border bg-surface-300 hover:bg-surface-100 text-slate-300 hover:text-white"
                      }`}
                    >
                      {isProcessing ? (
                        <>
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          <span>INDEXING...</span>
                        </>
                      ) : (
                        <>
                          <Activity className="h-3.5 w-3.5" />
                          <span>{isIndexed ? "RE-INDEX" : "INDEX NOW"}</span>
                        </>
                      )}
                    </button>

                    <button
                      onClick={() => handleDelete(repo.id, repo.name)}
                      title="Disconnect Repository"
                      className="p-2 rounded-lg border border-border bg-surface-300 text-slate-500 hover:text-brand-crimson hover:border-brand-crimson/30 transition-colors"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {/* Central Hub Navigation Bar for this Repository */}
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-2">
                    // Workspace Analysis Hub
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 font-mono text-xs">
                    <Link
                      href="/dashboard/search"
                      className="p-2.5 rounded-lg border border-border bg-surface-300 hover:bg-surface-100 hover:border-brand-sky/40 transition flex items-center space-x-2 text-slate-300 hover:text-white group"
                    >
                      <Search className="h-3.5 w-3.5 text-brand-sky group-hover:scale-110 transition-transform" />
                      <span className="truncate">Search Code</span>
                    </Link>
                    <Link
                      href="/dashboard/chat"
                      className="p-2.5 rounded-lg border border-border bg-surface-300 hover:bg-surface-100 hover:border-brand-sky/40 transition flex items-center space-x-2 text-slate-300 hover:text-white group"
                    >
                      <MessageSquare className="h-3.5 w-3.5 text-brand-sky group-hover:scale-110 transition-transform" />
                      <span className="truncate">Grounded Chat</span>
                    </Link>
                    <Link
                      href="/dashboard/graph?tab=topology"
                      className="p-2.5 rounded-lg border border-border bg-surface-300 hover:bg-surface-100 hover:border-brand-indigo/40 transition flex items-center space-x-2 text-slate-300 hover:text-white group"
                    >
                      <Network className="h-3.5 w-3.5 text-brand-indigo group-hover:scale-110 transition-transform" />
                      <span className="truncate">Dependency Graph</span>
                    </Link>
                    <Link
                      href="/dashboard/graph?tab=impact"
                      className="p-2.5 rounded-lg border border-border bg-surface-300 hover:bg-surface-100 hover:border-brand-amber/40 transition flex items-center space-x-2 text-slate-300 hover:text-white group"
                    >
                      <Activity className="h-3.5 w-3.5 text-brand-amber group-hover:scale-110 transition-transform" />
                      <span className="truncate">Blast Radius</span>
                    </Link>
                    <Link
                      href="/dashboard/graph?tab=path"
                      className="p-2.5 rounded-lg border border-border bg-surface-300 hover:bg-surface-100 hover:border-brand-sky/40 transition flex items-center space-x-2 text-slate-300 hover:text-white group"
                    >
                      <GitBranch className="h-3.5 w-3.5 text-brand-sky group-hover:scale-110 transition-transform" />
                      <span className="truncate">Call Path</span>
                    </Link>
                    <Link
                      href="/dashboard/graph?tab=cycles"
                      className="p-2.5 rounded-lg border border-border bg-surface-300 hover:bg-surface-100 hover:border-brand-crimson/40 transition flex items-center space-x-2 text-slate-300 hover:text-white group"
                    >
                      <ShieldAlert className="h-3.5 w-3.5 text-brand-crimson group-hover:scale-110 transition-transform" />
                      <span className="truncate">Cycles</span>
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Connect Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-surface-200 border border-border rounded-xl p-6 shadow-2xl space-y-5 font-mono">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h2 className="text-sm font-bold uppercase tracking-wider text-white">Connect GitHub Repository</h2>
              <button
                onClick={() => setShowModal(false)}
                className="text-xs text-slate-500 hover:text-white"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded-lg border border-rose-500/30 bg-rose-500/10 text-xs text-rose-400">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-[11px] text-slate-300 uppercase tracking-wider mb-1.5">
                  GitHub Repository URL
                </label>
                <input
                  type="url"
                  required
                  placeholder="https://github.com/organization/repo"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  className="w-full px-3 py-2.5 bg-surface-300 border border-border rounded-lg text-xs text-white placeholder-slate-600 focus:outline-none focus:border-brand-sky"
                />
              </div>

              <div>
                <label className="block text-[11px] text-slate-300 uppercase tracking-wider mb-1.5">
                  Default Branch
                </label>
                <input
                  type="text"
                  required
                  placeholder="main"
                  value={defaultBranch}
                  onChange={(e) => setDefaultBranch(e.target.value)}
                  className="w-full px-3 py-2.5 bg-surface-300 border border-border rounded-lg text-xs text-white placeholder-slate-600 focus:outline-none focus:border-brand-sky"
                />
              </div>

              <div className="flex items-center space-x-2 pt-1">
                <input
                  type="checkbox"
                  id="is_private"
                  checked={isPrivate}
                  onChange={(e) => setIsPrivate(e.target.checked)}
                  className="rounded border-border bg-surface-300 text-brand-sky focus:ring-0"
                />
                <label htmlFor="is_private" className="text-xs text-slate-400 select-none font-sans">
                  Private repository
                </label>
              </div>

              <div className="pt-3 flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 border border-border rounded-lg text-slate-400 hover:text-white text-xs uppercase"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center space-x-2 px-5 py-2.5 bg-brand-crimson hover:bg-brand-crimsonHover disabled:opacity-50 text-white text-xs uppercase font-extrabold tracking-wider rounded-lg shadow-md"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      <span>Connecting &amp; Indexing...</span>
                    </>
                  ) : (
                    <span>Add &amp; Index Repository</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

