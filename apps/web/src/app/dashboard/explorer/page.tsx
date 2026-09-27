"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileCode,
  ArrowLeft,
  Search,
  Code2,
  FolderGit2,
  ArrowRight,
  Layers,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import { Repository, RepositoryFile, CodeSymbol, IndexJob } from "@/types";
import { StatusBadge } from "@/components/StatusBadge";
import { CodeViewer } from "@/components/CodeViewer";

export default function ExplorerPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>("");
  const [files, setFiles] = useState<RepositoryFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<RepositoryFile | null>(null);
  const [symbols, setSymbols] = useState<CodeSymbol[]>([]);
  const [symbolFilter, setSymbolFilter] = useState<string>("");
  const [symbolTypeFilter, setSymbolTypeFilter] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Indexing state
  const [indexingJob, setIndexingJob] = useState<IndexJob | null>(null);
  const [isIndexing, setIsIndexing] = useState<boolean>(false);

  useEffect(() => {
    loadRepositories();
  }, []);

  useEffect(() => {
    if (selectedRepoId) {
      loadRepositoryData(selectedRepoId);
    }
  }, [selectedRepoId]);

  useEffect(() => {
    if (selectedRepoId) {
      loadSymbols(selectedRepoId, symbolFilter, symbolTypeFilter);
    }
  }, [selectedRepoId, symbolFilter, symbolTypeFilter]);

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

  async function loadRepositoryData(repoId: string) {
    try {
      const fileList = await api.getRepositoryFiles(repoId);
      setFiles(fileList);
      if (fileList.length > 0) {
        loadFileDetails(repoId, fileList[0].id);
      } else {
        setSelectedFile(null);
      }
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function loadFileDetails(repoId: string, fileId: string) {
    try {
      const details = await api.getFileDetails(repoId, fileId);
      setSelectedFile(details);
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function loadSymbols(repoId: string, query?: string, type?: string) {
    try {
      const symList = await api.getRepositorySymbols(repoId, query || undefined, type || undefined);
      setSymbols(symList);
    } catch {
      // Ignore symbol search errors
    }
  }

  async function handleTriggerIndex() {
    if (!selectedRepoId) return;
    try {
      setIsIndexing(true);
      const res = await api.triggerIndexing(selectedRepoId);
      const job = await api.getIndexingJob(selectedRepoId, res.job_id);
      setIndexingJob(job);

      // Poll indexing progress
      const interval = setInterval(async () => {
        try {
          const updated = await api.getIndexingJob(selectedRepoId, res.job_id);
          setIndexingJob(updated);
          if (updated.status === "COMPLETED" || updated.status === "FAILED") {
            clearInterval(interval);
            setIsIndexing(false);
            loadRepositoryData(selectedRepoId);
          }
        } catch {
          clearInterval(interval);
          setIsIndexing(false);
        }
      }, 1500);
    } catch (err: any) {
      setError(err.message || "Failed to trigger indexing");
      setIsIndexing(false);
    }
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-3 text-xs text-slate-500 font-mono">
            <Link href="/dashboard" className="hover:text-slate-300 flex items-center space-x-1">
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Dashboard</span>
            </Link>
            <span>/</span>
            <span className="text-slate-300">Code Explorer</span>
          </div>
          <h1 className="text-xl font-bold text-white flex items-center space-x-2.5">
            <FileCode className="h-5 w-5 text-brand-sky" />
            <span>AST Structural Explorer</span>
          </h1>
        </div>

        {/* Repository Selector & Trigger Index */}
        <div className="flex items-center space-x-3">
          <select
            value={selectedRepoId}
            onChange={(e) => setSelectedRepoId(e.target.value)}
            className="bg-surface-200 border border-border text-slate-200 text-xs rounded-lg px-3 py-2 font-mono focus:border-brand-sky focus:outline-none transition shadow-sm"
          >
            {repositories.map((repo) => (
              <option key={repo.id} value={repo.id}>
                {repo.full_name}
              </option>
            ))}
          </select>

          <button
            onClick={handleTriggerIndex}
            disabled={isIndexing || !selectedRepoId}
            className="flex items-center space-x-2 px-3 py-2 bg-brand-sky/10 hover:bg-brand-sky/20 text-brand-sky border border-brand-sky/30 rounded-lg text-xs font-mono disabled:opacity-50 transition shadow-sm"
          >
            {isIndexing ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <ArrowRight className="h-3.5 w-3.5" />
            )}
            <span>{isIndexing ? "Indexing AST..." : "Index AST"}</span>
          </button>
        </div>
      </div>

      {/* Indexing Status Banner */}
      {indexingJob && (
        <div className="p-3 rounded-lg border border-brand-sky/30 bg-brand-sky/10 flex items-center justify-between text-xs font-mono">
          <div className="flex items-center space-x-2 text-sky-300">
            <Loader2 className={`h-4 w-4 ${indexingJob.status !== "COMPLETED" ? "animate-spin" : ""}`} />
            <span>
              Stage: <strong>{indexingJob.current_step}</strong> ({indexingJob.progress_percent}%)
            </span>
          </div>
          <span className="text-slate-400 font-bold">{indexingJob.status}</span>
        </div>
      )}

      {error && (
        <div className="p-3 rounded-lg border border-brand-crimson/30 bg-brand-crimson/10 text-rose-400 text-xs font-mono flex items-center space-x-2">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}

      {/* Main 3-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: File Tree */}
        <div className="lg:col-span-3 rounded-xl border border-border bg-surface-200/90 p-4 space-y-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center space-x-2 text-xs font-semibold text-slate-200 font-mono">
              <FolderGit2 className="h-4 w-4 text-brand-sky" />
              <span>Parsed Files ({files.length})</span>
            </div>
          </div>

          <div className="space-y-1 max-h-[600px] overflow-y-auto pr-1">
            {files.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-500 font-mono">
                No indexed files yet.
                <br />
                Click &quot;Index AST&quot; to parse.
              </div>
            ) : (
              files.map((file) => {
                const isSelected = selectedFile?.id === file.id;
                return (
                  <button
                    key={file.id}
                    onClick={() => loadFileDetails(selectedRepoId, file.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-xs font-mono flex items-center justify-between transition ${
                      isSelected
                        ? "bg-brand-sky/15 text-brand-sky border border-brand-sky/40"
                        : "text-slate-400 hover:bg-surface-300 hover:text-slate-200 border border-transparent"
                    }`}
                  >
                    <span className="truncate mr-2">{file.path}</span>
                    <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-surface-100 text-slate-400 border border-border font-bold">
                      {file.language}
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Center Column: Selected File AST Detail */}
        <div className="lg:col-span-5 rounded-xl border border-border bg-surface-200/90 p-4 space-y-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center space-x-2 text-xs font-semibold text-slate-200 font-mono">
              <Code2 className="h-4 w-4 text-brand-sky" />
              <span>File AST Breakdown</span>
            </div>
            {selectedFile && (
              <span className="text-[10px] font-mono text-slate-500">
                {selectedFile.loc || 0} LOC • {selectedFile.symbols?.length || 0} Symbols
              </span>
            )}
          </div>

          {selectedFile ? (
            <div className="space-y-4 font-mono text-xs">
              <div className="p-3 rounded-lg bg-surface-300 border border-border space-y-1">
                <div className="text-white font-semibold truncate flex items-center space-x-1.5">
                  <FileCode className="h-3.5 w-3.5 text-brand-sky" />
                  <span>{selectedFile.path}</span>
                </div>
                <div className="text-[11px] text-slate-500 truncate">
                  SHA-256 Hash: {selectedFile.content_hash || "n/a"}
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                  <span>Extracted AST Symbols</span>
                  <span className="text-[10px] text-slate-500">{selectedFile.symbols?.length || 0} total</span>
                </div>

                <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                  {selectedFile.symbols && selectedFile.symbols.length > 0 ? (
                    selectedFile.symbols.map((sym) => (
                      <div
                        key={sym.id}
                        className="p-3 rounded-lg bg-surface-300 border border-border space-y-2 hover:border-slate-600 transition"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-xs font-bold text-slate-200">
                            {sym.name}
                          </span>
                          <div className="flex items-center space-x-2">
                            <StatusBadge type="nodeType" value={sym.symbol_type} />
                            <span className="text-[10px] font-mono text-slate-500">
                              L{sym.start_line}-{sym.end_line}
                            </span>
                          </div>
                        </div>

                        {sym.signature && (
                          <div className="p-2 rounded bg-surface-100 text-brand-sky font-mono text-[11px] border border-border truncate">
                            {sym.signature}
                          </div>
                        )}

                        {sym.docstring && (
                          <p className="text-[11px] text-slate-400 italic line-clamp-2">
                            &quot;{sym.docstring}&quot;
                          </p>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-6 text-xs text-slate-500 font-mono">
                      No symbols extracted for this file.
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-16 text-xs text-slate-500 font-mono">
              Select a file from the left to inspect its AST symbols.
            </div>
          )}
        </div>

        {/* Right Column: Repository Symbol Registry */}
        <div className="lg:col-span-4 rounded-xl border border-border bg-surface-200/90 p-4 space-y-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center space-x-2 text-xs font-semibold text-slate-200 font-mono">
              <Layers className="h-4 w-4 text-brand-sky" />
              <span>Symbol Registry</span>
            </div>
            <span className="text-[10px] font-mono text-slate-500">
              {symbols.length} Found
            </span>
          </div>

          {/* Filters */}
          <div className="space-y-2 font-mono text-xs">
            <div className="relative">
              <Search className="h-3.5 w-3.5 absolute left-3 top-2.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search symbol name..."
                value={symbolFilter}
                onChange={(e) => setSymbolFilter(e.target.value)}
                className="w-full bg-surface-300 border border-border text-slate-200 text-xs rounded-lg pl-8 pr-3 py-2 font-mono placeholder-slate-600 focus:border-brand-sky focus:outline-none transition"
              />
            </div>

            <select
              value={symbolTypeFilter}
              onChange={(e) => setSymbolTypeFilter(e.target.value)}
              className="w-full bg-surface-300 border border-border text-slate-300 text-xs rounded-lg px-3 py-2 font-mono focus:border-brand-sky focus:outline-none transition"
            >
              <option value="">All Symbol Types</option>
              <option value="FUNCTION">FUNCTION</option>
              <option value="METHOD">METHOD</option>
              <option value="CLASS">CLASS</option>
              <option value="MODEL">MODEL</option>
              <option value="ENDPOINT">ENDPOINT</option>
              <option value="INTERFACE">INTERFACE</option>
            </select>
          </div>

          {/* Symbol List */}
          <div className="space-y-1.5 max-h-[500px] overflow-y-auto pr-1">
            {symbols.map((sym) => (
              <div
                key={sym.id}
                className="p-2.5 rounded-lg bg-surface-300 border border-border/80 hover:border-slate-600 transition space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-slate-200 truncate mr-2">
                    {sym.name}
                  </span>
                  <StatusBadge type="nodeType" value={sym.symbol_type} />
                </div>
                {sym.signature && (
                  <div className="text-[10px] text-slate-500 font-mono truncate">
                    {sym.signature}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
