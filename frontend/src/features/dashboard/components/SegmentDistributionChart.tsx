import React from 'react';
import { 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell, 
  Tooltip 
} from 'recharts';

interface SegmentDistributionChartProps {
  data?: Array<{
    segment: string;
    count: number;
  }>;
  loading?: boolean;
}

const COLORS = ['#4F46E5', '#0EA5E9', '#8B5CF6', '#D946EF', '#71717A'];

export function SegmentDistributionChart({ data = [], loading = false }: SegmentDistributionChartProps) {
  if (loading) {
    return (
      <div className="h-[360px] w-full bg-card border rounded-lg p-6 flex flex-col justify-between animate-pulse">
        <div className="h-4 bg-muted rounded w-1/4"></div>
        <div className="h-56 bg-muted rounded w-full"></div>
      </div>
    );
  }

  // Pre-seed mock data if empty for investor demo completeness
  const chartData = data.length > 0 ? data : [
    { segment: 'VIP Customers', count: 240 },
    { segment: 'Loyal Buyers', count: 480 },
    { segment: 'Recent Reactivated', count: 180 },
    { segment: 'At-Risk Inactive', count: 120 },
  ];

  const total = chartData.reduce((sum, item) => sum + item.count, 0);

  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm flex flex-col justify-between h-[360px]">
      <div>
        <h3 className="text-sm font-semibold tracking-tight text-foreground font-sans">Segment Distribution</h3>
        <p className="text-xs text-muted-foreground mt-0.5">Customer weights across calculated behavioral cohorts</p>
      </div>

      <div className="flex items-center gap-4 mt-4 flex-1">
        {/* Pie Graph */}
        <div className="h-40 w-40 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={70}
                paddingAngle={3}
                dataKey="count"
                nameKey="segment"
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const value = payload[0].value as number;
                    const pct = total > 0 ? ((value / total) * 100).toFixed(0) : 0;
                    return (
                      <div className="bg-zinc-950 text-zinc-50 border border-zinc-800 p-2.5 rounded shadow-md text-xs font-mono">
                        <p className="font-semibold">{payload[0].name}</p>
                        <p className="text-accent mt-0.5">Count: {value} ({pct}%)</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Legend / Ranked list */}
        <div className="flex-1 space-y-2.5 overflow-y-auto max-h-48 pr-2">
          {chartData.map((item, idx) => {
            const pct = total > 0 ? ((item.count / total) * 100).toFixed(0) : 0;
            return (
              <div key={idx} className="flex items-center justify-between text-xs border-b pb-1.5 dark:border-zinc-800 last:border-b-0">
                <div className="flex items-center gap-2">
                  <span 
                    className="h-2 w-2 rounded-full shrink-0" 
                    style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                  ></span>
                  <span className="font-medium text-foreground truncate max-w-[120px]">{item.segment}</span>
                </div>
                <div className="text-right shrink-0">
                  <span className="font-semibold font-mono text-foreground">{item.count}</span>
                  <span className="text-muted-foreground font-mono ml-1.5">({pct}%)</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
export default SegmentDistributionChart;
