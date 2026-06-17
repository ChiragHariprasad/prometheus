import { create } from "zustand";
import { persist } from "zustand/middleware";

type Theme = "light" | "dark" | "system";

interface UIState {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  theme: Theme;
  activePage: string;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setTheme: (theme: Theme) => void;
  setActivePage: (page: string) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      sidebarCollapsed: false,
      theme: "system",
      activePage: "dashboard",
      toggleSidebar: () =>
        set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
      setSidebarCollapsed: (sidebarCollapsed) =>
        set({ sidebarCollapsed }),
      setTheme: (theme) => set({ theme }),
      setActivePage: (activePage) => set({ activePage }),
    }),
    {
      name: "prometheus-ui",
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
      }),
    }
  )
);
