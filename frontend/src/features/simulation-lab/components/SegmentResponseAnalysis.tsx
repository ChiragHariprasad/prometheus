import React from 'react';
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip,
  Legend 
} from 'recharts';
import { formatCurrency } from '../../../utils';
import { cn } from '../../../utils';

interface SegmentAnalysisProps {
  segmentProjections?: any;
  loading?: boolean;
}

export function SegmentResponseAnalysis({
  segmentProjections,
  loading = false,
}: SegmentAnalysisProps) {
  if (loading) {
    return (
      <div className="h-[280px] w-full bg-card border rounded-lg p-6 flex flex-col justify-between animate-pulse">
        <div className="h-4 bg-muted rounded w-1/4"></div>
        <div className="h-44 bg-muted rounded w-full"></div>
      </div>
    );
  }

  // Pre-seed mock data if empty
  const projections = segmentProjections ? Object.entries(segmentProjections).map(([key, val]: any) => ({
    name: key.toUpperCase(),
    'Response Rate': Math.round(val.response_rate * 100),
    'Conversion Rate': Math.round(val.conversion_rate * 100),
    revenue: val.revenue,
    count: val.count,
    action: val.avg_revenue_per_customer > 100 ? 'SCALE' : 'REVISE'
  })) : [
    { name: 'VIP BUYERS', 'Response Rate': 85, 'Conversion Rate': 35, revenue: 154000, count: 240, action: 'SCALE' },
    { name: 'LOYAL ACTIVES', 'Response Rate': 70, 'Conversion Rate': 22, revenue: 120000, count: 480, action: 'UPSELL' },
    { name: 'NEW SIGNUPS', 'Response Rate': 45, 'Conversion Rate': 15, revenue: 51000, count: 180, action: 'NURTURE' },
    { name: 'AT RISK', 'Response Rate': 30, 'Conversion Rate': 8, revenue: 18000, count: 120, action: 'REDUCE FREQ' },
  ];

  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm space-y-6 font-sans text-xs">
      <div>
        <h3 className="text-sm font-semibold tracking-tight text-foreground">Behavioral Segment Responses</h3>
        <p className="text-[10px] text-muted-foreground font-mono">Cohort simulation outcome parameters</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        {/* Horizontal Bars */}
        <div className="lg:col-span-6 h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              layout="vertical"
              data={projections}
              margin={{ top: 10, right: 10, left: 10, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e4e4e7" className="dark:stroke-zinc-800" />
              <XAxis type="number" domain={[0, 100]} tick={{ fill: '#71717a', fontSize: 9 }} axisLine={false} tickLine={false} />
              <YAxis dataKey="name" type="category" tick={{ fill: '#71717a', fontSize: 9 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ backgroundColor: '#09090b', borderColor: '#27272a', fontSize: 10 }} />
              <Legend wrapperStyle={{ fontSize: 9 }} />
              <Bar dataKey="Response Rate" fill="#0EA5E9" radius={[0, 3, 3, 0]} />
              <Bar dataKey="Conversion Rate" fill="#10B981" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Matrix Table */}
        <div className="lg:col-span-6 overflow-x-auto">
          <table className="w-full text-[11px] text-left">
            <thead>
              <tr className="border-b dark:border-zinc-800 text-muted-foreground">
                <th className="pb-2 font-semibold">Cohort</th>
                <th className="pb-2 font-semibold text-right">Count</th>
                <th className="pb-2 font-semibold text-right">Proj. Revenue</th>
                <th className="pb-2 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-900">
              {projections.map((row, idx) => (
                <tr key={idx} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-900/30">
                  <td className="py-2.5 font-semibold text-foreground">{row.name}</td>
                  <td className="py-2.5 text-right font-mono">{row.count}</td>
                  <td className="py-2.5 text-right font-mono">{formatCurrency(row.revenue)}</td>
                  <td className="py-2.5 text-right">
                    <span 
                      className={cn(
                        "text-[9px] font-bold px-1.5 py-0.5 rounded border",
                        row.action === 'SCALE' && "text-success border-success/30 bg-success/5",
                        row.action === 'UPSELL' && "text-blue-500 border-blue-500/20 bg-blue-500/5",
                        row.action === 'NURTURE' && "text-warning border-warning/20 bg-warning/5",
                        row.action === 'REDUCE FREQ' && "text-error border-error/20 bg-error/5"
                      )}
                    >
                      {row.action}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
export default SegmentResponseAnalysis;
