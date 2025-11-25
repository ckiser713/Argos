/**
 * Error display component for showing API and other errors.
 */

import React from "react";
import { AlertTriangle, X, RefreshCw } from "lucide-react";
import { getErrorMessage, isRetryableError, categorizeError } from "../lib/errorHandling";
import { GlassCard } from "./GlassCard";

interface ErrorDisplayProps {
  error: unknown;
  onRetry?: () => void;
  onDismiss?: () => void;
  title?: string;
  className?: string;
}

export function ErrorDisplay({
  error,
  onRetry,
  onDismiss,
  title,
  className = "",
}: ErrorDisplayProps) {
  const message = getErrorMessage(error);
  const errorType = categorizeError(error);
  const retryable = isRetryableError(error);

  const getErrorColor = () => {
    switch (errorType) {
      case "network":
      case "server":
        return "text-red-500";
      case "authentication":
      case "authorization":
        return "text-yellow-500";
      case "validation":
        return "text-orange-500";
      default:
        return "text-red-500";
    }
  };

  const getErrorBg = () => {
    switch (errorType) {
      case "network":
      case "server":
        return "bg-red-500/20 border-red-500/50";
      case "authentication":
      case "authorization":
        return "bg-yellow-500/20 border-yellow-500/50";
      case "validation":
        return "bg-orange-500/20 border-orange-500/50";
      default:
        return "bg-red-500/20 border-red-500/50";
    }
  };

  return (
    <GlassCard className={`p-4 ${getErrorBg()} border ${className}`}>
      <div className="flex items-start gap-3">
        <div className={`flex-shrink-0 ${getErrorColor()}`}>
          <AlertTriangle size={20} />
        </div>
        
        <div className="flex-1 min-w-0">
          {title && (
            <h3 className="text-sm font-mono font-bold text-white mb-1">
              {title}
            </h3>
          )}
          <p className="text-sm text-gray-300 font-mono">{message}</p>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {retryable && onRetry && (
            <button
              onClick={onRetry}
              className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white transition-colors"
              title="Retry"
            >
              <RefreshCw size={16} />
            </button>
          )}
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white transition-colors"
              title="Dismiss"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>
    </GlassCard>
  );
}

