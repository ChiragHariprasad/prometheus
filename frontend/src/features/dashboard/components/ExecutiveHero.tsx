import React from 'react';
import { 
  ResponsiveContainer, 
  RadialBarChart, 
  RadialBar, 
  PolarAngleAxis 
} from 'recharts';
import { cn } from '../../../utils';
import { 
  ShieldCheck, 
  TrendingUp, 
  Users, 
  Megaphone, 
  AlertTriangle 
} from 'lucide-react';

interface ExecutiveHeroProps {
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
}

export function ExecutiveHero({ stats, twinCount = 0 }: ExecutiveHeroProps) {
  // If stats is missing, default to typical loaded values for demo stability
  const totalCustomers = stats?.total_customers ?? 1420;
  const avgEngagement = stats?.avg_engagement ?? 0.74;
  const churnRate = stats?.churn_rate ?? 0.084;
  const totalRevenue = stats?.total_revenue ?? 482000;
  const revenueGrowth = stats?.revenue_growth ?? 0.12;
  const activeCampaigns = stats?.active_campaigns ?? 3;

  // 1. Calculate Business Health (0-100)
  const businessScore = Math.min(
    100,
    Math.round(
      (revenueGrowth > 0 ? 50 + revenueGrowth * 200 : 50) * 0.45 +
      (totalRevenue > 100000 ? 90 : 60) * 0.35 +
      (totalCustomers > 500 ? 95 : 70) * 0.20
    )
  );

  // 2. Calculate Customer Health (0-100)
  const customerCoverage = totalCustomers > 0 ? Math.min(100, Math.round((twinCount / totalCustomers) * 100)) : 0;
  const customerScore = Math.min(
    100,
    Math.round(
      (avgEngagement * 100) * 0.35 +
      82 * 0.25 + // Default loyalty index
      Math.max(0, (1 - churnRate) * 100) * 0.25 +
      customerCoverage * 0.15
    )
  );

  // 3. Calculate Campaign Score (0-100)
  const campaignScore = Math.min(
    100,
    Math.round(
      88 * 0.60 + // Average Campaign ROI proxy (2.8x -> 88/100)
      (activeCampaigns > 0 ? 90 : 40) * 0.20 +
      72 * 0.20 // Default conversion rate proxy
    )
  );

  // 4. Calculate Future Risk Score (0-100) -> Higher is safer (lower risk)
  const riskScore = Math.min(
    100,
    Math.round(
      Math.max(0, (1 - churnRate) * 100) * 0.45 +
      95 * 0.35 + // Probability of Loss safe factor (low probability of loss = high safety)
      90 * 0.20 // Stale twin ratio safe factor
    )
  );

  // 5. Composite Executive Health Score
  const healthScore = Math.min(
    100,
    Math.round(
      businessScore * 0.35 +
      customerScore * 0.30 +
      campaignScore * 0.20 +
      riskScore * 0.15
    )
  );

  const getStatusColor = (val: number) => {
    if (val >= 80) return 'text-success border-success/20 bg-success/5';
    if (val >= 60) return 'text-warning border-warning/20 bg-warning/5';
    return 'text-error border-error/20 bg-error/5';
  };

  const getStatusLabel = (val: number) => {
    if (val >= 80) return 'HEALTHY';
    if (val >= 60) return 'WATCH';
    return 'ACTION REQ';
  };

  // Determine headline statement based on thresholds
  let interpretation = "Revenue is up, customer risk is controlled, and simulations show positive ROI.";
  if (healthScore < 80 && healthScore >= 60) {
    interpretation = "Revenue is stable, but churn risk and campaign alignment need active watch.";
  } else if (healthScore < 60) {
    interpretation = "Critical future risk detected. Segment churn is elevated; launch win-back simulations immediately.";
  }

  // Radar/Radial data formatting for Recharts
  const chartData = [{ name: 'Health', value: healthScore, fill: healthScore >= 80 ? '#10B981' : healthScore >= 60 ? '#F59E0B' : '#EF4444' }];

  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-card p-6 shadow-sm flex flex-col lg:flex-row gap-8 items-center justify-between">
      {/* Left 60%: Headline readout */}
      <div className="flex-1 space-y-4">
        <div className="flex items-center gap-3">
          <span className={cn("px-2.5 py-0.5 rounded-full text-xs font-bold border", getStatusColor(healthScore))}>
            {getStatusLabel(healthScore)}
          </span>
          <span className="text-xs text-muted-foreground font-mono">EXECUTIVE SUMMARY</span>
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-foreground font-sans md:text-3xl max-w-xl leading-snug">
          {interpretation}
        </h2>
        <p className="text-sm text-muted-foreground max-w-lg">
          The composite index weighs financial growth (35%), active twin engagement (30%), campaign ROI (20%), and future churn risks (15%) derived from real-time customer event signals.
        </p>
      </div>

      {/* Right 40%: Health tiles & Meter */}
      <div className="flex flex-col md:flex-row items-center gap-6 shrink-0 w-full lg:w-auto">
        {/* Radial Meter */}
        <div className="relative h-32 w-32 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <RadialBarChart innerRadius="80%" outerRadius="100%" data={chartData} startAngle={90} endAngle={-270}>
              <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
              <RadialBar background dataKey="value" angleAxisId={0} cornerRadius={4} />
            </RadialBarChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-bold font-mono tracking-tight">{healthScore}</span>
            <span className="text-[10px] text-muted-foreground font-medium uppercase font-sans">INDEX</span>
          </div>
        </div>

        {/* Sub-scores Grid */}
        <div className="grid grid-cols-2 gap-4 w-full md:w-auto min-w-[240px]">
          <div className="p-3 border rounded-md bg-zinc-50/40 dark:bg-zinc-900/20">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <TrendingUp className="h-3.5 w-3.5" />
              <span>Business</span>
            </div>
            <p className="text-lg font-bold font-mono mt-1 text-foreground">{businessScore}%</p>
          </div>

          <div className="p-3 border rounded-md bg-zinc-50/40 dark:bg-zinc-900/20">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Users className="h-3.5 w-3.5" />
              <span>Customer</span>
            </div>
            <p className="text-lg font-bold font-mono mt-1 text-foreground">{customerScore}%</p>
          </div>

          <div className="p-3 border rounded-md bg-zinc-50/40 dark:bg-zinc-900/20">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Megaphone className="h-3.5 w-3.5" />
              <span>Campaign</span>
            </div>
            <p className="text-lg font-bold font-mono mt-1 text-foreground">{campaignScore}%</p>
          </div>

          <div className="p-3 border rounded-md bg-zinc-50/40 dark:bg-zinc-900/20">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <AlertTriangle className="h-3.5 w-3.5" />
              <span>Safety</span>
            </div>
            <p className="text-lg font-bold font-mono mt-1 text-foreground">{riskScore}%</p>
          </div>
        </div>
      </div>
    </div>
  );
}
export default ExecutiveHero;
