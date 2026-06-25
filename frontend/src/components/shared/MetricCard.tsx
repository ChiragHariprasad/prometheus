import React from 'react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { cn } from '../../utils';

interface MetricCardProps {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  trend?: number; // e.g. 12 for 12%
  trendType?: 'positive' | 'negative' | 'neutral';
  subtext?: string;
  loading?: boolean;
}

export function MetricCard({
  title,
  value,
  icon,
  trend,
  trendType,
  subtext,
  loading = false,
}: MetricCardProps) {
  if (loading) {
    return (
      <div className="rounded-lg border bg-card p-6 shadow-sm animate-pulse min-h-[120px] flex flex-col justify-between">
        <div className="flex justify-between items-center mb-2">
          <div className="h-3.5 bg-muted rounded w-2/3"></div>
          <div className="h-4 bg-muted rounded w-4"></div>
        </div>
        <div className="h-8 bg-muted rounded w-1/2 mb-2"></div>
        <div className="h-3 bg-muted rounded w-3/4"></div>
      </div>
    );
  }

  const isPos = trendType === 'positive' || (trend !== undefined && trend > 0 && trendType !== 'negative');
  const isNeg = trendType === 'negative' || (trend !== undefined && trend < 0 && trendType !== 'positive');

  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm flex flex-col justify-between min-h-[120px] hover:border-zinc-400 dark:hover:border-zinc-700 transition-colors duration-150">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{title}</span>
        {icon && <span className="text-muted-foreground">{icon}</span>}
      </div>
      
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-semibold tracking-normal text-foreground font-sans">{value}</span>
        {trend !== undefined && (
          <span
            className={cn(
              "text-xs font-semibold flex items-center ml-1",
              isPos && "text-success",
              isNeg && "text-error",
              !isPos && !isNeg && "text-muted-foreground"
            )}
          >
            {isPos ? '+' : ''}
            {trend}%
            {isPos ? <ArrowUpRight className="h-3.5 w-3.5 ml-0.5" /> : isNeg ? <ArrowDownRight className="h-3.5 w-3.5 ml-0.5" /> : null}
          </span>
        )}
      </div>

      {subtext && (
        <p className="text-xs text-muted-foreground mt-1 font-sans">{subtext}</p>
      )}
    </div>
  );
}
export default MetricCard;
