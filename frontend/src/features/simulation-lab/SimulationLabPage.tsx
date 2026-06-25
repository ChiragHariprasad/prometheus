import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { 
  useCreateSimulation, 
  useSimulationDetails, 
  useSimulationProgress,
  useSimulationResults,
  useRunSimulation
} from '../../hooks/queries';
import { PageHeader } from '../../components/shared/PageHeader';
import { CampaignConfigurationForm } from './components/CampaignConfigurationForm';
import { ExecutiveOutcomeStrip } from './components/ExecutiveOutcomeStrip';
import { SimulationResultsDashboard } from './components/SimulationResultsDashboard';
import { SegmentResponseAnalysis } from './components/SegmentResponseAnalysis';
import { ErrorBoundary } from '../../components/shared/ErrorBoundary';
import { StatusBadge } from '../../components/shared/StatusBadge';
import { cn } from '../../utils';
import { Sliders, Sparkles, Loader2, PlayCircle, ClipboardList, CheckCircle, AlertCircle } from 'lucide-react';

export function SimulationLabPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const runId = searchParams.get('runId');
  const [activeSimulationId, setActiveSimulationId] = useState<string | null>(runId);

  // Synchronize with URL search param
  useEffect(() => {
    if (runId) {
      setActiveSimulationId(runId);
    }
  }, [runId]);

  // Mutations & Queries
  const createSimulationMutation = useCreateSimulation();
  const runSimulationMutation = useRunSimulation();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: sim, isLoading: isSimLoading } = useSimulationDetails(activeSimulationId || undefined);
  const { data: results, isLoading: isResultsLoading } = useSimulationResults(activeSimulationId || undefined);

  // Poll status while calculation is running
  const isRunning = sim?.status === 'running' || sim?.status === 'queued';
  const { data: progressData } = useSimulationProgress(activeSimulationId || undefined, isRunning);

  const handleRunSimulation = (payload: any) => {
    setErrorMessage(null);
    createSimulationMutation.mutate(payload, {
      onSuccess: (data: any) => {
        setActiveSimulationId(data.id);
        setSearchParams({ runId: data.id });
        
        if (data.status === 'draft' || data.status === 'failed') {
          runSimulationMutation.mutate(data.id, {
            onError: (err: any) => {
              setErrorMessage(err?.response?.data?.detail || err?.message || 'Failed to start simulation');
            }
          });
        }
      },
      onError: (err: any) => {
        setErrorMessage(err?.response?.data?.detail || err?.message || 'Failed to create simulation');
      }
    });
  };

  const getStepStatus = (step: number) => {
    const status = sim?.status;
    const progress = progressData?.progress ?? 0;

    if (!activeSimulationId) return 'inactive';

    if (status === 'completed') return 'completed';
    if (status === 'failed') return 'failed';

    if (step === 1) return 'completed'; // Parameters configured
    if (step === 2) return status === 'queued' ? 'active' : 'completed';
    if (step === 3) return status === 'running' && progress < 40 ? 'active' : progress >= 40 ? 'completed' : 'inactive';
    if (step === 4) return status === 'running' && progress >= 40 && progress < 80 ? 'active' : progress >= 80 ? 'completed' : 'inactive';
    if (step === 5) return status === 'running' && progress >= 80 ? 'active' : 'inactive';

    return 'inactive';
  };

  const getStepClass = (status: string) => {
    switch (status) {
      case 'completed': return 'border-success bg-success/10 text-success';
      case 'active': return 'border-accent bg-accent/10 text-accent font-semibold animate-pulse';
      case 'failed': return 'border-error bg-error/10 text-error';
      default: return 'border-zinc-200 dark:border-zinc-800 text-muted-foreground';
    }
  };

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-10 font-sans">
      <PageHeader
        title="Simulation Lab"
        subtitle="Forecast campaign outcomes and Monte Carlo risk variables before budget launch"
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Persistent Configuration sliders panel */}
        <div className="lg:col-span-4 sticky top-6">
          <ErrorBoundary>
            <CampaignConfigurationForm
              onRunSimulation={handleRunSimulation}
              loading={createSimulationMutation.isPending || runSimulationMutation.isPending || isRunning}
            />
          </ErrorBoundary>
        </div>

        {/* Right Column: Outcomes Analysis workspace */}
        <div className="lg:col-span-8 space-y-6">
          {!activeSimulationId ? (
            /* Draft State Description */
            <div className="rounded-lg border border-dashed p-10 bg-card text-center flex flex-col items-center justify-center min-h-[460px]">
              <Sliders className="h-12 w-12 text-muted-foreground mb-4 animate-pulse" />
              <h3 className="text-sm font-bold text-foreground">Configure parameters to launch model calculation</h3>
              <p className="text-xs text-muted-foreground max-w-sm mt-1">
                Tune the campaign channel type, target customer segments, discount rates, and touches on the left to project revenue and ROI matrices.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Stepper Workflow status */}
              <div className="rounded-lg border bg-card p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase font-bold tracking-widest text-zinc-400 font-mono">Calculations Pipeline</span>
                  {sim?.status && <StatusBadge type="simulation" status={sim.status} />}
                </div>

                <div className="grid grid-cols-5 gap-3">
                  {[
                    { s: 1, name: 'Config' },
                    { s: 2, name: 'Queue' },
                    { s: 3, name: 'Build Agents' },
                    { s: 4, name: 'Monte Carlo' },
                    { s: 5, name: 'Aggregate' },
                  ].map((step) => {
                    const st = getStepStatus(step.s);
                    return (
                      <div 
                        key={step.s} 
                        className={cn(
                          "border p-2 rounded text-center transition-all",
                          getStepClass(st)
                        )}
                      >
                        <p className="text-[9px] font-mono tracking-widest uppercase">{step.name}</p>
                      </div>
                    );
                  })}
                </div>

                {isRunning && (
                  <div className="space-y-2 pt-2">
                    <div className="flex justify-between text-[10px] font-mono text-muted-foreground">
                      <span>Task Progress: {progressData?.progress ?? 20}%</span>
                      <span>Iterations: {progressData?.completed_iterations ?? 200} / 1000</span>
                    </div>
                    <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-1.5 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 transition-all duration-300" style={{ width: `${progressData?.progress ?? 20}%` }}></div>
                    </div>
                  </div>
                )}

                {errorMessage && (
                  <div className="flex items-start gap-2 p-3 rounded border border-red-500/30 bg-red-500/5 text-red-400">
                    <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                    <div className="text-xs">
                      <p className="font-semibold">Simulation Error</p>
                      <p className="font-mono mt-0.5">{errorMessage}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Execution Loading Indicator */}
              {isRunning && (
                <div className="rounded-lg border p-12 bg-card text-center flex flex-col items-center justify-center min-h-[300px]">
                  <Loader2 className="h-8 w-8 text-accent animate-spin mb-3" />
                  <h4 className="text-xs font-bold text-foreground">Running scenario projections...</h4>
                  <p className="text-[10px] text-muted-foreground mt-1 font-mono">
                    Simulating 1,000 Monte Carlo variations for twin agents population.
                  </p>
                </div>
              )}

              {/* Hydrated Results View */}
              {!isRunning && (
                <>
                  {/* KPI strips outcomes summary */}
                  <ErrorBoundary>
                    <ExecutiveOutcomeStrip 
                      results={results || sim?.results} 
                      loading={isResultsLoading} 
                    />
                  </ErrorBoundary>

                  {/* Scenarios Best/Expected/Worst Cards and lines charts */}
                  <ErrorBoundary>
                    <SimulationResultsDashboard 
                      results={results || sim?.results} 
                      loading={isResultsLoading} 
                    />
                  </ErrorBoundary>

                  {/* Segment behavioral distributions */}
                  <ErrorBoundary>
                    <SegmentResponseAnalysis 
                      segmentProjections={results?.segment_projections || sim?.results?.segment_projections} 
                      loading={isResultsLoading} 
                    />
                  </ErrorBoundary>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
export default SimulationLabPage;
