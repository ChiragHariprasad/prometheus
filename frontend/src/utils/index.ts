import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(val?: number | null) {
  if (val == null) return '$0';
  // Round to nearest integer to maintain dense dashboard metrics spacing
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(val);
}

export function formatPercentage(val?: number | null) {
  if (val == null) return '0%';
  return `${Math.round(val)}%`;
}

export function formatRoi(roi?: number | null) {
  if (roi == null) return '0.00x';
  return `${roi.toFixed(2)}x`;
}
