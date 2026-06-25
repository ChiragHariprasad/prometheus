# TWINCX Frontend Build Blueprint

This document serves as the complete implementation blueprint for the TWINCX frontend application. It is designed to allow a development team to begin execution immediately.

## Stack
React, TypeScript, Vite, Tailwind CSS, ShadCN UI, Recharts, Zustand (Global State), TanStack Query (Server State).

---

## 1. Folder Structure
We utilize a feature-based architecture to encapsulate logic, styles, and components, ensuring scalable maintenance.

```text
src/
├── api/                # Axios instance, API clients, endpoints
├── assets/             # Static assets (images, fonts, global CSS)
├── components/         # Global components
│   ├── layout/         # AppShell, Sidebar, Header
│   ├── shared/         # Reusable complex components (MetricCard, Charts)
│   └── ui/             # ShadCN UI base components
├── config/             # Environment variables, constants
├── features/           # Feature-based modules
│   ├── campaign-explorer/
│   ├── dashboard/
│   ├── scenario-comparison/
│   ├── simulation-lab/
│   └── twin-explorer/
├── hooks/              # Global custom hooks (useWindowSize, useAuth)
├── router/             # React Router definitions
├── store/              # Zustand stores (Global UI state)
├── types/              # Global TypeScript interfaces
└── utils/              # Helper functions (formatters, calculations)
```

## 2. Route Structure
Routing is flat and descriptive to facilitate deep linking.

- `/` → Redirects to `/dashboard`
- `/dashboard` → Executive Dashboard (**P0**)
- `/twins` → Twin Explorer Directory (**P0**)
- `/twins/:twinId` → Twin Profile & Insights
- `/simulations` → Simulation Lab Workspace (**P0**)
- `/simulations/compare` → Scenario Comparison (**P1**)
- `/campaigns` → Campaign Explorer (**P2**)

## 3. Component Hierarchy
High-level tree for the core application wrapper and primary layout.

```text
AppRoot
├── QueryClientProvider (TanStack Query)
├── ThemeProvider
├── BrowserRouter
└── AppLayout
    ├── SidebarNavigation
    ├── Topbar (User Profile, Notifications)
    ├── MainContentArea
    │   ├── ErrorBoundary
    │   └── React.Suspense
    │       ├── Dashboard (P0)
    │       ├── TwinExplorer (P0)
    │       └── SimulationLab (P0)
    └── Toaster (ShadCN)
```

## 4. Shared Components
These components must be built first as they are reused across all P0 modules.
- `MetricCard`: Displays a KPI, value, delta percentage, and mini sparkline.
- `RechartsWrapper`: Standardized configurations for Line, Bar, and Radar charts to ensure brand consistency.
- `DataTable`: ShadCN table wrapper with sorting, pagination, and sticky headers.
- `PageHeader`: Consistent title, breadcrumbs, and primary action buttons.
- `StatusBadge`: Tailwind-styled ShadCN badge for active/inactive/processing states.

## 5. API Layer Design
- **Client**: `axios` with interceptors for auth tokens and global error catching.
- **Data Fetching**: `TanStack Query (React Query)`.
- **Structure**: Each feature folder contains its own `api.ts` defining endpoints and `queries.ts` containing customized hooks (e.g., `useGetTwin(id)`).

## 6. State Management Strategy
- **Server State**: Managed strictly by TanStack Query. No API data goes into global stores unless absolutely necessary.
- **Global UI State**: Managed by `Zustand` (e.g., collapsed sidebar, active theme, global selected date range).
- **Local Form/Component State**: Managed by React `useState` and `useReducer` (or React Hook Form for complex inputs).

## 7. Error Handling Strategy
- **Network Level**: Axios interceptors push error messages to the global ShadCN Toaster.
- **Component Level**: React Error Boundaries wrap each top-level route (e.g., `/dashboard`). If a feature crashes, only that pane shows a localized fallback UI.
- **API Forms**: Validation via `Zod` combined with `React Hook Form`.

## 8. Loading Strategy
- **Initial App Load**: Full-screen skeleton or minimal branded loader.
- **Route Transitions**: React Suspense boundaries.
- **Data Loading**: "Skeleton mapping." When `isLoading` is true in TanStack Query, render ShadCN Skeletons that explicitly match the layout of the loaded component (e.g., a skeleton table, skeleton charts).

## 9. Build Order & Fastest Path to Demo
To achieve the fastest path to an investor-ready demo, strictly follow this sequence:

1. **Phase 1: Setup & Foundation (2 Days)**
   - Vite Init, Tailwind config, ShadCN initialization.
   - AppLayout, Routing skeleton, and Shared Components (`MetricCard`, `RechartsWrapper`).
2. **Phase 2: Dashboard [P0] (3 Days)**
   - Wire up mocked API. Implement the Executive Dashboard for instant visual impact.
3. **Phase 3: Simulation Lab [P0] (4 Days)**
   - Build the interactive sliders and real-time Recharts updates (the "wow" factor of the demo).
4. **Phase 4: Twin Explorer [P0] (3 Days)**
   - Data tables and individual twin profile pages.
5. **Phase 5: Scenario Comparison [P1] (2 Days)**
   - Re-use charts and tables to build the comparison matrix.
6. **Phase 6: Campaign Explorer [P2] (2 Days)**
   - Lower priority CRUD interface for campaigns.

## 10. Dependency Graph
```text
React 18
 ├── Vite (Bundler)
 ├── React Router DOM (Navigation)
 ├── Tailwind CSS (Styling Engine)
 │    └── ShadCN UI (Component Library)
 │         ├── Radix UI (Headless Primitives)
 │         ├── Lucide React (Icons)
 │         └── Tailwind Merge / CLSX
 ├── TanStack Query (Data Fetching / Caching)
 ├── Zustand (Global State)
 ├── Axios (HTTP Client)
 ├── Recharts (Data Visualization)
 └── Zod + React Hook Form (Validation)
```

---

## Project Estimates (Hours per Module)
*Assumes 1 Senior Frontend Engineer.*

| Module / Phase | Estimated Hours | Complexity |
| :--- | :--- | :--- |
| Setup, Routing, & Layout | 12h | Low |
| Design System & Shared Components | 16h | Medium |
| Executive Dashboard (P0) | 20h | Medium |
| Twin Explorer (P0) | 24h | Medium |
| Simulation Lab (P0) | 32h | High |
| Scenario Comparison (P1) | 16h | Medium |
| Campaign Explorer (P2) | 12h | Low |
| Polish, Animations & QA | 16h | High |
| **Total Estimated Time** | **~148 Hours** | (~3.5 Weeks) |

## Risk Areas
1. **Recharts Performance**: The Simulation Lab may render thousands of data points across multiple lines. **Mitigation**: Use Recharts `ReferenceLine` sparingly, enable data decimation if payloads are huge, and memoize chart components (`React.memo`).
2. **Simulation State Complexity**: Synchronizing 5+ sliders to instant chart updates without UI lag. **Mitigation**: Use `Zustand` for slider state and debounce the API calls, while instantly updating the UI optimistically.
3. **Investor-Grade Polish**: ShadCN out-of-the-box can look slightly generic. **Mitigation**: Invest the upfront 16 hours into the Design System phase to aggressively customize ShadCN variables for dark mode, glassmorphism, and branded accents before building feature pages.
