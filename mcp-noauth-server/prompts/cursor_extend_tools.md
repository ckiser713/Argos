SYSTEM (to Cursor / Code agent)

You are extending an existing MCP server project at `mcp-noauth-server/`.

The MCP server uses:

- `@modelcontextprotocol/sdk` with Streamable HTTP transport.

- All MCP logic lives under `src/mcp/`.

- `createMcpServer()` in `src/mcp/index.ts` returns a configured `McpServer`.



Your job in this run:

1. Inspect `src/mcp/index.ts` to understand current tools.

2. Add new tools as requested in the user prompt, but **do not** change the HTTP wiring in `src/index.ts`.

3. Each tool MUST:

   - Use `zod/v4` schemas for `inputSchema` and `outputSchema`.

   - Return both `content` (for model-readable text) and `structuredContent` (JSON typed output).

4. Keep tools small and composable; do not over-load a single tool with many unrelated actions.

5. Preserve the existing `echo` and `health-check` tools.



After changes, ensure TypeScript builds cleanly and briefly list the new tools with their names, descriptions, and input/output shapes.

