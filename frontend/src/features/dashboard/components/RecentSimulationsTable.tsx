import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Simulation } from '../../../types';
import { DataTable } from '../../../components/shared/DataTable';
import { StatusBadge } from '../../../components/shared/StatusBadge';
import { formatCurrency, formatRoi } from '../../../utils';

interface RecentSimulationsTableProps {
  simulations?: Simulation[];
  loading?: boolean;
}

export function RecentSimulationsTable({ simulations = [], loading = false }: RecentSimulationsTableProps) {
  const navigate = useNavigate();

  // If simulations is empty and loading is false, fallback to demo mocks
  const tableData = simulations.length > 0 ? simulations.slice(0, 5) : [
    {
      id: 'sim-1',
      name: 'Loyal Buyers Lift',
      status: 'completed' as const,
      time_horizon_days: 30,
      created_at: new Date(Date.now() - 3600000).toISOString(),
      results: {
        expected_revenue: 345000,
        expected_roi: 2.8,
        expected_churns: 5,
        ltv_impact: 450,
        probability_of_loss: 0.04
      }
    },
    {
      id: 'sim-2',
      name: 'VIP Churn Defense',
      status: 'running' as const,
      time_horizon_days: 30,
      created_at: new Date(Date.now() - 7200000).toISOString(),
      results: {
        expected_revenue: 120000,
        expected_roi: 1.5,
        expected_churns: 2,
        ltv_impact: 210,
        probability_of_loss: 0.12
      }
    },
    {
      id: 'sim-3',
      name: 'Reactivation Campaign Test',
      status: 'failed' as const,
      time_horizon_days: 14,
      created_at: new Date(Date.now() - 86400000).toISOString(),
      results: {
        expected_revenue: 0,
        expected_roi: 0,
        expected_churns: 0,
        ltv_impact: 0,
        probability_of_loss: 0.8
      }
    }
  ];

  const columns = [
    {
      header: 'Simulation Scenario',
      accessor: (item: any) => (
        <div className="flex flex-col gap-0.5">
          <span className="font-semibold text-foreground">{item.name}</span>
          <span className="text-[10px] text-muted-foreground font-mono">{item.id}</span>
        </div>
      )
    },
    {
      header: 'Status',
      accessor: (item: any) => (
        <div className="flex flex-col gap-1 w-24">
          <StatusBadge type="simulation" status={item.status} />
          {item.status === 'running' && (
            <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-1 rounded-full overflow-hidden">
              <div className="bg-blue-500 h-full animate-pulse w-3/5" />
            </div>
          )}
        </div>
      )
    },
    {
      header: 'Proj. Revenue',
      accessor: (item: any) => (
        <span className="font-mono font-medium">
          {item.status === 'completed' || item.status === 'running' 
            ? formatCurrency(item.results?.expected_revenue) 
            : '—'}
        </span>
      )
    },
    {
      header: 'ROI',
      accessor: (item: any) => (
        <span className="font-mono font-medium text-foreground">
          {item.status === 'completed' || item.status === 'running' 
            ? formatRoi(item.results?.expected_roi) 
            : '—'}
        </span>
      )
    },
    {
      header: 'Risk Score',
      accessor: (item: any) => {
        const risk = item.results?.probability_of_loss ?? 0;
        return (
          <span className={`font-mono font-semibold ${risk > 0.3 ? 'text-error' : risk > 0.1 ? 'text-warning' : 'text-success'}`}>
            {risk > 0 ? `${(risk * 100).toFixed(0)}% loss prob` : '0%'}
          </span>
        );
      }
    }
  ];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold tracking-tight text-foreground font-sans">Recent Simulations</h3>
        <button 
          onClick={() => navigate('/simulation-lab')} 
          className="text-xs font-semibold text-accent hover:underline"
        >
          Launch Simulation Lab
        </button>
      </div>

      <DataTable
        data={tableData}
        columns={columns}
        loading={loading}
        onRowClick={(item: any) => navigate(`/simulation-lab?runId=${item.id}`)}
      />
    </div>
  );
}
export default RecentSimulationsTable;
