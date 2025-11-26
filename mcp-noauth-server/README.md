# MCP No-Auth Server

Remote MCP server using the official TypeScript SDK and Streamable HTTP transport, with **no application-layer auth**. Access is restricted purely by your firewall / IP allowlist.

## Features

- Streamable HTTP MCP endpoint at `POST /mcp`.
- All MCP server code lives under `src/mcp/`.
- Minimal tools:
  - `echo` – round-trip text tool to verify connectivity.
  - `health-check` – quick status probe for Inspector / ChatGPT.

## Setup

1. Install dependencies:

   ```bash
   npm install
   ```

2. Build TypeScript:

   ```bash
   npm run build
   ```

3. Run the server:

   ```bash
   npm run start
   ```

   By default the server binds to `0.0.0.0:3000` and serves the MCP endpoint at:

   ```text
   http://YOUR_HOST:3000/mcp
   ```

## Firewall / Network Hardening

This server intentionally has **no auth** at the HTTP level. Lock it down via:

* Host firewall (ufw/iptables/nftables) to only allow ChatGPT / tunnel IP ranges.
* Optionally an HTTPS reverse proxy or tunnel (ngrok, Cloudflare Tunnel) that requires a secret URL or additional IP filtering.

## Connecting with MCP Inspector

1. Install the inspector:

   ```bash
   npx @modelcontextprotocol/inspector
   ```

2. Point it at your MCP endpoint (adjust host/port):

   * URL: `http://YOUR_HOST:3000/mcp`
   * Transport: Streamable HTTP

You should be able to see `echo` and `health-check` in the tool list.

## Connecting from ChatGPT Developer Mode

1. Deploy or tunnel the server behind **HTTPS** (for example, via reverse proxy or tunnel).

2. In ChatGPT **Settings → Apps & Connectors → Advanced → Developer Mode**, enable developer mode.

3. Create a new connector and set the MCP URL to your HTTPS `/mcp` endpoint (e.g. `https://YOUR_PUBLIC_HOST/mcp`).

4. Leave all OAuth/auth settings empty.

5. In a chat, enable your connector and call the `echo` or `health-check` tool.

## Dev Workflow

* Use `npm run dev` (via `tsx`) to run directly from TypeScript while iterating.
* Add new tools in `src/mcp/index.ts` or split them into separate modules and import here.

