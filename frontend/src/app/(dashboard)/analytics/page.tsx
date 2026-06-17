"use client";

import { useState } from "react";
import {
  useRevenueAnalytics,
  useEngagementAnalytics,
  useChurnAnalytics,
} from "@/hooks/use-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  BarChart3,
  Download,
  Calendar,
  TrendingUp,
  Users,
  DollarSign,
  AlertTriangle,
} from "lucide-react";
import { format } from "date-fns";

const COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6"];

export default function AnalyticsPage() {
  const [dateRange, setDateRange] = useState({
    start: format(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), "yyyy-MM-dd"),
    end: format(new Date(), "yyyy-MM-dd"),
  });
  const [activeMetric, setActiveMetric] = useState("revenue");
  const [granularity, setGranularity] = useState("day");

  const { data: revenueData } = useRevenueAnalytics({
    start_date: dateRange.start,
    end_date: dateRange.end,
    granularity,
  });

  const { data: engagementData } = useEngagementAnalytics({
    start_date: dateRange.start,
    end_date: dateRange.end,
    granularity,
  });

  const { data: churnData } = useChurnAnalytics({
    start_date: dateRange.start,
    end_date: dateRange.end,
  });

  const renderChart = () => {
    switch (activeMetric) {
      case "revenue":
        return (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={revenueData?.data || []}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="date"
                tickFormatter={(v) => format(new Date(v), "MMM d")}
                className="text-xs"
              />
              <YAxis
                tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                className="text-xs"
              />
              <Tooltip
                contentStyle={{
                  borderRadius: "8px",
                  border: "1px solid hsl(var(--border))",
                  background: "hsl(var(--background))",
                }}
              />
              <Legend />
              <Bar dataKey="revenue" fill="#3b82f6" name="Revenue" radius={[4,4,0,0]} />
              <Bar dataKey="cost" fill="#ef4444" name="Cost" radius={[4,4,0,0]} />
              <Bar dataKey="profit" fill="#22c55e" name="Profit" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        );
      case "engagement":
        return (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={engagementData?.data || []}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="date"
                tickFormatter={(v) => format(new Date(v), "MMM d")}
                className="text-xs"
              />
              <YAxis className="text-xs" />
              <Tooltip
                contentStyle={{
                  borderRadius: "8px",
                  border: "1px solid hsl(var(--border))",
                  background: "hsl(var(--background))",
                }}
              />
              <Legend />
              <Line type="monotone" dataKey="engagement" stroke="#3b82f6" name="Engagement" strokeWidth={2} />
              <Line type="monotone" dataKey="retention" stroke="#22c55e" name="Retention" strokeWidth={2} />
              <Line type="monotone" dataKey="satisfaction" stroke="#f59e0b" name="Satisfaction" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        );
      case "churn":
        return (
          <div className="grid gap-6 md:grid-cols-2">
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={[
                      { name: "Churned", value: churnData?.churned_customers || 0 },
                      { name: "At Risk", value: churnData?.at_risk || 0 },
                    ]}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    dataKey="value"
                  >
                    {COLORS.slice(0, 2).map((color, i) => (
                      <Cell key={i} fill={color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-4">
              <h3 className="font-semibold">Churn Rate: {((churnData?.churn_rate ?? 0) * 100).toFixed(1)}%</h3>
              <div className="space-y-2">
                {churnData?.by_segment?.map((s) => (
                  <div key={s.segment} className="flex justify-between text-sm">
                    <span>{s.segment}</span>
                    <span className="font-mono">{((s.churn_rate ?? 0) * 100).toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Analytics Center</h1>
          <p className="text-muted-foreground mt-1">
            Deep dive into your platform metrics
          </p>
        </div>
        <Button variant="outline">
          <Download className="mr-2 h-4 w-4" />
          Export Report
        </Button>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-2">
              <Label>Start Date</Label>
              <Input
                type="date"
                value={dateRange.start}
                onChange={(e) =>
                  setDateRange((prev) => ({ ...prev, start: e.target.value }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label>End Date</Label>
              <Input
                type="date"
                value={dateRange.end}
                onChange={(e) =>
                  setDateRange((prev) => ({ ...prev, end: e.target.value }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label>Granularity</Label>
              <Select value={granularity} onValueChange={setGranularity}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="hour">Hourly</SelectItem>
                  <SelectItem value="day">Daily</SelectItem>
                  <SelectItem value="week">Weekly</SelectItem>
                  <SelectItem value="month">Monthly</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs value={activeMetric} onValueChange={setActiveMetric}>
        <TabsList>
          <TabsTrigger value="revenue">
            <DollarSign className="mr-2 h-4 w-4" />
            Revenue
          </TabsTrigger>
          <TabsTrigger value="engagement">
            <TrendingUp className="mr-2 h-4 w-4" />
            Engagement
          </TabsTrigger>
          <TabsTrigger value="churn">
            <AlertTriangle className="mr-2 h-4 w-4" />
            Churn
          </TabsTrigger>
        </TabsList>
      </Tabs>

      <Card>
        <CardContent className="pt-6">{renderChart()}</CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Data Table</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-3">Date</th>
                  {activeMetric === "revenue" && (
                    <>
                      <th className="text-right py-2 px-3">Revenue</th>
                      <th className="text-right py-2 px-3">Cost</th>
                      <th className="text-right py-2 px-3">Profit</th>
                    </>
                  )}
                  {activeMetric === "engagement" && (
                    <>
                      <th className="text-right py-2 px-3">Engagement</th>
                      <th className="text-right py-2 px-3">Retention</th>
                      <th className="text-right py-2 px-3">Satisfaction</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {(activeMetric === "revenue" ? revenueData?.data : engagementData?.data)?.map(
                  (row: Record<string, unknown>, i: number) => (
                    <tr key={i} className="border-b hover:bg-muted/50">
                      <td className="py-2 px-3">
                        {format(new Date(row.date as string), "MMM d, yyyy")}
                      </td>
                      {activeMetric === "revenue" && (
                        <>
                          <td className="text-right py-2 px-3">
                            ${(row.revenue as number).toLocaleString()}
                          </td>
                          <td className="text-right py-2 px-3">
                            ${(row.cost as number).toLocaleString()}
                          </td>
                          <td className="text-right py-2 px-3">
                            ${(row.profit as number).toLocaleString()}
                          </td>
                        </>
                      )}
                      {activeMetric === "engagement" && (
                        <>
                          <td className="text-right py-2 px-3">
                            {(row.engagement as number).toFixed(1)}%
                          </td>
                          <td className="text-right py-2 px-3">
                            {(row.retention as number).toFixed(1)}%
                          </td>
                          <td className="text-right py-2 px-3">
                            {(row.satisfaction as number).toFixed(1)}%
                          </td>
                        </>
                      )}
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
