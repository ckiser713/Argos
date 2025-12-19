// src/hooks/useSystemStatus.ts
import { useQuery } from "@tanstack/react-query";
import { getSystemStatus, getModelLanesStatus } from "../lib/cortexApi";
import type { SystemStatus, ModelLaneStatus } from "../lib/cortexApi";

export const systemStatusQueryKey = ["systemStatus"] as const;
export const modelLanesQueryKey = ["modelLanes"] as const;

/**
 * Hook to fetch system status (GPU, CPU, memory, context).
 * 
 * Polls every 5 seconds by default for live dashboard updates.
 */
export function useSystemStatus(options?: { 
  refetchInterval?: number; 
  enabled?: boolean;
}) {
  const { refetchInterval = 5000, enabled = true } = options ?? {};
  
  const query = useQuery({
    queryKey: systemStatusQueryKey,
    queryFn: getSystemStatus,
    refetchInterval,
    enabled,
    staleTime: 2000, // Consider data fresh for 2 seconds
    retry: 2,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Hook to fetch model lanes status (vLLM/llama-server).
 * 
 * Polls every 10 seconds by default.
 */
export function useModelLanesStatus(options?: {
  refetchInterval?: number;
  enabled?: boolean;
}) {
  const { refetchInterval = 10000, enabled = true } = options ?? {};

  const query = useQuery({
    queryKey: modelLanesQueryKey,
    queryFn: getModelLanesStatus,
    refetchInterval,
    enabled,
    staleTime: 5000,
    retry: 2,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Derived helpers for common UI patterns.
 */
export function useVramUsage() {
  const { data } = useSystemStatus();
  
  if (!data?.gpu) {
    return { used: 0, total: 0, percentage: 0 };
  }
  
  const used = data.gpu.used_vram_gb ?? 0;
  const total = data.gpu.total_vram_gb ?? 1;
  const percentage = total > 0 ? (used / total) * 100 : 0;
  
  return { used, total, percentage };
}

export function useMemoryUsage() {
  const { data } = useSystemStatus();
  
  if (!data?.memory) {
    return { used: 0, total: 0, percentage: 0 };
  }
  
  const used = data.memory.used_gb;
  const total = data.memory.total_gb;
  const percentage = total > 0 ? (used / total) * 100 : 0;
  
  return { used, total, percentage };
}

export function useContextUsage() {
  const { data } = useSystemStatus();
  
  if (!data?.context) {
    return { used: 0, total: 0, percentage: 0 };
  }
  
  const used = data.context.used_tokens;
  const total = data.context.total_tokens;
  const percentage = total > 0 ? (used / total) * 100 : 0;
  
  return { used, total, percentage };
}

export type { SystemStatus, ModelLaneStatus };
