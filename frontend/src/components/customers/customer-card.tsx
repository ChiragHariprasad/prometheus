"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Customer } from "@/lib/api-client";
import { formatDistanceToNow } from "date-fns";
import { Mail, Phone, Tag, Activity, DollarSign, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface CustomerCardProps {
  customer: Customer;
  onClick?: () => void;
}

export function CustomerCard({ customer, onClick }: CustomerCardProps) {
  const churnVariant =
    customer.churn_risk === "high"
      ? "destructive"
      : customer.churn_risk === "medium"
        ? "warning"
        : "success";

  return (
    <Card
      className={cn(
        "cursor-pointer transition-all hover:shadow-md",
        customer.churn_risk === "high" && "border-destructive/50"
      )}
      onClick={onClick}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-base">{customer.name}</CardTitle>
            <p className="text-sm text-muted-foreground">{customer.email}</p>
          </div>
          <Badge variant={churnVariant}>
            {customer.churn_risk === "high" && (
              <AlertTriangle className="mr-1 h-3 w-3" />
            )}
            {customer.churn_risk} risk
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Engagement</span>
              <span className="font-medium">{customer.engagement_score}%</span>
            </div>
            <Progress
              value={customer.engagement_score}
              className={cn(
                "h-2",
                customer.engagement_score >= 70
                  ? "[&>div]:bg-engagement-high"
                  : customer.engagement_score >= 40
                    ? "[&>div]:bg-engagement-medium"
                    : "[&>div]:bg-engagement-low"
              )}
            />
          </div>
          <div>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Loyalty</span>
              <span className="font-medium">{customer.loyalty_score}%</span>
            </div>
            <Progress
              value={customer.loyalty_score}
              className="h-2 [&>div]:bg-primary"
            />
          </div>
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-1 text-muted-foreground">
              <DollarSign className="h-3.5 w-3.5" />
              <span>LTV: ${customer.ltv.toLocaleString()}</span>
            </div>
            <div className="flex items-center gap-1 text-muted-foreground">
              <Activity className="h-3.5 w-3.5" />
              <span>
                {formatDistanceToNow(new Date(customer.last_activity), {
                  addSuffix: true,
                })}
              </span>
            </div>
          </div>
          {customer.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {customer.tags.map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs">
                  <Tag className="mr-1 h-2.5 w-2.5" />
                  {tag}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
