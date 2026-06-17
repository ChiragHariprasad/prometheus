"use client";

import { cn } from "@/lib/utils";

interface ScoreGaugeProps {
  label: string;
  value: number;
  max?: number;
  size?: "sm" | "md" | "lg";
}

export function ScoreGauge({ label, value, max = 100, size = "md" }: ScoreGaugeProps) {
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
