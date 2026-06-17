"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Simulation } from "@/lib/api-client";
import { format } from "date-fns";

interface ForecastChartProps {
  simulation: Simulation;
}

export function ForecastChart({ simulation }: ForecastChartProps) {
  const { forecast, results } = simulation;

  if (!forecast) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">
            No forecast data available.
          </p>
        </CardContent>
      </Card>
    );
  }

  const chartData = forecast.dates.map((date, i) => ({
    date: format(new Date(date), "MMM d"),
    predicted: forecast.predicted[i],
    upper: forecast.upper_bound[i],
    lower: forecast.lower_bound[i],
  }));

  const maxVal = Math.max(...forecast.upper_bound);
  const minVal = Math.min(...forecast.lower_bound);
  const padding = (maxVal - minVal) * 0.1;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">
          Revenue Forecast
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="predictedGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="confidenceGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.1} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="date"
                className="text-xs text-muted-foreground"
                tick={{ fontSize: 11 }}
                interval="preserveStartEnd"
              />
              <YAxis
                className="text-xs text-muted-foreground"
                tick={{ fontSize: 11 }}
                domain={[
                  Math.floor((minVal - padding) / 1000) * 1000,
                  Math.ceil((maxVal + padding) / 1000) * 1000,
                ]}
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
                labelFormatter={(label) => `Date: ${label}`}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="upper"
                stroke="none"
                fill="url(#confidenceGrad)"
              />
              <Area
                type="monotone"
                dataKey="lower"
                stroke="none"
                fill="url(#confidenceGrad)"
              />
              <Line
                type="monotone"
                dataKey="predicted"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
                name="Predicted"
              />
              <Line
                type="monotone"
                dataKey="upper"
                stroke="#93c5fd"
                strokeWidth={1}
                strokeDasharray="5 5"
                dot={false}
                name="Upper Bound"
              />
              <Line
                type="monotone"
                dataKey="lower"
                stroke="#93c5fd"
                strokeWidth={1}
                strokeDasharray="5 5"
                dot={false}
                name="Lower Bound"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        {results && (
          <div className="mt-4 grid grid-cols-3 gap-4 border-t pt-4 text-center">
            <div>
              <p className="text-xs text-muted-foreground">Expected</p>
              <p className="text-lg font-bold text-primary">
                ${results.expected_revenue.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Best Case</p>
              <p className="text-lg font-bold text-green-600">
                ${results.scenarios.best_case.revenue?.toLocaleString() || 0}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Worst Case</p>
              <p className="text-lg font-bold text-red-600">
                ${results.scenarios.worst_case.revenue?.toLocaleString() || 0}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
