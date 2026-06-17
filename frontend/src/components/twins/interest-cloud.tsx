"use client";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

interface InterestCloudProps {
  interests: Array<{ name: string; weight: number }>;
  maxItems?: number;
}

export function InterestCloud({
  interests,
  maxItems = 30,
}: InterestCloudProps) {
  const sorted = [...interests]
    .sort((a, b) => b.weight - a.weight)
    .slice(0, maxItems);

  const maxWeight = Math.max(...sorted.map((i) => i.weight));
  const minWeight = Math.min(...sorted.map((i) => i.weight));

  const getSize = (weight: number) => {
    if (maxWeight === minWeight) return "md";
    const normalized = (weight - minWeight) / (maxWeight - minWeight);
    if (normalized > 0.8) return "xl";
    if (normalized > 0.6) return "lg";
    if (normalized > 0.4) return "md";
    if (normalized > 0.2) return "sm";
    return "xs";
  };

  const sizeClasses = {
    xs: "text-[10px] px-1.5 py-0.5",
    sm: "text-xs px-2 py-0.5",
    md: "text-sm px-2.5 py-1",
    lg: "text-base px-3 py-1",
    xl: "text-lg px-4 py-1.5",
  };

  return (
    <div className="flex flex-wrap gap-2 items-center justify-center p-4">
      {sorted.map((interest) => (
        <Badge
          key={interest.name}
          variant="secondary"
          className={cn(
            sizeClasses[getSize(interest.weight)],
            "transition-all hover:scale-110 cursor-default font-normal",
            interest.weight > 0.7 && "bg-primary/10 text-primary border-primary/20",
            interest.weight > 0.4 && interest.weight <= 0.7 && "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
          )}
        >
          {interest.name}
        </Badge>
      ))}
      {sorted.length === 0 && (
        <p className="text-sm text-muted-foreground">No interests data</p>
      )}
    </div>
  );
}
