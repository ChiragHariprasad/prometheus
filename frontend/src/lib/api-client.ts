import api from "./api";

export interface LoginRequest {
  email: string;
  password: string;
  mfa_code?: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  organization_name: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: {
    id: string;
    email: string;
    name: string;
    roles: string[];
    permissions: string[];
    organization_id: string;
  };
}

export interface Customer {
  id: string;
  email: string;
  name: string;
  phone?: string;
  tags: string[];
  segments: string[];
  engagement_score: number;
  loyalty_score: number;
  churn_risk: "low" | "medium" | "high";
  ltv: number;
  last_activity: string;
  created_at: string;
  updated_at: string;
  preferences?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface CustomerCreate {
  email: string;
  name: string;
  phone?: string;
  tags?: string[];
  preferences?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface CustomerUpdate extends Partial<CustomerCreate> {}

export interface CustomerEvent {
  id: string;
  customer_id: string;
  event_type: string;
  properties: Record<string, unknown>;
  channel: string;
  timestamp: string;
  created_at: string;
}

export interface CustomerSegment {
  id: string;
  name: string;
  description: string;
  criteria: Record<string, unknown>;
  customer_count: number;
  created_at: string;
}

export interface Twin {
  id: string;
  customer_id: string;
  engagement_score: number;
  loyalty_score: number;
  sentiment_score: number;
  churn_probability: number;
  interests: Array<{ name: string; weight: number }>;
  channel_affinity: Record<string, number>;
  sentiment_trend: Array<{ date: string; score: number }>;
  last_rebuilt: string;
  created_at: string;
}

export interface TwinSummary {
  total_twins: number;
  avg_engagement: number;
  avg_loyalty: number;
  avg_sentiment: number;
  churn_risk_distribution: { low: number; medium: number; high: number };
  top_interests: Array<{ name: string; count: number }>;
}

export interface Campaign {
  id: string;
  name: string;
  type: "email" | "sms" | "push" | "in_app";
  goal: string;
  status: "draft" | "active" | "paused" | "completed" | "cancelled";
  segment_ids?: string[];
  segments?: string[];
  content: Record<string, unknown>;
  schedule: Record<string, unknown>;
  ab_test?: {
    enabled: boolean;
    variants: Array<{
      name: string;
      content: Record<string, unknown>;
      traffic_percentage: number;
    }>;
    winning_metric: string;
  };
  ab_test_config?: Record<string, unknown>;
  metrics?: {
    sent: number;
    delivered: number;
    opened: number;
    clicked: number;
    converted: number;
    revenue: number;
    roi: number;
  };
  created_at: string;
  updated_at: string;
}

export interface CampaignCreate {
  name: string;
  type: string;
  channel: string;
  goal: string;
  segments: string[];
  content: Record<string, unknown>;
  schedule: Record<string, unknown>;
  ab_test_config?: Record<string, unknown>;
}

export interface Simulation {
  id: string;
  name: string;
  config: {
    iterations: number;
    time_horizon: number;
    confidence_level: number;
    segment_ids: string[];
    parameters: Record<string, unknown>;
  };
  status: "draft" | "running" | "completed" | "failed";
  results?: {
    expected_revenue: number;
    conversion_rate: number;
    confidence_interval: { lower: number; upper: number };
    scenarios: {
      best_case: Record<string, number>;
      worst_case: Record<string, number>;
      most_likely: Record<string, number>;
    };
    sensitivity: Array<{ variable: string; impact: number }>;
    risk_assessment: { level: string; factors: string[] };
  };
  forecast?: {
    dates: string[];
    predicted: number[];
    upper_bound: number[];
    lower_bound: number[];
  };
  created_at: string;
}

export interface CreateSimulationRequest {
  name: string;
  iterations: number;
  time_horizon: number;
  confidence_level: number;
  segment_ids: string[];
  parameters: Record<string, unknown>;
}

export interface Recommendation {
  id: string;
  customer_id: string;
  type: string;
  title: string;
  description: string;
  score: number;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface RecommendationFeedback {
  recommendation_id: string;
  feedback: "positive" | "negative" | "neutral";
  comment?: string;
}

export interface AnalyticsQuery {
  metric: string;
  dimensions: string[];
  filters: Record<string, unknown>;
  start_date: string;
  end_date: string;
  granularity: "hour" | "day" | "week" | "month";
}

export interface DashboardData {
  stats: {
    total_customers: number;
    events_24h: number;
    active_campaigns: number;
    avg_engagement: number;
    total_revenue: number;
    revenue_growth: number;
    churn_rate: number;
  };
  engagement_trend: Array<{ date: string; value: number }>;
  revenue_data: Array<{ date: string; value: number }>;
  segment_distribution: Array<{ name: string; value: number }>;
  top_segments: Array<{
    name: string;
    customer_count: number;
    avg_engagement: number;
    revenue: number;
  }>;
  recent_activity: Array<{
    id: string;
    type: string;
    description: string;
    timestamp: string;
    user: string;
  }>;
  churn_alerts: Array<{
    customer_id: string;
    customer_name: string;
    churn_probability: number;
    risk_factors: string[];
  }>;
}

export interface Segment {
  id: string;
  name: string;
  description: string;
  criteria: Record<string, unknown>;
  customer_count: number;
  computed: boolean;
  created_at: string;
  updated_at: string;
}

export interface Webhook {
  id: string;
  name: string;
  url: string;
  events: string[];
  active: boolean;
  secret: string;
  created_at: string;
}

export interface ApiKey {
  id: string;
  name: string;
  key: string;
  permissions: string[];
  last_used?: string;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  roles: string[];
  permissions: string[];
  organization_id: string;
  mfa_enabled: boolean;
  created_at: string;
}

export interface AuditLog {
  id: string;
  user_id: string;
  user_name: string;
  action: string;
  resource: string;
  resource_id: string;
  details: Record<string, unknown>;
  ip_address: string;
  timestamp: string;
}

export interface SystemHealth {
  services: Array<{
    name: string;
    status: "healthy" | "degraded" | "down";
    latency: number;
    uptime: number;
  }>;
  recent_errors: number;
  avg_response_time: number;
  requests_per_minute: number;
}

class ApiClient {
  // Auth
  async login(data: LoginRequest): Promise<AuthResponse> {
    const response = await api.post("/auth/login", data);
    return response.data;
  }

  async register(data: RegisterRequest): Promise<AuthResponse> {
    const response = await api.post("/auth/register", data);
    return response.data;
  }

  async refresh(refreshToken: string): Promise<AuthResponse> {
    const response = await api.post("/auth/refresh", {
      refresh_token: refreshToken,
    });
    return response.data;
  }

  async logout(): Promise<void> {
    await api.post("/auth/logout");
  }

  async getProfile(): Promise<AuthResponse["user"]> {
    const response = await api.get("/auth/me");
    return response.data;
  }

  // Customers
  async listCustomers(params?: {
    page?: number;
    limit?: number;
    search?: string;
    sort?: string;
    order?: string;
    tags?: string[];
    segments?: string[];
    engagement_tier?: string;
    churn_risk?: string;
  }): Promise<{ data: Customer[]; total: number; page: number; limit: number }> {
    const response = await api.get("/customers", { params });
    return response.data;
  }

  async getCustomer(id: string): Promise<Customer> {
    const response = await api.get(`/customers/${id}`);
    return response.data;
  }

  async createCustomer(data: CustomerCreate): Promise<Customer> {
    const response = await api.post("/customers", data);
    return response.data;
  }

  async updateCustomer(id: string, data: CustomerUpdate): Promise<Customer> {
    const response = await api.put(`/customers/${id}`, data);
    return response.data;
  }

  async deleteCustomer(id: string): Promise<void> {
    await api.delete(`/customers/${id}`);
  }

  async searchCustomers(query: string): Promise<Customer[]> {
    const response = await api.get("/customers/search", {
      params: { q: query },
    });
    return response.data;
  }

  async getCustomerEvents(
    customerId: string,
    params?: { event_type?: string; channel?: string; page?: number; limit?: number }
  ): Promise<{ data: CustomerEvent[]; total: number }> {
    const response = await api.get(`/customers/${customerId}/events`, {
      params,
    });
    return response.data;
  }

  async getCustomerSegments(customerId: string): Promise<CustomerSegment[]> {
    const response = await api.get(`/customers/${customerId}/segments`);
    return response.data;
  }

  // Twins
  async getTwin(customerId: string): Promise<Twin> {
    const response = await api.get(`/twins/${customerId}`);
    return response.data;
  }

  async getTwinSummary(): Promise<TwinSummary> {
    const response = await api.get("/twins/summary");
    return response.data;
  }

  async rebuildTwin(customerId: string): Promise<Twin> {
    const response = await api.post(`/twins/${customerId}/rebuild`);
    return response.data;
  }

  async getTwinPredictions(customerId: string): Promise<{
    churn: { probability: number; timeframe: string; factors: string[] };
    ltv: { predicted: number; range: [number, number]; confidence: number };
    next_best_action: { action: string; expected_impact: number };
  }> {
    const response = await api.get(`/twins/${customerId}/predictions`);
    return response.data;
  }

  // Campaigns
  async listCampaigns(params?: {
    status?: string;
    type?: string;
    page?: number;
    limit?: number;
  }): Promise<{ data: Campaign[]; total: number; page: number; limit: number }> {
    const response = await api.get("/campaigns", { params });
    return response.data;
  }

  async getCampaign(id: string): Promise<Campaign> {
    const response = await api.get(`/campaigns/${id}`);
    return response.data;
  }

  async createCampaign(data: CampaignCreate): Promise<Campaign> {
    const response = await api.post("/campaigns", data);
    return response.data.data ?? response.data;
  }

  async updateCampaign(
    id: string,
    data: Partial<CampaignCreate>
  ): Promise<Campaign> {
    const response = await api.put(`/campaigns/${id}`, data);
    return response.data;
  }

  async launchCampaign(id: string): Promise<Campaign> {
    const response = await api.post(`/campaigns/${id}/launch`);
    return response.data;
  }

  async pauseCampaign(id: string): Promise<Campaign> {
    const response = await api.post(`/campaigns/${id}/pause`);
    return response.data;
  }

  async cancelCampaign(id: string): Promise<Campaign> {
    const response = await api.post(`/campaigns/${id}/cancel`);
    return response.data;
  }

  async getCampaignResults(id: string): Promise<{
    metrics: Campaign["metrics"];
    timeline: Array<{ date: string; metric: string; value: number }>;
    ab_results?: Array<{
      variant: string;
      metrics: Record<string, number>;
      winner: boolean;
    }>;
  }> {
    const response = await api.get(`/campaigns/${id}/results`);
    return response.data;
  }

  // Simulations
  async listSimulations(params?: {
    page?: number;
    limit?: number;
  }): Promise<{ data: Simulation[]; total: number }> {
    const response = await api.get("/simulations", { params });
    return response.data;
  }

  async getSimulation(id: string): Promise<Simulation> {
    const response = await api.get(`/simulations/${id}`);
    return response.data;
  }

  async createSimulation(data: CreateSimulationRequest): Promise<Simulation> {
    const response = await api.post("/simulations", data);
    return response.data;
  }

  async runSimulation(id: string): Promise<Simulation> {
    const response = await api.post(`/simulations/${id}/run`);
    return response.data;
  }

  async getSimulationResults(id: string): Promise<Simulation["results"]> {
    const response = await api.get(`/simulations/${id}/results`);
    return response.data;
  }

  async getSimulationForecast(id: string): Promise<Simulation["forecast"]> {
    const response = await api.get(`/simulations/${id}/forecast`);
    return response.data;
  }

  // Events
  async ingestEvent(data: {
    customer_id: string;
    event_type: string;
    properties: Record<string, unknown>;
    channel: string;
    timestamp?: string;
  }): Promise<CustomerEvent> {
    const response = await api.post("/events/ingest", data);
    return response.data;
  }

  async ingestBatch(data: {
    events: Array<{
      customer_id: string;
      event_type: string;
      properties: Record<string, unknown>;
      channel: string;
      timestamp?: string;
    }>;
  }): Promise<{ ingested: number }> {
    const response = await api.post("/events/ingest-batch", data);
    return response.data;
  }

  async listEvents(params?: {
    page?: number;
    limit?: number;
    event_type?: string;
    customer_id?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<{ data: CustomerEvent[]; total: number }> {
    const response = await api.get("/events", { params });
    return response.data;
  }

  async getEventSummary(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<{
    total_events: number;
    by_type: Record<string, number>;
    by_channel: Record<string, number>;
    trend: Array<{ date: string; count: number }>;
  }> {
    const response = await api.get("/events/summary", { params });
    return response.data;
  }

  // Recommendations
  async getPersonalizedRecommendations(
    customerId: string,
    params?: { limit?: number; types?: string[] }
  ): Promise<Recommendation[]> {
    const response = await api.get(
      `/recommendations/${customerId}`,
      { params }
    );
    return response.data;
  }

  async sendFeedback(data: RecommendationFeedback): Promise<void> {
    await api.post("/recommendations/feedback", data);
  }

  // Analytics
  async getDashboard(): Promise<DashboardData> {
    const response = await api.get("/analytics/dashboard");
    return response.data;
  }

  async queryAnalytics(query: AnalyticsQuery): Promise<{
    data: Array<Record<string, unknown>>;
    summary: Record<string, unknown>;
  }> {
    const response = await api.post("/analytics/query", query);
    return response.data;
  }

  async getRevenueAnalytics(params?: {
    start_date?: string;
    end_date?: string;
    granularity?: string;
  }): Promise<{
    revenue_trend: Array<{ period: string; revenue: number; transactions: number; unique_customers: number; avg_order_value: number }>;
    total_revenue: number;
    recurring_revenue: number;
    average_order_value: number | null;
    revenue_by_channel: Record<string, unknown>;
    period: string;
    currency: string;
  }> {
    const response = await api.get("/analytics/revenue", { params });
    return response.data;
  }

  async getEngagementAnalytics(params?: {
    start_date?: string;
    end_date?: string;
    granularity?: string;
  }): Promise<{
    trend: Array<{ date: string; events: number; active_users: number; events_per_user: number }>;
    overall_score: number | null;
    by_channel: Record<string, unknown>;
    by_segment: Record<string, unknown>;
    period: string;
  }> {
    const response = await api.get("/analytics/engagement", { params });
    return response.data;
  }

  async getChurnAnalytics(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<{
    churn_rate: number | null;
    churned_customers: number;
    at_risk_customers: number;
    churn_by_segment: Array<{ segment_id: string; segment_name: string; total_customers: number; at_risk: number; churn_rate: number }>;
    churn_reasons: Array<Record<string, unknown>>;
    retention_rate: number | null;
    period: string;
  }> {
    const response = await api.get("/analytics/churn", { params });
    return response.data;
  }

  // Segments
  async listSegments(): Promise<Segment[]> {
    const response = await api.get("/segments");
    return response.data.data ?? response.data;
  }

  async getSegment(id: string): Promise<Segment> {
    const response = await api.get(`/segments/${id}`);
    return response.data;
  }

  async createSegment(data: {
    name: string;
    description: string;
    criteria: Record<string, unknown>;
  }): Promise<Segment> {
    const response = await api.post("/segments", data);
    return response.data;
  }

  async computeSegment(id: string): Promise<Segment> {
    const response = await api.post(`/segments/${id}/compute`);
    return response.data;
  }

  async getSegmentCustomers(
    segmentId: string,
    params?: { page?: number; limit?: number }
  ): Promise<{ data: Customer[]; total: number }> {
    const response = await api.get(`/segments/${segmentId}/customers`, {
      params,
    });
    return response.data;
  }

  // Settings - Users
  async listUsers(): Promise<User[]> {
    const response = await api.get("/admin/users");
    return response.data;
  }

  async updateUser(id: string, data: Partial<User>): Promise<User> {
    const response = await api.put(`/admin/users/${id}`, data);
    return response.data;
  }

  async deleteUser(id: string): Promise<void> {
    await api.delete(`/admin/users/${id}`);
  }

  // Settings - Roles
  async listRoles(): Promise<
    Array<{ id: string; name: string; permissions: string[]; description: string }>
  > {
    const response = await api.get("/admin/roles");
    return response.data;
  }

  // Settings - Integrations
  async listApiKeys(): Promise<ApiKey[]> {
    const response = await api.get("/admin/api-keys");
    return response.data;
  }

  async createApiKey(data: {
    name: string;
    permissions: string[];
  }): Promise<ApiKey> {
    const response = await api.post("/admin/api-keys", data);
    return response.data;
  }

  async deleteApiKey(id: string): Promise<void> {
    await api.delete(`/admin/api-keys/${id}`);
  }

  async listWebhooks(): Promise<Webhook[]> {
    const response = await api.get("/admin/webhooks");
    return response.data;
  }

  async createWebhook(data: {
    name: string;
    url: string;
    events: string[];
  }): Promise<Webhook> {
    const response = await api.post("/admin/webhooks", data);
    return response.data;
  }

  async updateWebhook(
    id: string,
    data: Partial<Webhook>
  ): Promise<Webhook> {
    const response = await api.put(`/admin/webhooks/${id}`, data);
    return response.data;
  }

  async deleteWebhook(id: string): Promise<void> {
    await api.delete(`/admin/webhooks/${id}`);
  }

  // Administration
  async getAuditLogs(params?: {
    page?: number;
    limit?: number;
    action?: string;
    user_id?: string;
    resource?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<{ data: AuditLog[]; total: number }> {
    const response = await api.get("/admin/audit-logs", { params });
    return response.data;
  }

  async getSystemHealth(): Promise<SystemHealth> {
    const response = await api.get("/admin/system-health");
    return response.data;
  }

  async getFeatureFlags(): Promise<
    Array<{ key: string; name: string; enabled: boolean; description: string }>
  > {
    const response = await api.get("/admin/feature-flags");
    return response.data;
  }

  async toggleFeatureFlag(
    key: string,
    enabled: boolean
  ): Promise<void> {
    await api.put(`/admin/feature-flags/${key}`, { enabled });
  }

  async getBackgroundJobs(): Promise<
    Array<{
      id: string;
      name: string;
      status: "running" | "completed" | "failed" | "queued";
      progress: number;
      started_at: string;
      completed_at?: string;
      error?: string;
    }>
  > {
    const response = await api.get("/admin/jobs");
    return response.data;
  }

  async getRateLimits(): Promise<
    Array<{
      endpoint: string;
      limit: number;
      remaining: number;
      reset: string;
    }>
  > {
    const response = await api.get("/admin/rate-limits");
    return response.data;
  }
}

export const apiClient = new ApiClient();
