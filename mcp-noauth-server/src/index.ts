import express from "express";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { createMcpServer } from "./mcp/index.js";

// Create a singleton MCP server instance for this process.
const mcpServer = createMcpServer();

const app = express();
app.use(express.json({ limit: "2mb" }));

// Streamable HTTP MCP endpoint – no auth, IP-restricted at firewall level.
app.post("/mcp", async (req, res) => {
  try {
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined,
      enableJsonResponse: true
    });

    // Clean up transport if connection is closed early.
    res.on("close", () => {
      transport.close();
    });

    await mcpServer.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (error) {
    console.error("Error handling /mcp request", error);
    if (!res.headersSent) {
      res.status(500).json({ error: "Internal MCP server error" });
    }
  }
});

const port = parseInt(process.env.PORT || "3000", 10);
const host = process.env.HOST || "0.0.0.0";

app.listen(port, host, () => {
  console.log(`MCP server listening on http://${host}:${port}/mcp`);
  console.log("Remember: lock down this port to ChatGPT / tunnel IP range only.");
});

