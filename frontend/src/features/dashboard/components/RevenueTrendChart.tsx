import React from 'react';
import { 
  ResponsiveContainer, 
  ComposedChart, 
  Bar, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend 
} from 'recharts';
import { formatCurrency } from '../../../utils';

interface RevenueTrendChartProps {
  data?: Array<{
    date: string;
    revenue?: number;
    avg_order_value?: number;
  }>;
  loading?: boolean;
}

export function RevenueTrendChart({ data = [], loading = false }: RevenueTrendChartProps) {
  if (loading) {
    return (
      <div className="h-[360px] w-full bg-card border rounded-lg p-6 flex flex-col justify-between animate-pulse">
        <div className="h-4 bg-muted rounded w-1/4"></div>
        <div className="h-56 bg-muted rounded w-full"></div>
      </div>
    );
  }

  // Map backend {date, value} to chart's expected {date, revenue}
  const mappedData = data.map((d: any) => ({
    date: d.date,
    revenue: d.revenue ?? d.value ?? 0,
    avg_order_value: d.avg_order_value ?? 0,
  }));
  const chartData = mappedData.length > 0 ? mappedData : [
    { date: 'Jun 19', revenue: 12000, avg_order_value: 85 },
    { date: 'Jun 20', revenue: 15400, avg_order_value: 92 },
    { date: 'Jun 21', revenue: 14200, avg_order_value: 88 },
    { date: 'Jun 22', revenue: 18100, avg_order_value: 95 },
    { date: 'Jun 23', revenue: 22000, avg_order_value: 104 },
    { date: 'Jun 24', revenue: 21500, avg_order_value: 98 },
    { date: 'Jun 25', revenue: 24500, avg_order_value: 105 },
  ];

  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm flex flex-col justify-between h-[360px]">
      <div>
        <h3 className="text-sm font-semibold tracking-tight text-foreground font-sans">Revenue & Order Values</h3>
        <p className="text-xs text-muted-foreground mt-0.5">Daily projected metrics for the selected time horizon</p>
      </div>

      <div className="h-60 mt-4">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e4e4e7" className="dark:stroke-zinc-800" />
            <XAxis 
              dataKey="date" 
              tick={{ fill: '#71717a', fontSize: 10 }} 
              axisLine={false}
              tickLine={false}
            />
            <YAxis 
              yAxisId="left"
              tickFormatter={(v) => `$${v / 1000}k`}
              tick={{ fill: '#71717a', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis 
              yAxisId="right"
              orientation="right"
              tickFormatter={(v) => `$${v}`}
              tick={{ fill: '#71717a', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const rVal = payload[0].value as number;
                  const aVal = payload[1]?.value as number;
                  return (
                    <div className="bg-zinc-950 text-zinc-50 border border-zinc-800 p-3 rounded shadow-md text-xs font-mono">
                      <p className="font-semibold mb-1 text-zinc-400">{payload[0].payload.date}</p>
                      <p className="text-[#10B981]">Revenue: {formatCurrency(rVal)}</p>
                      {aVal !== undefined && <p className="text-[#0EA5E9]">Avg Order: {formatCurrency(aVal)}</p>}
                    </div>
                  );
                }
                return null;
              }}
            />
            <Legend 
              wrapperStyle={{ fontSize: 10, paddingTop: 10 }} 
              iconSize={8}
            />
            <Bar 
              yAxisId="left"
              name="Revenue"
              dataKey="revenue" 
              fill="#10B981" 
              radius={[4, 4, 0, 0]} 
              maxBarSize={32}
            />
            <Line 
              yAxisId="right"
              name="Avg Order Value"
              type="monotone" 
              dataKey="avg_order_value" 
              stroke="#0EA5E9" 
              strokeWidth={2}
              dot={{ r: 3, stroke: '#0EA5E9', fill: '#0EA5E9' }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
export default RevenueTrendChart;
