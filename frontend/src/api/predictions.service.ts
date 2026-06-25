import api from './api';

export const predictionsService = {
  getPredictions: async (customerId: string, params?: { prediction_type?: string; limit?: number }) => {
    const res = await api.get(`/twins/${customerId}/predictions`, { params });
    return res.data; // Expected response: PredictionItem[]
  },

  getLatestPrediction: async (customerId: string, predictionType: string) => {
    const res = await api.get(`/twins/${customerId}/predictions/${predictionType}`);
    return res.data; // Expected response: PredictionItem
  },
};
