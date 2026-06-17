import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
  QueryKey,
} from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export function useCustomers(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ["customers", params],
    queryFn: () => apiClient.listCustomers(params as Parameters<typeof apiClient.listCustomers>[0]),
  });
}

export function useCustomer(id: string) {
  return useQuery({
    queryKey: ["customer", id],
    queryFn: () => apiClient.getCustomer(id),
    enabled: !!id,
  });
}

export function useCustomerEvents(
  customerId: string,
  params?: Record<string, unknown>
) {
  return useQuery({
    queryKey: ["customer-events", customerId, params],
    queryFn: () =>
      apiClient.getCustomerEvents(
        customerId,
        params as Parameters<typeof apiClient.getCustomerEvents>[1]
      ),
    enabled: !!customerId,
  });
}

export function useTwin(customerId: string) {
  return useQuery({
    queryKey: ["twin", customerId],
    queryFn: () => apiClient.getTwin(customerId),
    enabled: !!customerId,
  });
}

export function useTwinSummary() {
  return useQuery({
    queryKey: ["twin-summary"],
    queryFn: () => apiClient.getTwinSummary(),
  });
}

export function useTwinPredictions(customerId: string) {
  return useQuery({
    queryKey: ["twin-predictions", customerId],
    queryFn: () => apiClient.getTwinPredictions(customerId),
    enabled: !!customerId,
  });
}

export function useRebuildTwin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (customerId: string) => apiClient.rebuildTwin(customerId),
    onSuccess: (_, customerId) => {
      queryClient.invalidateQueries({ queryKey: ["twin", customerId] });
    },
  });
}

export function useCampaigns(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ["campaigns", params],
    queryFn: () => apiClient.listCampaigns(params as Parameters<typeof apiClient.listCampaigns>[0]),
  });
}

export function useCampaign(id: string) {
  return useQuery({
    queryKey: ["campaign", id],
    queryFn: () => apiClient.getCampaign(id),
    enabled: !!id,
  });
}

export function useCreateCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof apiClient.createCampaign>[0]) =>
      apiClient.createCampaign(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
    },
  });
}

export function useLaunchCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.launchCampaign(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["campaign", id] });
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
    },
  });
}

export function useSimulations(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ["simulations", params],
    queryFn: () => apiClient.listSimulations(params as Parameters<typeof apiClient.listSimulations>[0]),
  });
}

export function useSimulation(id: string) {
  return useQuery({
    queryKey: ["simulation", id],
    queryFn: () => apiClient.getSimulation(id),
    enabled: !!id,
    refetchInterval: (query) =>
      query.state.data?.status === "running" ? 2000 : false,
  });
}

export function useCreateSimulation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof apiClient.createSimulation>[0]) =>
      apiClient.createSimulation(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["simulations"] });
    },
  });
}

export function useRunSimulation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.runSimulation(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["simulation", id] });
    },
  });
}

export function useSegments() {
  return useQuery({
    queryKey: ["segments"],
    queryFn: () => apiClient.listSegments(),
  });
}

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: () => apiClient.getDashboard(),
  });
}

export function useRevenueAnalytics(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ["revenue-analytics", params],
    queryFn: () =>
      apiClient.getRevenueAnalytics(
        params as Parameters<typeof apiClient.getRevenueAnalytics>[0]
      ),
  });
}

export function useEngagementAnalytics(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ["engagement-analytics", params],
    queryFn: () =>
      apiClient.getEngagementAnalytics(
        params as Parameters<typeof apiClient.getEngagementAnalytics>[0]
      ),
  });
}

export function useChurnAnalytics(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ["churn-analytics", params],
    queryFn: () =>
      apiClient.getChurnAnalytics(
        params as Parameters<typeof apiClient.getChurnAnalytics>[0]
      ),
  });
}

export function useRecommendations(
  customerId: string,
  params?: Record<string, unknown>
) {
  return useQuery({
    queryKey: ["recommendations", customerId, params],
    queryFn: () =>
      apiClient.getPersonalizedRecommendations(
        customerId,
        params as Parameters<typeof apiClient.getPersonalizedRecommendations>[1]
      ),
    enabled: !!customerId,
  });
}

export function useAuditLogs(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ["audit-logs", params],
    queryFn: () =>
      apiClient.getAuditLogs(params as Parameters<typeof apiClient.getAuditLogs>[0]),
  });
}

export function useSystemHealth() {
  return useQuery({
    queryKey: ["system-health"],
    queryFn: () => apiClient.getSystemHealth(),
    refetchInterval: 30000,
  });
}

export function useFeatureFlags() {
  return useQuery({
    queryKey: ["feature-flags"],
    queryFn: () => apiClient.getFeatureFlags(),
  });
}
