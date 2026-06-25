import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children?: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="flex flex-col items-center justify-center p-8 border border-dashed rounded-lg bg-red-500/5 border-red-500/20 text-center min-h-[200px]">
          <AlertTriangle className="h-8 w-8 text-red-500 mb-3 animate-pulse" />
          <h3 className="text-sm font-medium text-red-400 mb-1">Component Failure</h3>
          <p className="text-xs text-muted-foreground max-w-sm">
            {this.state.error?.message || 'An unexpected exception occurred.'}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="mt-4 text-xs font-semibold px-3 py-1.5 border rounded-md hover:bg-surface-dark/40 transition-colors"
          >
            Retry Panel
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
export default ErrorBoundary;
