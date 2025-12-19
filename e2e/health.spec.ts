import type { APIRequestContext } from '@playwright/test';
import crypto from 'node:crypto';
import { test, expect } from './fixtures';

const API_BASE = process.env.PLAYWRIGHT_API_BASE || 'http://localhost:8000/api';
const FRONTEND_BASE = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
const QDRANT_URL = (process.env.ARGOS_QDRANT_URL || 'http://localhost:6333').replace(/\/$/, '');
const STORAGE_ENDPOINT = (process.env.ARGOS_STORAGE_ENDPOINT_URL || 'http://localhost:9000').replace(/\/$/, '');
const STORAGE_BUCKET = process.env.ARGOS_STORAGE_BUCKET || 'cortex-ingest';
const STORAGE_ACCESS_KEY = process.env.ARGOS_STORAGE_ACCESS_KEY || 'minioadmin';
const STORAGE_SECRET_KEY = process.env.ARGOS_STORAGE_SECRET_KEY || 'minioadmin';

const AWS_REGION = 'us-east-1';
const AWS_SERVICE = 's3';

const hmac = (key: crypto.BinaryLike, data: crypto.BinaryLike) =>
  crypto.createHmac('sha256', key).update(data).digest();

const hashHex = (data: crypto.BinaryLike) =>
  crypto.createHash('sha256').update(data).digest('hex');

const getSignatureKey = (key: string, dateStamp: string, region: string, service: string) => {
  const kDate = hmac(`AWS4${key}`, dateStamp);
  const kRegion = hmac(kDate, region);
  const kService = hmac(kRegion, service);
  return hmac(kService, 'aws4_request');
};

const assertBucketExists = async (api: APIRequestContext) => {
  const url = new URL(`/${STORAGE_BUCKET}`, STORAGE_ENDPOINT);
  const amzDate = new Date().toISOString().replace(/[:-]|\.\d{3}/g, '');
  const dateStamp = amzDate.slice(0, 8);
  const payloadHash = hashHex('');

  const canonicalHeaders = `host:${url.host}\nx-amz-content-sha256:${payloadHash}\nx-amz-date:${amzDate}\n`;
  const signedHeaders = 'host;x-amz-content-sha256;x-amz-date';
  const canonicalRequest = [
    'HEAD',
    url.pathname,
    '',
    canonicalHeaders,
    signedHeaders,
    payloadHash,
  ].join('\n');

  const credentialScope = `${dateStamp}/${AWS_REGION}/${AWS_SERVICE}/aws4_request`;
  const stringToSign = [
    'AWS4-HMAC-SHA256',
    amzDate,
    credentialScope,
    hashHex(canonicalRequest),
  ].join('\n');

  const signingKey = getSignatureKey(STORAGE_SECRET_KEY, dateStamp, AWS_REGION, AWS_SERVICE);
  const signature = crypto.createHmac('sha256', signingKey).update(stringToSign).digest('hex');

  const authorization = [
    `AWS4-HMAC-SHA256 Credential=${STORAGE_ACCESS_KEY}/${credentialScope}`,
    `SignedHeaders=${signedHeaders}`,
    `Signature=${signature}`,
  ].join(', ');

  const response = await api.fetch(url.toString(), {
    method: 'HEAD',
    headers: {
      'x-amz-content-sha256': payloadHash,
      'x-amz-date': amzDate,
      Authorization: authorization,
    },
  });

  expect(response.ok(), `Bucket ${STORAGE_BUCKET} should exist`).toBeTruthy();
};

test.describe('Health smoke', () => {
  test('backend readiness', async ({ api }) => {
    const health = await api.get(`${API_BASE}/system/health`);
    expect(health.ok()).toBeTruthy();

    const ready = await api.get(`${API_BASE}/system/ready`);
    expect(ready.ok()).toBeTruthy();
  });

  test('qdrant and storage services', async ({ api }) => {
    const qdrantHealth = await api.get(`${QDRANT_URL}/health`);
    expect(qdrantHealth.ok()).toBeTruthy();

    const minioHealth = await api.get(`${STORAGE_ENDPOINT}/minio/health/ready`);
    expect(minioHealth.ok()).toBeTruthy();

    await assertBucketExists(api);
  });

  test('frontend loads', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    await expect(authenticatedPage).toHaveTitle(/Cortex/i);
  });
});


