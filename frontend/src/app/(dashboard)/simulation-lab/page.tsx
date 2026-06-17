"use client";

import { useState } from "react";
import { useSimulations } from "@/hooks/use-query";
import { SimulationControls } from "@/components/simulation/simulation-controls";
import { SimulationResults } from "@/components/simulation/simulation-results";
import { ForecastChart } from "@/components/simulation/forecast-chart";
import { useSimulation } from "@/hooks/use-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FlaskConical, History, Plus } from "lucide-react";
import { format } from "date-fns";

export default function SimulationLabPage() {
  const [selectedSimulationId, setSelectedSimulationId] = useState<string | null>(null);
  const [showNewPanel, setShowNewPanel] = useState(true);

  const { data: simulationsData } = useSimulations();
  const { data: simulation } = useSimulation(selectedSimulationId || "");

  const handleSimulationCreated = (id: string) => {
    setSelectedSimulationId(id);
    setShowNewPanel(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Simulation Lab</h1>
          <p className="text-muted-foreground mt-1">
            Run Monte Carlo simulations and forecast scenarios
          </p>
        </div>
        <Button onClick={() => setShowNewPanel(true)}>
          <Plus className="mr-2 h-4 w-4" />
          New Simulation
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[350px_1fr]">
        <div className="space-y-6">
          {showNewPanel && (
            <SimulationControls
              onSimulationCreated={handleSimulationCreated}
            />
          )}

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm font-medium">
                <History className="h-4 w-4" />
                Run History
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 max-h-[400px] overflow-y-auto">
              {simulationsData?.data?.map((sim) => (
                <button
                  key={sim.id}
                  onClick={() => {
                    setSelectedSimulationId(sim.id);
                    setShowNewPanel(false);
                  }}
                  className="w-full text-left rounded-lg border p-3 hover:bg-muted transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium">{sim.name}</span>
                    <Badge
                      variant={
                        sim.status === "completed"
                          ? "success"
                          : sim.status === "running"
                            ? "default"
                            : sim.status === "failed"
                              ? "destructive"
                              : "secondary"
                      }
                      className="text-[10px]"
                    >
                      {sim.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {format(new Date(sim.created_at), "MMM d, yyyy HH:mm")}
                  </p>
                </button>
              ))}
              {(!simulationsData?.data || simulationsData.data.length === 0) && (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No simulations yet
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          {selectedSimulationId && simulation ? (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold">{simulation.name}</h2>
                  <p className="text-sm text-muted-foreground">
                    Status: {simulation.status}
                  </p>
                </div>
                <Badge variant="secondary">
                  {(simulation.config.confidence_level * 100).toFixed(0)}% confidence
                </Badge>
              </div>

              {simulation.status === "running" ? (
                <Card>
                  <CardContent className="flex items-center justify-center py-12">
                    <div className="text-center">
                      <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4" />
                      <p className="text-muted-foreground">
                        Running {simulation.config.iterations.toLocaleString()} iterations...
                      </p>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <>
                  <SimulationResults simulation={simulation} />
                  <ForecastChart simulation={simulation} />
                </>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
              <FlaskConical className="h-12 w-12 mb-4" />
              <p>Select a simulation or create a new one</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
