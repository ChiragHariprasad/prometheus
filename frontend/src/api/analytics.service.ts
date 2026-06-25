import api from './api';

export interface AnalyticsParams {
  granularity?: string;
  start_date?: string;
  end_date?: string;
}

export const analyticsService = {
  getDashboard: async () => {
    const res = await api.get('/analytics/dashboard');
    return res.data;
  },

  getChurnAnalytics: async (params?: AnalyticsParams) => {
    const res = await api.get('/analytics/churn', { params });
    return res.data;
  },

  getEngagementTrends: async (params?: AnalyticsParams) => {
    const res = await api.get('/analytics/engagement', { params });
    return res.data;
  },

  getRevenueAnalytics: async (params?: AnalyticsParams) => {
    const res = await api.get('/analytics/revenue', { params });
    return res.data;
  },

  getSegmentAnalytics: async (segmentId: string) => {
    const res = await api.get(`/analytics/segments/${segmentId}`);
    return res.data;
  },

  exportAnalytics: async (params?: { report_type?: string; format?: string; start_date?: string; end_date?: string }) => {
    const res = await api.get('/analytics/export', { params });
    return res.data;
  },

  runAnalyticsQuery: async (data: Record<string, any>) => {
    const res = await api.post('/analytics/query', data);
    return res.data;
  },
};
