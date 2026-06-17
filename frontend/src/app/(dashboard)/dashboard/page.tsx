"use client";

import { useDashboard } from "@/hooks/use-query";
import { StatsCard } from "@/components/dashboard/stats-card";
import { EngagementChart } from "@/components/dashboard/engagement-chart";
import { RevenueChart } from "@/components/dashboard/revenue-chart";
import { SegmentPie } from "@/components/dashboard/segment-pie";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Users,
  Activity,
  Megaphone,
  TrendingUp,
  DollarSign,
  AlertTriangle,
  Clock,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

export default function DashboardPage() {
  const { data: dashboard, isLoading } = useDashboard();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No dashboard data available.
      </div>
    );
  }

  const { stats, engagement_trend, revenue_data, segment_distribution, top_segments, recent_activity, churn_alerts } = dashboard;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Executive Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Real-time overview of your customer twin platform
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          label="Total Customers"
          value={stats.total_customers.toLocaleString()}
          trend={12}
          trendLabel="vs last month"
          icon={<Users className="h-4 w-4 text-white" />}
          color="bg-blue-500"
        />
        <StatsCard
          label="Events (24h)"
          value={stats.events_24h.toLocaleString()}
          trend={8}
          trendLabel="vs yesterday"
          icon={<Activity className="h-4 w-4 text-white" />}
          color="bg-green-500"
        />
        <StatsCard
          label="Active Campaigns"
          value={stats.active_campaigns}
          icon={<Megaphone className="h-4 w-4 text-white" />}
          color="bg-purple-500"
        />
        <StatsCard
          label="Avg Engagement"
          value={`${stats.avg_engagement}%`}
          trend={3}
          trendLabel="vs last week"
          icon={<TrendingUp className="h-4 w-4 text-white" />}
          color="bg-amber-500"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          label="Total Revenue"
          value={`$${stats.total_revenue.toLocaleString()}`}
          trend={stats.revenue_growth}
          trendLabel="vs last month"
          icon={<DollarSign className="h-4 w-4 text-white" />}
          color="bg-emerald-500"
        />
        <StatsCard
          label="Churn Rate"
          value={`${stats.churn_rate}%`}
          trend={-2}
          trendLabel="vs last month"
          icon={<AlertTriangle className="h-4 w-4 text-white" />}
          color="bg-red-500"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <EngagementChart data={engagement_trend} />
        <RevenueChart data={revenue_data} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <SegmentPie data={segment_distribution} />

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Top Segments
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {top_segments.map((segment) => (
                <div
                  key={segment.name}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div>
                    <p className="font-medium text-sm">{segment.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {segment.customer_count} customers
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold">
                      ${segment.revenue.toLocaleString()}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {segment.avg_engagement}% eng.
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recent_activity.map((activity) => (
                <div
                  key={activity.id}
                  className="flex items-start gap-3 text-sm"
                >
                  <div className="mt-0.5">
                    <div className="h-2 w-2 rounded-full bg-primary" />
                  </div>
                  <div className="flex-1">
                    <p>{activity.description}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-muted-foreground">
                        {activity.user}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        &middot;
                      </span>
                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatDistanceToNow(
                          new Date(activity.timestamp),
                          { addSuffix: true }
                        )}
                      </span>
                    </div>
                  </div>
                  <Badge variant="secondary" className="text-[10px]">
                    {activity.type}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <AlertTriangle className="h-4 w-4 text-destructive" />
              Churn Alerts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {churn_alerts.map((alert) => (
                <div
                  key={alert.customer_id}
                  className="rounded-lg border border-destructive/20 bg-destructive/5 p-3"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm">
                      {alert.customer_name}
                    </span>
                    <Badge variant="destructive" className="text-[10px]">
                      {(alert.churn_probability * 100).toFixed(0)}%
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {alert.risk_factors.map((factor) => (
                      <Badge
                        key={factor}
                        variant="outline"
                        className="text-[10px]"
                      >
                        {factor}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
