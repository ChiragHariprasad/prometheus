import React from 'react';
import { 
  Check, 
  X, 
  Loader2, 
  Clock, 
  RefreshCw, 
  AlertTriangle, 
  Activity,
  MoreHorizontal
} from 'lucide-react';
import { cn } from '../../utils';

type TwinStatus = 'building' | 'built' | 'stale' | 'rebuilding' | 'failed';
type SimulationStatus = 'queued' | 'running' | 'completed' | 'failed';
type ConfidenceLevel = 'low' | 'medium' | 'high';

interface StatusBadgeProps {
  type: 'twin' | 'simulation' | 'confidence';
  status: string;
  className?: string;
}

export function StatusBadge({ type, status, className }: StatusBadgeProps) {
  const normStatus = status?.toLowerCase();

  if (type === 'twin') {
    const ts = normStatus as TwinStatus;
    switch (ts) {
      case 'building':
        return (
          <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400", className)}>
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Building
          </span>
        );
      case 'built':
        return (
          <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400", className)}>
            <Check className="h-3.5 w-3.5" />
            Built
          </span>
        );
      case 'stale':
        return (
          <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400", className)}>
            <Clock className="h-3.5 w-3.5" />
            Stale
          </span>
        );
      case 'rebuilding':
        return (
          <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400", className)}>
            <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            Rebuilding
          </span>
        );
      case 'failed':
        return (
          <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400", className)}>
            <AlertTriangle className="h-3.5 w-3.5" />
            Failed
          </span>
        );
      default:
        return (
          <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400", className)}>
            Unknown
          </span>
        );
    }
  }

  if (type === 'simulation') {
    const ss = normStatus as SimulationStatus;
    switch (ss) {
      case 'queued':
        return (
          <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400", className)}>
            <MoreHorizontal className="h-3.5 w-3.5" />
            Queued
          </span>
        );
      case 'running':
        return (
          <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400", className)}>
            <Activity className="h-3.5 w-3.5 animate-pulse" />
            Running
          </span>
        );
      case 'completed':
        return (
          <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400", className)}>
            <Check className="h-3.5 w-3.5" />
            Completed
          </span>
        );
      case 'failed':
        return (
          <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400", className)}>
            <X className="h-3.5 w-3.5" />
            Failed
          </span>
        );
      default:
        return (
          <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400", className)}>
            Draft
          </span>
        );
    }
  }

  if (type === 'confidence') {
    const cl = normStatus as ConfidenceLevel;
    switch (cl) {
      case 'low':
        return (
          <span className={cn("inline-flex items-center gap-1.5 text-xs font-semibold text-error", className)}>
            <span className="flex gap-0.5 items-end h-3 w-3">
              <span className="w-0.5 h-1.5 bg-error rounded-full"></span>
              <span className="w-0.5 h-2.5 bg-zinc-300 dark:bg-zinc-700 rounded-full"></span>
              <span className="w-0.5 h-3.5 bg-zinc-300 dark:bg-zinc-700 rounded-full"></span>
            </span>
            Low
          </span>
        );
      case 'medium':
        return (
          <span className={cn("inline-flex items-center gap-1.5 text-xs font-semibold text-blue-500", className)}>
            <span className="flex gap-0.5 items-end h-3 w-3">
              <span className="w-0.5 h-1.5 bg-blue-500 rounded-full"></span>
              <span className="w-0.5 h-2.5 bg-blue-500 rounded-full"></span>
              <span className="w-0.5 h-3.5 bg-zinc-300 dark:bg-zinc-700 rounded-full"></span>
            </span>
            Medium
          </span>
        );
      case 'high':
        return (
          <span className={cn("inline-flex items-center gap-1.5 text-xs font-semibold text-success", className)}>
            <span className="flex gap-0.5 items-end h-3 w-3">
              <span className="w-0.5 h-1.5 bg-success rounded-full"></span>
              <span className="w-0.5 h-2.5 bg-success rounded-full"></span>
              <span className="w-0.5 h-3.5 bg-success rounded-full"></span>
            </span>
            High
          </span>
        );
      default:
        return (
          <span className={cn("inline-flex items-center gap-1 text-xs font-medium text-muted-foreground", className)}>
            Unknown
          </span>
        );
    }
  }

  return null;
}
export default StatusBadge;
