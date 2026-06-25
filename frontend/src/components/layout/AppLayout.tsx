import React, { useState, useEffect } from 'react';
import { Link, useLocation, Outlet, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Database, 
  Sliders, 
  BarChart3, 
  Sun, 
  Moon, 
  RefreshCw,
  Bell,
  Menu,
  ChevronLeft,
  ChevronRight,
  LogOut,
  User
} from 'lucide-react';
import { useUIStore } from '../../store/ui-store';
import { useAuthStore } from '../../store/auth-store';
import { cn } from '../../utils';
import { useQueryClient } from '@tanstack/react-query';

export function AppLayout() {
  const { sidebarCollapsed, setSidebarCollapsed, dateRange, setDateRange, theme, setTheme } = useUIStore();
  const { user, clearAuth } = useAuthStore();
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [freshTime, setFreshTime] = useState(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
  const [profileOpen, setProfileOpen] = useState(false);

  useEffect(() => {
    // Initial theme sync
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
  }, [theme]);

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: <LayoutDashboard className="h-5 w-5" /> },
    { name: 'Twin Explorer', path: '/twins', icon: <Database className="h-5 w-5" /> },
    { name: 'Simulation Lab', path: '/simulation-lab', icon: <Sliders className="h-5 w-5" /> },
    { name: 'Scenario Comparison', path: '/simulations/compare', icon: <BarChart3 className="h-5 w-5" /> },
  ];

  const handleRefreshAll = () => {
    queryClient.invalidateQueries();
    setFreshTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
  };

  const handleLogout = () => {
    clearAuth();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex transition-colors duration-200 font-sans">
      {/* Sidebar Navigation */}
      <aside
        className={cn(
          "bg-zinc-950 border-r border-zinc-900 flex flex-col justify-between shrink-0 transition-all duration-300 z-30",
          sidebarCollapsed ? "w-16" : "w-64"
        )}
      >
        <div>
          {/* Brand header */}
          <div className="h-16 flex items-center justify-between px-4 border-b border-zinc-900">
            {!sidebarCollapsed && (
              <span className="text-lg font-bold tracking-wider text-white flex items-center gap-1.5 font-sans">
                TWIN<span className="text-accent">CX</span>
              </span>
            )}
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="text-zinc-400 hover:text-white p-1 rounded-md hover:bg-zinc-900 ml-auto"
            >
              {sidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="mt-6 px-2 space-y-1.5">
            {navItems.map((item) => {
              const active = location.pathname.startsWith(item.path);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors group relative",
                    active 
                      ? "bg-accent text-white" 
                      : "text-zinc-400 hover:text-white hover:bg-zinc-900"
                  )}
                >
                  {item.icon}
                  {!sidebarCollapsed && <span>{item.name}</span>}
                  {sidebarCollapsed && (
                    <span className="absolute left-full rounded-md px-2 py-1 ml-6 bg-zinc-900 text-xs text-white opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50 shadow-md">
                      {item.name}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-zinc-900">
          <div className="flex items-center justify-between">
            {!sidebarCollapsed && (
              <div className="flex flex-col">
                <span className="text-xs font-semibold text-white">{user?.name || 'Administrator'}</span>
                <span className="text-[10px] text-zinc-500 font-mono">PROMETHEUS-X</span>
              </div>
            )}
            <button
              onClick={handleLogout}
              className="text-zinc-400 hover:text-white p-1 rounded hover:bg-zinc-900"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <header className="h-16 border-b border-zinc-200 dark:border-zinc-800 bg-card flex items-center justify-between px-6 z-20 shrink-0">
          <div className="flex items-center gap-4">
            {/* Range Toggle */}
            <div className="flex rounded-md border border-zinc-200 dark:border-zinc-800 p-0.5 bg-zinc-50 dark:bg-zinc-900/50">
              {(['7D', '30D', '90D', 'YTD'] as const).map((r) => (
                <button
                  key={r}
                  onClick={() => setDateRange(r)}
                  className={cn(
                    "px-3 py-1 rounded text-xs font-semibold transition-all",
                    dateRange === r
                      ? "bg-white dark:bg-zinc-800 text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Freshness Indicator */}
            <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono bg-zinc-50 dark:bg-zinc-900/40 border px-3 py-1.5 rounded-md">
              <span className="h-2 w-2 rounded-full bg-success animate-pulse"></span>
              Synced: {freshTime}
            </div>

            {/* Refresh Button */}
            <button
              onClick={handleRefreshAll}
              className="p-2 border rounded-md hover:bg-zinc-50 dark:hover:bg-zinc-900/40 text-muted-foreground hover:text-foreground"
              title="Invalidate and Refetch"
            >
              <RefreshCw className="h-4 w-4" />
            </button>

            {/* Theme Toggle */}
            <button
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="p-2 border rounded-md hover:bg-zinc-50 dark:hover:bg-zinc-900/40 text-muted-foreground hover:text-foreground"
            >
              {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>

            {/* Profile Dropdown */}
            <div className="relative">
              <button
                onClick={() => setProfileOpen(!profileOpen)}
                className="h-8 w-8 rounded-full border bg-muted flex items-center justify-center text-xs font-semibold hover:border-zinc-400 dark:hover:border-zinc-600"
              >
                {user?.first_name?.charAt(0) || 'A'}
              </button>
              {profileOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setProfileOpen(false)} />
                  <div className="absolute right-0 mt-2 w-48 rounded-md border bg-card py-1 shadow-lg z-50">
                    <div className="px-4 py-2 border-b">
                      <p className="text-xs font-semibold text-foreground">{user?.name}</p>
                      <p className="text-[10px] text-muted-foreground truncate">{user?.email}</p>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="w-full text-left px-4 py-2 text-xs text-error hover:bg-zinc-50 dark:hover:bg-zinc-900/30 flex items-center gap-2"
                    >
                      <LogOut className="h-3.5 w-3.5" />
                      Sign Out
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        {/* Content Body */}
        <main className="flex-1 overflow-y-auto px-6 py-6 min-w-0 bg-background/50">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
export default AppLayout;
