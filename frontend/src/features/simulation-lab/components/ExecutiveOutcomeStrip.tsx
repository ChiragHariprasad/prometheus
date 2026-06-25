import React from 'react';
import { MetricCard } from '../../../components/shared/MetricCard';
import { DollarSign, TrendingUp, AlertTriangle, Gem } from 'lucide-react';
import { formatCurrency, formatRoi } from '../../../utils';

interface ExecutiveOutcomeStripProps {
  results?: any;
  loading?: boolean;
}

export function ExecutiveOutcomeStrip({
  results,
  loading = false,
}: ExecutiveOutcomeStripProps) {
  const outcomes = results?.expected_outcomes || {};
  const metrics = results?.aggregated_metrics || {};

  const rev = outcomes?.expected_revenue ?? 0;
  const roi = outcomes?.expected_roi ?? metrics?.roi ?? 0;
  const churn = metrics?.churn_rate ?? (outcomes?.expected_churns ? outcomes.expected_churns / 100 : 0);
  const ltv = outcomes?.ltv_impact ?? 0;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
      <MetricCard
        title="Expected Revenue"
        value={formatCurrency(rev)}
        icon={<DollarSign className="h-4 w-4" />}
        subtext="Total projected return"
        loading={loading}
      />

      <MetricCard
        title="Expected ROI"
        value={formatRoi(roi)}
        icon={<TrendingUp className="h-4 w-4" />}
        subtext="Efficiency score multiplier"
        loading={loading}
      />

      <MetricCard
        title="Expected Churn"
        value={`${(churn * 100).toFixed(1)}%`}
        icon={<AlertTriangle className="h-4 w-4" />}
        subtext="Projected customer drop-offs"
        loading={loading}
      />

      <MetricCard
        title="LTV Impact"
        value={`+${formatCurrency(ltv)}`}
        icon={<Gem className="h-4 w-4" />}
        subtext="Per-customer lifetime growth"
        loading={loading}
      />
    </div>
  );
}
export default ExecutiveOutcomeStrip;
