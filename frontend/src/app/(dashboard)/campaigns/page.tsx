"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCampaigns } from "@/hooks/use-query";
import { CampaignCard } from "@/components/campaigns/campaign-card";
import { StatsCard } from "@/components/dashboard/stats-card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Megaphone, Plus, BarChart3, Send, TrendingUp } from "lucide-react";

export default function CampaignsPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState("all");

  const { data, isLoading } = useCampaigns({
    status: statusFilter !== "all" ? statusFilter : undefined,
  });

  const campaigns = data?.data || [];

  const stats = {
    total: campaigns.length,
    active: campaigns.filter((c) => c.status === "active").length,
    sent: campaigns.reduce((sum, c) => sum + (c.metrics?.sent || 0), 0),
    revenue: campaigns.reduce((sum, c) => sum + (c.metrics?.revenue || 0), 0),
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Campaigns</h1>
          <p className="text-muted-foreground mt-1">
            Create, manage, and analyze marketing campaigns
          </p>
        </div>
        <Button onClick={() => router.push("/campaigns/new")}>
          <Plus className="mr-2 h-4 w-4" />
          New Campaign
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          label="Total Campaigns"
          value={stats.total}
          icon={<Megaphone className="h-4 w-4 text-white" />}
          color="bg-purple-500"
        />
        <StatsCard
          label="Active"
          value={stats.active}
          icon={<BarChart3 className="h-4 w-4 text-white" />}
          color="bg-green-500"
        />
        <StatsCard
          label="Total Sent"
          value={stats.sent.toLocaleString()}
          icon={<Send className="h-4 w-4 text-white" />}
          color="bg-blue-500"
        />
        <StatsCard
          label="Revenue Generated"
          value={`$${stats.revenue.toLocaleString()}`}
          icon={<TrendingUp className="h-4 w-4 text-white" />}
          color="bg-emerald-500"
        />
      </div>

      <Tabs value={statusFilter} onValueChange={setStatusFilter}>
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="draft">Draft</TabsTrigger>
          <TabsTrigger value="active">Active</TabsTrigger>
          <TabsTrigger value="paused">Paused</TabsTrigger>
          <TabsTrigger value="completed">Completed</TabsTrigger>
        </TabsList>
      </Tabs>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {campaigns.map((campaign) => (
            <CampaignCard
              key={campaign.id}
              campaign={campaign}
              onClick={() => router.push(`/campaigns/${campaign.id}`)}
            />
          ))}
          {campaigns.length === 0 && (
            <div className="col-span-full text-center py-12 text-muted-foreground">
              No campaigns found. Create your first campaign to get started.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
