"use client";

import Link from "next/link";
import { GitPullRequest, Clock, ArrowLeft, GitCompare, Zap, CheckCircle2 } from "lucide-react";

export default function PullRequestsPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center space-x-3 text-xs text-slate-500 font-mono">
        <Link href="/dashboard" className="hover:text-slate-300 flex items-center space-x-1">
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Dashboard</span>
        </Link>
        <span>/</span>
        <span className="text-slate-300">Pull Requests</span>
      </div>

      <div className="p-8 rounded-2xl border border-border bg-surface-200/90 space-y-6 shadow-sm">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-brand-sky/10 border border-brand-sky/30 flex items-center justify-center text-brand-sky">
              <GitPullRequest className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white font-mono">PR Semantic Impact &amp; Risk Engine</h1>
              <p className="text-xs text-slate-400 font-mono">Graph-Grounded Blast Radius, Breaking Changes &amp; Diff Risk Scoring</p>
            </div>
          </div>
          <span className="px-2.5 py-1 rounded text-xs font-mono bg-brand-amber/10 text-brand-amber border border-brand-amber/30 font-bold">
            Milestone 5
          </span>
        </div>

        <p className="text-xs text-slate-300 font-mono leading-relaxed">
          Unlike surface-level PR summarizers, CodeAtlas analyzes git diffs through the lens of the repository dependency graph. It detects broken downstream callers, modified public interfaces, untested paths, and outputs actionable architectural impact reports.
        </p>

        <div className="space-y-3 font-mono text-xs">
          <div className="text-slate-400 font-semibold">// Pipeline Architecture:</div>
          <div className="p-4 rounded-xl bg-surface-300 border border-border space-y-3 text-slate-300">
            <div className="flex items-center space-x-2.5">
              <Clock className="h-3.5 w-3.5 text-brand-amber" />
              <span>Automated GitHub Webhook Ingestion &amp; AST Diff Extraction</span>
            </div>
            <div className="flex items-center space-x-2.5">
              <Clock className="h-3.5 w-3.5 text-brand-amber" />
              <span>Graph-Traversed Blast Radius Calculation for PR Commits</span>
            </div>
            <div className="flex items-center space-x-2.5">
              <Clock className="h-3.5 w-3.5 text-brand-amber" />
              <span>Public Interface &amp; REST Endpoint Breaking Change Detection</span>
            </div>
            <div className="flex items-center space-x-2.5">
              <Clock className="h-3.5 w-3.5 text-brand-amber" />
              <span>Automated Semantic Review Comments posted to GitHub Pull Request</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
