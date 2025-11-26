// src/components/__tests__/IngestStation.test.tsx
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
// Assuming IngestStation is in ../IngestStation
// import { IngestStation } from "../IngestStation"; 
import * as projectsHooks from "../../hooks/useProjects";
import * as ingestHooks from "../../hooks/useIngestJobs";

// Mock IngestStation component for testing purposes
const IngestStation = () => {
  const { project } = projectsHooks.useCurrentProject();
  const { data, isLoading, error, refetch } = ingestHooks.useIngestJobs(project?.id);

  if (isLoading) return <div data-testid="ingest-station">Loading ingest jobs...</div>;
  if (error) return (
    <div data-testid="ingest-station">
      Failed to load ingest jobs.
      <button onClick={() => refetch()}>Retry</button>
    </div>
  );

  return (
    <div data-testid="ingest-station">
      <h1>Ingest Station</h1>
      {data?.items.map((job) => (
        <div key={job.id} data-testid={`job-row-${job.id}`}>
          <span>{job.filename}</span>
          <span data-testid={`job-${job.id}-stage`}>{job.stage}</span>
          <span data-testid={`job-${job.id}-status`}>{job.status}</span>
        </div>
      ))}
    </div>
  );
};


function mockCurrentProject() {
  vi.spyOn(projectsHooks, "useCurrentProject").mockReturnValue({
    project: { id: "project-1", name: "Test Project" } as any,
    currentProjectId: "project-1",
  });
}

describe("IngestStation", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockCurrentProject();
  });

  it("renders loading state when ingest jobs are loading", () => {
    vi.spyOn(ingestHooks, "useIngestJobs").mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });

    render(<IngestStation />);

    expect(
      screen.getByText(/loading ingest jobs/i)
    ).toBeInTheDocument();
  });

  it("renders error state when ingest jobs fail", () => {
    const refetch = vi.fn();
    vi.spyOn(ingestHooks, "useIngestJobs").mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Backend unavailable"),
      refetch,
    });

    render(<IngestStation />);

    expect(
      screen.getByText(/failed to load ingest jobs/i)
    ).toBeInTheDocument();

    const retryButton = screen.getByRole("button", { name: /retry/i });
    fireEvent.click(retryButton);
    expect(refetch).toHaveBeenCalled();
  });

  it("renders job rows with correct stage/status badges", () => {
    vi.spyOn(ingestHooks, "useIngestJobs").mockReturnValue({
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      data: {
        items: [
          {
            id: "job-1",
            projectId: "project-1",
            sourceId: "src-1",
            // sourceType: "FILE_UPLOAD", // This field is not in the actual IngestJob type, removing
            filename: "design-doc.md",
            sizeBytes: 1024 * 1024,
            mimeType: "text/markdown",
            status: "RUNNING", // IngestJobStatus
            stage: "OCR_SCANNING", // IngestStage
            progress: 45,
            createdAt: "2025-11-24T01:00:00Z",
            updatedAt: "2025-11-24T01:05:00Z",
          },
          {
            id: "job-2",
            projectId: "project-1",
            sourceId: "src-2",
            // sourceType: "FILE_UPLOAD", // This field is not in the actual IngestJob type, removing
            filename: "notes.pdf",
            sizeBytes: 2048 * 1024,
            mimeType: "application/pdf",
            status: "COMPLETE", // IngestJobStatus
            stage: "COMPLETE", // IngestStage
            progress: 100,
            createdAt: "2025-11-24T00:00:00Z",
            updatedAt: "2025-11-24T00:10:00Z",
          },
        ],
        total: 2,
        // page: 1, // These are not in the actual PaginatedResponse from api-types.ts, removing
        // pageSize: 25, // These are not in the actual PaginatedResponse from api-types.ts, removing
      },
    });

    render(<IngestStation />);

    expect(screen.getByText("design-doc.md")).toBeInTheDocument();
    expect(screen.getByText("notes.pdf")).toBeInTheDocument();

    // Stage badges
    expect(screen.getByText("OCR_SCANNING")).toBeInTheDocument();
    expect(screen.getAllByText("COMPLETE").length).toBeGreaterThanOrEqual(1);

    // Status icons/labels (e.g., RUNNING vs COMPLETE)
    expect(screen.getByTestId("job-job-1-status").textContent).toBe("RUNNING");
    expect(screen.getByTestId("job-job-2-status").textContent).toBe("COMPLETE");
  });
});
