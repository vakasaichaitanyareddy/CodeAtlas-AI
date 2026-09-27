"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { ArrowUpRight, AlertCircle, Loader2, Lock, User } from "lucide-react";
import { GlobalNavbar } from "@/components/GlobalNavbar";
import { GlobalFooter } from "@/components/GlobalFooter";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setLoading(true);

    try {
      await api.register(email, password, fullName || undefined);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Registration failed. Please try again.");
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
            <span className="font-extrabold text-xl tracking-tight text-white uppercase">CodeAtlas</span>
          </Link>
          <h2 className="text-xl font-bold tracking-tight text-white font-mono">
            Create Developer Account
          </h2>
          <p className="text-xs text-slate-400 font-mono">
            Provision developer workspace &amp; begin codebase indexing
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
                Full Name
              </label>
              <div className="relative">
                <User className="h-4 w-4 absolute left-3 top-3 text-slate-500" />
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Ada Lovelace"
                  className="w-full pl-9 pr-4 py-2.5 bg-surface-300 border border-border rounded-lg focus:border-brand-crimson focus:ring-1 focus:ring-brand-crimson text-white text-xs outline-none transition placeholder:text-slate-600"
                />
              </div>
            </div>

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
              <label className="block text-[11px] font-medium text-slate-300 uppercase tracking-wider">
                Password (min. 8 characters)
              </label>
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
                  <span>CREATING ACCOUNT...</span>
                </>
              ) : (
                <>
                  <span>CREATE ACCOUNT</span>
                  <ArrowUpRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          <div className="pt-4 border-t border-border flex items-center justify-between text-xs font-mono">
            <span className="text-slate-500">Already have an account?</span>
            <Link
              href="/login"
              className="text-brand-crimson hover:text-rose-400 font-semibold transition"
            >
              Sign In &rarr;
            </Link>
          </div>
        </div>
      </main>

      <GlobalFooter />
    </div>
  );
}

