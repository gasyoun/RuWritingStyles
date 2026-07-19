export const SETTINGS_STORAGE_KEY = 'ruwritingstyles.web.settings';

export class ApiClientError extends Error {
  constructor(message, { status = null, url = null, cause = null } = {}) {
    super(message, cause ? { cause } : undefined);
    this.name = 'ApiClientError';
    this.status = status;
    this.url = url;
  }
}

export function normalizeBaseUrl(value) {
  const raw = String(value ?? '').trim();
  if (!raw) throw new ApiClientError('Backend URL is required.');

  let parsed;
  try {
    parsed = new URL(raw);
  } catch (error) {
    throw new ApiClientError(`Invalid backend URL: ${raw}`, { cause: error });
  }
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new ApiClientError('Backend URL must use http:// or https://.');
  }
  if (parsed.username || parsed.password || parsed.search || parsed.hash) {
    throw new ApiClientError('Backend URL must not contain credentials, a query, or a fragment.');
  }
  return parsed.toString().replace(/\/$/, '');
}

export function defaultBackendUrl(
  locationLike,
  configuredUrl = '',
  isViteDevelopment = false,
) {
  if (String(configuredUrl).trim()) return normalizeBaseUrl(configuredUrl);
  if (!locationLike) throw new ApiClientError('Browser location is unavailable.');
  if (isViteDevelopment) {
    const protocol = locationLike.protocol === 'https:' ? 'https:' : 'http:';
    return normalizeBaseUrl(`${protocol}//${locationLike.hostname}:8000`);
  }
  return normalizeBaseUrl(locationLike.origin);
}

export function loadSessionSettings(storage, defaults) {
  const fallback = {
    backendUrl: normalizeBaseUrl(defaults.backendUrl),
    token: String(defaults.token ?? ''),
  };
  if (!storage) return fallback;
  try {
    const stored = JSON.parse(storage.getItem(SETTINGS_STORAGE_KEY) || 'null');
    if (!stored || typeof stored !== 'object') return fallback;
    return {
      backendUrl: normalizeBaseUrl(stored.backendUrl || fallback.backendUrl),
      token: typeof stored.token === 'string' ? stored.token : fallback.token,
    };
  } catch {
    return fallback;
  }
}

export function saveSessionSettings(storage, settings) {
  const normalized = {
    backendUrl: normalizeBaseUrl(settings.backendUrl),
    token: String(settings.token ?? ''),
  };
  storage?.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(normalized));
  return normalized;
}

export function bearerHeaders(token, initialHeaders = {}) {
  const headers = new Headers(initialHeaders);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return headers;
}

export function apiUrl(baseUrl, path) {
  const base = normalizeBaseUrl(baseUrl);
  const suffix = String(path).startsWith('/') ? path : `/${path}`;
  return `${base}${suffix}`;
}

export function webSocketUrl(baseUrl, path, token = '') {
  const url = new URL(apiUrl(baseUrl, path));
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  if (token) url.searchParams.set('token', token);
  return url.toString();
}

function errorDetail(payload) {
  if (payload && typeof payload === 'object') return payload.detail || payload.message || '';
  return typeof payload === 'string' ? payload : '';
}

export async function apiFetch(settings, path, options = {}, fetchImpl = fetch) {
  const url = apiUrl(settings.backendUrl, path);
  let response;
  try {
    response = await fetchImpl(url, {
      ...options,
      headers: bearerHeaders(settings.token, options.headers),
    });
  } catch (error) {
    if (error instanceof ApiClientError) throw error;
    throw new ApiClientError(`Cannot connect to ${settings.backendUrl}.`, { url, cause: error });
  }
  if (response.ok) return response;

  let payload;
  try {
    const contentType = response.headers?.get?.('content-type') || '';
    payload = contentType.includes('application/json')
      ? await response.json()
      : await response.text();
  } catch {
    payload = '';
  }
  const detail = errorDetail(payload);
  const prefix = response.status === 401 ? 'Unauthorized' : `Backend request failed (${response.status})`;
  throw new ApiClientError(detail ? `${prefix}: ${detail}` : prefix, {
    status: response.status,
    url,
  });
}
