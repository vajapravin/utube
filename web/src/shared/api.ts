/** API client wrapper with credentials and CSRF double-submit token. */

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}

export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = endpoint.startsWith('/api') ? endpoint : `/api/v1${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
  const headers = new Headers(options.headers || {});

  // Add CSRF token on state-changing requests
  const method = (options.method || 'GET').toUpperCase();
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const csrfToken = getCookie('mytube_csrf');
    if (csrfToken) {
      headers.set('X-CSRF-Token', csrfToken);
    }
  }

  headers.set('Accept', 'application/json');
  if (options.body && typeof options.body === 'string' && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include', // Include __Host- session cookie
  });

  if (!response.ok) {
    if (response.status === 401 && !window.location.pathname.startsWith('/login')) {
      window.location.href = '/login';
    }
    const errData = await response.json().catch(() => ({ detail: response.statusText }));
    let errorMsg = `Request failed with status ${response.status}`;
    if (typeof errData.detail === 'string') {
      errorMsg = errData.detail;
    } else if (Array.isArray(errData.detail)) {
      errorMsg = errData.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
    } else if (errData.detail && typeof errData.detail === 'object') {
      errorMsg = JSON.stringify(errData.detail);
    }
    throw new Error(errorMsg);
  }

  return response.json();
}
