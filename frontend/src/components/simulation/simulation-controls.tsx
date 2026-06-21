"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useSegments, useCreateSimulation, useRunSimulation } from "@/hooks/use-query";
import { useSimulationRealtime } from "@/hooks/use-realtime";
import { Play, Square, FlaskConical, Sliders } from "lucide-react";

interface SimulationControlsProps {
  onSimulationCreated: (id: string) => void;
}

export function SimulationControls({
  onSimulationCreated,
}: SimulationControlsProps) {
  const { data: segments } = useSegments();
  const createSimulation = useCreateSimulation();
  const [config, setConfig] = useState({
    name: "",
    iterations: 1000,
    time_horizon: 30,
    confidence_level: 0.95,
    segment_ids: [] as string[],
    parameters: {} as Record<string, unknown>,
  });

  const runSimulation = useRunSimulation();

  const handleCreate = async () => {
    const result = await createSimulation.mutateAsync({
      name: config.name || `Simulation ${new Date().toLocaleDateString()}`,
      iterations: config.iterations,
      time_horizon: config.time_horizon,
      confidence_level: config.confidence_level,
      segment_ids: config.segment_ids,
      parameters: config.parameters,
    });
    await runSimulation.mutateAsync(result.id);
    onSimulationCreated(result.id);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <FlaskConical className="h-5 w-5" />
          Simulation Configuration
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <Label>Simulation Name</Label>
          <Input
            value={config.name}
            onChange={(e) =>
              setConfig((prev) => ({ ...prev, name: e.target.value }))
            }
            placeholder="Q3 Forecast Simulation"
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Monte Carlo Iterations</Label>
            <Badge variant="secondary">{config.iterations.toLocaleString()}</Badge>
          </div>
          <Input
            type="range"
            min={100}
            max={10000}
            step={100}
            value={config.iterations}
            onChange={(e) =>
              setConfig((prev) => ({
                ...prev,
                iterations: parseInt(e.target.value),
              }))
            }
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>100</span>
            <span>10,000</span>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Time Horizon (days)</Label>
            <Badge variant="secondary">{config.time_horizon} days</Badge>
          </div>
          <Input
            type="range"
            min={7}
            max={365}
            step={7}
            value={config.time_horizon}
            onChange={(e) =>
              setConfig((prev) => ({
                ...prev,
                time_horizon: parseInt(e.target.value),
              }))
            }
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>7 days</span>
            <span>365 days</span>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Confidence Level</Label>
            <Badge variant="secondary">
              {(config.confidence_level * 100).toFixed(0)}%
            </Badge>
          </div>
          <Input
            type="range"
            min={0.8}
            max={0.99}
            step={0.01}
            value={config.confidence_level}
            onChange={(e) =>
              setConfig((prev) => ({
                ...prev,
                confidence_level: parseFloat(e.target.value),
              }))
            }
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>80%</span>
            <span>99%</span>
          </div>
        </div>

        <div className="space-y-2">
          <Label>Target Segments</Label>
          <Select
            onValueChange={(value) =>
              setConfig((prev) => ({
                ...prev,
                segment_ids: [value],
              }))
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Select segment..." />
            </SelectTrigger>
            <SelectContent>
              {segments?.map((segment) => (
                <SelectItem key={segment.id} value={segment.id}>
                  {segment.name} ({segment.customer_count})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button
          className="w-full"
          onClick={handleCreate}
          disabled={createSimulation.isPending}
        >
          <Play className="mr-2 h-4 w-4" />
          {createSimulation.isPending ? "Creating..." : "Create & Run Simulation"}
        </Button>
      </CardContent>
    </Card>
  );
}
