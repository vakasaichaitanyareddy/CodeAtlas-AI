"use client";

import Link from "next/link";
import { ArrowUpRight, ShieldCheck, Activity, Terminal } from "lucide-react";

export function GlobalFooter() {
  return (
    <footer className="border-t border-border bg-surface-300 text-slate-400 font-mono text-xs selection:bg-brand-crimson selection:text-white">
      <div className="max-w-[1536px] mx-auto px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8 mb-10">
          {/* Brand Info */}
          <div className="lg:col-span-2 space-y-4">
            <Link href="/" className="flex items-center space-x-3 group">
              <div className="h-8 w-8 rounded-lg bg-surface-100 border border-border flex items-center justify-center font-mono font-black text-sm text-brand-crimson group-hover:border-brand-crimson transition-colors shadow-inner">
                CA
              </div>
              <span className="font-extrabold text-lg tracking-tight text-white uppercase font-mono">
                CodeAtlas
              </span>
            </Link>
            <p className="text-xs text-slate-400 font-sans leading-relaxed max-w-sm">
              Deterministic, evidence-gated developer intelligence platform. Fusing AST symbol hierarchies, lexical BM25, 768-D dense vectors, and FlashRank cross-encoder reranking.
            </p>
            <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-lg border border-border bg-surface-200 text-[10px] text-slate-300">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-emerald animate-pulse"></span>
              <span>8-Container Production Architecture • Qdrant + Redis + Postgres</span>
            </div>
          </div>

          {/* Navigation Column 1 */}
          <div className="space-y-3">
            <h4 className="text-white text-xs font-bold uppercase tracking-wider">
              Core Intelligence
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/dashboard" className="hover:text-brand-sky transition-colors flex items-center space-x-1">
                  <span>Command Center</span>
                </Link>
              </li>
              <li>
                <Link href="/dashboard/search" className="hover:text-brand-sky transition-colors flex items-center space-x-1">
                  <span>Dual Search (BM25 + Qdrant)</span>
                </Link>
              </li>
              <li>
                <Link href="/dashboard/graph" className="hover:text-brand-sky transition-colors flex items-center space-x-1">
                  <span>Dependency &amp; Call Graph</span>
                </Link>
              </li>
              <li>
                <Link href="/dashboard/chat" className="hover:text-brand-sky transition-colors flex items-center space-x-1">
                  <span>Grounded RAG Chat</span>
                </Link>
              </li>
              <li>
                <Link href="/dashboard/explorer" className="hover:text-brand-sky transition-colors flex items-center space-x-1">
                  <span>AST Code Explorer</span>
                </Link>
              </li>
              <li>
                <Link href="/dashboard/repositories" className="hover:text-brand-sky transition-colors flex items-center space-x-1">
                  <span>Repositories</span>
                </Link>
              </li>
            </ul>
          </div>

          {/* Navigation Column 2 */}
          <div className="space-y-3">
            <h4 className="text-white text-xs font-bold uppercase tracking-wider">
              Platform &amp; Ops
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/dashboard/pull-requests" className="hover:text-brand-sky transition-colors flex items-center space-x-1">
                  <span>Pull Request Intelligence</span>
                </Link>
              </li>
              <li>
                <Link href="/dashboard/analytics" className="hover:text-brand-sky transition-colors flex items-center space-x-1">
                  <span>Observability &amp; Eval</span>
                </Link>
              </li>
              <li>
                <Link href="/dashboard/security" className="hover:text-brand-sky transition-colors flex items-center space-x-1">
                  <span>Security &amp; Tenant Isolation</span>
                </Link>
              </li>
              <li>
                <Link href="/dashboard/docs" className="hover:text-brand-sky transition-colors flex items-center space-x-1">
                  <span>Documentation &amp; API Spec</span>
                </Link>
              </li>
              <li>
                <Link href="/dashboard/admin" className="hover:text-brand-sky transition-colors flex items-center space-x-1">
                  <span>Admin Console</span>
                </Link>
              </li>
              <li>
                <Link href="/dashboard/settings" className="hover:text-brand-sky transition-colors flex items-center space-x-1">
                  <span>Settings &amp; Providers</span>
                </Link>
              </li>
            </ul>
          </div>

          {/* Navigation Column 3 */}
          <div className="space-y-3">
            <h4 className="text-white text-xs font-bold uppercase tracking-wider">
              Access &amp; Auth
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/login" className="hover:text-brand-sky transition-colors flex items-center space-x-1">
                  <span>Sign In</span>
                </Link>
              </li>
              <li>
                <Link href="/register" className="hover:text-brand-sky transition-colors flex items-center space-x-1">
                  <span>Create Account</span>
                </Link>
              </li>
              <li>
                <Link href="/dashboard" className="text-brand-crimson hover:text-brand-crimsonHover transition-colors flex items-center space-x-1 font-bold">
                  <span>Launch Console</span>
                  <ArrowUpRight className="h-3 w-3" />
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-border flex flex-col sm:flex-row items-center justify-between text-[11px] text-slate-500 gap-4">
          <div className="flex items-center space-x-3">
            <span>© {new Date().getFullYear()} CodeAtlas Engineering. All rights reserved.</span>
            <span>•</span>
            <span className="text-slate-400">Deterministic RAG Engine</span>
          </div>
          <div className="flex items-center space-x-6">
            <Link href="/dashboard/docs" className="hover:text-slate-300 transition-colors">
              OpenAPI Specification
            </Link>
            <Link href="/dashboard/security" className="hover:text-slate-300 transition-colors">
              Security Compliance
            </Link>
            <Link href="/dashboard/graph" className="hover:text-slate-300 transition-colors">
              Tarjan SCC Graph
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
