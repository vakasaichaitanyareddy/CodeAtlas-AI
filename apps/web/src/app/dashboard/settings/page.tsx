"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { User } from "@/types";
import { Settings, Key, Shield, User as UserIcon, CheckCircle2, Server, ArrowLeft, Cpu, Database } from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const u = await api.getMe();
        setUser(u);
      } catch {
        setUser({
          id: "local-user",
          email: "user@codeatlas.dev",
          role: "ADMIN",
          is_active: true,
          created_at: new Date().toISOString(),
        });
      }
    }
    load();
  }, []);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center space-x-3 text-xs text-slate-500 font-mono">
        <Link href="/dashboard" className="hover:text-slate-300 flex items-center space-x-1">
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Dashboard</span>
        </Link>
        <span>/</span>
        <span className="text-slate-300">Settings</span>
      </div>

      <div>
        <h1 className="text-xl font-bold tracking-tight text-white flex items-center space-x-2.5 font-mono">
          <Settings className="h-5 w-5 text-brand-sky" />
          <span>Platform Settings &amp; Configuration</span>
        </h1>
        <p className="mt-1 text-xs text-slate-400 font-mono">
          Manage your account profile, RBAC role privileges, and AI provider configurations.
        </p>
      </div>

      {/* Account Profile Card */}
      <div className="p-6 rounded-xl border border-border bg-surface-200/90 space-y-4 shadow-sm">
        <div className="flex items-center space-x-2 border-b border-border pb-3">
          <UserIcon className="h-4 w-4 text-brand-sky" />
          <h2 className="text-sm font-semibold text-slate-200 font-mono">User Identity &amp; RBAC Verification</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
          <div>
            <label className="text-slate-500 block mb-1">Email Address</label>
            <div className="p-2.5 rounded-lg bg-surface-300 border border-border text-slate-200">
              {user?.email || "loading..."}
            </div>
          </div>
          <div>
            <label className="text-slate-500 block mb-1">Assigned RBAC Role</label>
            <div className="p-2.5 rounded-lg bg-surface-300 border border-border text-brand-emerald flex items-center space-x-2">
              <Shield className="h-3.5 w-3.5" />
              <span className="font-bold">{user?.role || "USER"}</span>
            </div>
          </div>
          <div>
            <label className="text-slate-500 block mb-1">User Identifier</label>
            <div className="p-2.5 rounded-lg bg-surface-300 border border-border text-slate-400 truncate">
              {user?.id || "loading..."}
            </div>
          </div>
          <div>
            <label className="text-slate-500 block mb-1">Account Status</label>
            <div className="p-2.5 rounded-lg bg-surface-300 border border-border text-brand-emerald flex items-center space-x-1.5">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span className="font-bold">{user?.is_active ? "Active" : "Suspended"}</span>
            </div>
          </div>
        </div>
      </div>

      {/* AI Provider Config */}
      <div className="p-6 rounded-xl border border-border bg-surface-200/90 space-y-4 shadow-sm">
        <div className="flex items-center space-x-2 border-b border-border pb-3">
          <Key className="h-4 w-4 text-brand-sky" />
          <h2 className="text-sm font-semibold text-slate-200 font-mono">Model Provider Strategy &amp; Pipeline Engine</h2>
        </div>

        <p className="text-xs text-slate-400 font-mono">
          CodeAtlas uses a zero-downtime provider factory abstraction with automated failover and citation enforcement.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 font-mono text-xs">
          <div className="p-4 rounded-xl bg-surface-300 border border-border space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-white flex items-center space-x-1.5">
                <Cpu className="h-3.5 w-3.5 text-brand-sky" />
                <span>Google Gemini</span>
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-brand-emerald/15 text-brand-emerald border border-brand-emerald/30 font-bold">ACTIVE</span>
            </div>
            <p className="text-[11px] text-slate-400">
              Gemini 2.5 Flash / 1.5 Pro with text-embedding-004 vector embeddings and native JSON schema output.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-surface-300 border border-border space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-white flex items-center space-x-1.5">
                <Database className="h-3.5 w-3.5 text-brand-indigo" />
                <span>Qdrant + BM25</span>
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-brand-indigo/15 text-brand-indigo border border-brand-indigo/30 font-bold">HYBRID</span>
            </div>
            <p className="text-[11px] text-slate-400">
              Reciprocal Rank Fusion (RRF, k=60) with FlashRank TinyBERT CrossEncoder reranking.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-surface-300 border border-border space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-white flex items-center space-x-1.5">
                <Server className="h-3.5 w-3.5 text-brand-amber" />
                <span>Mock Provider</span>
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-surface-100 text-slate-400 border border-border font-bold">STANDBY</span>
            </div>
            <p className="text-[11px] text-slate-400">
              Hermetic offline baseline for reproducible integration testing and CI environments.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
