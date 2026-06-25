import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useUIStore } from '../../../store/ui-store';
import { cn } from '../../../utils';
import { AlertCircle, ArrowRight, Lightbulb, Play } from 'lucide-react';

interface RecommendationsPanelProps {
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

interface ActionCard {
  severity: 'critical' | 'warning' | 'opportunity';
  title: string;
  driver: string;
  description: string;
  ctaText: string;
  path: string;
}

export function RecommendationsPanel({ stats, twinCount = 0 }: RecommendationsPanelProps) {
  const navigate = useNavigate();
  
  const totalCustomers = stats?.total_customers ?? 1420;
  const churnRate = stats?.churn_rate ?? 0.084;
  const avgEngagement = stats?.avg_engagement ?? 0.74;
  
  // Calculate twin coverage ratio
  const twinCoverage = totalCustomers > 0 ? twinCount / totalCustomers : 0;

  // Build recommendation list using the specified deterministic rule engine
  const recommendations: ActionCard[] = [];

  if (churnRate > 0.10) {
    recommendations.push({
      severity: 'critical',
      title: 'Protect high-value at-risk customers',
      driver: `Churn rate at ${(churnRate * 100).toFixed(1)}%`,
      description: 'Active churn alerts are concentrated in Loyal Buyers segment. Launch a win-back simulation before launching the next campaign.',
      ctaText: 'Open Simulation Lab',
      path: '/simulation-lab'
    });
  } else if (churnRate > 0.05) {
    recommendations.push({
      severity: 'warning',
      title: 'Initiate churn mitigation scenarios',
      driver: `Elevated churn rate: ${(churnRate * 100).toFixed(1)}%`,
      description: 'Behavioral anomalies indicate early attrition signals. Test promotional discount rate sliders to protect engagement.',
      ctaText: 'Simulate Retention',
      path: '/simulation-lab'
    });
  }

  if (twinCoverage < 0.85) {
    recommendations.push({
      severity: 'opportunity',
      title: 'Increase Digital Twin coverage ratio',
      driver: `Twin coverage at ${Math.round(twinCoverage * 100)}%`,
      description: 'Twin coverage is below the 85% investor threshold. Rebuild stale twins to populate current psychographic traits.',
      ctaText: 'Build Customer Twins',
      path: '/twins'
    });
  }

  if (avgEngagement < 0.80) {
    recommendations.push({
      severity: 'opportunity',
      title: 'Target high-affinity engagement categories',
      driver: `Engagement index at ${Math.round(avgEngagement * 100)}%`,
      description: 'VIP buyers display low touch frequencies this period. Build a push message scenario with increased creative urgency.',
      ctaText: 'Design Scenarios',
      path: '/simulation-lab'
    });
  }

  // Ensure fallback recommendations are populated if all metrics are green
  if (recommendations.length === 0) {
    recommendations.push({
      severity: 'opportunity',
      title: 'Expand campaign to VIP cohorts',
      driver: 'All metrics within baseline bounds',
      description: 'VIP buyers display high loyalty scores and low touch frequencies. Build a high-value retention campaign.',
      ctaText: 'Open Simulation Lab',
      path: '/simulation-lab'
    });
  }

  const getSeverityStyles = (sev: ActionCard['severity']) => {
    switch (sev) {
      case 'critical':
        return 'border-red-500/20 bg-red-500/5 text-red-500';
      case 'warning':
        return 'border-amber-500/20 bg-amber-500/5 text-amber-500';
      case 'opportunity':
        return 'border-blue-500/20 bg-blue-500/5 text-blue-500';
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Lightbulb className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold tracking-tight text-foreground font-sans">Recommended Actions</h3>
      </div>

      <div className="space-y-3">
        {recommendations.map((action, idx) => (
          <div 
            key={idx} 
            className={cn(
              "p-4 border rounded-lg bg-card shadow-sm flex flex-col md:flex-row justify-between md:items-center gap-4 hover:border-zinc-400 dark:hover:border-zinc-700 transition-colors"
            )}
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className={cn("text-[9px] font-bold px-2 py-0.5 rounded uppercase border font-mono tracking-wider", getSeverityStyles(action.severity))}>
                  {action.severity}
                </span>
                <span className="text-[10px] text-muted-foreground font-mono font-medium">{action.driver}</span>
              </div>
              <h4 className="text-sm font-semibold text-foreground mt-1.5">{action.title}</h4>
              <p className="text-xs text-muted-foreground max-w-xl">{action.description}</p>
            </div>
            
            <button
              onClick={() => navigate(action.path)}
              className="px-3 py-2 rounded text-xs font-semibold bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 flex items-center justify-center gap-1.5 shrink-0 self-start md:self-auto text-foreground"
            >
              <span>{action.ctaText}</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
export default RecommendationsPanel;
