"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { User, Repository } from "@/types";
import { CommandPalette } from "@/components/CommandPalette";
import { GlobalNavbar } from "@/components/GlobalNavbar";
import { GlobalFooter } from "@/components/GlobalFooter";
import {
  LayoutDashboard,
  GitBranch,
  FileCode,
  MessageSquare,
  Network,
  GitPullRequest,
  ShieldCheck,
  BookOpen,
  BarChart3,
  Settings,
  Shield,
  LogOut,
  ChevronDown,
  Search,
  Activity,
  Layers,
  ArrowLeft,
  ArrowRight,
  ExternalLink,
  Cpu,
  Boxes,
} from "lucide-react";

interface NavGroup {
  title: string;
  items: Array<{
    label: string;
    href: string;
    icon: React.ComponentType<{ className?: string }>;
    badge?: string;
  }>;
}

const NAV_GROUPS: NavGroup[] = [
  {
    title: "Core Intelligence",
    items: [
      { label: "Overview", href: "/dashboard", icon: LayoutDashboard },
      { label: "Repositories", href: "/dashboard/repositories", icon: GitBranch },
      { label: "AST Explorer", href: "/dashboard/explorer", icon: FileCode },
      { label: "Dual Search", href: "/dashboard/search", icon: Search },
      { label: "Grounded Chat", href: "/dashboard/chat", icon: MessageSquare, badge: "RAG" },
    ],
  },
  {
    title: "Graph & Architecture",
    items: [
      { label: "Dependency Graph", href: "/dashboard/graph", icon: Network },
      { label: "Pull Requests", href: "/dashboard/pull-requests", icon: GitPullRequest },
    ],
  },
  {
    title: "Observability & Platform",
    items: [
      { label: "Analytics & Eval", href: "/dashboard/analytics", icon: BarChart3 },
      { label: "Security Isolation", href: "/dashboard/security", icon: ShieldCheck },
      { label: "Documentation", href: "/dashboard/docs", icon: BookOpen },
      { label: "Settings", href: "/dashboard/settings", icon: Settings },
      { label: "Admin Console", href: "/dashboard/admin", icon: Shield },
    ],
  },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const [u, repos] = await Promise.all([
          api.getMe().catch(() => null),
          api.listRepositories().catch(() => []),
        ]);
        if (!u) {
          router.push("/login");
          return;
        }
        setUser(u);
        setRepositories(repos);
      } catch {
        router.push("/login");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [router]);

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileDrawerOpen(false);
  }, [pathname]);

  const handleLogout = async () => {
    await api.logout();
    router.push("/login");
  };

  const activeRepo = repositories.length > 0 ? repositories[0] : null;

  // Derive section name for breadcrumbs
  const getSectionTitle = () => {
    for (const group of NAV_GROUPS) {
      for (const item of group.items) {
        if (pathname === item.href) return item.label;
      }
    }
    if (pathname.includes("/dashboard/graph")) return "Dependency Graph";
    if (pathname.includes("/dashboard/chat")) return "Grounded Chat";
    if (pathname.includes("/dashboard/search")) return "Hybrid Search";
    if (pathname.includes("/dashboard/repositories")) return "Repositories";
    return "Overview";
  };

  return (
    <div className="min-h-screen bg-background text-slate-100 flex flex-col font-sans selection:bg-brand-sky/30 selection:text-sky-200">
      {/* Universal Top Navigation Header - Same for All Pages */}
      <GlobalNavbar
        user={user}
        activeRepoName={activeRepo?.name}
        onOpenCommandPalette={() => setCommandPaletteOpen(true)}
        onToggleSidebar={() => setMobileDrawerOpen(true)}
        showSidebarToggle={true}
      />

      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        currentRepoName={activeRepo?.name}
      />

      {/* Mobile Drawer Backdrop */}
      {mobileDrawerOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/80 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileDrawerOpen(false)}
        />
      )}

      {/* Main Two-Column Dashboard Workspace */}
      <div className="flex-1 flex min-h-[calc(100vh-4rem)]">
        {/* Primary Sidebar (Desktop + Mobile Drawer) */}
        <aside
          className={`fixed inset-y-0 left-0 top-16 z-40 lg:static flex flex-col justify-between border-r border-border bg-surface-200/95 transition-all duration-300 select-none ${
            isCollapsed ? "w-16" : "w-64"
          } ${mobileDrawerOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}
        >
          <div className="flex flex-col h-full overflow-y-auto">
            {/* Active Repository Selector */}
            {!isCollapsed && (
              <div className="p-3 border-b border-border/80 bg-surface-300/40">
                <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-1.5 px-1">
                  Active Repository
                </div>
                <Link
                  href="/dashboard/repositories"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-surface-100/60 hover:bg-surface-50 text-left flex items-center justify-between text-xs transition-colors group"
                >
                  <div className="flex items-center space-x-2 overflow-hidden">
                    <GitBranch className="h-3.5 w-3.5 text-brand-crimson flex-shrink-0" />
                    <span className="font-mono font-semibold text-slate-200 group-hover:text-white truncate text-[11px]">
                      {activeRepo ? activeRepo.name : "Select Repository..."}
                    </span>
                  </div>
                  <ChevronDown className="h-3.5 w-3.5 text-slate-500 flex-shrink-0" />
                </Link>
              </div>
            )}

            {/* Navigation Groups */}
            <nav className="flex-1 p-2 space-y-4">
              {NAV_GROUPS.map((group, gIdx) => (
                <div key={gIdx} className="space-y-1">
                  {!isCollapsed && (
                    <div className="px-3 text-[10px] font-mono uppercase tracking-widest text-slate-500 font-semibold mb-1">
                      {group.title}
                    </div>
                  )}
                  {group.items.map((item) => {
                    const Icon = item.icon;
                    const isActive = pathname === item.href;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        title={isCollapsed ? item.label : undefined}
                        className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs font-mono tracking-tight transition-all group ${
                          isActive
                            ? "bg-surface-100 text-brand-sky font-bold border border-border shadow-sm"
                            : "text-slate-400 hover:text-slate-100 hover:bg-surface-100/50"
                        }`}
                      >
                        <div className="flex items-center space-x-3 truncate">
                          <Icon
                            className={`h-4 w-4 flex-shrink-0 transition-colors ${
                              isActive
                                ? "text-brand-sky"
                                : "text-slate-500 group-hover:text-slate-300"
                            }`}
                          />
                          {!isCollapsed && <span className="truncate">{item.label}</span>}
                        </div>
                        {!isCollapsed && item.badge && (
                          <span className="text-[9px] px-1.5 py-0.2 rounded bg-surface-300 text-brand-crimson border border-brand-crimson/30 font-bold">
                            {item.badge}
                          </span>
                        )}
                      </Link>
                    );
                  })}
                </div>
              ))}
            </nav>

            {/* System Status Pill */}
            {!isCollapsed && (
              <div className="p-3 border-t border-border bg-surface-300/30">
                <div className="p-2.5 rounded-lg border border-border bg-surface-300 flex items-center justify-between text-[10px] font-mono">
                  <div className="flex items-center space-x-2">
                    <span className="h-2 w-2 rounded-full bg-brand-emerald animate-pulse"></span>
                    <span className="text-slate-300 font-semibold">8-Containers Active</span>
                  </div>
                  <span className="text-slate-500">646 LOC/s</span>
                </div>
              </div>
            )}

            {/* User Account Section */}
            <div className="p-3 border-t border-border bg-surface-300">
              <div className="flex items-center justify-between p-2 rounded-lg bg-surface-100 border border-border">
                <div className="flex items-center space-x-2.5 overflow-hidden">
                  <div className="h-7 w-7 rounded-md bg-surface-300 border border-border flex items-center justify-center text-xs font-mono font-bold text-brand-crimson flex-shrink-0">
                    {user?.full_name?.charAt(0) || user?.email?.charAt(0) || "U"}
                  </div>
                  {!isCollapsed && (
                    <div className="overflow-hidden">
                      <p className="text-xs font-bold text-white truncate font-sans">
                        {user?.full_name || "Engineer"}
                      </p>
                      <p className="text-[10px] text-slate-400 truncate font-mono">
                        {user?.email || "loading..."}
                      </p>
                    </div>
                  )}
                </div>
                {!isCollapsed && (
                  <button
                    onClick={handleLogout}
                    title="Sign Out"
                    className="p-1.5 rounded hover:bg-surface-300 text-slate-500 hover:text-brand-crimson transition-colors"
                  >
                    <LogOut className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Desktop Collapse Toggle */}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="hidden lg:flex items-center justify-center h-7 border-t border-border bg-surface-300 text-slate-500 hover:text-white transition-colors"
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? (
              <ArrowRight className="h-3.5 w-3.5" />
            ) : (
              <ArrowLeft className="h-3.5 w-3.5" />
            )}
          </button>
        </aside>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-background">
          {/* Sub-header Breadcrumb & Quick Actions */}
          <div className="h-12 border-b border-border bg-surface-300/40 backdrop-blur-sm px-4 sm:px-6 flex items-center justify-between z-10 flex-shrink-0">
            {/* Breadcrumb Trail */}
            <div className="flex items-center space-x-2 text-xs font-mono truncate">
              <Link href="/dashboard" className="text-slate-500 hover:text-slate-300 transition-colors">
                Console
              </Link>
              <span className="text-slate-600">/</span>
              <span className="text-slate-300 font-semibold truncate">
                {activeRepo ? activeRepo.name : "celery-repo"}
              </span>
              <span className="text-slate-600">/</span>
              <span className="text-brand-sky font-bold">{getSectionTitle()}</span>
            </div>

            {/* Ingestion & Grounding Status Indicator */}
            <div className="flex items-center space-x-3">
              <div className="hidden sm:flex items-center space-x-2 px-2.5 py-1 rounded-lg border border-emerald-500/20 bg-emerald-500/10 text-[10px] font-mono text-emerald-400 uppercase tracking-wider font-semibold">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>INDEXED (768-D)</span>
              </div>
            </div>
          </div>

          {/* Main Viewport Body */}
          <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
            {children}
          </main>
        </div>
      </div>

      {/* Universal Footer */}
      <GlobalFooter />
    </div>
  );
}

