import React from 'react';
import { MetricCard } from '../../../components/shared/MetricCard';
import { DollarSign, Users, Network, AlertTriangle, TrendingUp, Gem } from 'lucide-react';
import { formatCurrency, formatPercentage, formatRoi } from '../../../utils';

interface KPIGridProps {
  stats?: {
    total_customers: number;
    events_24h: number;
    active_campaigns: number;
    avg_engagement: number;
    total_revenue: number;
    revenue_growth: number;
    churn_rate: number;
  };
  twinCount?: number;
  avgLtv?: number;
  avgCampaignRoi?: number;
  loading?: boolean;
}

export function KPIGrid({
  stats,
  twinCount = 0,
  avgLtv = 0,
  avgCampaignRoi = 0,
  loading = false,
}: KPIGridProps) {
  const totalCustomers = stats?.total_customers ?? 0;
  const events24h = stats?.events_24h ?? 0;
  const totalRevenue = stats?.total_revenue ?? 0;
  const revenueGrowth = stats?.revenue_growth ?? 0;
  const churnRate = stats?.churn_rate ?? 0;

  const coverage = totalCustomers > 0 ? (twinCount / totalCustomers) * 100 : 0;
  
  const getChurnRiskColor = (rate: number): 'positive' | 'neutral' | 'negative' => {
    const percent = rate * 100;
    if (percent < 5) return 'positive';
    if (percent <= 12) return 'neutral';
    return 'negative';
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
      {/* Revenue */}
      <MetricCard
        title="Revenue"
        value={formatCurrency(totalRevenue)}
        icon={<DollarSign className="h-4 w-4" />}
        trend={revenueGrowth !== 0 ? Math.round(revenueGrowth * 100) : undefined}
        subtext="For selected range"
        loading={loading}
      />

      {/* Customer Count */}
      <MetricCard
        title="Customers"
        value={totalCustomers.toLocaleString()}
        icon={<Users className="h-4 w-4" />}
        subtext={`${events24h.toLocaleString()} events in 24h`}
        loading={loading}
      />

      {/* Twin Count */}
      <MetricCard
        title="Digital Twins"
        value={twinCount.toLocaleString()}
        icon={<Network className="h-4 w-4" />}
        subtext={`${coverage.toFixed(0)}% twin coverage`}
        loading={loading}
      />

      {/* Average Churn */}
      <MetricCard
        title="Average Churn"
        value={`${(churnRate * 100).toFixed(1)}%`}
        icon={<AlertTriangle className="h-4 w-4" />}
        trendType={getChurnRiskColor(churnRate)}
        subtext={
          churnRate * 100 < 5 
            ? "Healthy bounds" 
            : churnRate * 100 <= 12 
              ? "Elevated risks" 
              : "Critical threshold"
        }
        loading={loading}
      />

      {/* Campaign ROI */}
      <MetricCard
        title="Campaign ROI"
        value={avgCampaignRoi > 0 ? formatRoi(avgCampaignRoi) : "Pending"}
        icon={<TrendingUp className="h-4 w-4" />}
        subtext="Weighted average ROI"
        loading={loading}
      />

      {/* Average LTV */}
      <MetricCard
        title="Average LTV"
        value={formatCurrency(avgLtv)}
        icon={<Gem className="h-4 w-4" />}
        subtext="Customer lifetime value"
        loading={loading}
      />
    </div>
  );
}
export default KPIGrid;
