/**
 * Error handling utilities for the Argos frontend.
 */

import { ApiError } from "./http";

/**
 * Get a user-friendly error message from an error.
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    // Map common HTTP status codes to user-friendly messages
    switch (error.status) {
      case 400:
        return error.message || "Invalid request. Please check your input.";
      case 401:
        return "Authentication required. Please log in.";
      case 403:
        return "You don't have permission to perform this action.";
      case 404:
        return "The requested resource was not found.";
      case 409:
        return "A conflict occurred. The resource may have been modified.";
      case 422:
        return "Validation error. Please check your input.";
      case 429:
        return "Too many requests. Please try again later.";
      case 500:
        return "Server error. Please try again later.";
      case 503:
        return "Service unavailable. Please try again later.";
      default:
        return error.message || "An error occurred.";
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === "string") {
    return error;
  }

  return "An unexpected error occurred.";
}

/**
 * Get error code from an error.
 */
export function getErrorCode(error: unknown): string | undefined {
  if (error instanceof ApiError) {
    return error.code;
  }
  return undefined;
}

/**
 * Check if error is retryable.
 */
export function isRetryableError(error: unknown): boolean {
  if (error instanceof ApiError) {
    // Retry on network errors and 5xx errors
    return error.status >= 500 || error.status === 429;
  }
  return false;
}

/**
 * Log error for debugging and monitoring.
 */
export function logError(error: unknown, context?: Record<string, any>): void {
  const errorMessage = getErrorMessage(error);
  const errorCode = getErrorCode(error);
  
  console.error("Error:", {
    message: errorMessage,
    code: errorCode,
    error,
    context,
    timestamp: new Date().toISOString(),
  });

  // In production, you would send this to an error tracking service
  // e.g., Sentry.captureException(error, { extra: context });
}

/**
 * Error types for categorization.
 */
export type ErrorType = 
  | "network"
  | "validation"
  | "authentication"
  | "authorization"
  | "not_found"
  | "server"
  | "unknown";

/**
 * Categorize error type.
 */
export function categorizeError(error: unknown): ErrorType {
  if (error instanceof ApiError) {
    if (error.status >= 500) return "server";
    if (error.status === 401) return "authentication";
    if (error.status === 403) return "authorization";
    if (error.status === 404) return "not_found";
    if (error.status === 400 || error.status === 422) return "validation";
    if (error.status === 0 || error.status >= 500) return "network";
  }
  
  if (error instanceof TypeError && error.message.includes("fetch")) {
    return "network";
  }
  
  return "unknown";
}

