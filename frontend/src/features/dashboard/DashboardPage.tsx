import React from 'react';
import { useDashboardData, useTwinSummary } from '../../hooks/queries';
import { PageHeader } from '../../components/shared/PageHeader';
import { ExecutiveHero } from './components/ExecutiveHero';
import { KPIGrid } from './components/KPIGrid';
import { RevenueTrendChart } from './components/RevenueTrendChart';
import { SegmentDistributionChart } from './components/SegmentDistributionChart';
import { RecentSimulationsTable } from './components/RecentSimulationsTable';
import { RecommendationsPanel } from './components/RecommendationsPanel';
import { ErrorBoundary } from '../../components/shared/ErrorBoundary';
import { useQuery } from '@tanstack/react-query';
import { simulationsService } from '../../api/simulations.service';
import { customersService } from '../../api/customers.service';

export function DashboardPage() {
  const { data: dashData, isLoading: dashLoading, isError: dashError, refetch } = useDashboardData();
  const { data: twinSummary, isLoading: twinLoading } = useTwinSummary();

  // Additional secondary queries for KPI grid enrichment (LTV, ROI averages)
  const { data: simsData } = useQuery({
    queryKey: ['simulations-list-dashboard'],
    queryFn: () => simulationsService.listSimulations({ page: 1, page_size: 50 }),
    staleTime: 60000,
  });

  const { data: customersData } = useQuery({
    queryKey: ['customers-list-dashboard'],
    queryFn: () => customersService.listCustomers({ page: 1, page_size: 100 }),
    staleTime: 60000,
  });

  const twinCount = twinSummary?.total_twins ?? 0;
  
  // Calculate average LTV from customer list fallback
  const customersList = customersData?.data || [];
  const avgLtv = customersList.length > 0
    ? Math.round(customersList.reduce((sum: number, c: any) => sum + (c.ltv || 0), 0) / customersList.length)
    : 382; // Fallback demo placeholder

  // Calculate average ROI from simulations
  const completedSims = simsData?.data?.filter((s: any) => s.status === 'completed' && s.results?.expected_outcomes?.expected_roi) || [];
  const avgCampaignRoi = completedSims.length > 0
    ? completedSims.reduce((sum: number, s: any) => sum + s.results.expected_outcomes.expected_roi, 0) / completedSims.length
    : 2.34; // Fallback demo placeholder

  const handleRefresh = () => {
    refetch();
  };

  if (dashError) {
    return (
      <div className="flex flex-col items-center justify-center py-20 border border-dashed rounded-lg bg-red-500/5 border-red-500/20 text-center font-sans">
        <h3 className="text-lg font-bold text-red-500 mb-2">Dashboard metrics are unavailable</h3>
        <p className="text-sm text-muted-foreground max-w-sm mb-6">
          Unable to establish database or socket connection to the analytics engine.
        </p>
        <button
          onClick={handleRefresh}
          className="h-10 px-4 rounded bg-accent text-white text-sm font-semibold hover:bg-blue-700 transition-colors"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-10">
      {/* Top Banner Readout */}
      <PageHeader
        title="Executive Dashboard"
        subtitle="Operational command view of customer health, campaign simulations, and revenue projections"
      />

      {/* Hero Section: Executive Health Meter & Sub-health category scores */}
      <ErrorBoundary>
        <ExecutiveHero 
          stats={dashData?.stats} 
          twinCount={twinCount} 
        />
      </ErrorBoundary>

      {/* KPI ribbon containing six major business items */}
      <ErrorBoundary>
        <KPIGrid
          stats={dashData?.stats}
          twinCount={twinCount}
          avgLtv={avgLtv}
          avgCampaignRoi={avgCampaignRoi}
          loading={dashLoading || twinLoading}
        />
      </ErrorBoundary>

      {/* Primary analytical charts */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8">
          <ErrorBoundary>
            <RevenueTrendChart 
              data={dashData?.revenue_data} 
              loading={dashLoading} 
            />
          </ErrorBoundary>
        </div>

        <div className="lg:col-span-4">
          <ErrorBoundary>
            <SegmentDistributionChart 
              data={dashData?.segment_distribution} 
              loading={dashLoading} 
            />
          </ErrorBoundary>
        </div>
      </div>

      {/* Bottom Insights and Action list */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7">
          <ErrorBoundary>
            <RecentSimulationsTable 
              simulations={simsData?.data} 
              loading={dashLoading} 
            />
          </ErrorBoundary>
        </div>

        <div className="lg:col-span-5">
          <ErrorBoundary>
            <RecommendationsPanel 
              stats={dashData?.stats} 
              twinCount={twinCount} 
            />
          </ErrorBoundary>
        </div>
      </div>
    </div>
  );
}
export default DashboardPage;
