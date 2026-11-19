import test from 'node:test';
import assert from 'node:assert/strict';
import { createDemoService, categoryGroup, PRIORITIES } from '../demo-service.js';

const payload = { repository_id: 101, authorization_confirmed: true, dependency_lookup: true };

test('fixture counts agree with overview categories and priorities', async () => {
  const { analysis } = await createDemoService().report('demo-completed');
  assert.deepEqual(PRIORITIES.map(p => analysis.findings.filter(f => f.priority === p).length), [1, 3, 4, 2, 2]);
  assert.deepEqual(['code', 'dependencies', 'secrets'].map(c => analysis.findings.filter(f => categoryGroup(f.category) === c).length), [6, 4, 2]);
  assert.equal(analysis.commit_sha.length, 40);
});

test('invalid authorization, references, and repository IDs do not create a run', async () => {
  const service = createDemoService();
  await assert.rejects(service.start({ ...payload, authorization_confirmed: false }), /authorization/);
  await assert.rejects(service.start({ ...payload, reference: 'bad branch' }), /without whitespace/);
  await assert.rejects(service.start({ ...payload, reference: 'a'.repeat(201) }), /200 characters/);
  await assert.rejects(service.start({ ...payload, repository_id: 999 }), /sample repositories/);
  assert.equal((await service.history()).analyses.length, 4);
});

test('simulated runs move from queued through running to completed without network access', async () => {
  let time = 0;
  const service = createDemoService({ now: () => time });
  const { analysis } = await service.start(payload);
  assert.equal(analysis.status, 'queued');
  time = 2000;
  const running = (await service.report(analysis.id)).analysis;
  assert.equal(running.status, 'running');
  assert.equal(running.checks[0].status, 'running');
  await assert.rejects(service.delete(analysis.id), /running example/);
  time = 9000;
  const completed = (await service.report(analysis.id)).analysis;
  assert.equal(completed.status, 'completed');
  assert.equal(completed.findings.length, 12);
  assert.ok(completed.checks.every(c => c.status === 'completed'));
});

test('denying dependency lookup produces partial coverage and excludes dependency findings', async () => {
  let time = 100;
  const service = createDemoService({ now: () => time });
  const { analysis } = await service.start({ ...payload, dependency_lookup: false });
  time = 10000;
  const result = (await service.report(analysis.id)).analysis;
  assert.equal(result.status, 'partial');
  assert.equal(result.checks[1].status, 'skipped');
  assert.match(result.checks[1].error, /not assessed/);
  assert.equal(result.findings.filter(f => categoryGroup(f.category) === 'dependencies').length, 0);
});

test('repeated start requests reuse an active example; different references remain separate', async () => {
  const service = createDemoService({ now: () => 0 });
  const a = await service.start(payload);
  const b = await service.start(payload);
  const c = await service.start({ ...payload, reference: 'dev' });
  assert.equal(b.created, false);
  assert.equal(a.analysis.id, b.analysis.id);
  assert.notEqual(c.analysis.id, a.analysis.id);
});

test('deletion, reset and returned object mutation cannot corrupt original fixtures', async () => {
  const service = createDemoService();
  const first = (await service.report('demo-completed')).analysis;
  first.findings.length = 0;
  assert.equal((await service.report('demo-completed')).analysis.findings.length, 12);
  await service.delete('demo-completed');
  await assert.rejects(service.report('demo-completed'), /not be found/);
  service.reset();
  assert.equal((await service.report('demo-completed')).analysis.findings.length, 12);
  assert.equal((await service.history()).analyses.length, 4);
});

test('default branches come from the selected repository and clean examples stay empty', async () => {
  let time = 0;
  const service = createDemoService({ now: () => time });
  const { analysis: privateExample } = await service.start({ ...payload, repository_id: 103 });
  assert.equal(privateExample.requested_ref, 'develop');
  const { analysis: cleanExample } = await service.start({ ...payload, repository_id: 102 });
  time = 9000;
  const finished = (await service.report(cleanExample.id)).analysis;
  assert.equal(finished.status, 'completed');
  assert.deepEqual(finished.findings, []);
});
