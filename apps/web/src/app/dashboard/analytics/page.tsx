"use client";

import Link from "next/link";
import { BarChart3, Clock, ArrowLeft, Activity, Gauge, Terminal } from "lucide-react";

export default function AnalyticsPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center space-x-3 text-xs text-slate-500 font-mono">
        <Link href="/dashboard" className="hover:text-slate-300 flex items-center space-x-1">
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Dashboard</span>
        </Link>
        <span>/</span>
        <span className="text-slate-300">Analytics &amp; Telemetry</span>
      </div>

      <div className="p-8 rounded-2xl border border-border bg-surface-200/90 space-y-6 shadow-sm">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-brand-sky/10 border border-brand-sky/30 flex items-center justify-center text-brand-sky">
              <BarChart3 className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white font-mono">Telemetry, Benchmarking &amp; Evaluation</h1>
              <p className="text-xs text-slate-400 font-mono">Retrieval Recall@K, MRR, Latency Histograms &amp; Prometheus Metrics</p>
            </div>
          </div>
          <span className="px-2.5 py-1 rounded text-xs font-mono bg-brand-indigo/10 text-brand-indigo border border-brand-indigo/30 font-bold">
            Milestone 6
          </span>
        </div>

        <p className="text-xs text-slate-300 font-mono leading-relaxed">
          CodeAtlas exposes real Prometheus metrics at <code className="font-mono text-brand-sky bg-surface-300 px-1.5 py-0.5 rounded border border-border">/metrics</code>. In Milestone 6, this dashboard provides comprehensive evaluation tracking including Retrieval Precision, Recall@K, Mean Reciprocal Rank (MRR), Citation Fidelity, and end-to-end token latency histograms.
        </p>

        <div className="space-y-3 font-mono text-xs">
          <div className="text-slate-400 font-semibold">// Telemetry Suite:</div>
          <div className="p-4 rounded-xl bg-surface-300 border border-border space-y-3 text-slate-300">
            <div className="flex items-center space-x-2.5">
              <Clock className="h-3.5 w-3.5 text-brand-indigo" />
              <span>Automated RAG Evaluation Suite (Recall@5, Recall@10, MRR)</span>
            </div>
            <div className="flex items-center space-x-2.5">
              <Clock className="h-3.5 w-3.5 text-brand-indigo" />
              <span>Citation Hallucination Benchmark with Golden Ground-Truth Sets</span>
            </div>
            <div className="flex items-center space-x-2.5">
              <Clock className="h-3.5 w-3.5 text-brand-indigo" />
              <span>Grafana + Prometheus Dashboards for Query &amp; Indexing Throughput</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
