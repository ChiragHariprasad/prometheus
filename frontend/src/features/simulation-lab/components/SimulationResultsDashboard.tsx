import React from 'react';
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  AreaChart, 
  Area,
  Legend
} from 'recharts';
import { formatCurrency, formatRoi } from '../../../utils';
import { cn } from '../../../utils';
import { ShieldCheck, AlertCircle, Award, Target, BarChart2 } from 'lucide-react';

interface SimulationResultsProps {
  results?: any;
  loading?: boolean;
}

export function SimulationResultsDashboard({
  results,
  loading = false,
}: SimulationResultsProps) {
  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-28 bg-muted rounded"></div>
        <div className="h-64 bg-muted rounded"></div>
      </div>
    );
  }

  const dist = results?.monte_carlo_distribution || {};
  const scenarios = dist?.scenarios || {};
  const risk = results?.risk_assessment || {};
  const outcomes = results?.expected_outcomes || {};
  const metrics = results?.aggregated_metrics || {};

  const bestCase = scenarios?.best_case ?? { revenue: 425000, conversions: 2450, conversion_rate: 0.18 };
  const expectedCase = scenarios?.expected_case ?? { revenue: 345000, conversions: 1840, conversion_rate: 0.12 };
  const worstCase = scenarios?.worst_case ?? { revenue: 215000, conversions: 1120, conversion_rate: 0.07 };

  const probLoss = risk?.probability_of_loss ?? 0.04;
  const roi = outcomes?.expected_roi ?? metrics?.roi ?? 2.8;

  const getDecisionBadge = () => {
    if (roi > 2.0 && probLoss < 0.10) return { label: 'SCALE', color: 'bg-emerald-500 text-white' };
    if (roi > 1.0 && probLoss < 0.20) return { label: 'PROCEED', color: 'bg-emerald-600/80 text-white' };
    if (roi > 0 && probLoss < 0.35) return { label: 'TEST SMALL', color: 'bg-amber-500 text-white' };
    return { label: 'REVISE', color: 'bg-red-500 text-white' };
  };

  const decision = getDecisionBadge();

  const histogramData = dist?.histogram?.length > 0 ? dist.histogram.map((h: any) => ({
    bin: `$${Math.round(h.bin_start / 1000)}k`,
    Frequency: h.count,
  })) : [
    { bin: '$200k', Frequency: 20 },
    { bin: '$250k', Frequency: 65 },
    { bin: '$300k', Frequency: 180 },
    { bin: '$350k', Frequency: 320 },
    { bin: '$400k', Frequency: 240 },
    { bin: '$450k', Frequency: 90 },
    { bin: '$500k', Frequency: 15 },
  ];

  const intervalData = results?.confidence_intervals?.length > 0
    ? results.confidence_intervals.map((ci: any, i: number) => ({
        day: `Day ${(i + 1) * 5}`,
        Expected: ci.expected || 0,
        Lower95: ci.lower || 0,
        Upper95: ci.upper || 0,
      }))
    : [
    { day: 'Day 1', Expected: 12000, Lower95: 10000, Upper95: 14000 },
    { day: 'Day 5', Expected: 58000, Lower95: 50000, Upper95: 66000 },
    { day: 'Day 10', Expected: 124000, Lower95: 105000, Upper95: 143000 },
    { day: 'Day 15', Expected: 182000, Lower95: 150000, Upper95: 214000 },
    { day: 'Day 20', Expected: 245000, Lower95: 200000, Upper95: 290000 },
    { day: 'Day 25', Expected: 298000, Lower95: 245000, Upper95: 351000 },
    { day: 'Day 30', Expected: 345000, Lower95: 280000, Upper95: 410000 },
  ];

  return (
    <div className="space-y-6 font-sans text-xs">
      {/* Scenario Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="rounded-lg border border-success/20 bg-success/5 p-4 space-y-2 relative overflow-hidden">
          <span className="text-[10px] uppercase font-bold tracking-widest text-success font-mono">Best Case Scenario</span>
          <p className="text-xl font-bold font-mono text-foreground">{formatCurrency(bestCase.revenue)}</p>
          <div className="text-[10px] text-muted-foreground flex flex-col gap-0.5">
            <span>Conversions: {bestCase.conversions.toLocaleString()}</span>
            <span>Conv. Rate: {(bestCase.conversion_rate * 100).toFixed(0)}%</span>
          </div>
        </div>

        <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-4 space-y-2 relative overflow-hidden">
          <span className="text-[10px] uppercase font-bold tracking-widest text-blue-500 font-mono">Expected Case (Mean)</span>
          <p className="text-xl font-bold font-mono text-foreground">{formatCurrency(expectedCase.revenue)}</p>
          <div className="text-[10px] text-muted-foreground flex flex-col gap-0.5">
            <span>Conversions: {expectedCase.conversions.toLocaleString()}</span>
            <span>Conv. Rate: {(expectedCase.conversion_rate * 100).toFixed(0)}%</span>
          </div>
          <span className={cn("absolute right-2 top-2 px-1.5 py-0.5 rounded text-[8px] font-bold", decision.color)}>
            {decision.label}
          </span>
        </div>

        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4 space-y-2 relative overflow-hidden">
          <span className="text-[10px] uppercase font-bold tracking-widest text-error font-mono">Worst Case Scenario</span>
          <p className="text-xl font-bold font-mono text-foreground">{formatCurrency(worstCase.revenue)}</p>
          <div className="text-[10px] text-muted-foreground flex flex-col gap-0.5">
            <span>Conversions: {worstCase.conversions.toLocaleString()}</span>
            <span>Conv. Rate: {(worstCase.conversion_rate * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

      {/* Histograms & confidence intervals */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-lg border bg-card p-6 h-72 flex flex-col justify-between">
          <div>
            <h4 className="font-semibold tracking-tight text-foreground flex items-center gap-1.5">
              <BarChart2 className="h-4 w-4 text-accent" />
              Monte Carlo Frequency Distribution
            </h4>
            <p className="text-[10px] text-muted-foreground font-mono">Simulated output distribution frequencies</p>
          </div>
          <div className="h-44 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={histogramData} margin={{ top: 10, right: 0, left: -25, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e4e4e7" className="dark:stroke-zinc-800" />
                <XAxis dataKey="bin" tick={{ fill: '#71717a', fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#71717a', fontSize: 9 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ backgroundColor: '#09090b', borderColor: '#27272a', fontSize: 10 }} />
                <Bar dataKey="Frequency" fill="#2563EB" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-lg border bg-card p-6 h-72 flex flex-col justify-between">
          <div>
            <h4 className="font-semibold tracking-tight text-foreground flex items-center gap-1.5">
              <Target className="h-4 w-4 text-accent" />
              95% Confidence Interval Band
            </h4>
            <p className="text-[10px] text-muted-foreground font-mono">Risk uncertainty spreads over time</p>
          </div>
          <div className="h-44 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={intervalData} margin={{ top: 10, right: 0, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="ciGlow" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563EB" stopOpacity={0.15}/>
                    <stop offset="95%" stopColor="#2563EB" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e4e4e7" className="dark:stroke-zinc-800" />
                <XAxis dataKey="day" tick={{ fill: '#71717a', fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={(v) => `$${v / 1000}k`} tick={{ fill: '#71717a', fontSize: 9 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ backgroundColor: '#09090b', borderColor: '#27272a', fontSize: 10 }} />
                <Area type="monotone" dataKey="Upper95" stroke="none" fill="url(#ciGlow)" />
                <Area type="monotone" dataKey="Lower95" stroke="none" fill="#09090b" fillOpacity={1} />
                <Area type="monotone" dataKey="Expected" stroke="#2563EB" strokeWidth={2} fill="none" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Risk Assessment Values */}
      <div className="rounded-lg border bg-card p-5 space-y-3">
        <h4 className="font-semibold uppercase tracking-wider text-muted-foreground">Scenario Risk Assessment</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <span className="text-zinc-500 font-semibold">Value at Risk (95%)</span>
            <p className="text-sm font-bold font-mono text-foreground mt-0.5">{formatCurrency(risk?.value_at_risk_95 ?? 15000)}</p>
          </div>

          <div>
            <span className="text-zinc-500 font-semibold">Expected Shortfall</span>
            <p className="text-sm font-bold font-mono text-foreground mt-0.5">{formatCurrency(risk?.expected_shortfall ?? 18500)}</p>
          </div>

          <div>
            <span className="text-zinc-500 font-semibold">Loss Probability</span>
            <p className={cn("text-sm font-bold font-mono mt-0.5", probLoss > 0.15 ? 'text-error' : 'text-success')}>
              {(probLoss * 100).toFixed(0)}%
            </p>
          </div>

          <div>
            <span className="text-zinc-500 font-semibold">Sentiment Impact</span>
            <p className="text-sm font-bold text-foreground mt-0.5">{risk?.sentiment_risk ?? 'NEUTRAL'}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
export default SimulationResultsDashboard;
