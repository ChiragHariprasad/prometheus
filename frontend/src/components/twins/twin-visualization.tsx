"use client";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Activity,
  Heart,
  MessageCircle,
} from "lucide-react";

interface ScoreGaugeProps {
  label: string;
  value: number;
  max?: number;
  size?: "sm" | "md" | "lg";
  color?: string;
}

export function ScoreGauge({
  label,
  value,
  max = 100,
  size = "md",
}: ScoreGaugeProps) {
  const percentage = (value / max) * 100;
  const circumference = 2 * Math.PI * 40;
  const offset = circumference - (percentage / 100) * circumference;

  const getColor = (val: number) => {
    if (val >= 70) return "#22c55e";
    if (val >= 40) return "#f59e0b";
    return "#ef4444";
  };

  const dims = size === "sm" ? 60 : size === "md" ? 100 : 140;
  const strokeWidth = size === "sm" ? 4 : size === "md" ? 6 : 8;
  const radius = (dims - strokeWidth) / 2;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={dims} height={dims} className="-rotate-90">
        <circle
          cx={dims / 2}
          cy={dims / 2}
          r={radius}
          fill="none"
          stroke="hsl(var(--muted))"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={dims / 2}
          cy={dims / 2}
          r={radius}
          fill="none"
          stroke={getColor(value)}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-500"
        />
      </svg>
      <span
        className={cn(
          "font-bold",
          size === "sm" ? "text-sm" : size === "md" ? "text-lg" : "text-2xl"
        )}
        style={{ color: getColor(value) }}
      >
        {Math.round(value)}%
      </span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

interface TwinVisualizationProps {
  twin: {
    engagement_score: number;
    loyalty_score: number;
    sentiment_score: number;
    churn_probability: number;
    interests: Array<{ name: string; weight: number }>;
    channel_affinity: Record<string, number>;
    sentiment_trend: Array<{ date: string; score: number }>;
  };
}

export function TwinVisualization({ twin }: TwinVisualizationProps) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <ScoreGauge label="Engagement" value={twin.engagement_score} />
        <ScoreGauge label="Loyalty" value={twin.loyalty_score} />
        <ScoreGauge label="Sentiment" value={twin.sentiment_score} />
        <div className="flex flex-col items-center justify-center gap-2">
          <div
            className={cn(
              "flex items-center gap-2 rounded-full px-3 py-1",
              twin.churn_probability > 0.5
                ? "bg-destructive/10 text-destructive"
                : twin.churn_probability > 0.3
                  ? "bg-yellow-50 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300"
                  : "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300"
            )}
          >
            <AlertTriangle className="h-4 w-4" />
            <span className="text-sm font-medium">
              {(twin.churn_probability * 100).toFixed(0)}% churn risk
            </span>
          </div>
          <span className="text-xs text-muted-foreground">Churn Risk</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Interests</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {twin.interests.map((interest) => (
                <Badge
                  key={interest.name}
                  variant="secondary"
                  className={cn(
                    "text-xs",
                    interest.weight > 0.7 && "bg-primary/10 text-primary"
                  )}
                >
                  {interest.name}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Channel Affinity
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(twin.channel_affinity).map(([channel, score]) => (
              <div key={channel}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="capitalize">{channel}</span>
                  <span>{(score * 100).toFixed(0)}%</span>
                </div>
                <Progress
                  value={score * 100}
                  className="h-2 [&>div]:bg-primary"
                />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {twin.sentiment_trend.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Sentiment Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 flex items-end gap-1">
              {twin.sentiment_trend.slice(-30).map((point, i) => (
                <div
                  key={i}
                  className="flex-1 flex flex-col justify-end"
                >
                  <div
                    className={cn(
                      "w-full rounded-t transition-all",
                      point.score >= 0.7
                        ? "bg-engagement-high"
                        : point.score >= 0.4
                          ? "bg-engagement-medium"
                          : "bg-engagement-low"
                    )}
                    style={{ height: `${point.score * 100}%` }}
                  />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
