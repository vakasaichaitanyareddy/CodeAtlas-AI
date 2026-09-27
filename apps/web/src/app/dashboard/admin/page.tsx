"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { User } from "@/types";
import { Shield, ShieldAlert, CheckCircle2, Lock, Terminal, ArrowLeft, KeyRound } from "lucide-react";

export default function AdminPage() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const u = await api.getMe();
        setUser(u);
      } catch {
        setUser(null);
      }
    }
    load();
  }, []);

  const isAdmin = user?.role === "ADMIN";

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center space-x-3 text-xs text-slate-500 font-mono">
        <Link href="/dashboard" className="hover:text-slate-300 flex items-center space-x-1">
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Dashboard</span>
        </Link>
        <span>/</span>
        <span className="text-slate-300">Admin</span>
      </div>

      <div>
        <h1 className="text-xl font-bold tracking-tight text-white flex items-center space-x-2.5 font-mono">
          <Shield className="h-5 w-5 text-brand-emerald" />
          <span>Enterprise Administration &amp; RBAC Governance</span>
        </h1>
        <p className="mt-1 text-xs text-slate-400 font-mono">
          Role-based access control (RBAC) governance, session authorization traces, and audit logs.
        </p>
      </div>

      {!isAdmin ? (
        <div className="p-8 rounded-2xl border border-brand-crimson/30 bg-brand-crimson/10 text-center space-y-3 font-mono shadow-sm">
          <div className="h-10 w-10 rounded-full bg-brand-crimson/20 border border-brand-crimson/40 flex items-center justify-center text-brand-crimson mx-auto">
            <Lock className="h-5 w-5" />
          </div>
          <h2 className="text-sm font-bold text-white">Access Restricted (HTTP 403 Forbidden)</h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            This administrative endpoint requires the <code className="font-mono text-brand-crimson font-bold">ADMIN</code> role. Your active session role is{" "}
            <code className="font-mono text-slate-200">{user?.role || "USER"}</code>.
          </p>
        </div>
      ) : (
        <div className="p-6 rounded-xl border border-border bg-surface-200/90 space-y-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center space-x-2">
              <Shield className="h-4 w-4 text-brand-emerald" />
              <h2 className="text-sm font-semibold text-slate-200 font-mono">RBAC Policy Guard Active</h2>
            </div>
            <span className="text-[10px] font-mono text-brand-emerald bg-brand-emerald/10 px-2 py-0.5 rounded border border-brand-emerald/30 font-bold">
              VERIFIED
            </span>
          </div>

          <p className="text-xs text-slate-400 font-mono leading-relaxed">
            Backend RBAC security is enforced via <code className="font-mono text-brand-sky">require_role(&quot;ADMIN&quot;)</code> FastAPI dependency. All protected administrative mutations are strictly locked to privileged operators.
          </p>

          <div className="p-4 rounded-lg bg-surface-300 border border-border font-mono text-xs text-slate-300 space-y-1.5">
            <div className="text-slate-500 font-bold">// RBAC Verification Audit Trace</div>
            <div>Admin ID: <span className="text-brand-sky">{user?.id}</span></div>
            <div>Admin Email: <span className="text-brand-sky">{user?.email}</span></div>
            <div>Privilege Scope: <span className="text-brand-emerald">[REPO_INDEX, REPO_DELETE, ROLE_ELEVATE, METRICS_READ]</span></div>
          </div>
        </div>
      )}
    </div>
  );
}
