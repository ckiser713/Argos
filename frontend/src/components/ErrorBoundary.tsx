/**
 * React Error Boundary component for catching and displaying errors.
 */

import React, { Component, ErrorInfo, ReactNode } from "react";
import { GlassCard } from "./GlassCard";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { logError } from "../lib/errorHandling";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    logError(error, {
      componentStack: errorInfo.componentStack,
    });
    
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center p-4">
          <GlassCard className="max-w-md w-full p-6">
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-red-500/20 rounded-lg">
                <AlertTriangle className="text-red-500" size={24} />
              </div>
              <div>
                <h2 className="text-xl font-mono text-white font-bold">
                  SYSTEM_ERROR
                </h2>
                <p className="text-gray-400 text-sm font-mono">
                  COMPONENT_FAILURE_DETECTED
                </p>
              </div>
            </div>

            <div className="mb-6">
              <p className="text-gray-300 mb-2 font-mono text-sm">
                {this.state.error?.message || "An unexpected error occurred"}
              </p>
              {process.env.NODE_ENV === "development" && this.state.error && (
                <details className="mt-4">
                  <summary className="text-gray-400 text-xs font-mono cursor-pointer mb-2">
                    Stack Trace
                  </summary>
                  <pre className="text-xs text-gray-500 font-mono overflow-auto max-h-40 bg-black/40 p-2 rounded">
                    {this.state.error.stack}
                  </pre>
                </details>
              )}
            </div>

            <div className="flex gap-3">
              <button
                onClick={this.handleReset}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-cyan/20 text-cyan rounded hover:bg-cyan/30 transition-colors font-mono"
              >
                <RefreshCw size={16} />
                Reset Component
              </button>
              <button
                onClick={() => window.location.reload()}
                className="flex-1 px-4 py-2 bg-white/10 text-white rounded hover:bg-white/20 transition-colors font-mono"
              >
                Reload Page
              </button>
            </div>
          </GlassCard>
        </div>
      );
    }

    return this.props.children;
  }
}

