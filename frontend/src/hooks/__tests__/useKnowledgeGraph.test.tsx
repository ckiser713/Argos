// src/hooks/__tests__/useKnowledgeGraph.test.tsx
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useKnowledgeGraph } from "../useKnowledgeGraph";
import * as cortexApi from "../../lib/cortexApi";

const sampleKnowledgeGraph: any = {
  nodes: [
    {
      id: "k1",
      label: "Cortex PRD",
      type: "document",
      weight: 0.9,
      clusterId: "c1",
    },
    {
      id: "k2",
      label: "LangGraph Orchestration",
      type: "concept",
      weight: 0.7,
      clusterId: "c1",
    },
  ],
  edges: [
    { id: "ke1", source: "k1", target: "k2", relation: "REFERENCES" },
  ],
};

function createClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function KnowledgeGraphTestComponent({ projectId }: { projectId?: string }) {
  const { data, isLoading, error } = useKnowledgeGraph(projectId);

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

describe("useKnowledgeGraph", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches knowledge graph for a project", async () => {
    const spy = vi
      .spyOn(cortexApi, "fetchKnowledgeGraph")
      .mockResolvedValue(sampleKnowledgeGraph);

    const client = createClient();

    render(
      <QueryClientProvider client={client}>
        <KnowledgeGraphTestComponent projectId="project-1" />
      </QueryClientProvider>
    );

    await waitFor(() =>
      expect(screen.getByTestId("state").textContent).toBe("success")
    );

    expect(screen.getByTestId("node-count").textContent).toBe("2");
    expect(screen.getByTestId("edge-count").textContent).toBe("1");
    expect(screen.getByTestId("first-node-label").textContent).toBe(
      "Cortex PRD"
    );
    expect(spy).toHaveBeenCalledWith("project-1", undefined);
  });
});
