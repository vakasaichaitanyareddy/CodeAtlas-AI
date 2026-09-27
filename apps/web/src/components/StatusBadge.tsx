"use client";

import React from "react";
import { CheckCircle2, AlertCircle, ShieldAlert, Cpu, Network, FileCode, Layers } from "lucide-react";
import { GroundingStatus } from "@/types";

interface StatusBadgeProps {
  type: "grounding" | "nodeType" | "severity" | "edgeType" | "status";
  value: string;
  className?: string;
  size?: "sm" | "md";
}

export function StatusBadge({ type, value, className = "", size = "md" }: StatusBadgeProps) {
  const sizeClasses = size === "sm" ? "px-1.5 py-0.5 text-[9px]" : "px-2 py-0.5 text-[10px]";

  if (type === "grounding") {
    if (value === "VERIFIED") {
      return (
        <span
          className={`inline-flex items-center space-x-1 rounded font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 ${sizeClasses} ${className}`}
        >
          <CheckCircle2 className={size === "sm" ? "h-2.5 w-2.5" : "h-3 w-3"} />
          <span>VERIFIED GROUNDING</span>
        </span>
      );
    }
    if (value === "PARTIALLY_VERIFIED") {
      return (
        <span
          className={`inline-flex items-center space-x-1 rounded font-mono font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/25 ${sizeClasses} ${className}`}
        >
          <AlertCircle className={size === "sm" ? "h-2.5 w-2.5" : "h-3 w-3"} />
          <span>PARTIALLY VERIFIED</span>
        </span>
      );
    }
    return (
      <span
        className={`inline-flex items-center space-x-1 rounded font-mono font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/25 ${sizeClasses} ${className}`}
      >
        <AlertCircle className={size === "sm" ? "h-2.5 w-2.5" : "h-3 w-3"} />
        <span>UNSUPPORTED EVIDENCE</span>
      </span>
    );
  }

  if (type === "severity") {
    const s = value.toUpperCase();
    if (s === "CRITICAL") {
      return (
        <span className={`inline-flex items-center space-x-1 rounded font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 uppercase ${sizeClasses} ${className}`}>
          <ShieldAlert className={size === "sm" ? "h-2.5 w-2.5" : "h-3 w-3"} />
          <span>CRITICAL RISK</span>
        </span>
      );
    }
    if (s === "HIGH") {
      return (
        <span className={`inline-flex items-center space-x-1 rounded font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 uppercase ${sizeClasses} ${className}`}>
          <span>HIGH SEVERITY</span>
        </span>
      );
    }
    if (s === "MEDIUM") {
      return (
        <span className={`inline-flex items-center space-x-1 rounded font-mono font-bold bg-yellow-500/20 text-yellow-300 border border-yellow-500/40 uppercase ${sizeClasses} ${className}`}>
          <span>MEDIUM SEVERITY</span>
        </span>
      );
    }
    return (
      <span className={`inline-flex items-center space-x-1 rounded font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 uppercase ${sizeClasses} ${className}`}>
        <span>LOW SEVERITY</span>
      </span>
    );
  }

  if (type === "nodeType") {
    const t = value.toUpperCase();
    const map: Record<string, string> = {
      FUNCTION: "bg-sky-500/10 text-sky-400 border-sky-500/30",
      METHOD: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30",
      CLASS: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
      MODEL: "bg-purple-500/10 text-purple-400 border-purple-500/30",
      ENDPOINT: "bg-amber-500/10 text-amber-400 border-amber-500/30",
      INTERFACE: "bg-teal-500/10 text-teal-400 border-teal-500/30",
      FILE: "bg-slate-800 text-slate-300 border-slate-700",
    };
    const cls = map[t] || "bg-slate-800 text-slate-300 border-slate-700";
    return (
      <span className={`inline-flex items-center rounded font-mono font-semibold border ${cls} ${sizeClasses} ${className}`}>
        {t}
      </span>
    );
  }

  if (type === "edgeType") {
    const e = value.toUpperCase();
    const map: Record<string, string> = {
      CALLS: "bg-sky-500/10 text-sky-400 border-sky-500/30",
      IMPORTS: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30",
      INHERITS: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
      EXPOSES: "bg-amber-500/10 text-amber-400 border-amber-500/30",
      QUERIES: "bg-purple-500/10 text-purple-400 border-purple-500/30",
      DEPENDS_ON: "bg-slate-800 text-slate-300 border-slate-700",
    };
    const cls = map[e] || "bg-slate-800 text-slate-300 border-slate-700";
    return (
      <span className={`inline-flex items-center rounded font-mono font-semibold border ${cls} ${sizeClasses} ${className}`}>
        {e}
      </span>
    );
  }

  // General Status
  const s = value.toUpperCase();
  if (s === "INDEXED" || s === "ACTIVE" || s === "COMPLETED") {
    return (
      <span className={`inline-flex items-center space-x-1 rounded font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 ${sizeClasses} ${className}`}>
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
        <span>{s}</span>
      </span>
    );
  }
  if (s === "INDEXING" || s === "PARSING" || s === "CLONING" || s === "QUEUED") {
    return (
      <span className={`inline-flex items-center space-x-1 rounded font-mono bg-brand-crimson/10 text-brand-crimson border border-brand-crimson/30 animate-pulse ${sizeClasses} ${className}`}>
        <span className="h-1.5 w-1.5 rounded-full bg-brand-crimson"></span>
        <span>{s}</span>
      </span>
    );
  }
  if (s === "FAILED") {
    return (
      <span className={`inline-flex items-center space-x-1 rounded font-mono bg-rose-500/10 text-rose-400 border border-rose-500/30 ${sizeClasses} ${className}`}>
        <AlertCircle className={size === "sm" ? "h-2.5 w-2.5" : "h-3 w-3"} />
        <span>FAILED</span>
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center rounded font-mono bg-surface-100 text-slate-400 border border-border ${sizeClasses} ${className}`}>
      {value}
    </span>
  );
}
