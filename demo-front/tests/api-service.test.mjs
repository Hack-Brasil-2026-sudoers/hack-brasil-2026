import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiError, createApiService } from '../api-service.js';

const user = { mode: 'github', user: { id: 1, login: 'alice' }, csrf_token: 'synthetic-csrf' };
const response = (data, status = 200) => new Response(status === 204 ? null : JSON.stringify(data), { status });

test('writes use browser credentials and session CSRF without embedding a GitHub token', async () => {
  const calls = [];
  const service = createApiService({ fetcher: async (path, options) => {
    calls.push({ path, options });
    return response(path === '/auth/me' ? user : { analysis: { id: 'job' }, created: true });
  } });
  const payload = { repository_id: 123, authorization_confirmed: true, dependency_lookup: false };
  const result = await service.start(payload);
  assert.equal(result.created, true);
  assert.equal(calls[0].path, '/auth/me');
  const { path, options } = calls[1];
  assert.equal(path, '/api/analyses');
  assert.equal(options.credentials, 'include');
  assert.equal(options.headers['X-CSRF-Token'], user.csrf_token);
  assert.equal(options.headers['Content-Type'], 'application/json');
  assert.equal(options.headers.Authorization, undefined);
  assert.deepEqual(JSON.parse(options.body), payload);
});

test('installation and repository pagination preserve the selected installation', async () => {
  const paths = [];
  const service = createApiService({ fetcher: async path => {
    paths.push(path);
    if (path === '/auth/me') return response(user);
    const url = new URL(path, 'http://127.0.0.1:8000');
    const page = Number(url.searchParams.get('page'));
    if (url.pathname.endsWith('installations')) return response({
      total_count: 2, installations: [{ id: page, account: `account-${page}`, suspended: false }],
    });
    assert.equal(url.searchParams.get('installation_id'), '2');
    return response({ total_count: 2, repositories: [{ id: page, full_name: `team/project-${page}` }] });
  } });
  await service.session();
  assert.equal((await service.installations()).installations.length, 2);
  service.selectInstallation(2);
  assert.equal((await service.repositories()).repositories.length, 2);
  assert.ok(paths.includes('/api/repositories?installation_id=2&page=2'));
});

test('history loads additional pages without duplicating grouped findings', async () => {
  const paths = [];
  const service = createApiService({ fetcher: async path => {
    paths.push(path);
    return response({ analyses: path.endsWith('offset=0') ? Array.from({ length: 100 }, (_, id) => ({ id })) : [{ id: 100 }] });
  } });
  assert.equal((await service.history()).analyses.length, 101);
  assert.deepEqual(paths, ['/api/analyses?limit=100&offset=0', '/api/analyses?limit=100&offset=100']);
});

test('session expiry clears installation selection and does not fall back to demo data', async () => {
  let expired = false;
  const service = createApiService({ fetcher: async path => {
    if (expired) return response({ detail: 'Sign in with GitHub.' }, 401);
    return response(path === '/auth/me' ? user : { analyses: [] });
  } });
  await service.session();
  service.selectInstallation(5);
  expired = true;
  await assert.rejects(service.history(), error => error instanceof ApiError && error.status === 401);
  assert.deepEqual(await service.repositories(), { repositories: [], total_count: 0 });
});

test('logout sends CSRF and accepts an empty 204 response', async () => {
  const service = createApiService({ fetcher: async (path, options) => {
    if (path === '/auth/me') return response(user);
    assert.equal(path, '/auth/logout');
    assert.equal(options.method, 'POST');
    assert.equal(options.headers['X-CSRF-Token'], user.csrf_token);
    return response(null, 204);
  } });
  await service.logout();
});

test('validation and queue errors surface the safe API message', async () => {
  const service = createApiService({ fetcher: async path => response(path === '/auth/me' ? user : {
    detail: [{ msg: 'Invalid reference.' }],
  }, path === '/auth/me' ? 200 : 422) });
  await assert.rejects(service.start({}), error => error.status === 422 && error.message === 'Invalid reference.');
});

test('connection failures and unreadable responses do not produce simulated success', async () => {
  const offline = createApiService({ fetcher: async () => { throw new Error('synthetic-internal-detail'); } });
  await assert.rejects(offline.history(), error => error.status === 0 && !error.message.includes('synthetic-internal-detail'));
  const unreadable = createApiService({ fetcher: async () => new Response('<html>unavailable</html>', { status: 502 }) });
  await assert.rejects(unreadable.history(), error => error.status === 502);
});

test('configuration is public and requests refuse redirects', async () => {
  const calls=[];
  const service=createApiService({fetcher:async (path,options)=>{
    calls.push(path);
    assert.equal(options.redirect,'error');
    return response({github_enabled:true,installation_url:'https://github.com/apps/example/installations/new'});
  }});
  assert.equal((await service.configuration()).github_enabled,true);
  assert.deepEqual(calls,['/api/auth/status']);
});

test('requests time out without returning simulated results', async () => {
  const service=createApiService({timeoutMs:5,fetcher:(path,{signal})=>new Promise((resolve,reject)=>{
    signal.addEventListener('abort',()=>reject(signal.reason));
  })});
  await assert.rejects(service.history(),error=>error.status===0 && /timed out/.test(error.message));
});
