import api from './api';
import { Twin } from '../types';

export const twinsService = {
  getTwinSummary: async () => {
    const res = await api.get('/twins/summary');
    return res.data; // Expected response: { total_twins: number, average_engagement: number, average_loyalty: number }
  },

  getCustomerTwin: async (customerId: string): Promise<Twin> => {
    const res = await api.get(`/twins/${customerId}`);
    return res.data; // Expected response: Twin (might require dictionary mapping)
  },

  getTwinHistory: async (customerId: string, params?: { limit?: number }) => {
    const res = await api.get(`/twins/${customerId}/history`, { params });
    return res.data; // Expected response: Twin[]
  },

  rebuildTwin: async (customerId: string) => {
    const res = await api.post(`/twins/${customerId}/rebuild`);
    return res.data;
  },
};
