import assert from 'node:assert/strict';
import test from 'node:test';

import {
  ApiClientError,
  SETTINGS_STORAGE_KEY,
  apiFetch,
  bearerHeaders,
  defaultBackendUrl,
  loadSessionSettings,
  normalizeBaseUrl,
  saveSessionSettings,
  webSocketUrl,
} from './api-client.js';


function memoryStorage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  };
}

test('bundled and Vite development defaults use the expected host', () => {
  const location = {
    origin: 'https://studio.example.org',
    protocol: 'https:',
    hostname: 'studio.example.org',
  };
  assert.equal(defaultBackendUrl(location), 'https://studio.example.org');
  assert.equal(defaultBackendUrl(location, '', true), 'https://studio.example.org:8000');
});

test('session settings persist both URL and token', () => {
  const storage = memoryStorage();
  const saved = saveSessionSettings(storage, {
    backendUrl: 'https://api.example.org/',
    token: 'session secret',
  });
  assert.deepEqual(saved, {
    backendUrl: 'https://api.example.org',
    token: 'session secret',
  });
  assert.deepEqual(loadSessionSettings(storage, { backendUrl: 'http://fallback', token: '' }), saved);
  assert.match(storage.getItem(SETTINGS_STORAGE_KEY), /session secret/);
});

test('bearer token is added to HTTP headers', () => {
  const headers = bearerHeaders('abc123', { 'Content-Type': 'application/json' });
  assert.equal(headers.get('Authorization'), 'Bearer abc123');
  assert.equal(headers.get('Content-Type'), 'application/json');
});

test('HTTP requests keep the token out of the URL', async () => {
  let observedUrl = '';
  let observedHeaders;
  const fakeFetch = async (url, options) => {
    observedUrl = url;
    observedHeaders = options.headers;
    return new Response('{}', { status: 200 });
  };
  await apiFetch(
    { backendUrl: 'https://api.example.org', token: 'a+b&c=d' },
    '/runs',
    {},
    fakeFetch,
  );
  assert.equal(observedUrl, 'https://api.example.org/runs');
  assert.equal(observedHeaders.get('Authorization'), 'Bearer a+b&c=d');
});

test('HTTPS becomes WSS and the WebSocket token is URL encoded', () => {
  const url = webSocketUrl('https://api.example.org/', '/ws/run 1', 'a+b&c=d');
  assert.equal(url, 'wss://api.example.org/ws/run%201?token=a%2Bb%26c%3Dd');
});

test('invalid backend URLs fail clearly', () => {
  assert.throws(() => normalizeBaseUrl('localhost:8000'), ApiClientError);
  assert.throws(() => normalizeBaseUrl('ftp://example.org'), /http:\/\/ or https:\/\//);
});

test('unauthorized responses become typed visible errors', async () => {
  const fakeFetch = async () => new Response(
    JSON.stringify({ detail: 'bad token' }),
    { status: 401, headers: { 'Content-Type': 'application/json' } },
  );
  await assert.rejects(
    apiFetch(
      { backendUrl: 'https://api.example.org', token: 'wrong' },
      '/status',
      {},
      fakeFetch,
    ),
    (error) => error instanceof ApiClientError
      && error.status === 401
      && error.message === 'Unauthorized: bad token',
  );
});

test('network failures identify the configured backend', async () => {
  const fakeFetch = async () => { throw new TypeError('offline'); };
  await assert.rejects(
    apiFetch({ backendUrl: 'http://127.0.0.1:8000', token: '' }, '/runs', {}, fakeFetch),
    /Cannot connect to http:\/\/127\.0\.0\.1:8000/,
  );
});
