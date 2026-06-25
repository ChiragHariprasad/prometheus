import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  useCustomers, 
  useCustomerDetails, 
  useCustomerTwin, 
  useCustomerEvents, 
  useRebuildTwin 
} from '../../hooks/queries';
import { Customer } from '../../types';
import { PageHeader } from '../../components/shared/PageHeader';
import { CustomerSelector } from './components/CustomerSelector';
import { CustomerSummary } from './components/CustomerSummary';
import { DigitalTwinCanvas } from './components/DigitalTwinCanvas';
import { InterestGraph } from './components/InterestGraph';
import { MemoryTimeline } from './components/MemoryTimeline';
import { SentimentPanel } from './components/SentimentPanel';
import { PredictionPanel } from './components/PredictionPanel';
import { ErrorBoundary } from '../../components/shared/ErrorBoundary';
import { cn } from '../../utils';
import { RefreshCw, Play, Search, Network } from 'lucide-react';

export function TwinExplorerPage() {
  const { twinId } = useParams<{ twinId?: string }>();
  const navigate = useNavigate();
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | undefined>(twinId);

  // Sync selected ID with URL parameter
  useEffect(() => {
    if (twinId) {
      setSelectedCustomerId(twinId);
    }
  }, [twinId]);

  // If no twinId parameter is set, default to first customer in list to seed the dashboard demo
  const { data: listData } = useCustomers(1, 1);
  useEffect(() => {
    if (!twinId && listData?.data && listData.data.length > 0) {
      setSelectedCustomerId(listData.data[0].id);
    }
  }, [listData, twinId]);

  // Core Data Queries
  const { data: customer, isLoading: isCustLoading } = useCustomerDetails(selectedCustomerId);
  const { data: twin, isLoading: isTwinLoading, refetch: refetchTwin } = useCustomerTwin(selectedCustomerId);
  const { data: eventsData, isLoading: isEventsLoading } = useCustomerEvents(selectedCustomerId);

  const rebuildTwinMutation = useRebuildTwin();

  const handleSelectCustomer = (cust: Customer) => {
    setSelectedCustomerId(cust.id);
    navigate(`/twins/${cust.id}`);
  };

  const handleRebuild = () => {
    if (selectedCustomerId) {
      rebuildTwinMutation.mutate(selectedCustomerId);
    }
  };

  const events = eventsData?.data || [];

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-10 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between pb-4 border-b gap-4">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight text-foreground font-sans">Digital Twin Explorer</h2>
          <p className="text-sm text-muted-foreground font-sans">Dive deep into predictive, real-time customer behavior models</p>
        </div>
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <CustomerSelector 
            selectedId={selectedCustomerId} 
            onSelect={handleSelectCustomer} 
          />
          <button
            onClick={handleRebuild}
            disabled={!selectedCustomerId || rebuildTwinMutation.isPending}
            className="h-10 px-4 rounded bg-accent hover:bg-blue-700 text-white text-xs font-semibold flex items-center justify-center gap-2 shrink-0 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", rebuildTwinMutation.isPending && "animate-spin")} />
            Rebuild Model
          </button>
        </div>
      </div>

      {/* Main command layout grid */}
      {!selectedCustomerId ? (
        <div className="flex flex-col items-center justify-center p-20 border border-dashed rounded-lg bg-card text-center">
          <Network className="h-12 w-12 text-muted-foreground mb-4 animate-pulse" />
          <h3 className="text-sm font-bold text-foreground">Select a customer twin to begin profile exploration</h3>
          <p className="text-xs text-muted-foreground max-w-sm mt-1">
            Choose a customer from the dropdown search above to hydrate their traits, orbits, and next best action forecasts.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left panel: Summary & Scores */}
          <div className="lg:col-span-3">
            <ErrorBoundary>
              <CustomerSummary
                customer={customer}
                twin={twin || undefined}
                events={events}
                loading={isCustLoading || isTwinLoading}
              />
            </ErrorBoundary>
          </div>

          {/* Center panel: Canvas & tabs */}
          <div className="lg:col-span-6 space-y-6">
            {/* SVG Interactive Canvas */}
            <ErrorBoundary>
              <DigitalTwinCanvas
                customer={customer}
                twin={twin || undefined}
                loading={isTwinLoading}
              />
            </ErrorBoundary>

            {/* Bottom details charts tab layout */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <ErrorBoundary>
                <InterestGraph 
                  twin={twin || undefined} 
                  loading={isTwinLoading} 
                />
              </ErrorBoundary>

              <ErrorBoundary>
                <SentimentPanel
                  sentimentScore={twin?.sentiment_score}
                  sentimentTrend={twin?.sentiment_trend as any}
                  loading={isTwinLoading}
                />
              </ErrorBoundary>
            </div>

            {/* Timeline Log */}
            <div className="rounded-lg border bg-card p-6 shadow-sm space-y-4">
              <h3 className="text-sm font-semibold tracking-tight text-foreground font-sans">Chronological Interaction History</h3>
              <ErrorBoundary>
                <MemoryTimeline 
                  events={events} 
                  loading={isEventsLoading} 
                />
              </ErrorBoundary>
            </div>
          </div>

          {/* Right panel: Predictions & recommendations */}
          <div className="lg:col-span-3">
            <ErrorBoundary>
              <PredictionPanel
                customer={customer}
                twin={twin || undefined}
                loading={isCustLoading || isTwinLoading}
              />
            </ErrorBoundary>
          </div>
        </div>
      )}
    </div>
  );
}
export default TwinExplorerPage;
