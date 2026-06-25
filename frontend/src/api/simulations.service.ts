import api from './api';
import { Simulation } from '../types';

export const simulationsService = {
  listSimulations: async (params?: { page?: number; page_size?: number; sort_by?: string; sort_order?: string }) => {
    const res = await api.get('/simulations', { params });
    return res.data; // Expected response: { data: Simulation[], total: number }
  },

  createSimulation: async (data: any) => {
    const res = await api.post('/simulations', data);
    return res.data; // Expected: Simulation
  },

  deleteSimulation: async (simulationId: string) => {
    const res = await api.delete(`/simulations/${simulationId}`);
    return res.data;
  },

  getSimulation: async (simulationId: string) => {
    const res = await api.get(`/simulations/${simulationId}`);
    return res.data; // Expected: Simulation
  },

  updateSimulation: async (simulationId: string, data: Partial<Simulation>) => {
    const res = await api.put(`/simulations/${simulationId}`, data);
    return res.data;
  },

  getSimulationForecast: async (simulationId: string) => {
    const res = await api.get(`/simulations/${simulationId}/forecast`);
    return res.data;
  },

  getSimulationProgress: async (simulationId: string) => {
    const res = await api.get(`/simulations/${simulationId}/progress`);
    return res.data; // Expected response: { progress: number, completed_iterations: number, total_iterations: number }
  },

  getSimulationResults: async (simulationId: string) => {
    const res = await api.get(`/simulations/${simulationId}/results`);
    return res.data; // Expected response: SimulationResult
  },

  runSimulation: async (simulationId: string) => {
    const res = await api.post(`/simulations/${simulationId}/run`);
    return res.data;
  },

  getSimulationRuns: async (simulationId: string) => {
    const res = await api.get(`/simulations/${simulationId}/runs`);
    return res.data;
  },

  getSimulationStatus: async (simulationId: string) => {
    const res = await api.get(`/simulations/${simulationId}/status`);
    return res.data; // Expected response: { status: string, error?: string }
  },

  compareCampaignPerformance: async (ids: string) => {
    // ids is a comma-separated list of scenario IDs
    const res = await api.get('/simulations/compare', { params: { ids } });
    return res.data;
  },
};
