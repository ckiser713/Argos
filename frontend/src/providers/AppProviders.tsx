/**
 * App-level providers for error handling, toasts, and React Query.
 */

import React, { PropsWithChildren } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { ToastContainer } from "../components/ToastContainer";
import { useToast } from "../hooks/useToast";
import { logError, getErrorMessage } from "../lib/errorHandling";
import { getApiBaseUrl } from "../lib/http";

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
    (window as any).__argosToast = toast;
  }, [toast]);

  return (
    <>
      {children}
      <ToastContainer toasts={toast.toasts} onDismiss={toast.dismissToast} />
    </>
  );
}

export function AppProviders({ children }: PropsWithChildren) {
  const [isCheckingBackend, setIsCheckingBackend] = React.useState(true);
  const [backendReady, setBackendReady] = React.useState(false);

  // Poll backend readiness before attempting auth
  React.useEffect(() => {
    const checkBackendReadiness = async () => {
      if (typeof window === "undefined") return;

      const apiBaseUrl =
        import.meta.env.VITE_CORTEX_API_BASE_URL ||
        import.meta.env.VITE_API_BASE_URL ||
        getApiBaseUrl();

      const maxAttempts = 15; // 30 seconds total (15 * 2s)
      let attempts = 0;

      // #region agent log
      fetch('http://localhost:7243/ingest/22b2bc10-668b-4e25-b7af-89ca2a3e5432',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AppProviders.tsx:59',message:'Startup check began',data:{apiBaseUrl},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'A'})}).catch(()=>{});
      // #endregion

      while (attempts < maxAttempts) {
        try {
          const response = await fetch(`${apiBaseUrl}/api/system/startup-progress`, {
            method: "GET",
            headers: { "Content-Type": "application/json" },
          });

          // #region agent log
          fetch('http://localhost:7243/ingest/22b2bc10-668b-4e25-b7af-89ca2a3e5432',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AppProviders.tsx:76',message:'Startup endpoint response',data:{status: response.status, attempts},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'A'})}).catch(()=>{});
          // #endregion

          if (response.ok) {
            const data = await response.json();

            // #region agent log
            fetch('http://localhost:7243/ingest/22b2bc10-668b-4e25-b7af-89ca2a3e5432',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AppProviders.tsx:83',message:'Startup data received',data:{database: data.database, keys: Object.keys(data)},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'B'})}).catch(()=>{});
            // #endregion

            // Check if critical components are ready
            if (data.database) {
              setBackendReady(true);
              setIsCheckingBackend(false);
              return;
            }

            // Backend responding but not fully ready, keep polling
            console.log(`Backend starting... (attempt ${attempts + 1}/${maxAttempts})`);
          }
        } catch (error) {
          // #region agent log
          fetch('http://localhost:7243/ingest/22b2bc10-668b-4e25-b7af-89ca2a3e5432',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AppProviders.tsx:98',message:'Startup check failed',data:{error: String(error), attempts},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'A'})}).catch(()=>{});
          // #endregion
          // Backend not responding yet, keep trying
          console.log(`Waiting for backend... (attempt ${attempts + 1}/${maxAttempts})`);
        }

        attempts++;
        await new Promise((resolve) => setTimeout(resolve, 2000)); // Wait 2s between attempts
      }

      // Max attempts reached, backend may be down
      console.warn("Backend readiness check timeout - proceeding anyway");
      setBackendReady(true);
      setIsCheckingBackend(false);
    };

    checkBackendReadiness();
  }, []);

  // Auto-authenticate after backend is ready
  React.useEffect(() => {
    if (!backendReady) return;

    const ensureAuthToken = async () => {
      if (typeof window === "undefined") return;

      const existingToken = window.localStorage.getItem("argos_auth_token");
      if (existingToken) {
        // Token exists, verify it's still valid by checking expiry
        try {
          const payload = JSON.parse(atob(existingToken.split(".")[1]));
          const expiresAt = payload.exp * 1000; // Convert to milliseconds
          if (Date.now() < expiresAt) {
            // Token is still valid
            return;
          }
        } catch {
          // Invalid token format, will fetch new one
        }
      }

      // No valid token, fetch a new one
      try {
        const apiBaseUrl =
          import.meta.env.VITE_CORTEX_API_BASE_URL ||
          import.meta.env.VITE_API_BASE_URL ||
          getApiBaseUrl();
        const formData = new URLSearchParams();
        formData.append("username", "admin");
        formData.append("password", "password");

        const response = await fetch(`${apiBaseUrl}/api/auth/token`, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: formData.toString(),
        });

        if (response.ok) {
          const data = await response.json();
          window.localStorage.setItem("argos_auth_token", data.access_token);
          console.log("✅ Auto-authenticated successfully");
        } else {
          console.warn("⚠️ Auto-authentication failed:", response.status);
        }
      } catch (error) {
        console.warn("⚠️ Auto-authentication error:", error);
      }
    };

    ensureAuthToken();
  }, [backendReady]);

  // Show loading overlay while checking backend
  if (isCheckingBackend) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          backgroundColor: "#0f172a",
          color: "#e2e8f0",
          fontFamily: "system-ui, -apple-system, sans-serif",
        }}
      >
        <div
          style={{
            width: "48px",
            height: "48px",
            border: "4px solid #1e293b",
            borderTop: "4px solid #3b82f6",
            borderRadius: "50%",
            animation: "spin 1s linear infinite",
            marginBottom: "16px",
          }}
        />
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
        <p style={{ fontSize: "18px", fontWeight: "500" }}>
          Connecting to Argos backend...
        </p>
        <p style={{ fontSize: "14px", color: "#64748b", marginTop: "8px" }}>
          Please wait while services initialize
        </p>
      </div>
    );
  }

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
