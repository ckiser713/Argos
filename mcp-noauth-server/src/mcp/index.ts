import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import * as z from "zod/v4";
import { promises as fs } from "fs";
import * as path from "path";
import { homedir } from "os";

/**
 * Factory to create the MCP server.
 * All tools and resources are registered here.
 */
export function createMcpServer() {
  const server = new McpServer({
    name: "cursor-noauth-mcp",
    version: "0.1.0"
  });

  // Simple echo tool – great for smoke tests from MCP Inspector or ChatGPT.
  server.registerTool(
    "echo",
    {
      title: "Echo text",
      description: "Echo back the provided text. Useful for connectivity tests.",
      inputSchema: {
        text: z.string()
      },
      outputSchema: {
        text: z.string()
      }
    },
    async ({ text }) => {
      const output = { text };
      return {
        content: [
          {
            type: "text",
            text: text
          }
        ],
        structuredContent: output
      };
    }
  );

  // Health check tool so ChatGPT / Inspector can verify server status.
  server.registerTool(
    "health-check",
    {
      title: "Health check for MCP server",
      description: "Returns basic status information about this MCP server.",
      inputSchema: {},
      outputSchema: {
        status: z.string(),
        uptimeSeconds: z.number(),
        timestamp: z.string()
      }
    },
    async () => {
      const now = new Date();
      const uptimeSeconds = process.uptime();
      const output = {
        status: "ok",
        uptimeSeconds,
        timestamp: now.toISOString()
      };

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(output, null, 2)
          }
        ],
        structuredContent: output
      };
    }
  );

  // Text manipulation tools
  server.registerTool(
    "reverse-text",
    {
      title: "Reverse text",
      description: "Reverses the order of characters in the provided text.",
      inputSchema: {
        text: z.string()
      },
      outputSchema: {
        original: z.string(),
        reversed: z.string()
      }
    },
    async ({ text }) => {
      const reversed = text.split("").reverse().join("");
      const output = {
        original: text,
        reversed
      };
      return {
        content: [
          {
            type: "text",
            text: `Original: ${text}\nReversed: ${reversed}`
          }
        ],
        structuredContent: output
      };
    }
  );

  server.registerTool(
    "text-case",
    {
      title: "Transform text case",
      description: "Transforms text to uppercase, lowercase, or title case.",
      inputSchema: {
        text: z.string(),
        case: z.enum(["uppercase", "lowercase", "title"])
      },
      outputSchema: {
        original: z.string(),
        transformed: z.string(),
        case: z.string()
      }
    },
    async ({ text, case: caseType }) => {
      let transformed: string;
      switch (caseType) {
        case "uppercase":
          transformed = text.toUpperCase();
          break;
        case "lowercase":
          transformed = text.toLowerCase();
          break;
        case "title":
          transformed = text
            .split(" ")
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join(" ");
          break;
      }
      const output = {
        original: text,
        transformed,
        case: caseType
      };
      return {
        content: [
          {
            type: "text",
            text: `Original: ${text}\nTransformed (${caseType}): ${transformed}`
          }
        ],
        structuredContent: output
      };
    }
  );

  server.registerTool(
    "word-count",
    {
      title: "Count words and characters",
      description: "Counts the number of words, characters, and lines in the provided text.",
      inputSchema: {
        text: z.string()
      },
      outputSchema: {
        characters: z.number(),
        charactersNoSpaces: z.number(),
        words: z.number(),
        lines: z.number()
      }
    },
    async ({ text }) => {
      const output = {
        characters: text.length,
        charactersNoSpaces: text.replace(/\s/g, "").length,
        words: text.trim() === "" ? 0 : text.trim().split(/\s+/).length,
        lines: text.split("\n").length
      };
      return {
        content: [
          {
            type: "text",
            text: `Characters: ${output.characters}\nCharacters (no spaces): ${output.charactersNoSpaces}\nWords: ${output.words}\nLines: ${output.lines}`
          }
        ],
        structuredContent: output
      };
    }
  );

  // Math/calculation tools
  server.registerTool(
    "calculate",
    {
      title: "Basic calculator",
      description: "Performs basic arithmetic operations: add, subtract, multiply, divide.",
      inputSchema: {
        operation: z.enum(["add", "subtract", "multiply", "divide"]),
        a: z.number(),
        b: z.number()
      },
      outputSchema: {
        operation: z.string(),
        a: z.number(),
        b: z.number(),
        result: z.number()
      }
    },
    async ({ operation, a, b }) => {
      let result: number;
      switch (operation) {
        case "add":
          result = a + b;
          break;
        case "subtract":
          result = a - b;
          break;
        case "multiply":
          result = a * b;
          break;
        case "divide":
          if (b === 0) {
            throw new Error("Division by zero is not allowed");
          }
          result = a / b;
          break;
      }
      const output = {
        operation,
        a,
        b,
        result
      };
      return {
        content: [
          {
            type: "text",
            text: `${a} ${operation} ${b} = ${result}`
          }
        ],
        structuredContent: output
      };
    }
  );

  server.registerTool(
    "random-number",
    {
      title: "Generate random number",
      description: "Generates a random integer between min and max (inclusive).",
      inputSchema: {
        min: z.number(),
        max: z.number()
      },
      outputSchema: {
        min: z.number(),
        max: z.number(),
        random: z.number()
      }
    },
    async ({ min, max }) => {
      if (min >= max) {
        throw new Error("min must be less than max");
      }
      const random = Math.floor(Math.random() * (max - min + 1)) + min;
      const output = {
        min,
        max,
        random
      };
      return {
        content: [
          {
            type: "text",
            text: `Random number between ${min} and ${max}: ${random}`
          }
        ],
        structuredContent: output
      };
    }
  );

  // Date/time tools
  server.registerTool(
    "get-time",
    {
      title: "Get current time",
      description: "Returns the current time in ISO format and Unix timestamp.",
      inputSchema: {
        timezone: z.string().optional()
      },
      outputSchema: {
        iso: z.string(),
        unix: z.number(),
        timezone: z.string().optional()
      }
    },
    async ({ timezone }) => {
      const now = new Date();
      const output = {
        iso: now.toISOString(),
        unix: Math.floor(now.getTime() / 1000),
        timezone: timezone || "UTC"
      };
      return {
        content: [
          {
            type: "text",
            text: `Current time (ISO): ${output.iso}\nUnix timestamp: ${output.unix}\nTimezone: ${output.timezone}`
          }
        ],
        structuredContent: output
      };
    }
  );

  server.registerTool(
    "format-date",
    {
      title: "Format date",
      description: "Formats a Unix timestamp or ISO date string into a readable format.",
      inputSchema: {
        timestamp: z.union([z.number(), z.string()]),
        format: z.enum(["iso", "unix", "readable"]).optional()
      },
      outputSchema: {
        timestamp: z.union([z.number(), z.string()]),
        iso: z.string(),
        unix: z.number(),
        readable: z.string()
      }
    },
    async ({ timestamp, format }) => {
      let date: Date;
      if (typeof timestamp === "number") {
        date = new Date(timestamp * 1000);
      } else {
        date = new Date(timestamp);
      }
      if (isNaN(date.getTime())) {
        throw new Error("Invalid timestamp or date string");
      }
      const output = {
        timestamp,
        iso: date.toISOString(),
        unix: Math.floor(date.getTime() / 1000),
        readable: date.toLocaleString()
      };
      return {
        content: [
          {
            type: "text",
            text: format === "readable" ? output.readable : format === "unix" ? output.unix.toString() : output.iso
          }
        ],
        structuredContent: output
      };
    }
  );

  // Data transformation tools
  server.registerTool(
    "base64-encode",
    {
      title: "Base64 encode",
      description: "Encodes a string to Base64 format.",
      inputSchema: {
        text: z.string()
      },
      outputSchema: {
        original: z.string(),
        encoded: z.string()
      }
    },
    async ({ text }) => {
      const encoded = Buffer.from(text, "utf8").toString("base64");
      const output = {
        original: text,
        encoded
      };
      return {
        content: [
          {
            type: "text",
            text: `Original: ${text}\nBase64: ${encoded}`
          }
        ],
        structuredContent: output
      };
    }
  );

  server.registerTool(
    "base64-decode",
    {
      title: "Base64 decode",
      description: "Decodes a Base64 string back to plain text.",
      inputSchema: {
        encoded: z.string()
      },
      outputSchema: {
        encoded: z.string(),
        decoded: z.string()
      }
    },
    async ({ encoded }) => {
      try {
        const decoded = Buffer.from(encoded, "base64").toString("utf8");
        const output = {
          encoded,
          decoded
        };
        return {
          content: [
            {
              type: "text",
              text: `Encoded: ${encoded}\nDecoded: ${decoded}`
            }
          ],
          structuredContent: output
        };
      } catch (error) {
        throw new Error("Invalid Base64 string");
      }
    }
  );

  server.registerTool(
    "json-format",
    {
      title: "Format JSON",
      description: "Formats and validates a JSON string with pretty printing.",
      inputSchema: {
        json: z.string()
      },
      outputSchema: {
        valid: z.boolean(),
        formatted: z.string().optional(),
        error: z.string().optional()
      }
    },
    async ({ json }) => {
      try {
        const parsed = JSON.parse(json);
        const formatted = JSON.stringify(parsed, null, 2);
        const output = {
          valid: true,
          formatted
        };
        return {
          content: [
            {
              type: "text",
              text: formatted
            }
          ],
          structuredContent: output
        };
      } catch (error) {
        const output = {
          valid: false,
          error: error instanceof Error ? error.message : "Invalid JSON"
        };
        return {
          content: [
            {
              type: "text",
              text: `JSON validation failed: ${output.error}`
            }
          ],
          structuredContent: output
        };
      }
    }
  );

  // System/info tools
  server.registerTool(
    "get-env",
    {
      title: "Get environment variable",
      description: "Retrieves the value of an environment variable.",
      inputSchema: {
        name: z.string()
      },
      outputSchema: {
        name: z.string(),
        value: z.string().optional(),
        exists: z.boolean()
      }
    },
    async ({ name }) => {
      const value = process.env[name];
      const output = {
        name,
        value: value || undefined,
        exists: value !== undefined
      };
      return {
        content: [
          {
            type: "text",
            text: output.exists ? `${name}=${value}` : `Environment variable ${name} does not exist`
          }
        ],
        structuredContent: output
      };
    }
  );

  server.registerTool(
    "system-info",
    {
      title: "Get system information",
      description: "Returns basic system information about the Node.js process.",
      inputSchema: {},
      outputSchema: {
        platform: z.string(),
        nodeVersion: z.string(),
        arch: z.string(),
        uptime: z.number(),
        memoryUsage: z.object({
          rss: z.number(),
          heapTotal: z.number(),
          heapUsed: z.number(),
          external: z.number()
        })
      }
    },
    async () => {
      const memUsage = process.memoryUsage();
      const output = {
        platform: process.platform,
        nodeVersion: process.version,
        arch: process.arch,
        uptime: process.uptime(),
        memoryUsage: {
          rss: memUsage.rss,
          heapTotal: memUsage.heapTotal,
          heapUsed: memUsage.heapUsed,
          external: memUsage.external
        }
      };
      return {
        content: [
          {
            type: "text",
            text: `Platform: ${output.platform}\nNode.js: ${output.nodeVersion}\nArchitecture: ${output.arch}\nUptime: ${output.uptime}s\nMemory: ${Math.round(memUsage.heapUsed / 1024 / 1024)}MB / ${Math.round(memUsage.heapTotal / 1024 / 1024)}MB`
          }
        ],
        structuredContent: output
      };
    }
  );

  // UUID generation tool
  server.registerTool(
    "generate-uuid",
    {
      title: "Generate UUID",
      description: "Generates a random UUID v4.",
      inputSchema: {},
      outputSchema: {
        uuid: z.string()
      }
    },
    async () => {
      // Simple UUID v4 generator
      const uuid = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        const v = c === "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
      });
      const output = {
        uuid
      };
      return {
        content: [
          {
            type: "text",
            text: uuid
          }
        ],
        structuredContent: output
      };
    }
  );

  // Hash generation tool
  server.registerTool(
    "hash-text",
    {
      title: "Hash text",
      description: "Generates a simple hash (not cryptographically secure) for the given text.",
      inputSchema: {
        text: z.string(),
        algorithm: z.enum(["simple", "djb2"]).optional()
      },
      outputSchema: {
        text: z.string(),
        algorithm: z.string(),
        hash: z.string()
      }
    },
    async ({ text, algorithm = "simple" }) => {
      let hash: string;
      if (algorithm === "djb2") {
        let hashValue = 5381;
        for (let i = 0; i < text.length; i++) {
          hashValue = (hashValue << 5) + hashValue + text.charCodeAt(i);
        }
        hash = Math.abs(hashValue).toString(16);
      } else {
        // Simple hash
        let hashValue = 0;
        for (let i = 0; i < text.length; i++) {
          const char = text.charCodeAt(i);
          hashValue = (hashValue << 5) - hashValue + char;
          hashValue = hashValue & hashValue; // Convert to 32-bit integer
        }
        hash = Math.abs(hashValue).toString(16);
      }
      const output = {
        text,
        algorithm,
        hash
      };
      return {
        content: [
          {
            type: "text",
            text: `Text: ${text}\nAlgorithm: ${algorithm}\nHash: ${hash}`
          }
        ],
        structuredContent: output
      };
    }
  );

  // Base directory for file operations
  const BASE_DIR = path.join(homedir(), "Argos_Chatgpt");

  // File system tools for ~/Argos_Chatgpt
  server.registerTool(
    "read-file",
    {
      title: "Read file from Argos_Chatgpt",
      description: "Reads the contents of a file from ~/Argos_Chatgpt directory.",
      inputSchema: {
        filePath: z.string()
      },
      outputSchema: {
        filePath: z.string(),
        content: z.string(),
        exists: z.boolean()
      }
    },
    async ({ filePath }) => {
      try {
        // Resolve path relative to BASE_DIR, prevent directory traversal
        const resolvedPath = path.resolve(BASE_DIR, filePath);
        if (!resolvedPath.startsWith(BASE_DIR)) {
          throw new Error("Path traversal detected");
        }
        const content = await fs.readFile(resolvedPath, "utf8");
        const output = {
          filePath: resolvedPath,
          content,
          exists: true
        };
        return {
          content: [
            {
              type: "text",
              text: content
            }
          ],
          structuredContent: output
        };
      } catch (error) {
        if ((error as NodeJS.ErrnoException).code === "ENOENT") {
          const output = {
            filePath,
            content: "",
            exists: false
          };
          return {
            content: [
              {
                type: "text",
                text: `File not found: ${filePath}`
              }
            ],
            structuredContent: output
          };
        }
        throw error;
      }
    }
  );

  server.registerTool(
    "list-directory",
    {
      title: "List directory contents",
      description: "Lists files and directories in ~/Argos_Chatgpt or a subdirectory.",
      inputSchema: {
        dirPath: z.string().optional()
      },
      outputSchema: {
        path: z.string(),
        items: z.array(
          z.object({
            name: z.string(),
            type: z.enum(["file", "directory"]),
            size: z.number().optional()
          })
        )
      }
    },
    async ({ dirPath = "." }) => {
      try {
        const resolvedPath = path.resolve(BASE_DIR, dirPath);
        if (!resolvedPath.startsWith(BASE_DIR)) {
          throw new Error("Path traversal detected");
        }
        const entries = await fs.readdir(resolvedPath, { withFileTypes: true });
        const items = await Promise.all(
          entries.map(async (entry) => {
            const itemPath = path.join(resolvedPath, entry.name);
            let size: number | undefined;
            if (entry.isFile()) {
              const stats = await fs.stat(itemPath);
              size = stats.size;
            }
            return {
              name: entry.name,
              type: entry.isDirectory() ? ("directory" as const) : ("file" as const),
              size
            };
          })
        );
        const output = {
          path: resolvedPath,
          items
        };
        return {
          content: [
            {
              type: "text",
              text: `Directory: ${resolvedPath}\n\n${items.map((item) => `${item.type === "directory" ? "📁" : "📄"} ${item.name}${item.size ? ` (${item.size} bytes)` : ""}`).join("\n")}`
            }
          ],
          structuredContent: output
        };
      } catch (error) {
        throw new Error(`Failed to list directory: ${error instanceof Error ? error.message : String(error)}`);
      }
    }
  );

  server.registerTool(
    "write-file",
    {
      title: "Write file to Argos_Chatgpt",
      description: "Writes content to a file in ~/Argos_Chatgpt directory. Creates parent directories if needed.",
      inputSchema: {
        filePath: z.string(),
        content: z.string(),
        createDirs: z.boolean().optional()
      },
      outputSchema: {
        filePath: z.string(),
        written: z.boolean(),
        bytesWritten: z.number()
      }
    },
    async ({ filePath, content, createDirs = true }) => {
      try {
        const resolvedPath = path.resolve(BASE_DIR, filePath);
        if (!resolvedPath.startsWith(BASE_DIR)) {
          throw new Error("Path traversal detected");
        }
        if (createDirs) {
          await fs.mkdir(path.dirname(resolvedPath), { recursive: true });
        }
        await fs.writeFile(resolvedPath, content, "utf8");
        const output = {
          filePath: resolvedPath,
          written: true,
          bytesWritten: Buffer.byteLength(content, "utf8")
        };
        return {
          content: [
            {
              type: "text",
              text: `File written successfully: ${resolvedPath}\nBytes written: ${output.bytesWritten}`
            }
          ],
          structuredContent: output
        };
      } catch (error) {
        throw new Error(`Failed to write file: ${error instanceof Error ? error.message : String(error)}`);
      }
    }
  );

  server.registerTool(
    "file-info",
    {
      title: "Get file information",
      description: "Gets detailed information about a file or directory in ~/Argos_Chatgpt.",
      inputSchema: {
        filePath: z.string()
      },
      outputSchema: {
        path: z.string(),
        exists: z.boolean(),
        type: z.enum(["file", "directory"]).optional(),
        size: z.number().optional(),
        created: z.string().optional(),
        modified: z.string().optional(),
        permissions: z.string().optional()
      }
    },
    async ({ filePath }) => {
      try {
        const resolvedPath = path.resolve(BASE_DIR, filePath);
        if (!resolvedPath.startsWith(BASE_DIR)) {
          throw new Error("Path traversal detected");
        }
        const stats = await fs.stat(resolvedPath);
        const output = {
          path: resolvedPath,
          exists: true,
          type: stats.isDirectory() ? ("directory" as const) : ("file" as const),
          size: stats.isFile() ? stats.size : undefined,
          created: stats.birthtime.toISOString(),
          modified: stats.mtime.toISOString(),
          permissions: stats.mode.toString(8).slice(-3)
        };
        return {
          content: [
            {
              type: "text",
              text: `Path: ${resolvedPath}\nType: ${output.type}\nSize: ${output.size ?? "N/A"} bytes\nCreated: ${output.created}\nModified: ${output.modified}\nPermissions: ${output.permissions}`
            }
          ],
          structuredContent: output
        };
      } catch (error) {
        if ((error as NodeJS.ErrnoException).code === "ENOENT") {
          const output = {
            path: filePath,
            exists: false
          };
          return {
            content: [
              {
                type: "text",
                text: `File or directory not found: ${filePath}`
              }
            ],
            structuredContent: output
          };
        }
        throw error;
      }
    }
  );

  server.registerTool(
    "search-files",
    {
      title: "Search files by name",
      description: "Searches for files matching a pattern in ~/Argos_Chatgpt directory (recursive).",
      inputSchema: {
        pattern: z.string(),
        maxDepth: z.number().optional(),
        fileType: z.enum(["file", "directory", "both"]).optional()
      },
      outputSchema: {
        pattern: z.string(),
        matches: z.array(
          z.object({
            path: z.string(),
            type: z.enum(["file", "directory"]),
            size: z.number().optional()
          })
        ),
        count: z.number()
      }
    },
    async ({ pattern, maxDepth = 10, fileType = "both" }) => {
      const matches: Array<{ path: string; type: "file" | "directory"; size?: number }> = [];
      const regex = new RegExp(pattern.replace(/\*/g, ".*"), "i");

      async function searchDir(currentPath: string, depth: number): Promise<void> {
        if (depth > maxDepth) return;
        try {
          const entries = await fs.readdir(currentPath, { withFileTypes: true });
          for (const entry of entries) {
            const entryPath = path.join(currentPath, entry.name);
            const relativePath = path.relative(BASE_DIR, entryPath);
            if (regex.test(entry.name) || regex.test(relativePath)) {
              if (entry.isDirectory() && (fileType === "directory" || fileType === "both")) {
                const stats = await fs.stat(entryPath);
                matches.push({
                  path: relativePath,
                  type: "directory",
                  size: stats.size
                });
              } else if (entry.isFile() && (fileType === "file" || fileType === "both")) {
                const stats = await fs.stat(entryPath);
                matches.push({
                  path: relativePath,
                  type: "file",
                  size: stats.size
                });
              }
            }
            if (entry.isDirectory() && depth < maxDepth) {
              await searchDir(entryPath, depth + 1);
            }
          }
        } catch (error) {
          // Skip directories we can't read
        }
      }

      await searchDir(BASE_DIR, 0);
      const output = {
        pattern,
        matches,
        count: matches.length
      };
      return {
        content: [
          {
            type: "text",
            text: `Found ${matches.length} matches for pattern "${pattern}":\n\n${matches.map((m) => `${m.type === "directory" ? "📁" : "📄"} ${m.path}${m.size ? ` (${m.size} bytes)` : ""}`).join("\n")}`
          }
        ],
        structuredContent: output
      };
    }
  );

  return server;
}

