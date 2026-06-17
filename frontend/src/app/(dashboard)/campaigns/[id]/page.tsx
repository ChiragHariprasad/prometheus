"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useCampaign } from "@/hooks/use-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ArrowLeft,
  Play,
  Pause,
  XCircle,
  Mail,
  MessageSquare,
  Bell,
  Smartphone,
  Eye,
  MousePointerClick,
  TrendingUp,
  DollarSign,
  Users,
  Clock,
  BarChart3,
  Send,
} from "lucide-react";
import { format } from "date-fns";
import Link from "next/link";

const channelIcons: Record<string, typeof Mail> = {
  email: Mail,
  sms: MessageSquare,
  push: Bell,
  in_app: Smartphone,
};

export default function CampaignDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { data: campaign, isLoading } = useCampaign(id);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        Campaign not found.
      </div>
    );
  }

  const ChannelIcon = channelIcons[campaign.type] || Mail;

  const statusActions: Record<string, React.ReactNode> = {
    draft: (
      <>
        <Button>
          <Play className="mr-2 h-4 w-4" />
          Launch
        </Button>
      </>
    ),
    active: (
      <>
        <Button variant="outline">
          <Pause className="mr-2 h-4 w-4" />
          Pause
        </Button>
        <Button variant="destructive">
          <XCircle className="mr-2 h-4 w-4" />
          Cancel
        </Button>
      </>
    ),
    paused: (
      <>
        <Button>
          <Play className="mr-2 h-4 w-4" />
          Resume
        </Button>
        <Button variant="destructive">
          <XCircle className="mr-2 h-4 w-4" />
          Cancel
        </Button>
      </>
    ),
  };

  const metrics = [
    {
      label: "Sent",
      value: campaign.metrics.sent.toLocaleString(),
      icon: Send,
      color: "text-blue-600",
    },
    {
      label: "Open Rate",
      value: campaign.metrics.sent
        ? `${((campaign.metrics.opened / campaign.metrics.sent) * 100).toFixed(1)}%`
        : "—",
      icon: Eye,
      color: "text-green-600",
    },
    {
      label: "Click Rate",
      value: campaign.metrics.delivered
        ? `${((campaign.metrics.clicked / campaign.metrics.delivered) * 100).toFixed(1)}%`
        : "—",
      icon: MousePointerClick,
      color: "text-purple-600",
    },
    {
      label: "Conversion",
      value: campaign.metrics.sent
        ? `${((campaign.metrics.converted / campaign.metrics.sent) * 100).toFixed(1)}%`
        : "—",
      icon: TrendingUp,
      color: "text-amber-600",
    },
    {
      label: "Revenue",
      value: `$${campaign.metrics.revenue.toLocaleString()}`,
      icon: DollarSign,
      color: "text-emerald-600",
    },
    {
      label: "ROI",
      value: `${(campaign.metrics.roi * 100).toFixed(0)}%`,
      icon: BarChart3,
      color: "text-rose-600",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/campaigns">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <ChannelIcon className="h-5 w-5 text-muted-foreground" />
            <h1 className="text-3xl font-bold">{campaign.name}</h1>
            <Badge
              variant={
                campaign.status === "active"
                  ? "success"
                  : campaign.status === "paused"
                    ? "warning"
                    : campaign.status === "completed"
                      ? "default"
                      : campaign.status === "cancelled"
                        ? "destructive"
                        : "secondary"
              }
            >
              {campaign.status}
            </Badge>
          </div>
          <p className="text-muted-foreground mt-1">{campaign.goal}</p>
        </div>
        <div className="flex items-center gap-2">
          {statusActions[campaign.status] || null}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Campaign Details
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Type</span>
              <Badge variant="secondary">{campaign.type}</Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Status</span>
              <Badge>{campaign.status}</Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Start</span>
              <span>
                {format(new Date(campaign.schedule.start), "MMM d, yyyy HH:mm")}
              </span>
            </div>
            {campaign.schedule.end && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">End</span>
                <span>
                  {format(new Date(campaign.schedule.end), "MMM d, yyyy HH:mm")}
                </span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-muted-foreground">Segments</span>
              <span>{campaign.segment_ids.length}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Schedule
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center gap-2 text-sm">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span>
                {format(new Date(campaign.schedule.start), "EEEE, MMMM d, yyyy 'at' HH:mm")}
              </span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span>Timezone: {campaign.schedule.timezone}</span>
            </div>
            {campaign.schedule.frequency && (
              <div className="flex items-center gap-2 text-sm">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span>Frequency: {campaign.schedule.frequency}</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Performance Metrics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {metrics.map((metric) => (
              <div
                key={metric.label}
                className="flex flex-col items-center p-3 rounded-lg border"
              >
                <metric.icon className={`h-5 w-5 mb-1 ${metric.color}`} />
                <p className="text-lg font-bold">{metric.value}</p>
                <p className="text-xs text-muted-foreground">{metric.label}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {campaign.ab_test?.enabled && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              A/B Test Results
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {campaign.ab_test.variants.map((variant) => (
                <div
                  key={variant.name}
                  className="rounded-lg border p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{variant.name}</span>
                    <Badge variant="secondary">
                      {variant.traffic_percentage}% traffic
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Subject: {variant.content.subject as string}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}


