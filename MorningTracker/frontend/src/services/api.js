import axios from 'axios';

// #region agent log (debug-9146a2)
const _agentDbg = (hypothesisId, location, message, data) => {
  try {
    fetch('http://127.0.0.1:7391/ingest/9e6c858b-9e0c-408a-820f-feefeb91d02b', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '9146a2' },
      body: JSON.stringify({
        sessionId: '9146a2',
        runId: 'rerun-2',
        hypothesisId,
        location,
        message,
        data,
        timestamp: Date.now(),
      }),
    }).catch(() => {});
  } catch (_) {}
};
// #endregion agent log (debug-9146a2)

const getApiBase = () => {
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://127.0.0.1:8000/api/';
  }
  return '/api/'; // Use relative path in production
};

const API_BASE = getApiBase();

const apiClient = axios.create({
  baseURL: API_BASE,
  // Enforce absolute baseURL by making sure relative URLs are always appended to it
  // This is the default behavior of axios when baseURL is set, but good to be explicit
  // and ensure no leading slashes in requests bypass it.
});

// Auth Interceptor
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  _agentDbg('H4', 'frontend/src/services/api.js:request', 'request', {
    baseURL: config.baseURL,
    url: config.url,
    method: config.method,
  });
  return config;
});

// Error handling Interceptor
apiClient.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const originalRequest = error.config;
    
    // 1. Handle Token Expiry / Unauthorized
    if (error.response?.status === 401 && !originalRequest._retry) {
      console.warn("Unauthorized! Clearing local session...");
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      // Force reload to trigger AuthContext logout/redirect
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }

    // 2. Handle Transient Network Errors / 503s with Retries
    // Axios "Network Error" usually means backend not reachable yet (no response object).
    const isNetworkError = !error.response && (error.message === 'Network Error' || error.code === 'ERR_NETWORK');

    if ((isNetworkError || error.code === 'ECONNABORTED' || error.response?.status >= 500) && !originalRequest._retry) {
      originalRequest._retry = true;
      _agentDbg('H5', 'frontend/src/services/api.js:response_error', 'retrying', {
        baseURL: originalRequest.baseURL,
        url: originalRequest.url,
        method: originalRequest.method,
        status: error.response?.status,
        code: error.code,
        isNetworkError,
      });
      console.log("Transient error. Retrying request...");
      // No artificial delay; retry immediately once.
      return apiClient(originalRequest);
    }

    _agentDbg('H6', 'frontend/src/services/api.js:response_error', 'error', {
      baseURL: originalRequest?.baseURL,
      url: originalRequest?.url,
      method: originalRequest?.method,
      status: error.response?.status,
      message: error.response?.data?.detail || error.message,
    });
    const message =
      error.response?.data?.detail ||
      (isNetworkError ? 'Backend not reachable (starting up). Please retry.' : error.message) ||
      'Unknown Error';
    return Promise.reject(new Error(message));
  }
);

export const api = {
  get: (url, params) => apiClient.get(url, { params }),
  post: (url, data) => apiClient.post(url, data),
  put: (url, data) => apiClient.put(url, data),
  delete: (url) => apiClient.delete(url),
  
  // Helper for direct URLs
  getExportUrl: (job_id) => {
    const token = localStorage.getItem('token');
    return `${API_BASE}articles/export/csv?job_id=${job_id}${token ? `&query_token=${token}` : ''}`;
  },
  getExcelUrl: (job_id) => {
    const token = localStorage.getItem('token');
    return `${API_BASE}articles/export/xlsx?job_id=${job_id}${token ? `&query_token=${token}` : ''}`;
  },
  getDocxUrl: (job_id) => {
    const token = localStorage.getItem('token');
    return `${API_BASE}articles/export/docx?job_id=${job_id}${token ? `&query_token=${token}` : ''}`;
  }
};

export default apiClient;
