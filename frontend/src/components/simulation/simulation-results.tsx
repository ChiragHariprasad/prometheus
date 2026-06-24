"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Simulation } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Target,
  AlertTriangle,
  BarChart3,
} from "lucide-react";

interface SimulationResultsProps {
  simulation: Simulation;
}

export function SimulationResults({ simulation }: SimulationResultsProps) {
  const { results } = simulation;

  if (!results) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">
            Run the simulation to see results.
          </p>
        </CardContent>
      </Card>
    );
  }

  const riskVariant =
    results.risk_assessment.level === "low"
      ? "success"
      : results.risk_assessment.level === "medium"
        ? "warning"
        : "destructive";

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <DollarSign className="h-4 w-4" />
              Expected Revenue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600 dark:text-green-400">
              ${results.expected_outcomes.expected_revenue.toLocaleString()}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Range: ${results.confidence_intervals.revenue[0].toLocaleString()} - $
              {results.confidence_intervals.revenue[1].toLocaleString()}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Target className="h-4 w-4" />
              Conversion Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-primary">
              {(results.aggregated_metrics.mean_conversion_rate * 100).toFixed(1)}%
            </p>
            <Progress
              value={results.aggregated_metrics.mean_conversion_rate * 100}
              className="mt-2 h-2"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <AlertTriangle className="h-4 w-4" />
              Risk Assessment
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant={riskVariant} className="mb-2">
              {results.risk_assessment.level.toUpperCase()} Risk
            </Badge>
            <ul className="space-y-1">
              {results.risk_assessment.factors.map((factor, i) => (
                <li
                  key={i}
                  className="text-xs text-muted-foreground flex items-start gap-1"
                >
                  <span className="mt-0.5">&#8226;</span>
                  {factor}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Scenario Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {(["best_case", "most_likely", "worst_case"] as const).map(
              (scenario) => {
                const data = results.monte_carlo_distribution.scenarios[scenario];
                const isBest = scenario === "best_case";
                const isWorst = scenario === "worst_case";
                const revenue = data?.revenue || 0;

                return (
                  <div
                    key={scenario}
                    className={cn(
                      "rounded-lg border p-4",
                      isBest && "border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950",
                      isWorst && "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950"
                    )}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium capitalize">
                        {scenario.replace("_", " ")}
                      </span>
                      <Badge
                        variant={
                          isBest
                            ? "success"
                            : isWorst
                              ? "destructive"
                              : "secondary"
                        }
                      >
                        ${revenue.toLocaleString()}
                      </Badge>
                    </div>
                    {data &&
                      Object.entries(data).map(([key, val]) => (
                        <div
                          key={key}
                          className="flex justify-between text-sm text-muted-foreground"
                        >
                          <span className="capitalize">
                            {key.replace("_", " ")}
                          </span>
                          <span>
                            {typeof val === "number" && val < 1
                              ? `${(val * 100).toFixed(1)}%`
                              : typeof val === "number"
                                ? `$${val.toLocaleString()}`
                                : String(val)}
                          </span>
                        </div>
                      ))}
                  </div>
                );
              }
            )}
          </div>
        </CardContent>
      </Card>

      {results.aggregated_metrics.sensitivity && results.aggregated_metrics.sensitivity.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <BarChart3 className="h-4 w-4" />
              Sensitivity Analysis
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {results.aggregated_metrics.sensitivity
                .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact))
                .map((item) => (
                  <div key={item.parameter}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="capitalize">
                        {item.parameter.replace("_", " ")}
                      </span>
                      <span
                        className={cn(
                          "font-mono",
                          item.impact > 0
                            ? "text-green-600"
                            : "text-red-600"
                        )}
                      >
                        {item.impact > 0 ? "+" : ""}
                        {(item.impact * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className={cn(
                          "absolute left-1/2 h-full rounded-full transition-all",
                          item.impact > 0
                            ? "bg-green-500"
                            : "bg-red-500"
                        )}
                        style={{
                          width: `${Math.abs(item.impact) * 100}%`,
                          transform: item.impact > 0 ? "translateX(0)" : "translateX(-100%)",
                          left: item.impact > 0 ? "50%" : "50%",
                        }}
                      />
                      <div className="absolute left-1/2 top-0 h-full w-px bg-border" />
                    </div>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
