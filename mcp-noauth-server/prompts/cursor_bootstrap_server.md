SYSTEM (to Cursor / Code agent)

You are an expert TypeScript + Node MCP server engineer.

Your task: bootstrap a new MCP server project that matches the following requirements **exactly**:

- Project name: `mcp-noauth-server`.

- Use Node 18+ and TypeScript.

- Use the official `@modelcontextprotocol/sdk` with **Streamable HTTP** transport.

- Expose a single MCP endpoint at `POST /mcp` via Express.

- No authentication at the HTTP/MCP layer — **all** access control is via host firewall/IP allowlist.

- All MCP-specific code must live under `src/mcp/`.

- Entry HTTP file: `src/index.ts`.

- MCP server factory file: `src/mcp/index.ts`.

- Tools to implement:

  - `echo(text: string)` returning the same text.

  - `health-check()` returning `status`, `uptimeSeconds`, and `timestamp`.



Follow this plan:

1. Create or update `package.json`, `tsconfig.json`, `.gitignore`, and `src/` tree to match the provided structure.

2. Implement `createMcpServer` in `src/mcp/index.ts` using `McpServer` from `@modelcontextprotocol/sdk/server/mcp.js` and `zod/v4` for schemas.

3. Implement `src/index.ts` using Express and `StreamableHTTPServerTransport` from `@modelcontextprotocol/sdk/server/streamableHttp.js`.

4. Ensure `npm run build` compiles and `npm run start` runs the server.

5. Add minimal logging and error handling for the `/mcp` route.



When finished, print a short summary of what changed and show `npm run build && npm run start` as the final command to run.

