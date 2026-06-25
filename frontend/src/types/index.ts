// TWINCX TypeScript Interfaces

export interface Customer {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  name?: string;
  organization_id: string;
  created_at: string;
  updated_at?: string;
  ltv: number;
  lifecycle_stage?: string;
  rfm_segment?: string;
  last_activity_at?: string;
  location?: string;
  locale?: string;
  timezone?: string;
  source?: string;
}

export interface CustomerEvent {
  id: string;
  customer_id: string;
  event_type: string;
  channel?: string;
  source?: string;
  value?: number;
  currency?: string;
  campaign_id?: string;
  event_properties?: Record<string, any>;
  event_timestamp?: string;
  ingested_at?: string;
}

export interface InterestNode {
  id: string;
  label: string;
  affinity: number;
  interactionCount: number;
  lastInteractionAt?: string;
  relatedInterests?: string[];
}

export interface MemoryItem {
  id: string;
  type: string;
  channel?: string;
  campaignId?: string;
  value?: number;
  timestamp: string;
  properties?: Record<string, any>;
}

export interface Twin {
  customer_id: string;
  status: 'building' | 'built' | 'stale' | 'rebuilding' | 'failed';
  engagement_score: number;
  loyalty_score: number;
  confidence_score: number;
  staleness_score: number;
  sentiment_score?: number;
  churn_probability?: number;
  interests?: string[];
  interest_graph?: {
    nodes?: Array<{ id: string; label: string; weight: number }>;
    edges?: Array<{ source: string; target: string; weight: number }>;
  };
  channel_affinity?: Record<string, number>;
  sentiment_trend?: Array<{ date: string; score: number } | number>;
  last_rebuilt?: string;
  built_at?: string;
  lifetime_value?: number;
  version?: number;
}

export interface Campaign {
  id: string;
  name: string;
  description?: string;
  status: 'draft' | 'active' | 'paused' | 'completed' | 'cancelled';
  type: string;
  channel: string;
  discount_rate?: number;
  budget?: number;
  roi?: number;
  conversions?: number;
  conversion_rate?: number;
  created_at: string;
  launched_at?: string;
  paused_at?: string;
  completed_at?: string;
}

export interface SimulationScenario {
  revenue: number;
  conversions: number;
  open_rate: number;
  click_rate: number;
  conversion_rate: number;
  label?: string;
}

export interface SimulationResult {
  expected_revenue: number;
  expected_roi: number;
  expected_churns: number;
  churn_rate?: number;
  ltv_impact: number;
  expected_conversions?: number;
  expected_open_rate?: number;
  expected_click_rate?: number;
  expected_conversion_rate?: number;
  expected_cost?: number;
  expected_profit?: number;
  probability_of_loss?: number;
  value_at_risk_95?: number;
  expected_shortfall?: number;
  upside_potential?: number;
  sentiment_shift?: number;
  sentiment_risk?: string;
  churn_risk_level?: string;
  revenue_95?: [number, number];
  revenue_90?: [number, number];
  roi_interval?: [number, number];
  conversion_interval?: [number, number];
  scenarios?: {
    best_case?: SimulationScenario;
    expected_case?: SimulationScenario;
    worst_case?: SimulationScenario;
  };
  segment_projections?: Record<string, {
    count: number;
    response_rate: number;
    conversion_rate: number;
    revenue: number;
    avg_revenue_per_customer?: number;
    share_of_revenue?: number;
  }>;
  recommendations?: string[];
  sensitivity?: Array<{ parameter: string; impact: number; direction: 'positive' | 'negative' }>;
  next_best_action?: {
    recommended_channel: string;
    recommended_discount: number;
    recommended_frequency: number;
    actions: Array<{ action: string; rationale: string; expected_impact: string }>;
  };
}

export interface Simulation {
  id: string;
  name: string;
  description?: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  sample_size: number;
  time_horizon_days: number;
  monte_carlo_iterations: number;
  confidence_level: number;
  created_at: string;
  parameters?: {
    avg_order_value?: number;
    cost_per_contact?: number;
    fixed_cost?: number;
    customer_count?: number;
  };
  agent_configuration?: {
    channel: string;
    offer_type: string;
    discount_rate: number;
    urgency: string;
    frequency: number;
    creative_type: string;
    scenario: string;
    competitor_pressure?: number;
  };
  results?: SimulationResult;
}

export interface DashboardStats {
  total_customers: number;
  events_24h: number;
  active_campaigns: number;
  avg_engagement: number;
  total_revenue: number;
  revenue_growth: number;
  churn_rate: number;
}

export interface DashboardResponse {
  stats: DashboardStats;
  engagement_trend?: Array<Record<string, any>>;
  revenue_data?: Array<Record<string, any>>;
  segment_distribution?: Array<Record<string, any>>;
  top_segments?: Array<Record<string, any>>;
  recent_activity?: Array<Record<string, any>>;
  churn_alerts?: Array<{ customer_id: string; name: string; churn_probability: number }>;
}
