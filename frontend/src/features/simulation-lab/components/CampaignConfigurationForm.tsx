import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../../api/api';
import { cn } from '../../../utils';

interface CampaignConfigurationFormProps {
  onRunSimulation: (params: any) => void;
  loading?: boolean;
}

export function CampaignConfigurationForm({
  onRunSimulation,
  loading = false,
}: CampaignConfigurationFormProps) {
  // Config form state
  const [name, setName] = useState('Loyal Reactivation Promo');
  const [description, setDescription] = useState('Win-back campaign targeting high-value buyers.');
  const [campaignType, setCampaignType] = useState('retention');
  const [channel, setChannel] = useState('email');
  const [discountRate, setDiscountRate] = useState(15);
  const [urgency, setUrgency] = useState('medium');
  const [frequency, setFrequency] = useState(3);
  const [sampleSize, setSampleSize] = useState(1000);
  const [avgOrderValue, setAvgOrderValue] = useState(85);
  const [costPerContact, setCostPerContact] = useState(0.05);
  const [fixedCost, setFixedCost] = useState(500);

  // Fetch segments
  const { data: segmentsData } = useQuery({
    queryKey: ['segments-list-simulation-form'],
    queryFn: async () => {
      try {
        const res = await api.get('/segments');
        return res.data;
      } catch {
        return { data: [
          { id: 'seg-1', name: 'VIP Buyers', customer_count: 240 },
          { id: 'seg-2', name: 'At-Risk Actives', customer_count: 480 },
          { id: 'seg-3', name: 'Inactive Dormants', customer_count: 720 },
        ] };
      }
    }
  });

  const segments = segmentsData?.data || [];
  const [selectedSegmentIds, setSelectedSegmentIds] = useState<string[]>(['seg-2']);

  const handleToggleSegment = (id: string) => {
    setSelectedSegmentIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onRunSimulation({
      name,
      description,
      type: 'campaign',
      segment_ids: selectedSegmentIds,
      sample_size: sampleSize,
      monte_carlo_iterations: 1000,
      confidence_level: 0.95,
      time_horizon_days: 30,
      parameters: {
        avg_order_value: avgOrderValue,
        cost_per_contact: costPerContact,
        fixed_cost: fixedCost,
        customer_count: sampleSize,
      },
      agent_configuration: {
        channel,
        offer_type: 'discount',
        discount_rate: discountRate / 100,
        urgency,
        frequency,
        creative_type: 'personalized',
        scenario: 'expected_case',
      }
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 font-sans text-xs bg-card p-5 border rounded-lg shadow-sm">
      <div className="border-b pb-2">
        <h3 className="text-sm font-semibold tracking-tight text-foreground">Simulation Parameters</h3>
        <p className="text-[10px] text-muted-foreground font-mono">Tune variables to recalculate projections</p>
      </div>

      {/* Campaign Details */}
      <div className="space-y-3">
        <div>
          <label className="block text-zinc-400 font-semibold mb-1 uppercase tracking-wider">Simulation Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full h-8 px-2 rounded border bg-zinc-950 text-white focus:outline-none focus:border-accent"
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-zinc-400 font-semibold mb-1 uppercase tracking-wider">Channel</label>
            <select
              value={channel}
              onChange={(e) => setChannel(e.target.value)}
              className="w-full h-8 px-2 rounded border bg-zinc-950 text-white focus:outline-none"
            >
              <option value="email">Email</option>
              <option value="sms">SMS</option>
              <option value="push">Push Notification</option>
              <option value="whatsapp">WhatsApp</option>
            </select>
          </div>

          <div>
            <label className="block text-zinc-400 font-semibold mb-1 uppercase tracking-wider">Urgency</label>
            <select
              value={urgency}
              onChange={(e) => setUrgency(e.target.value)}
              className="w-full h-8 px-2 rounded border bg-zinc-950 text-white focus:outline-none"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
        </div>
      </div>

      {/* Target Audiences */}
      <div className="space-y-2">
        <label className="block text-zinc-400 font-semibold uppercase tracking-wider">Audience Segment</label>
        <div className="space-y-1.5 max-h-24 overflow-y-auto border p-2.5 rounded bg-zinc-950/40">
          {segments.map((seg: any) => {
            const active = selectedSegmentIds.includes(seg.id);
            return (
              <div 
                key={seg.id}
                onClick={() => handleToggleSegment(seg.id)}
                className={cn(
                  "flex items-center justify-between p-1.5 rounded cursor-pointer transition-colors border",
                  active ? "border-accent/40 bg-accent/5 text-foreground font-semibold" : "border-transparent text-muted-foreground hover:bg-zinc-900"
                )}
              >
                <span>{seg.name}</span>
                <span className="font-mono text-[9px]">{seg.customer_count} count</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Sliders */}
      <div className="space-y-4 pt-2 border-t">
        {/* Discount slider */}
        <div>
          <div className="flex justify-between items-center mb-1">
            <span className="text-zinc-400 font-semibold uppercase tracking-wider">Discount Rate</span>
            <span className="font-bold text-foreground font-mono">{discountRate}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="50"
            value={discountRate}
            onChange={(e) => setDiscountRate(Number(e.target.value))}
            className="w-full h-1 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-accent"
          />
        </div>

        {/* Frequency Touches stepper */}
        <div>
          <div className="flex justify-between items-center mb-1">
            <span className="text-zinc-400 font-semibold uppercase tracking-wider">Touch Frequency</span>
            <span className="font-bold text-foreground font-mono">{frequency} Touches</span>
          </div>
          <input
            type="range"
            min="1"
            max="7"
            value={frequency}
            onChange={(e) => setFrequency(Number(e.target.value))}
            className="w-full h-1 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-accent"
          />
        </div>
      </div>

      {/* Financials & Budget */}
      <div className="space-y-3 pt-2 border-t">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-zinc-400 font-semibold mb-1 uppercase tracking-wider">Avg Order Value</label>
            <input
              type="number"
              value={avgOrderValue}
              onChange={(e) => setAvgOrderValue(Number(e.target.value))}
              className="w-full h-8 px-2 rounded border bg-zinc-950 text-white font-mono focus:outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-zinc-400 font-semibold mb-1 uppercase tracking-wider">Audience Size</label>
            <input
              type="number"
              value={sampleSize}
              onChange={(e) => setSampleSize(Number(e.target.value))}
              className="w-full h-8 px-2 rounded border bg-zinc-950 text-white font-mono focus:outline-none"
              required
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-zinc-400 font-semibold mb-1 uppercase tracking-wider">Cost per Contact</label>
            <input
              type="number"
              step="0.01"
              value={costPerContact}
              onChange={(e) => setCostPerContact(Number(e.target.value))}
              className="w-full h-8 px-2 rounded border bg-zinc-950 text-white font-mono focus:outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-zinc-400 font-semibold mb-1 uppercase tracking-wider">Fixed Campaign Cost</label>
            <input
              type="number"
              value={fixedCost}
              onChange={(e) => setFixedCost(Number(e.target.value))}
              className="w-full h-8 px-2 rounded border bg-zinc-950 text-white font-mono focus:outline-none"
              required
            />
          </div>
        </div>
      </div>

      <button
        type="submit"
        disabled={loading || selectedSegmentIds.length === 0}
        className="w-full h-10 bg-accent hover:bg-blue-700 text-white rounded text-sm font-semibold transition-colors disabled:opacity-50"
      >
        {loading ? 'Executing calculations...' : 'Execute Campaign Simulation'}
      </button>
    </form>
  );
}
export default CampaignConfigurationForm;
