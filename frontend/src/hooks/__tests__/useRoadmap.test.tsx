// src/hooks/__tests__/useRoadmap.test.tsx
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRoadmap } from "../useRoadmap";
import * as cortexApi from "../../lib/cortexApi";

const sampleRoadmap: any = {
  nodes: [
    { id: "n1", label: "Ingest", status: "COMPLETE", type: "stage" },
    { id: "n2", label: "Canonicalize", status: "RUNNING", type: "stage" },
  ],
  edges: [
    { id: "e1", source: "n1", target: "n2", label: "feeds" },
  ],
};

function createClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function RoadmapTestComponent({ projectId }: { projectId: string }) {
  const { data, isLoading, error } = useRoadmap(projectId);

  if (isLoading) return <div data-testid="state">loading</div>;
  if (error) return <div data-testid="state">error</div>;

  return (
    <div>
      <div data-testid="state">success</div>
      <div data-testid="node-count">{data?.nodes.length ?? 0}</div>
      <div data-testid="edge-count">{data?.edges.length ?? 0}</div>
      <div data-testid="first-node-label">{data?.nodes[0]?.label ?? ""}</div>
    </div>
  );
}

describe("useRoadmap", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches roadmap graph for a project", async () => {
    const spy = vi
      .spyOn(cortexApi, "fetchRoadmap")
      .mockResolvedValue(sampleRoadmap);

    const client = createClient();

    render(
      <QueryClientProvider client={client}>
        <RoadmapTestComponent projectId="project-1" />
      </QueryClientProvider>
    );

    await waitFor(() =>
      expect(screen.getByTestId("state").textContent).toBe("success")
    );

    expect(screen.getByTestId("node-count").textContent).toBe("2");
    expect(screen.getByTestId("edge-count").textContent).toBe("1");
    expect(screen.getByTestId("first-node-label").textContent).toBe("Ingest");
    expect(spy).toHaveBeenCalledWith({ projectId: "project-1" });
  });
});
