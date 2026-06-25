import React, { useState } from 'react';
import { CustomerEvent } from '../../../types';
import { formatCurrency } from '../../../utils';
import { 
  ShoppingBag, 
  Mail, 
  Megaphone, 
  HelpCircle, 
  Activity, 
  Search,
  SlidersHorizontal 
} from 'lucide-react';
import { cn } from '../../../utils';

interface MemoryTimelineProps {
  events?: CustomerEvent[];
  loading?: boolean;
}

export function MemoryTimeline({ events = [], loading = false }: MemoryTimelineProps) {
  const [filter, setFilter] = useState<'all' | 'purchase' | 'campaign' | 'support' | 'engagement'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse p-4">
        <div className="h-8 bg-muted rounded w-1/3"></div>
        <div className="space-y-2">
          <div className="h-12 bg-muted rounded"></div>
          <div className="h-12 bg-muted rounded"></div>
          <div className="h-12 bg-muted rounded"></div>
        </div>
      </div>
    );
  }

  // Pre-seed demo events if empty
  const timelineData = events.length > 0 ? events : [
    {
      id: 'ev-1',
      customer_id: 'cust-1',
      event_type: 'purchase',
      channel: 'email',
      value: 125,
      event_timestamp: new Date(Date.now() - 3600000).toISOString(),
      event_properties: { category: 'Designer Shoes', item: 'Nike Free Run' }
    },
    {
      id: 'ev-2',
      customer_id: 'cust-1',
      event_type: 'campaign_response',
      channel: 'SMS',
      campaign_id: 'camp-12',
      event_timestamp: new Date(Date.now() - 86400000).toISOString(),
      event_properties: { campaign_name: 'Summer Reactivation' }
    },
    {
      id: 'ev-3',
      customer_id: 'cust-1',
      event_type: 'support_ticket',
      channel: 'web',
      event_timestamp: new Date(Date.now() - 172800000).toISOString(),
      event_properties: { subject: 'Delivery delay issue', sentiment: 'negative' }
    },
    {
      id: 'ev-4',
      customer_id: 'cust-1',
      event_type: 'page_view',
      channel: 'web',
      event_timestamp: new Date(Date.now() - 259200000).toISOString(),
      event_properties: { path: '/checkout/payment', duration_seconds: 45 }
    }
  ];

  // Filter and search logic
  const filteredEvents = timelineData.filter((ev) => {
    // 1. Filter type mapping
    if (filter === 'purchase' && ev.event_type !== 'purchase') return false;
    if (filter === 'campaign' && !ev.event_type.includes('campaign') && !ev.campaign_id) return false;
    if (filter === 'support' && !ev.event_type.includes('support') && !ev.event_type.includes('complaint')) return false;
    if (filter === 'engagement' && (ev.event_type === 'purchase' || ev.event_type.includes('support'))) return false;

    // 2. Search query mapping
    if (searchQuery) {
      const matchText = `${ev.event_type} ${ev.channel || ''} ${JSON.stringify(ev.event_properties || {})}`.toLowerCase();
      if (!matchText.includes(searchQuery.toLowerCase())) return false;
    }
    return true;
  });

  const getEventIcon = (type: string) => {
    if (type.includes('purchase')) return <ShoppingBag className="h-4 w-4 text-success" />;
    if (type.includes('campaign')) return <Megaphone className="h-4 w-4 text-blue-500" />;
    if (type.includes('support') || type.includes('complaint')) return <HelpCircle className="h-4 w-4 text-error" />;
    return <Activity className="h-4 w-4 text-zinc-400" />;
  };

  const getEventColor = (type: string) => {
    if (type.includes('purchase')) return 'border-success/30 bg-success/5';
    if (type.includes('campaign')) return 'border-blue-500/20 bg-blue-500/5';
    if (type.includes('support') || type.includes('complaint')) return 'border-error/20 bg-error/5';
    return 'border-zinc-200 dark:border-zinc-800 bg-zinc-50/40 dark:bg-zinc-900/10';
  };

  return (
    <div className="space-y-4 font-sans text-xs">
      {/* Search & Filter Toolbar */}
      <div className="flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:max-w-[200px]">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search memory..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-8 pl-8 pr-3 rounded border border-zinc-200 dark:border-zinc-800 bg-card text-xs focus:outline-none"
          />
        </div>

        <div className="flex flex-wrap items-center gap-1">
          {(['all', 'purchase', 'campaign', 'support', 'engagement'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                "px-2.5 py-1 rounded-md text-[10px] font-semibold border transition-all uppercase tracking-wider",
                filter === f
                  ? "bg-foreground text-background border-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-zinc-50 dark:hover:bg-zinc-900/30"
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Chronological Vertical Feed */}
      <div className="relative border-l pl-4 border-zinc-200 dark:border-zinc-800 space-y-4 max-h-[380px] overflow-y-auto pr-1">
        {filteredEvents.length === 0 ? (
          <p className="text-center text-muted-foreground py-6">No matching remembered events.</p>
        ) : (
          filteredEvents.map((ev) => (
            <div key={ev.id} className="relative group">
              {/* Left timeline dot indicator */}
              <span className="absolute -left-[23px] top-1.5 h-3 w-3 rounded-full border border-card bg-zinc-900 flex items-center justify-center">
                <span className="h-1.5 w-1.5 rounded-full bg-zinc-500"></span>
              </span>

              {/* Event Card */}
              <div className={cn("p-3.5 border rounded-lg shadow-sm space-y-1.5", getEventColor(ev.event_type))}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {getEventIcon(ev.event_type)}
                    <span className="font-bold capitalize text-foreground">{ev.event_type.replace('_', ' ')}</span>
                  </div>
                  <span className="text-[10px] text-muted-foreground font-mono">
                    {ev.event_timestamp ? new Date(ev.event_timestamp).toLocaleDateString() : 'Recent'}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-3 text-[10px] text-muted-foreground pt-1">
                  {ev.channel && (
                    <span>
                      Channel: <strong className="text-foreground uppercase font-mono">{ev.channel}</strong>
                    </span>
                  )}
                  {ev.value !== undefined && ev.value > 0 && (
                    <span>
                      Value: <strong className="text-foreground font-mono">{formatCurrency(ev.value)}</strong>
                    </span>
                  )}
                  {ev.campaign_id && (
                    <span className="bg-blue-500/10 text-blue-500 px-1.5 py-0.5 rounded font-mono font-semibold">
                      {ev.campaign_id}
                    </span>
                  )}
                </div>

                {ev.event_properties && Object.keys(ev.event_properties).length > 0 && (
                  <div className="mt-1.5 border-t border-zinc-200/40 dark:border-zinc-800/40 pt-1.5 text-[9px] font-mono text-muted-foreground flex flex-col gap-0.5">
                    {Object.entries(ev.event_properties).map(([k, v]) => (
                      <div key={k} className="truncate">
                        <span className="text-zinc-500 capitalize">{k}:</span> {String(v)}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
export default MemoryTimeline;
