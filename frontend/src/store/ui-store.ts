import { create } from 'zustand';

type DateRange = '7D' | '30D' | '90D' | 'YTD';

interface UIState {
  sidebarCollapsed: boolean;
  dateRange: DateRange;
  theme: 'light' | 'dark';
  setSidebarCollapsed: (collapsed: boolean) => void;
  setDateRange: (range: DateRange) => void;
  setTheme: (theme: 'light' | 'dark') => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  dateRange: '30D',
  theme: 'dark', // Default to Dark Mode for premium aesthetics
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setDateRange: (range) => set({ dateRange: range }),
  setTheme: (theme) => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
    set({ theme });
  },
}));
