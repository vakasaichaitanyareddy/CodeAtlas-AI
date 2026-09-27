"use client";

import Link from "next/link";
import { BookOpen, Clock, ArrowLeft, FileText, Sparkles, Network } from "lucide-react";

export default function DocsPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center space-x-3 text-xs text-slate-500 font-mono">
        <Link href="/dashboard" className="hover:text-slate-300 flex items-center space-x-1">
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Dashboard</span>
        </Link>
        <span>/</span>
        <span className="text-slate-300">Documentation</span>
      </div>

      <div className="p-8 rounded-2xl border border-border bg-surface-200/90 space-y-6 shadow-sm">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-brand-emerald/10 border border-brand-emerald/30 flex items-center justify-center text-brand-emerald">
              <BookOpen className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white font-mono">Living Architectural Documentation</h1>
              <p className="text-xs text-slate-400 font-mono">Continuously Updated System Architecture, Data Flows &amp; Component Guides</p>
            </div>
          </div>
          <span className="px-2.5 py-1 rounded text-xs font-mono bg-brand-emerald/10 text-brand-emerald border border-brand-emerald/30 font-bold">
            Milestone 5
          </span>
        </div>

        <p className="text-xs text-slate-300 font-mono leading-relaxed">
          CodeAtlas generates living, self-updating architecture documentation grounded in the actual codebase structure. As commits land and PRs merge, the system refreshes architectural maps, module responsibilities, and onboarding guides automatically.
        </p>

        <div className="space-y-3 font-mono text-xs">
          <div className="text-slate-400 font-semibold">// Living Documentation Engine:</div>
          <div className="p-4 rounded-xl bg-surface-300 border border-border space-y-3 text-slate-300">
            <div className="flex items-center space-x-2.5">
              <Clock className="h-3.5 w-3.5 text-brand-emerald" />
              <span>Automated System Architecture &amp; Module Boundary Mapping</span>
            </div>
            <div className="flex items-center space-x-2.5">
              <Clock className="h-3.5 w-3.5 text-brand-emerald" />
              <span>Interactive Topology Diagrams &amp; Sequence Call Flows</span>
            </div>
            <div className="flex items-center space-x-2.5">
              <Clock className="h-3.5 w-3.5 text-brand-emerald" />
              <span>Incremental Doc Invalidation on Targeted Git Commits</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
