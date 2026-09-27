"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { User } from "@/types";
import {
  ArrowUpRight,
  Search,
  MessageSquare,
  Network,
  FileCode,
  GitBranch,
  BookOpen,
  LayoutDashboard,
  LogOut,
  User as UserIcon,
  Menu,
  X,
  ShieldCheck,
  BarChart3,
  GitPullRequest,
  Settings,
  Shield,
  Layers,
} from "lucide-react";

interface GlobalNavbarProps {
  user?: User | null;
  activeRepoName?: string;
  onOpenCommandPalette?: () => void;
  onToggleSidebar?: () => void;
  showSidebarToggle?: boolean;
}

export function GlobalNavbar({
  user: initialUser,
  activeRepoName,
  onOpenCommandPalette,
  onToggleSidebar,
  showSidebarToggle = false,
}: GlobalNavbarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(initialUser || null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    if (!initialUser) {
      api.getMe().then((u) => setUser(u)).catch(() => setUser(null));
    } else {
      setUser(initialUser);
    }
  }, [initialUser, pathname]);

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch {}
    setUser(null);
    router.push("/login");
  };

  const navLinks = [
    { label: "Command Center", href: "/dashboard", icon: LayoutDashboard },
    { label: "Dual Search", href: "/dashboard/search", icon: Search },
    { label: "Graph Engine", href: "/dashboard/graph", icon: Network },
    { label: "Grounded Chat", href: "/dashboard/chat", icon: MessageSquare, badge: "RAG" },
    { label: "AST Explorer", href: "/dashboard/explorer", icon: FileCode },
    { label: "Repositories", href: "/dashboard/repositories", icon: GitBranch },
    { label: "Docs & Spec", href: "/dashboard/docs", icon: BookOpen },
  ];

  const isActive = (href: string) => {
    if (href === "/dashboard" && pathname === "/dashboard") return true;
    if (href !== "/dashboard" && pathname.startsWith(href)) return true;
    return false;
  };

  return (
    <header className="border-b border-border bg-surface-200/95 backdrop-blur-md sticky top-0 z-50 transition-colors">
      <div className="max-w-[1536px] mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Left: Brand Logo + Sidebar Toggle */}
        <div className="flex items-center space-x-3">
          {showSidebarToggle && (
            <button
              onClick={onToggleSidebar}
              className="p-1.5 rounded-lg border border-border bg-surface-300 hover:bg-surface-100 text-slate-400 hover:text-white transition lg:hidden"
              title="Toggle Sidebar"
            >
              <Layers className="h-4 w-4" />
            </button>
          )}

          <Link href="/" className="flex items-center space-x-3 group">
            <div className="h-8 w-8 rounded-lg bg-surface-100 border border-border flex items-center justify-center font-mono font-black text-sm text-brand-crimson group-hover:border-brand-crimson transition-colors shadow-inner">
              CA
            </div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-lg tracking-tight text-white uppercase font-mono">
                CodeAtlas
              </span>
              <span className="hidden sm:inline-block text-[9px] font-mono px-1.5 py-0.5 rounded bg-surface-100 text-brand-sky border border-border font-bold">
                PROD
              </span>
            </div>
          </Link>

          {activeRepoName && (
            <div className="hidden xl:flex items-center space-x-1.5 pl-3 border-l border-border text-xs font-mono text-slate-400">
              <GitBranch className="h-3.5 w-3.5 text-brand-crimson" />
              <span className="text-slate-200 font-semibold">{activeRepoName}</span>
            </div>
          )}
        </div>

        {/* Center: Universal Navigation Links */}
        <nav className="hidden lg:flex items-center space-x-1 xl:space-x-2 font-mono text-xs uppercase tracking-wider">
          {navLinks.map((link) => {
            const active = isActive(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`px-3 py-1.5 rounded-lg transition-all flex items-center space-x-1.5 ${
                  active
                    ? "bg-surface-100 text-brand-sky font-bold border border-border shadow-sm"
                    : "text-slate-400 hover:text-white hover:bg-surface-300/50"
                }`}
              >
                <span>{link.label}</span>
                {link.badge && (
                  <span className="text-[8px] font-bold px-1 py-0.2 bg-brand-crimson/20 border border-brand-crimson/40 text-brand-crimson rounded">
                    {link.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Right: Actions, Search, Auth */}
        <div className="flex items-center space-x-2.5">
          {onOpenCommandPalette && (
            <button
              onClick={onOpenCommandPalette}
              className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-lg border border-border bg-surface-300 hover:bg-surface-100 text-xs font-mono text-slate-400 hover:text-slate-200 transition shadow-sm"
            >
              <Search className="h-3.5 w-3.5 text-slate-400" />
              <span className="hidden md:inline">Quick Jump</span>
              <kbd className="kbd-badge text-[10px]">⌘K</kbd>
            </button>
          )}

          {user ? (
            <div className="flex items-center space-x-2">
              <Link
                href="/dashboard/settings"
                className="hidden sm:flex items-center space-x-2 p-1.5 pr-3 rounded-lg border border-border bg-surface-300 hover:bg-surface-100 text-xs font-mono text-slate-200 transition"
              >
                <div className="h-6 w-6 rounded bg-brand-crimson/20 border border-brand-crimson/40 flex items-center justify-center font-bold text-[11px] text-brand-crimson">
                  {user.full_name?.charAt(0) || user.email.charAt(0).toUpperCase()}
                </div>
                <span className="hidden md:inline font-semibold truncate max-w-[120px]">
                  {user.full_name || user.email.split("@")[0]}
                </span>
              </Link>

              <button
                onClick={handleLogout}
                title="Sign Out"
                className="p-2 rounded-lg border border-border bg-surface-300 hover:bg-surface-100 text-slate-400 hover:text-brand-crimson transition"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <Link
                href="/login"
                className="px-3.5 py-1.5 rounded-lg border border-border bg-surface-300 hover:bg-surface-100 text-slate-300 hover:text-white font-mono text-xs uppercase font-semibold transition-colors"
              >
                Sign In
              </Link>
              <Link
                href="/dashboard"
                className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-brand-crimson hover:bg-brand-crimsonHover text-white font-mono text-xs uppercase font-extrabold tracking-wider transition-all shadow-md shadow-brand-crimson/20 active:scale-95"
              >
                <span>Console</span>
                <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          )}

          {/* Mobile Menu Toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg border border-border bg-surface-300 text-slate-400 hover:text-white lg:hidden transition"
            title="Toggle Menu"
          >
            {mobileMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-border bg-surface-200/98 px-6 py-4 space-y-3 font-mono text-xs uppercase">
          <div className="space-y-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const active = isActive(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center justify-between px-3 py-2.5 rounded-lg transition-colors ${
                    active
                      ? "bg-surface-100 text-brand-sky font-bold border border-border"
                      : "text-slate-300 hover:bg-surface-300"
                  }`}
                >
                  <div className="flex items-center space-x-2.5">
                    <Icon className="h-4 w-4" />
                    <span>{link.label}</span>
                  </div>
                  {link.badge && (
                    <span className="text-[9px] font-bold px-1.5 py-0.5 bg-brand-crimson text-white rounded">
                      {link.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>

          <div className="pt-3 border-t border-border flex items-center justify-between">
            {user ? (
              <div className="flex items-center justify-between w-full">
                <span className="text-slate-400">{user.email}</span>
                <button
                  onClick={handleLogout}
                  className="px-3 py-1.5 rounded border border-border bg-surface-300 text-brand-crimson hover:bg-surface-100 font-bold"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-3 w-full">
                <Link
                  href="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex-1 py-2 text-center rounded border border-border bg-surface-300 text-white font-bold"
                >
                  Sign In
                </Link>
                <Link
                  href="/register"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex-1 py-2 text-center rounded bg-brand-crimson text-white font-bold"
                >
                  Sign Up
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
