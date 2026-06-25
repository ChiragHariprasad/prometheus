import React, { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';

const DashboardPage = lazy(() => import('../features/dashboard/DashboardPage'));
const TwinExplorerPage = lazy(() => import('../features/twin-explorer/TwinExplorerPage'));
const SimulationLabPage = lazy(() => import('../features/simulation-lab/SimulationLabPage'));
const ScenarioComparisonPage = lazy(() => import('../features/scenario-comparison/ScenarioComparisonPage'));
const LoginPage = lazy(() => import('../features/auth/LoginPage'));

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: '/login',
    element: (
      <Suspense fallback={<div className="h-screen w-screen bg-background flex items-center justify-center">Loading...</div>}>
        <LoginPage />
      </Suspense>
    ),
  },
  {
    element: <AppLayout />,
    children: [
      {
        path: '/dashboard',
        element: (
          <Suspense fallback={<div className="h-full w-full bg-background flex items-center justify-center font-mono text-xs">Loading Executive Dashboard...</div>}>
            <DashboardPage />
          </Suspense>
        ),
      },
      {
        path: '/twins',
        element: (
          <Suspense fallback={<div className="h-full w-full bg-background flex items-center justify-center font-mono text-xs">Loading Twin Explorer...</div>}>
            <TwinExplorerPage />
          </Suspense>
        ),
      },
      {
        path: '/twins/:twinId',
        element: (
          <Suspense fallback={<div className="h-full w-full bg-background flex items-center justify-center font-mono text-xs">Loading Twin Profile...</div>}>
            <TwinExplorerPage />
          </Suspense>
        ),
      },
      {
        path: '/simulation-lab',
        element: (
          <Suspense fallback={<div className="h-full w-full bg-background flex items-center justify-center font-mono text-xs">Loading Simulation Lab...</div>}>
            <SimulationLabPage />
          </Suspense>
        ),
      },
      {
        path: '/simulations',
        element: <Navigate to="/simulation-lab" replace />,
      },
      {
        path: '/simulations/compare',
        element: (
          <Suspense fallback={<div className="h-full w-full bg-background flex items-center justify-center font-mono text-xs">Loading Scenario Matrix...</div>}>
            <ScenarioComparisonPage />
          </Suspense>
        ),
      },
    ],
  },
]);
export default router;
