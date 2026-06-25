import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { customersService } from '../api/customers.service';
import { twinsService } from '../api/twins.service';
import { analyticsService } from '../api/analytics.service';
import { simulationsService } from '../api/simulations.service';
import { predictionsService } from '../api/predictions.service';
import { Twin } from '../types';

// Normalized Percentage Utility
export function toPercent(score?: number | null) {
  if (score == null) return 0;
  return score <= 1 ? Math.round(score * 100) : Math.round(score);
}

// Sentiment Trend Normalizer (Normalizes [number] or [{date, score}] to scale of -100 to 100 or -1 to 1)
export function normalizeSentimentTrend(trend?: any[] | null) {
  if (!trend) return [];
  return trend.map((item, index) => {
    if (typeof item === 'number') {
      return { date: `Day ${index + 1}`, score: toPercent(item) };
    }
    if (item && typeof item === 'object') {
      const score = typeof item.score === 'number' ? toPercent(item.score) : 0;
      return { date: item.date || `Day ${index + 1}`, score };
    }
    return { date: `Day ${index + 1}`, score: 0 };
  });
}

// Customers Hooks
export function useCustomers(page = 1, pageSize = 20, search = '') {
  return useQuery({
    queryKey: ['customers', page, pageSize, search],
    queryFn: () => customersService.listCustomers({ page, page_size: pageSize, search }),
    staleTime: 60000,
  });
}

export function useCustomerDetails(customerId: string | undefined) {
  return useQuery({
    queryKey: ['customer', customerId],
    queryFn: () => (customerId ? customersService.getCustomer(customerId) : Promise.reject('No ID')),
    enabled: !!customerId,
    staleTime: 30000,
  });
}

export function useCustomerEvents(customerId: string | undefined, page = 1, pageSize = 50) {
  return useQuery({
    queryKey: ['customer-events', customerId, page, pageSize],
    queryFn: () => (customerId ? customersService.getCustomerEvents(customerId, { page, page_size: pageSize }) : Promise.reject('No ID')),
    enabled: !!customerId,
    staleTime: 30000,
  });
}

// Twins Hooks
export function useTwinSummary() {
  return useQuery({
    queryKey: ['twins-summary'],
    queryFn: async () => {
      try {
        return await twinsService.getTwinSummary();
      } catch (err: any) {
        // Fallback zero-state if summary returns 404
        if (err.response?.status === 404) {
          return { total_twins: 0, average_engagement: 0, average_loyalty: 0 };
        }
        throw err;
      }
    },
    staleTime: 60000,
  });
}

export function useCustomerTwin(customerId: string | undefined) {
  return useQuery({
    queryKey: ['twin', customerId],
    queryFn: async () => {
      if (!customerId) return null;
      const data = await twinsService.getCustomerTwin(customerId);
      // Backend Freeze normalizations
      return {
        ...data,
        engagement_score: toPercent(data.engagement_score),
        loyalty_score: toPercent(data.loyalty_score),
        confidence_score: toPercent(data.confidence_score),
        staleness_score: toPercent(data.staleness_score),
        sentiment_score: data.sentiment_score !== undefined ? toPercent(data.sentiment_score) : undefined,
        lastBuiltAt: data.built_at || data.last_rebuilt,
        sentiment_trend: normalizeSentimentTrend(data.sentiment_trend as any[]),
      } as Twin & { lastBuiltAt?: string };
    },
    enabled: !!customerId,
    staleTime: 30000,
  });
}

export function useRebuildTwin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (customerId: string) => twinsService.rebuildTwin(customerId),
    onSuccess: (_, customerId) => {
      queryClient.invalidateQueries({ queryKey: ['twin', customerId] });
      queryClient.invalidateQueries({ queryKey: ['twins-summary'] });
      queryClient.invalidateQueries({ queryKey: ['customer', customerId] });
      queryClient.invalidateQueries({ queryKey: ['predictions', customerId] });
    },
  });
}

// Analytics Hooks
export function useDashboardData() {
  return useQuery({
    queryKey: ['dashboard-data'],
    queryFn: () => analyticsService.getDashboard(),
    staleTime: 30000,
    refetchInterval: 60000,
  });
}

// Simulations Hooks
export function useSimulations(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ['simulations', page, pageSize],
    queryFn: () => simulationsService.listSimulations({ page, page_size: pageSize, sort_by: 'created_at', sort_order: 'desc' }),
    staleTime: 15000,
  });
}

export function useSimulationDetails(simulationId: string | undefined) {
  return useQuery({
    queryKey: ['simulation', simulationId],
    queryFn: () => (simulationId ? simulationsService.getSimulation(simulationId) : Promise.reject('No ID')),
    enabled: !!simulationId,
    staleTime: 10000,
  });
}

export function useSimulationResults(simulationId: string | undefined) {
  return useQuery({
    queryKey: ['simulation-results', simulationId],
    queryFn: () => (simulationId ? simulationsService.getSimulationResults(simulationId) : Promise.reject('No ID')),
    enabled: !!simulationId,
    staleTime: 10000,
  });
}

export function useSimulationProgress(simulationId: string | undefined, enabled = false) {
  return useQuery({
    queryKey: ['simulation-progress', simulationId],
    queryFn: () => (simulationId ? simulationsService.getSimulationProgress(simulationId) : Promise.reject('No ID')),
    enabled: enabled && !!simulationId,
    refetchInterval: (query) => {
      const data = query.state.data as any;
      if (data && data.progress >= 100) return false;
      return 2000;
    },
  });
}

export function useCreateSimulation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => simulationsService.createSimulation(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['simulations'] });
    },
  });
}

export function useRunSimulation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (simulationId: string) => simulationsService.runSimulation(simulationId),
    onSuccess: (_, simulationId) => {
      queryClient.invalidateQueries({ queryKey: ['simulation', simulationId] });
      queryClient.invalidateQueries({ queryKey: ['simulations'] });
    },
  });
}

// Predictions Hooks
export function usePredictions(customerId: string | undefined, predictionType?: string) {
  return useQuery({
    queryKey: ['predictions', customerId, predictionType],
    queryFn: () => (customerId ? predictionsService.getPredictions(customerId, { prediction_type: predictionType }) : Promise.reject('No ID')),
    enabled: !!customerId,
    staleTime: 30000,
  });
}
