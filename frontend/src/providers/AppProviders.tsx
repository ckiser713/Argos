/**
 * App-level providers for error handling, toasts, and React Query.
 */

import React, { PropsWithChildren } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { ToastContainer } from "../components/ToastContainer";
import { useToast } from "../hooks/useToast";
import { logError, getErrorMessage } from "../lib/errorHandling";

// Create QueryClient with error handling
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors
        if (error?.status >= 400 && error?.status < 500) {
          return false;
        }
        // Retry up to 3 times for network/server errors
        return failureCount < 3;
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      onError: (error) => {
        logError(error, { context: "react-query" });
      },
    },
    mutations: {
      onError: (error) => {
        logError(error, { context: "react-query-mutation" });
      },
    },
  },
});

function ToastProvider({ children }: PropsWithChildren) {
  const toast = useToast();

  // Make toast available globally via context if needed
  React.useEffect(() => {
    (window as any).__cortexToast = toast;
  }, [toast]);

  return (
    <>
      {children}
      <ToastContainer toasts={toast.toasts} onDismiss={toast.dismissToast} />
    </>
  );
}

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        logError(error, {
          componentStack: errorInfo.componentStack,
          context: "error-boundary",
        });
      }}
    >
      <QueryClientProvider client={queryClient}>
        <ToastProvider>{children}</ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

