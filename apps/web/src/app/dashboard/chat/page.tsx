"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import {
  MessageSquare,
  Sparkles,
  Zap,
  Trash2,
  Plus,
  FileCode,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Clock,
  Layers,
  Search,
  Check,
  Cpu,
  ShieldCheck,
  ArrowRight,
  ExternalLink,
} from "lucide-react";
import { api } from "@/lib/api";
import {
  Repository,
  ChatSession,
  ChatMessage,
  CitationDTO,
  ContextChunkDTO,
  RetrievalEvidenceDTO,
  GroundingStatus,
} from "@/types";
import { StatusBadge } from "@/components/StatusBadge";
import { CodeViewer } from "@/components/CodeViewer";

export default function ChatPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>("");
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState<string>("");
  const [searchMode, setSearchMode] = useState<"hybrid" | "lexical" | "semantic">("hybrid");

  const [loading, setLoading] = useState<boolean>(false);
  const [streaming, setStreaming] = useState<boolean>(false);
  const [streamingText, setStreamingText] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  // Inspector and Citation Drawers
  const [selectedCitation, setSelectedCitation] = useState<CitationDTO | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<{
    evidence: RetrievalEvidenceDTO | null;
    chunks: ContextChunkDTO[];
  } | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadRepositories();
  }, []);

  useEffect(() => {
    if (selectedRepoId) {
      loadSessions(selectedRepoId);
    }
  }, [selectedRepoId]);

  useEffect(() => {
    if (selectedRepoId && activeSessionId) {
      loadSessionDetail(selectedRepoId, activeSessionId);
    } else {
      setMessages([]);
    }
  }, [activeSessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

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

  async function loadSessions(repoId: string) {
    try {
      const list = await api.listChatSessions(repoId);
      setSessions(list);
      if (list.length > 0 && !activeSessionId) {
        setActiveSessionId(list[0].id);
      }
    } catch (err: any) {
      console.error("Failed to load chat sessions:", err);
    }
  }

  async function loadSessionDetail(repoId: string, sessionId: string) {
    try {
      setLoading(true);
      const detail = await api.getChatSession(repoId, sessionId);
      setMessages(detail.messages);
    } catch (err: any) {
      setError(err.message || "Failed to load session history");
    } finally {
      setLoading(false);
    }
  }

  function handleNewChat() {
    setActiveSessionId(null);
    setMessages([]);
    setStreamingText("");
    setError(null);
    chatInputRef.current?.focus();
  }

  async function handleDeleteSession(sessionId: string) {
    if (!selectedRepoId) return;
    try {
      await api.deleteChatSession(selectedRepoId, sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        handleNewChat();
      }
    } catch (err: any) {
      setError(err.message || "Failed to delete session");
    }
  }

  async function handleSendMessage(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!selectedRepoId || !inputQuery.trim() || streaming) return;

    const query = inputQuery.trim();
    setInputQuery("");
    setError(null);

    // Optimistic user message
    const tempUserMsg: ChatMessage = {
      id: "temp-" + Date.now(),
      conversation_id: activeSessionId || "",
      role: "USER",
      content: query,
      citations: [],
      context_chunks: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setStreaming(true);
    setStreamingText("");

    let currentConversationId = activeSessionId;

    await api.streamChatMessage(
      selectedRepoId,
      {
        message: query,
        conversation_id: activeSessionId || undefined,
        mode: searchMode,
      },
      (token: string, conversationId?: string) => {
        if (conversationId && !currentConversationId) {
          currentConversationId = conversationId;
          setActiveSessionId(conversationId);
        }
        setStreamingText((prev) => prev + token);
      },
      (completePayload: any) => {
        setStreaming(false);
        setStreamingText("");

        const assistantMsg: ChatMessage = {
          id: completePayload.message_id || "msg-" + Date.now(),
          conversation_id: completePayload.conversation_id,
          role: "ASSISTANT",
          content: completePayload.answer,
          grounding_status: completePayload.grounding_status,
          intent: completePayload.intent,
          provider: completePayload.provider,
          is_mock: completePayload.is_mock,
          citations: completePayload.citations || [],
          context_chunks: completePayload.context_chunks || [],
          retrieval_evidence: completePayload.retrieval_evidence || null,
          tokens_used: completePayload.tokens_used,
          latency_ms: completePayload.latency_ms,
          created_at: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, assistantMsg]);
        loadSessions(selectedRepoId);
      },
      (err: any) => {
        setStreaming(false);
        setStreamingText("");
        setError(err.message || "Chat generation failed");
      }
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 font-sans">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-border gap-4">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-brand-sky mb-1 flex items-center space-x-1.5">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Evidence-Gated RAG &amp; Citation Engine</span>
          </div>
          <h1 className="text-2xl font-black uppercase tracking-tight text-white font-sans">
            Grounded Codebase Intelligence Console
          </h1>
          <p className="mt-1 text-xs text-slate-400 font-mono">
            Multi-turn architectural and process reasoning. Every statement is bounded by retrieved AST chunks and line-verified.
          </p>
        </div>

        {/* Repository Selector */}
        <select
          value={selectedRepoId}
          onChange={(e) => {
            setSelectedRepoId(e.target.value);
            setActiveSessionId(null);
          }}
          className="bg-surface-300 border border-border text-slate-200 text-xs rounded-lg px-3.5 py-2 font-mono focus:border-brand-sky focus:outline-none shadow-sm"
        >
          {repositories.map((repo) => (
            <option key={repo.id} value={repo.id}>
              {repo.full_name || repo.name} ({repo.default_branch})
            </option>
          ))}
        </select>
      </div>

      {/* Main Grid: 3-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Session Threads */}
        <div className="lg:col-span-3 space-y-3 bg-surface-200 p-4 rounded-xl border border-border font-mono text-xs shadow-sm">
          <button
            onClick={handleNewChat}
            className="w-full py-2.5 px-3 rounded-lg bg-brand-sky hover:bg-brand-skyHover text-slate-950 font-bold flex items-center justify-center space-x-2 transition shadow-sm active:scale-95"
          >
            <Plus className="h-4 w-4" />
            <span>New Chat Thread</span>
          </button>

          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold pt-2 flex items-center justify-between">
            <span>Conversations ({sessions.length})</span>
            <span className="text-slate-600">ID Threaded</span>
          </div>

          <div className="space-y-1.5 max-h-[560px] overflow-y-auto pr-1">
            {sessions.length === 0 && (
              <div className="text-slate-500 text-center py-8 text-[11px]">
                No conversation sessions yet.
                <br />
                Start a thread below.
              </div>
            )}
            {sessions.map((sess) => {
              const isSelected = activeSessionId === sess.id;
              return (
                <div
                  key={sess.id}
                  onClick={() => setActiveSessionId(sess.id)}
                  className={`p-3 rounded-lg border cursor-pointer transition flex items-center justify-between group ${
                    isSelected
                      ? "bg-surface-100 border-brand-sky/40 text-brand-sky shadow-sm"
                      : "border-border/60 text-slate-400 hover:bg-surface-100/50 hover:text-slate-200"
                  }`}
                >
                  <div className="truncate pr-2 min-w-0">
                    <div className="truncate font-bold text-xs">{sess.title}</div>
                    <div className="text-[10px] text-slate-500 flex items-center space-x-2 mt-1 font-mono">
                      <span>{sess.message_count} msgs</span>
                      <span>•</span>
                      <span>{new Date(sess.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteSession(sess.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-surface-300 text-slate-500 hover:text-rose-400 transition"
                    title="Delete conversation"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Center / Main Column: Chat Stream */}
        <div className="lg:col-span-9 space-y-4">
          {/* Messages Container */}
          <div className="h-[580px] overflow-y-auto p-5 rounded-xl border border-border bg-surface-200 space-y-5 shadow-inner">
            {messages.length === 0 && !streaming && (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-4">
                <div className="h-12 w-12 rounded-xl bg-surface-100 border border-border flex items-center justify-center text-brand-sky shadow-inner">
                  <MessageSquare className="h-6 w-6" />
                </div>
                <div className="space-y-1 max-w-md">
                  <h3 className="text-base font-bold text-white uppercase font-sans">
                    Grounded Codebase Intelligence
                  </h3>
                  <p className="text-xs text-slate-400 leading-relaxed font-mono">
                    Ask questions about architecture, request routing, AST definitions, dependencies, or blast radius. Answers are grounded in indexed chunks with verified citations.
                  </p>
                </div>

                {/* Quick Prompts */}
                <div className="flex flex-wrap gap-2 justify-center pt-4 font-mono text-xs max-w-xl">
                  <button
                    onClick={() => {
                      setInputQuery("How does Flask route a request to a view function?");
                      chatInputRef.current?.focus();
                    }}
                    className="px-3 py-2 rounded-lg border border-border bg-surface-300 text-slate-300 hover:text-white hover:border-brand-sky/40 transition text-left"
                  >
                    How does Flask route a request to a view function?
                  </button>
                  <button
                    onClick={() => {
                      setInputQuery("How does request context work in Flask?");
                      chatInputRef.current?.focus();
                    }}
                    className="px-3 py-2 rounded-lg border border-border bg-surface-300 text-slate-300 hover:text-white hover:border-brand-sky/40 transition text-left"
                  >
                    How does request context work in Flask?
                  </button>
                  <button
                    onClick={() => {
                      setInputQuery("Where is the Flask application class implemented?");
                      chatInputRef.current?.focus();
                    }}
                    className="px-3 py-2 rounded-lg border border-border bg-surface-300 text-slate-300 hover:text-white hover:border-brand-sky/40 transition text-left"
                  >
                    Where is the Flask application class implemented?
                  </button>
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col ${msg.role === "USER" ? "items-end" : "items-start"} space-y-2`}
              >
                {/* Role Header & Metadata Tags */}
                <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono text-slate-500">
                  <span className="font-bold text-slate-400">{msg.role === "USER" ? "DEVELOPER" : "CODEATLAS"}</span>
                  <span>•</span>
                  <span>{new Date(msg.created_at).toLocaleTimeString()}</span>
                  {msg.intent && (
                    <>
                      <span>•</span>
                      <span className="uppercase px-1.5 py-0.2 rounded bg-surface-300 text-brand-sky border border-border font-bold">
                        {msg.intent}
                      </span>
                    </>
                  )}
                  {msg.grounding_status && (
                    <StatusBadge type="grounding" value={msg.grounding_status} size="sm" />
                  )}
                  {msg.role === "ASSISTANT" && (
                    msg.is_mock ? (
                      <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[9px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20 font-bold">
                        <span>OFFLINE BASELINE (MOCK)</span>
                      </span>
                    ) : msg.provider ? (
                      <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[9px] font-mono bg-brand-sky/10 text-brand-sky border border-brand-sky/20 uppercase font-bold">
                        <span>AI: {msg.provider}</span>
                      </span>
                    ) : null
                  )}
                  {msg.latency_ms && (
                    <span className="text-slate-600">{msg.latency_ms}ms</span>
                  )}
                </div>

                {/* Message Bubble */}
                <div
                  className={`p-4 sm:p-5 rounded-xl max-w-3xl text-xs font-mono leading-relaxed shadow-sm ${
                    msg.role === "USER"
                      ? "bg-brand-sky text-slate-950 font-semibold"
                      : "bg-surface-300 border border-border text-slate-200 space-y-3.5"
                  }`}
                >
                  <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>

                  {/* Assistant Footer: Citations & Context Inspector */}
                  {msg.role === "ASSISTANT" && (
                    <div className="pt-3 border-t border-border/80 flex flex-wrap items-center justify-between gap-2 text-[10px]">
                      {/* Citations list */}
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-slate-500 font-bold uppercase">Citations:</span>
                        {msg.citations.length === 0 ? (
                          <span className="text-slate-500 italic">No formal citations</span>
                        ) : (
                          msg.citations.map((cit, idx) => (
                            <button
                              key={idx}
                              onClick={() => setSelectedCitation(cit)}
                              className={`px-2 py-0.5 rounded border transition flex items-center space-x-1 ${
                                cit.is_valid
                                  ? "bg-brand-sky/10 text-brand-sky border-brand-sky/30 hover:bg-brand-sky/20"
                                  : "bg-rose-500/10 text-rose-400 border-rose-500/30 hover:bg-rose-500/20"
                              }`}
                            >
                              <FileCode className="h-3 w-3" />
                              <span>{cit.raw_citation}</span>
                            </button>
                          ))
                        )}
                      </div>

                      {/* Context Inspector Trigger */}
                      {msg.context_chunks && msg.context_chunks.length > 0 && (
                        <button
                          onClick={() =>
                            setSelectedEvidence({
                              evidence: msg.retrieval_evidence || null,
                              chunks: msg.context_chunks,
                            })
                          }
                          className="px-2.5 py-1 rounded bg-surface-100 hover:bg-surface-50 text-slate-300 border border-border flex items-center space-x-1.5 transition font-semibold"
                        >
                          <Layers className="h-3 w-3 text-brand-purple" />
                          <span>Inspect Evidence ({msg.context_chunks.length})</span>
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Live Streaming Delta Bubble */}
            {streaming && (
              <div className="flex flex-col items-start space-y-2">
                <div className="flex items-center space-x-2 text-[10px] font-mono text-slate-500">
                  <span className="font-bold text-slate-400">CODEATLAS</span>
                  <span>•</span>
                  <span className="text-brand-sky flex items-center space-x-1 font-bold">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    <span>Streaming verified tokens...</span>
                  </span>
                </div>
                <div className="p-4 rounded-xl max-w-3xl text-xs font-mono leading-relaxed bg-surface-300 border border-brand-sky/30 text-slate-200">
                  <div className="whitespace-pre-wrap">{streamingText}</div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {error && (
            <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-400 text-xs font-mono flex items-center space-x-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Chat Input & Toolbar */}
          <form onSubmit={handleSendMessage} className="space-y-3 font-mono">
            <div className="relative">
              <input
                ref={chatInputRef}
                type="text"
                placeholder="Ask about functions, dependencies, callers, or architecture (e.g. 'How does Flask route a request to a view function?')..."
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                disabled={streaming}
                className="w-full bg-surface-200 border border-border rounded-xl pl-4 pr-24 py-3.5 text-xs text-slate-100 placeholder-slate-500 focus:border-brand-sky focus:outline-none focus:ring-1 focus:ring-brand-sky transition shadow-inner"
              />
              <button
                type="submit"
                disabled={streaming || !inputQuery.trim()}
                className="absolute right-2.5 top-2 px-4 py-1.5 bg-brand-sky hover:bg-brand-skyHover text-slate-950 rounded-lg text-xs font-bold disabled:opacity-50 transition flex items-center space-x-1.5 shadow-sm active:scale-95"
              >
                {streaming ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
                <span>Send</span>
              </button>
            </div>

            {/* Mode Toolbar */}
            <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
              <div className="flex items-center space-x-2">
                <span>Retrieval Mode:</span>
                <select
                  value={searchMode}
                  onChange={(e) => setSearchMode(e.target.value as any)}
                  className="bg-surface-300 border border-border text-slate-300 rounded px-2 py-0.5 focus:border-brand-sky focus:outline-none text-[11px]"
                >
                  <option value="hybrid">Hybrid (RRF + Reranker)</option>
                  <option value="lexical">Lexical (BM25 Okapi)</option>
                  <option value="semantic">Semantic (Qdrant Vector)</option>
                </select>
              </div>
              <span className="text-slate-500 hidden sm:inline">
                Strict Grounding Active (Deterministic Evidence Verification Gate)
              </span>
            </div>
          </form>
        </div>
      </div>

      {/* Citation Slide-over Drawer */}
      {selectedCitation && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex justify-end animate-fade-in">
          <div className="w-full max-w-lg bg-surface-200 border-l border-border h-full p-6 space-y-5 overflow-y-auto font-mono text-xs shadow-2xl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center space-x-2">
                <FileCode className="h-4 w-4 text-brand-sky" />
                <h3 className="font-bold text-white uppercase">Citation Verification Audit</h3>
              </div>
              <button
                onClick={() => setSelectedCitation(null)}
                className="text-slate-400 hover:text-white text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <span className="text-slate-500 text-[10px] uppercase">Raw Citation Token:</span>
                <div className="text-brand-sky font-bold text-sm mt-0.5">{selectedCitation.raw_citation}</div>
              </div>

              <div>
                <span className="text-slate-500 text-[10px] uppercase">Resolved Target File:</span>
                <div className="text-slate-200 font-semibold">{selectedCitation.file_path}</div>
              </div>

              <div>
                <span className="text-slate-500 text-[10px] uppercase">Physical Line Bounds:</span>
                <div className="text-slate-300">
                  Lines {selectedCitation.start_line} to {selectedCitation.end_line}
                </div>
              </div>

              {/* Checklist Grid */}
              <div className="p-4 rounded-xl border border-border bg-surface-300 space-y-2 text-[11px]">
                <div className="flex justify-between items-center border-b border-border/60 pb-1.5">
                  <span className="text-slate-400">File Exists in Commit:</span>
                  <span className={selectedCitation.file_exists ? "text-brand-emerald font-bold" : "text-rose-400 font-bold"}>
                    {selectedCitation.file_exists ? "YES" : "NO"}
                  </span>
                </div>
                <div className="flex justify-between items-center border-b border-border/60 pb-1.5">
                  <span className="text-slate-400">Lines within Physical Bounds:</span>
                  <span className={selectedCitation.lines_in_bounds ? "text-brand-emerald font-bold" : "text-rose-400 font-bold"}>
                    {selectedCitation.lines_in_bounds ? "YES" : "NO"}
                  </span>
                </div>
                <div className="flex justify-between items-center border-b border-border/60 pb-1.5">
                  <span className="text-slate-400">Overlaps Retrieved Context:</span>
                  <span className={selectedCitation.overlaps_context ? "text-brand-emerald font-bold" : "text-rose-400 font-bold"}>
                    {selectedCitation.overlaps_context ? "YES" : "NO"}
                  </span>
                </div>
                <div className="flex justify-between items-center border-b border-border/60 pb-1.5">
                  <span className="text-slate-400">AST Symbol Match:</span>
                  <span className={selectedCitation.symbol_matches ? "text-brand-emerald font-bold" : "text-amber-400 font-bold"}>
                    {selectedCitation.symbol_matches ? "VERIFIED" : "N/A"}
                  </span>
                </div>
                <div className="flex justify-between items-center border-b border-border/60 pb-1.5">
                  <span className="text-slate-400">Grounding Confidence:</span>
                  <span className="text-brand-sky font-bold">{(selectedCitation.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="flex justify-between items-center pt-1">
                  <span className="text-slate-400">Gate Status:</span>
                  <span className={selectedCitation.is_valid ? "text-brand-emerald font-bold" : "text-rose-400 font-bold"}>
                    {selectedCitation.validation_reason}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Context Evidence Inspector Drawer */}
      {selectedEvidence && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex justify-end animate-fade-in">
          <div className="w-full max-w-2xl bg-surface-200 border-l border-border h-full p-6 space-y-5 overflow-y-auto font-mono text-xs shadow-2xl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center space-x-2">
                <Layers className="h-4 w-4 text-brand-purple" />
                <h3 className="font-bold text-white uppercase">Retrieval Evidence &amp; Context Inspector</h3>
              </div>
              <button
                onClick={() => setSelectedEvidence(null)}
                className="text-slate-400 hover:text-white text-sm font-bold"
              >
                ✕
              </button>
            </div>

            {selectedEvidence.evidence && (
              <div className="p-4 rounded-xl border border-border bg-surface-300 grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
                <div>
                  <div className="text-slate-500 uppercase text-[10px]">Candidates:</div>
                  <div className="text-white font-bold text-sm">{selectedEvidence.evidence.candidate_count}</div>
                </div>
                <div>
                  <div className="text-slate-500 uppercase text-[10px]">Selected:</div>
                  <div className="text-brand-emerald font-bold text-sm">{selectedEvidence.evidence.selected_count}</div>
                </div>
                <div>
                  <div className="text-slate-500 uppercase text-[10px]">Budget Truncated:</div>
                  <div className="text-slate-400 font-bold text-sm">{selectedEvidence.evidence.discarded_count}</div>
                </div>
                <div>
                  <div className="text-slate-500 uppercase text-[10px]">Context Tokens:</div>
                  <div className="text-brand-sky font-bold text-sm">{selectedEvidence.evidence.context_tokens}</div>
                </div>
              </div>
            )}

            <div className="space-y-4">
              <div className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Selected Source Chunks ({selectedEvidence.chunks.length})
              </div>
              {selectedEvidence.chunks.map((ch, idx) => (
                <div key={idx} className="space-y-2">
                  <div className="flex items-center justify-between text-slate-300 font-semibold px-1">
                    <span className="text-brand-sky font-mono">{ch.file_path}:L{ch.start_line}-{ch.end_line}</span>
                    <span className="text-[10px] text-slate-500">Score: {ch.score.toFixed(4)} • Source: {ch.source}</span>
                  </div>
                  <CodeViewer
                    code={ch.content}
                    filePath={ch.file_path}
                    startLine={ch.start_line}
                    endLine={ch.end_line}
                    symbolName={ch.symbol_name || undefined}
                    symbolType={ch.symbol_type || undefined}
                    maxHeight="max-h-60"
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

