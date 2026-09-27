"use client";

import Link from "next/link";
import { ShieldCheck, Clock, ArrowLeft, ShieldAlert, KeyRound } from "lucide-react";

export default function SecurityPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center space-x-3 text-xs text-slate-500 font-mono">
        <Link href="/dashboard" className="hover:text-slate-300 flex items-center space-x-1">
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Dashboard</span>
        </Link>
        <span>/</span>
        <span className="text-slate-300">Security</span>
      </div>

      <div className="p-8 rounded-2xl border border-border bg-surface-200/90 space-y-6 shadow-sm">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-brand-crimson/10 border border-brand-crimson/30 flex items-center justify-center text-brand-crimson">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white font-mono">Static Security &amp; Entropy Secret Scanner</h1>
              <p className="text-xs text-slate-400 font-mono">Secret Detection, OWASP Pattern Scans &amp; Remediation Suggestions</p>
            </div>
          </div>
          <span className="px-2.5 py-1 rounded text-xs font-mono bg-brand-crimson/10 text-brand-crimson border border-brand-crimson/30 font-bold">
            Milestone 5
          </span>
        </div>

        <p className="text-xs text-slate-300 font-mono leading-relaxed">
          Continuous static analysis scanner integrated directly into CodeAtlas. Automatically identifies hardcoded secrets, high-entropy tokens, insecure cryptography, SQL injection risks, and unsafe deserialization during repository indexing.
        </p>

        <div className="space-y-3 font-mono text-xs">
          <div className="text-slate-400 font-semibold">// Scanner Engine:</div>
          <div className="p-4 rounded-xl bg-surface-300 border border-border space-y-3 text-slate-300">
            <div className="flex items-center space-x-2.5">
              <Clock className="h-3.5 w-3.5 text-brand-crimson" />
              <span>Regex &amp; High-Entropy Shannon Secret Scanner (API keys, Private Keys, DB passwords)</span>
            </div>
            <div className="flex items-center space-x-2.5">
              <Clock className="h-3.5 w-3.5 text-brand-crimson" />
              <span>AST-Based Insecure Pattern Detection (e.g. raw SQL concatenation, eval)</span>
            </div>
            <div className="flex items-center space-x-2.5">
              <Clock className="h-3.5 w-3.5 text-brand-crimson" />
              <span>AI-Assisted Patch &amp; Remediation Guidance</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
