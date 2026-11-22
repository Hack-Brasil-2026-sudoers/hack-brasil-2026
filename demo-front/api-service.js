/** Same-origin API adapter. GitHub tokens remain on the server. */
export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

export function createApiService({ fetcher = globalThis.fetch.bind(globalThis) } = {}) {
  let identity;
  let installation;

  async function request(path, options = {}) {
    const headers = { Accept: 'application/json', ...options.headers };
    if (options.method && options.method !== 'GET') {
      if (!identity) await session();
      headers['X-CSRF-Token'] = identity.csrf_token;
      if (options.body) headers['Content-Type'] = 'application/json';
    }
    let response;
    try {
      response = await fetcher(path, { ...options, headers, credentials: 'include', cache: 'no-store' });
    } catch {
      throw new ApiError('Could not reach CyberCheck. Check the connection and try again.', 0);
    }
    if (response.status === 204) return null;
    let data;
    try { data = await response.json(); }
    catch { throw new ApiError('The server returned an unreadable response. Try again.', response.status); }
    if (!response.ok) {
      if (response.status === 401) { identity = undefined; installation = undefined; }
      const detail = Array.isArray(data.detail) ? data.detail.map(issue => issue.msg).join(' ') : data.detail;
      throw new ApiError(typeof detail === 'string' ? detail : 'The request could not be completed.', response.status);
    }
    return data;
  }

  async function session() {
    const result = await request('/auth/me');
    if (result.mode !== 'github') throw new ApiError('GitHub user login is not configured on this server.', 503);
    if (identity?.user.id !== result.user.id) installation = undefined;
    identity = result;
    return result;
  }

  async function pages(path, key) {
    const rows = [];
    for (let page = 1; ; page++) {
      const result = await request(`${path}${path.includes('?') ? '&' : '?'}page=${page}`);
      rows.push(...result[key]);
      if (!result[key].length || rows.length >= result.total_count) return rows;
    }
  }

  return {
    session,
    loginUrl: '/auth/github/start',
    async logout() {
      await request('/auth/logout', { method: 'POST' });
      identity = undefined; installation = undefined;
    },
    async installations() { return { installations: await pages('/api/github/installations', 'installations') }; },
    selectInstallation(id) { installation = id; },
    async repositories() {
      if (!installation) return { repositories: [], total_count: 0 };
      const repositories = await pages(`/api/repositories?installation_id=${encodeURIComponent(installation)}`, 'repositories');
      return { repositories, total_count: repositories.length };
    },
    async history() {
      const analyses = [];
      for (let offset = 0; ; offset += 100) {
        const result = await request(`/api/analyses?limit=100&offset=${offset}`);
        analyses.push(...result.analyses);
        if (result.analyses.length < 100) return { analyses };
      }
    },
    report(id) { return request(`/api/analyses/${encodeURIComponent(id)}`); },
    start(payload) { return request('/api/analyses', { method: 'POST', body: JSON.stringify(payload) }); },
    delete(id) { return request(`/api/analyses/${encodeURIComponent(id)}`, { method: 'DELETE' }); },
  };
}
