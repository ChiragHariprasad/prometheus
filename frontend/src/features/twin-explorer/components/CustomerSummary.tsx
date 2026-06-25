import React from 'react';
import { Customer, Twin, CustomerEvent } from '../../../types';
import { formatCurrency } from '../../../utils';
import { 
  User, 
  Mail, 
  Calendar, 
  MapPin, 
  TrendingUp,
  Clock,
  Layers,
  ChevronDown
} from 'lucide-react';
import { cn } from '../../../utils';

interface CustomerSummaryProps {
  customer?: Customer;
  twin?: Twin & { lastBuiltAt?: string };
  events?: CustomerEvent[];
  loading?: boolean;
}

export function CustomerSummary({
  customer,
  twin,
  events = [],
  loading = false,
}: CustomerSummaryProps) {
  if (loading) {
    return (
      <div className="space-y-6 animate-pulse font-sans">
        <div className="h-28 bg-muted rounded"></div>
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded w-1/3"></div>
          <div className="h-20 bg-muted rounded"></div>
        </div>
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded w-1/3"></div>
          <div className="h-28 bg-muted rounded"></div>
        </div>
      </div>
    );
  }

  if (!customer) {
    return (
      <div className="p-6 border border-dashed rounded-lg text-center text-xs text-muted-foreground font-sans">
        Select a customer to view model summary
      </div>
    );
  }

  // Score Stack values (default back-up if absent)
  const eng = twin?.engagement_score ?? 0;
  const loy = twin?.loyalty_score ?? 0;
  const conf = twin?.confidence_score ?? 0;
  const stale = twin?.staleness_score ?? 0; // High stale is worse

  const getMeterColor = (val: number, invert = false) => {
    const checkVal = invert ? 100 - val : val;
    if (checkVal >= 85) return 'bg-success';
    if (checkVal >= 55) return 'bg-warning';
    return 'bg-error';
  };

  const getStaleLabel = (val: number) => {
    if (val >= 75) return 'CRITICAL';
    if (val >= 45) return 'STALE';
    return 'CURRENT';
  };

  // Extract channel affinities
  const affinity = twin?.channel_affinity || { Email: 0.65, SMS: 0.20, Push: 0.15 };

  return (
    <div className="space-y-6 font-sans text-xs">
      {/* Customer Identity Card */}
      <div className="rounded-lg border bg-card p-5 space-y-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-full bg-accent/15 text-accent flex items-center justify-center text-sm font-semibold">
            {customer.first_name?.charAt(0) || customer.email.charAt(0).toUpperCase()}
          </div>
          <div className="truncate">
            <h4 className="text-sm font-bold text-foreground truncate">
              {customer.first_name ? `${customer.first_name} ${customer.last_name}` : customer.email}
            </h4>
            <p className="text-[10px] text-muted-foreground font-mono truncate">{customer.id}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-2 pt-2 border-t font-sans">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Mail className="h-3.5 w-3.5" />
            <span className="truncate text-foreground font-semibold">{customer.email}</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Calendar className="h-3.5 w-3.5" />
            <span>Member since:</span>
            <span className="text-foreground font-mono">{new Date(customer.created_at).toLocaleDateString()}</span>
          </div>
          {customer.location && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <MapPin className="h-3.5 w-3.5" />
              <span>Location:</span>
              <span className="text-foreground">{customer.location}</span>
            </div>
          )}
        </div>
      </div>

      {/* Twin Score Stack */}
      <div className="rounded-lg border bg-card p-5 space-y-4">
        <h4 className="font-semibold uppercase tracking-wider text-muted-foreground">Twin Score Stack</h4>
        
        <div className="space-y-3">
          {/* Engagement */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-zinc-400 font-semibold">Engagement Index</span>
              <span className="font-bold font-mono text-foreground">{eng}%</span>
            </div>
            <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-1.5 rounded-full overflow-hidden">
              <div className={cn("h-full", getMeterColor(eng))} style={{ width: `${eng}%` }}></div>
            </div>
          </div>

          {/* Loyalty */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-zinc-400 font-semibold">Loyalty Index</span>
              <span className="font-bold font-mono text-foreground">{loy}%</span>
            </div>
            <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-1.5 rounded-full overflow-hidden">
              <div className={cn("h-full", getMeterColor(loy))} style={{ width: `${loy}%` }}></div>
            </div>
          </div>

          {/* Model Confidence */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-zinc-400 font-semibold">Model Confidence</span>
              <span className="font-bold font-mono text-foreground">{conf}%</span>
            </div>
            <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-1.5 rounded-full overflow-hidden">
              <div className={cn("h-full", getMeterColor(conf))} style={{ width: `${conf}%` }}></div>
            </div>
          </div>

          {/* Model Staleness */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-zinc-400 font-semibold">Model Staleness</span>
              <span className={cn("font-bold font-mono", stale > 50 ? 'text-error' : 'text-success')}>
                {stale}% ({getStaleLabel(stale)})
              </span>
            </div>
            <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-1.5 rounded-full overflow-hidden">
              <div className={cn("h-full", getMeterColor(stale, true))} style={{ width: `${stale}%` }}></div>
            </div>
          </div>
        </div>
      </div>

      {/* Segment Memberships & Channel Affinity */}
      <div className="rounded-lg border bg-card p-5 space-y-4">
        <h4 className="font-semibold uppercase tracking-wider text-muted-foreground">Behavioral Channels</h4>
        
        <div className="space-y-3">
          {Object.entries(affinity).map(([ch, val]) => {
            const rawVal = typeof val === 'number' ? val : 0;
            const pct = rawVal <= 1 ? Math.round(rawVal * 100) : Math.round(rawVal);
            return (
              <div key={ch} className="space-y-1">
                <div className="flex justify-between text-[11px]">
                  <span className="text-zinc-400 capitalize">{ch} Response Rate</span>
                  <span className="font-bold font-mono text-foreground">{pct}%</span>
                </div>
                <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-1 rounded-full overflow-hidden">
                  <div className="h-full bg-accent" style={{ width: `${pct}%` }}></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
export default CustomerSummary;
