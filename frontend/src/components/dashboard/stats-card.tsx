"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface StatsCardProps {
  label: string;
  value: string | number;
  trend?: number;
  trendLabel?: string;
  icon?: React.ReactNode;
  color?: string;
}

export function StatsCard({
  label,
  value,
  trend,
  trendLabel,
  icon,
  color,
}: StatsCardProps) {
  const TrendIcon =
    trend && trend > 0
      ? TrendingUp
      : trend && trend < 0
        ? TrendingDown
        : Minus;

  const trendColor =
    trend && trend > 0
      ? "text-green-600"
      : trend && trend < 0
        ? "text-red-600"
        : "text-muted-foreground";

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {label}
        </CardTitle>
        {icon && (
          <div
            className={cn(
              "h-8 w-8 rounded-lg flex items-center justify-center",
              color
            )}
          >
            {icon}
          </div>
        )}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {trend !== undefined && (
          <div className="flex items-center gap-1 mt-1">
            <TrendIcon
              className={cn("h-4 w-4", trendColor)}
            />
            <span className={cn("text-sm font-medium", trendColor)}>
              {trend > 0 ? "+" : ""}
              {trend}%
            </span>
            {trendLabel && (
              <span className="text-xs text-muted-foreground ml-1">
                {trendLabel}
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
