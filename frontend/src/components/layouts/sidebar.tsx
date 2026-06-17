"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useUIStore } from "@/store/ui-store";
import {
  LayoutDashboard,
  Users,
  Bot,
  Megaphone,
  FlaskConical,
  BarChart3,
  Settings,
  Shield,
  ChevronLeft,
  ChevronRight,
  Building2,
} from "lucide-react";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Customers", href: "/customers", icon: Users },
  { name: "Twins", href: "/twins", icon: Bot },
  { name: "Campaigns", href: "/campaigns", icon: Megaphone },
  { name: "Simulation Lab", href: "/simulation-lab", icon: FlaskConical },
  { name: "Analytics", href: "/analytics", icon: BarChart3 },
  { name: "Settings", href: "/settings", icon: Settings },
  { name: "Administration", href: "/administration", icon: Shield },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, setSidebarCollapsed } = useUIStore();

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 flex h-screen flex-col border-r bg-background transition-all duration-300",
        sidebarCollapsed ? "w-16" : "w-64"
      )}
    >
      <div className="flex h-14 items-center border-b px-4">
        {!sidebarCollapsed && (
          <div className="flex items-center gap-2">
            <Bot className="h-6 w-6 text-prometheus-500" />
            <span className="text-lg font-bold">PROMETHEUS</span>
          </div>
        )}
        {sidebarCollapsed && (
          <Bot className="mx-auto h-6 w-6 text-prometheus-500" />
        )}
      </div>

      {!sidebarCollapsed && (
        <div className="border-b px-4 py-3">
          <Button
            variant="outline"
            className="w-full justify-start gap-2 text-sm"
            size="sm"
          >
            <Building2 className="h-4 w-4" />
            <span className="truncate">Acme Corp</span>
          </Button>
        </div>
      )}

      <nav className="flex-1 space-y-1 p-2">
        {navigation.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                sidebarCollapsed && "justify-center px-2"
              )}
            >
              <item.icon className="h-5 w-5 shrink-0" />
              {!sidebarCollapsed && <span>{item.name}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-2">
        <Button
          variant="ghost"
          size="sm"
          className={cn(
            "w-full",
            sidebarCollapsed ? "justify-center" : "justify-start"
          )}
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4 mr-2" />
              Collapse
            </>
          )}
        </Button>
      </div>
    </aside>
  );
}
