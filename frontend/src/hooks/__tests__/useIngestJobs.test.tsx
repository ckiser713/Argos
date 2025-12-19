// src/hooks/__tests__/useIngestJobs.test.tsx
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useIngestJobs } from "../useIngestJobs";
import * as argosApi from "../../lib/argosApi";

const sampleIngestResponse: any = {
  items: [
    {
      id: "job-1",
      projectId: "project-1",
      sourceId: "src-1",
      sourceType: "FILE_UPLOAD",
      filename: "spec.md",
      sizeBytes: 1024 * 1024,
      mimeType: "text/markdown",
      status: "RUNNING",
      stage: "GRAPH_INDEXING",
      progress: 72,
      createdAt: "2025-11-24T01:23:45Z",
      updatedAt: "2025-11-24T01:30:00Z",
    },
    {
      id: "job-2",
      projectId: "project-1",
      sourceId: "src-2",
      sourceType: "URL",
      filename: "design-doc.html",
      sizeBytes: 512 * 1024,
      mimeType: "text/html",
      status: "COMPLETE",
      stage: "COMPLETE",
      progress: 100,
      createdAt: "2025-11-24T02:00:00Z",
      updatedAt: "2025-11-24T02:10:00Z",
    },
  ],
  total: 2,
  page: 1,
  pageSize: 25,
};

function createClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

function IngestJobsTestComponent({ projectId }: { projectId: string }) {
  const { data, isLoading, error } = useIngestJobs(projectId);

  if (isLoading) return <div data-testid="state">loading</div>;
  if (error) return <div data-testid="state">error</div>;

  return (
    <div>
      <div data-testid="state">success</div>
      <div data-testid="count">{data?.items.length ?? 0}</div>
      <div data-testid="first-stage">{data?.items[0]?.stage ?? ""}</div>
    </div>
  );
}

describe("useIngestJobs", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns data from argosApi.listIngestJobs", async () => {
    const spy = vi
      .spyOn(argosApi, "listIngestJobs")
      .mockResolvedValue(sampleIngestResponse);

    const client = createClient();

    render(
      <QueryClientProvider client={client}>
        <IngestJobsTestComponent projectId="project-1" />
      </QueryClientProvider>
    );

    expect(screen.getByTestId("state").textContent).toBe("loading");

    await waitFor(() =>
      expect(screen.getByTestId("state").textContent).toBe("success")
    );

    expect(screen.getByTestId("count").textContent).toBe("2");
    expect(screen.getByTestId("first-stage").textContent).toBe("GRAPH_INDEXING");
    expect(spy).toHaveBeenCalledWith({ projectId: "project-1" });
  });

  it("surface errors when argosApi.listIngestJobs rejects", async () => {
    vi.spyOn(argosApi, "listIngestJobs").mockRejectedValue(
      new Error("Network failure")
    );

    const client = createClient();

    render(
      <QueryClientProvider client={client}>
        <IngestJobsTestComponent projectId="project-1" />
      </QueryClientProvider>
    );

    await waitFor(() =>
      expect(screen.getByTestId("state").textContent).toBe("error")
    );
  });
});
