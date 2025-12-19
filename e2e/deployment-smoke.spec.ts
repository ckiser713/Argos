/**
 * Deployment Smoke Tests
 *
 * Validates that a production-like docker-compose deployment works correctly.
 * Tests service health, frontend serving, backend API, and basic authentication.
 */

import { test, expect } from "@playwright/test";
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

// Configuration
const COMPOSE_FILE = "ops/docker-compose.yml";
const BACKEND_URL = process.env.PLAYWRIGHT_API_BASE || "http://localhost:8000";
const FRONTEND_URL = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:5173";
const STARTUP_TIMEOUT = 120000; // 2 minutes

test.describe.serial("Deployment Smoke Tests", () => {
  test.beforeAll(async () => {
    console.log("Starting docker-compose stack...");

    try {
      // Ensure clean state
      await execAsync(`docker-compose -f ${COMPOSE_FILE} down -v`, {
        timeout: 30000,
      });

      // Start services
      await execAsync(`docker-compose -f ${COMPOSE_FILE} up -d --build`, {
        timeout: 300000, // 5 min for builds
      });

      console.log("Waiting for services to be healthy...");

      // Wait for all services to be healthy
      let attempts = 0;
      const maxAttempts = 60; // 2 minutes

      while (attempts < maxAttempts) {
        const { stdout } = await execAsync(
          `docker-compose -f ${COMPOSE_FILE} ps --format json`
        );

        const services = stdout
          .trim()
          .split("\n")
          .filter(Boolean)
          .map(line => JSON.parse(line));

        const allHealthy = services.every(
          service =>
            service.State === "running" &&
            (service.Health === "healthy" || service.Health === undefined)
        );

        if (allHealthy && services.length > 0) {
          console.log("All services healthy!");
          break;
        }

        console.log(
          `Waiting for services... (${attempts + 1}/${maxAttempts})`
        );
        await new Promise(resolve => setTimeout(resolve, 2000));
        attempts++;
      }

      if (attempts >= maxAttempts) {
        throw new Error("Services did not become healthy in time");
      }

      // Additional wait for backend startup
      console.log("Waiting for backend to fully initialize...");
      await new Promise(resolve => setTimeout(resolve, 10000));

    } catch (error) {
      console.error("Failed to start services:", error);
      // Print logs for debugging
      try {
        const { stdout: logs } = await execAsync(
          `docker-compose -f ${COMPOSE_FILE} logs --tail=50`
        );
        console.error("Service logs:", logs);
      } catch {}
      throw error;
    }
  });

  test.afterAll(async () => {
    console.log("Cleaning up docker-compose stack...");

    // Print final logs
    try {
      const { stdout: logs } = await execAsync(
        `docker-compose -f ${COMPOSE_FILE} logs --tail=100`
      );
      console.log("Final service logs:", logs);
    } catch {}

    // Teardown
    await execAsync(`docker-compose -f ${COMPOSE_FILE} down -v`, {
      timeout: 60000,
    });
  });

  test("backend health endpoint responds", async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/health`);

    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty("status", "healthy");
  });

  test("backend system ready endpoint responds", async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/system/ready`);

    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty("status");
  });

  test("backend startup progress endpoint works", async ({ request }) => {
    const response = await request.get(
      `${BACKEND_URL}/api/system/startup-progress`
    );

    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty("database");
    expect(body).toHaveProperty("embeddings");
    expect(body).toHaveProperty("lanes");
    expect(body).toHaveProperty("ready");

    // Database should be ready in local dev compose
    expect(body.database).toBe(true);
  });

  test("backend CORS headers present", async ({ request }) => {
    const response = await request.options(`${BACKEND_URL}/api/system/health`);

    const headers = response.headers();
    expect(headers["access-control-allow-origin"]).toBeDefined();
    expect(headers["access-control-allow-methods"]).toBeDefined();
  });

  test("frontend serves index.html", async ({ request }) => {
    const response = await request.get(FRONTEND_URL);

    expect(response.status()).toBe(200);

    const contentType = response.headers()["content-type"];
    expect(contentType).toContain("text/html");

    const body = await response.text();
    expect(body).toContain("<html");
    expect(body).toContain("</html>");
    expect(body).toContain("Argos"); // App name should be in title
  });

  test("frontend static assets accessible", async ({ page }) => {
    await page.goto(FRONTEND_URL);

    // Wait for page to load
    await page.waitForLoadState("networkidle");

    // Check that no critical resources failed to load
    const failedRequests: string[] = [];
    page.on("requestfailed", request => {
      failedRequests.push(request.url());
    });

    // Navigate around a bit
    await page.waitForTimeout(2000);

    expect(failedRequests.length).toBe(0);
  });

  test("frontend can reach backend API", async ({ page }) => {
    await page.goto(FRONTEND_URL);

    // Wait for backend connection check to complete
    await page.waitForTimeout(5000);

    // Should not see the "Connecting to backend" loading screen
    const loadingText = page.getByText("Connecting to Argos backend");
    await expect(loadingText).not.toBeVisible({ timeout: 5000 });
  });

  test("authentication flow works", async ({ request }) => {
    // Attempt to get an auth token
    const formData = new URLSearchParams();
    formData.append("username", "admin");
    formData.append("password", "password");

    const response = await request.post(`${BACKEND_URL}/api/auth/token`, {
      data: formData.toString(),
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });

    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty("access_token");
    expect(body).toHaveProperty("token_type", "bearer");

    // Verify token is valid JWT
    const token = body.access_token;
    expect(token.split(".")).toHaveLength(3); // JWT has 3 parts
  });

  test("authenticated API request works", async ({ request }) => {
    // Get token
    const formData = new URLSearchParams();
    formData.append("username", "admin");
    formData.append("password", "password");

    const authResponse = await request.post(`${BACKEND_URL}/api/auth/token`, {
      data: formData.toString(),
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });

    const authBody = await authResponse.json();
    const token = authBody.access_token;

    // Use token to access protected endpoint
    const response = await request.get(`${BACKEND_URL}/api/system/info`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    expect(response.status()).toBe(200);
  });

  test("Qdrant is accessible", async ({ request }) => {
    // Backend should be able to reach Qdrant
    // This is indirectly tested via startup-progress endpoint
    const response = await request.get(
      `${BACKEND_URL}/api/system/embeddings/health`
    );

    expect([200, 503]).toContain(response.status());

    if (response.status() === 200) {
      const body = await response.json();
      expect(body).toHaveProperty("qdrant_reachable");
    }
  });

  test("database migrations ran successfully", async ({ request }) => {
    // Try to access projects endpoint (requires DB tables)
    const formData = new URLSearchParams();
    formData.append("username", "admin");
    formData.append("password", "password");

    const authResponse = await request.post(`${BACKEND_URL}/api/auth/token`, {
      data: formData.toString(),
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });

    const authBody = await authResponse.json();
    const token = authBody.access_token;

    const response = await request.get(`${BACKEND_URL}/api/projects`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test("environment variables set correctly", async () => {
    const { stdout } = await execAsync(
      `docker-compose -f ${COMPOSE_FILE} exec -T backend env | grep RUNNING_IN_DOCKER`
    );

    expect(stdout.trim()).toBe("RUNNING_IN_DOCKER=1");
  });

  test("docker-compose services all running", async () => {
    const { stdout } = await execAsync(
      `docker-compose -f ${COMPOSE_FILE} ps --format json`
    );

    const services = stdout
      .trim()
      .split("\n")
      .filter(Boolean)
      .map(line => JSON.parse(line));

    // Should have at least: backend, frontend-dev, postgres, qdrant, redis
    expect(services.length).toBeGreaterThanOrEqual(5);

    // All should be running
    services.forEach(service => {
      expect(service.State).toBe("running");
    });
  });
});