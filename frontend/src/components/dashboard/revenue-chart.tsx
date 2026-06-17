"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { format } from "date-fns";

interface RevenueChartProps {
  data: Array<{ date: string; value: number }>;
  title?: string;
}

export function RevenueChart({
  data,
  title = "Revenue Over Time",
}: RevenueChartProps) {
  const chartData = data.map((point) => ({
    date: format(new Date(point.date), "MMM d"),
    Revenue: point.value,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid
                strokeDasharray="3 3"
                className="stroke-muted"
              />
              <XAxis
                dataKey="date"
                className="text-xs text-muted-foreground"
                tick={{ fontSize: 11 }}
              />
              <YAxis
                className="text-xs text-muted-foreground"
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: "8px",
                  border: "1px solid hsl(var(--border))",
                  background: "hsl(var(--background))",
                }}
                formatter={(value: number) => [
                  `$${value.toLocaleString()}`,
                ]}
              />
              <Legend />
              <Bar
                dataKey="Revenue"
                fill="#3b82f6"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
