"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { ArrowUpRight, AlertCircle, Loader2, Lock, User, ShieldCheck } from "lucide-react";
import { GlobalNavbar } from "@/components/GlobalNavbar";
import { GlobalFooter } from "@/components/GlobalFooter";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await api.login(email, password);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Failed to authenticate. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-slate-100 flex flex-col font-sans selection:bg-brand-crimson selection:text-white bg-tech-grid">
      <GlobalNavbar />

      <main className="flex-1 flex flex-col justify-center items-center px-6 py-16">
        <div className="w-full max-w-md space-y-6">
          {/* Brand Header */}
          <div className="text-center space-y-2">
            <Link href="/" className="inline-flex items-center space-x-3 mb-2 group">
              <div className="h-10 w-10 bg-surface-200 border border-border rounded-xl flex items-center justify-center font-mono font-black text-sm text-brand-crimson group-hover:border-brand-crimson transition shadow-sm">
                CA
              </div>
              <span className="font-extrabold text-xl tracking-tight text-white uppercase font-mono">CodeAtlas</span>
            </Link>
            <h2 className="text-xl font-bold tracking-tight text-white font-mono">
              Sign in to Console
            </h2>
            <p className="text-xs text-slate-400 font-mono">
              Access indexed repositories &amp; grounded developer intelligence
            </p>
          </div>

          {/* Card Form */}
          <div className="p-8 border border-border bg-surface-200/90 rounded-2xl shadow-2xl backdrop-blur-md space-y-6">
            {error && (
              <div className="p-4 border border-brand-crimson/30 bg-brand-crimson/10 rounded-xl flex items-start space-x-3 text-brand-crimson text-xs font-mono">
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4 font-mono text-xs">
              <div className="space-y-1.5">
                <label className="block text-[11px] font-medium text-slate-300 uppercase tracking-wider">
                  Work Email
                </label>
                <div className="relative">
                  <User className="h-4 w-4 absolute left-3 top-3 text-slate-500" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="developer@company.com"
                    className="w-full pl-9 pr-4 py-2.5 bg-surface-300 border border-border rounded-lg focus:border-brand-crimson focus:ring-1 focus:ring-brand-crimson text-white text-xs outline-none transition placeholder:text-slate-600"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="block text-[11px] font-medium text-slate-300 uppercase tracking-wider">
                    Password
                  </label>
                </div>
                <div className="relative">
                  <Lock className="h-4 w-4 absolute left-3 top-3 text-slate-500" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-9 pr-4 py-2.5 bg-surface-300 border border-border rounded-lg focus:border-brand-crimson focus:ring-1 focus:ring-brand-crimson text-white text-xs outline-none transition placeholder:text-slate-600"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-4 flex items-center justify-center space-x-2 px-4 py-3 bg-brand-crimson hover:bg-rose-600 disabled:opacity-50 text-white rounded-lg font-mono text-xs uppercase font-bold tracking-wider transition shadow-lg shadow-brand-crimson/20 active:scale-98"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>AUTHENTICATING...</span>
                  </>
                ) : (
                  <>
                    <span>AUTHENTICATE SESSION</span>
                    <ArrowUpRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>

            <div className="pt-4 border-t border-border flex items-center justify-between text-xs font-mono">
              <span className="text-slate-500">Need an account?</span>
              <Link
                href="/register"
                className="text-brand-crimson hover:text-rose-400 font-semibold transition"
              >
                Register &rarr;
              </Link>
            </div>
          </div>

          {/* Demo Credentials Pill */}
          <div className="p-4 border border-border bg-surface-200/50 rounded-xl text-center font-mono text-[11px] text-slate-400 space-y-1">
            <div className="flex items-center justify-center space-x-1 text-slate-300">
              <ShieldCheck className="h-3.5 w-3.5 text-brand-emerald" />
              <span>Default Demo Login</span>
            </div>
            <div><code className="text-brand-sky">admin@codeatlas.dev</code> / <code className="text-brand-sky">admin123456</code></div>
          </div>
        </div>
      </main>

      <GlobalFooter />
    </div>
  );
}

