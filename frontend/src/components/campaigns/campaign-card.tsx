"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Campaign } from "@/lib/api-client";
import { formatDistanceToNow, format } from "date-fns";
import {
  Mail,
  MessageSquare,
  Bell,
  Smartphone,
  Eye,
  MousePointerClick,
  TrendingUp,
  DollarSign,
} from "lucide-react";

interface CampaignCardProps {
  campaign: Campaign;
  onClick?: () => void;
}

const channelIcons: Record<string, typeof Mail> = {
  email: Mail,
  sms: MessageSquare,
  push: Bell,
  in_app: Smartphone,
};

const statusVariants: Record<string, "default" | "secondary" | "success" | "warning" | "destructive"> = {
  draft: "secondary",
  active: "success",
  paused: "warning",
  completed: "default",
  cancelled: "destructive",
};

export function CampaignCard({ campaign, onClick }: CampaignCardProps) {
  const ChannelIcon = channelIcons[campaign.type] || Mail;

  return (
    <Card
      className="cursor-pointer transition-all hover:shadow-md"
      onClick={onClick}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <ChannelIcon className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-base">{campaign.name}</CardTitle>
          </div>
          <Badge variant={statusVariants[campaign.status] || "secondary"}>
            {campaign.status}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground line-clamp-1">
          {campaign.goal}
        </p>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              {format(new Date(campaign.schedule.start), "MMM d, yyyy")}
            </span>
            <span className="text-muted-foreground">
              {formatDistanceToNow(new Date(campaign.created_at), {
                addSuffix: true,
              })}
            </span>
          </div>
          {campaign.metrics.sent > 0 && (
            <div className="grid grid-cols-4 gap-2 pt-2 border-t">
              <div className="flex flex-col items-center">
                <span className="text-lg font-bold">
                  {campaign.metrics.sent.toLocaleString()}
                </span>
                <span className="text-[10px] text-muted-foreground">Sent</span>
              </div>
              <div className="flex flex-col items-center">
                <span className="text-lg font-bold">
                  {((campaign.metrics.opened / campaign.metrics.sent) * 100).toFixed(1)}%
                </span>
                <span className="text-[10px] text-muted-foreground">
                  <Eye className="inline h-3 w-3 mr-0.5" />
                  Open
                </span>
              </div>
              <div className="flex flex-col items-center">
                <span className="text-lg font-bold">
                  {((campaign.metrics.clicked / campaign.metrics.sent) * 100).toFixed(1)}%
                </span>
                <span className="text-[10px] text-muted-foreground">
                  <MousePointerClick className="inline h-3 w-3 mr-0.5" />
                  CTR
                </span>
              </div>
              <div className="flex flex-col items-center">
                <span className="text-lg font-bold">
                  ${campaign.metrics.revenue.toLocaleString()}
                </span>
                <span className="text-[10px] text-muted-foreground">
                  <DollarSign className="inline h-3 w-3 mr-0.5" />
                  Rev
                </span>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
