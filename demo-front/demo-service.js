/** In-memory fixtures only. This module never calls GitHub, scanners, or an API. */
export const PRIORITIES = ['critical', 'high', 'medium', 'low', 'review'];
export const CATEGORY_LABELS = { code: 'Code issues', dependencies: 'Dependencies', secrets: 'Secrets & configuration', web: 'Website configuration' };
export const categoryGroup = category => category.startsWith('web_') ? 'web' : category === 'vulnerable_dependency' ? 'dependencies' : ['exposed_secret', 'insecure_configuration'].includes(category) ? 'secrets' : 'code';

const makeFinding = (title, category, priority, path, line, rule, recommendation, evidence = {}) => ({
  title, category, priority, path, line, rule_id: rule,
  tool: category === 'vulnerable_dependency' ? 'osv-scanner' : category === 'exposed_secret' ? 'betterleaks' : 'bandit',
  severity: priority === 'review' ? 'unknown' : priority,
  confidence: category === 'vulnerable_dependency' ? 'version_match' : priority === 'review' ? 'low' : 'high',
  status: 'potential', recommendation, evidence,
  priority_reason: `Illustrative ${priority} priority for this demonstration. Exposure has not been confirmed; validate the data flow and deployment context.`,
});

const findings = [
  makeFinding('Potential SQL injection', 'sql_injection', 'critical', 'app/database.py', 42, 'B608', 'Use parameterized queries instead of inserting user input into SQL strings. Validate the input source and add a regression test.', { rule: 'B608', cwe: 89 }),
  makeFinding('Potential command injection', 'command_injection', 'high', 'app/utils.py', 18, 'B602', 'Pass separate arguments to a fixed executable with shell=False. Validate user-controlled arguments.', { rule: 'B602', cwe: 78 }),
  makeFinding('Affected dependency: demo-http', 'vulnerable_dependency', 'high', 'requirements.txt', null, 'DEMO-2026-001', 'Review a compatible fixed version, update the lockfile, and test the application. This advisory is fictional.', { package: 'demo-http', version: '1.2.0', fixed_versions: ['1.2.1'], advisory: 'DEMO-2026-001', ecosystem: 'PyPI' }),
  makeFinding('Unsafe deserialization', 'unsafe_deserialization', 'high', 'app/imports.py', 31, 'B301', 'Avoid loading untrusted pickle objects. Use JSON with explicit schema validation.', { rule: 'B301', cwe: 502 }),
  makeFinding('Dynamic code evaluation', 'unsafe_execution', 'medium', 'app/calculator.py', 24, 'B307', 'Replace eval with a parser for the expected input format.', { rule: 'B307' }),
  makeFinding('Unsafe YAML loading', 'unsafe_deserialization', 'medium', 'app/loaders.py', 12, 'B506', 'Use yaml.safe_load and validate the returned structure.', { rule: 'B506' }),
  makeFinding('Affected dependency: demo-parser', 'vulnerable_dependency', 'medium', 'requirements.txt', null, 'DEMO-2026-002', 'Evaluate the fictional fixed version in a controlled test environment.', { package: 'demo-parser', version: '2.0.0', fixed_versions: ['2.0.2'], advisory: 'DEMO-2026-002', ecosystem: 'PyPI' }),
  makeFinding('Affected dependency: demo-utils', 'vulnerable_dependency', 'medium', 'requirements.txt', null, 'DEMO-2026-003', 'Review usage and test the fictional patched release.', { package: 'demo-utils', version: '3.1.0', fixed_versions: ['3.1.1'], advisory: 'DEMO-2026-003', ecosystem: 'PyPI' }),
  makeFinding('Command path needs review', 'command_injection', 'low', 'app/tasks.py', 56, 'B607', 'Use the absolute path of the intended executable.', { rule: 'B607' }),
  makeFinding('Affected dependency: demo-cache', 'vulnerable_dependency', 'low', 'requirements.txt', null, 'DEMO-2026-004', 'Assess the fictional advisory against the application’s use case.', { package: 'demo-cache', version: '1.0.0', fixed_versions: [], advisory: 'DEMO-2026-004', ecosystem: 'PyPI' }),
  makeFinding('Potentially exposed credential', 'exposed_secret', 'review', 'app/config.py', 9, 'demo-token', 'If this were a real credential, confirm exposure, revoke or rotate it, and remove it from source control. Do not test it against its provider.', { rule: 'demo-token', secret: '[REDACTED]', validated: false }),
  makeFinding('Debug mode needs review', 'insecure_configuration', 'review', 'app/server.py', 73, 'B201', 'Check whether this configuration is used in production. Disable debug mode before deployment.', { rule: 'B201' }),
];
export const toolLabel = tool => ({ bandit: 'Bandit', 'osv-scanner': 'OSV-Scanner', betterleaks: 'Betterleaks' })[tool] ?? tool;
const fullChecks = () => [
  { tool: 'bandit', version: '1.9.4', status: 'completed', error: null },
  { tool: 'osv-scanner', version: '2.7.1', status: 'completed', error: null },
  { tool: 'betterleaks', version: '1.10.1', status: 'completed', error: null },
];
const repositories = [
  { id: 101, full_name: 'sudoers/vulnerable-demo', private: false, default_branch: 'main', description: 'A deliberately vulnerable Python application for controlled testing.' },
  { id: 102, full_name: 'sudoers/cybercheck', private: false, default_branch: 'main', description: 'Security findings that developers can understand and act on.' },
  { id: 103, full_name: 'sudoers/internal-api', private: true, default_branch: 'develop', description: 'A sample private repository. No real access is configured.' },
];
const sha = '7f3a91d8c450e683af64c00b649abac0589e0c11';
const clone = value => structuredClone(value);
const wait = () => new Promise(resolve => setTimeout(resolve, 120));

function seed() {
  const base = { repository_id: 101, repository: repositories[0].full_name, commit_sha: sha, requested_ref: 'main', dependency_lookup: true, error: null };
  return [
    { ...base, id: 'demo-completed', status: 'completed', created_at: '2026-11-18T21:30:00Z', started_at: '2026-11-18T21:30:01Z', finished_at: '2026-11-18T21:30:43Z', findings: clone(findings), checks: fullChecks() },
    { ...base, id: 'demo-partial', requested_ref: 'dev', commit_sha: 'b2e4187569a2c4fdac8ee13708533fbeec416d40', status: 'partial', dependency_lookup: false, created_at: '2026-11-17T18:15:00Z', started_at: '2026-11-17T18:15:01Z', finished_at: '2026-11-17T18:15:27Z', findings: clone(findings.filter(f => f.tool !== 'osv-scanner')), checks: fullChecks().map(c => c.tool === 'osv-scanner' ? { ...c, status: 'skipped', error: 'External dependency metadata lookup was not authorized. Dependencies were not assessed.' } : c) },
    { ...base, id: 'demo-clean', repository_id: 102, repository: repositories[1].full_name, status: 'completed', created_at: '2026-11-16T14:00:00Z', started_at: '2026-11-16T14:00:01Z', finished_at: '2026-11-16T14:00:31Z', findings: [], checks: fullChecks() },
    { ...base, id: 'demo-failed', repository_id: 103, repository: repositories[2].full_name, status: 'failed', created_at: '2026-11-15T10:00:00Z', started_at: '2026-11-15T10:00:01Z', finished_at: '2026-11-15T10:00:03Z', findings: [], checks: [], error: 'Example failure: repository access was revoked before the analysis started.' },
  ];
}

/** API-shaped methods are the replacement boundary for a future real API adapter. */
export function createDemoService({ now = () => Date.now() } = {}) {
  let analyses = seed();
  const starts = new Map();
  function advance() {
    for (const analysis of analyses) {
      const start = starts.get(analysis.id);
      if (start === undefined) continue;
      const elapsed = now() - start;
      if (elapsed >= 1600 && analysis.status === 'queued') { analysis.status = 'running'; analysis.started_at = new Date(now()).toISOString(); }
      analysis.checks = fullChecks().map((c, i) => ({ ...c, status: elapsed >= (i + 1) * 2600 ? 'completed' : elapsed >= i * 2600 + 1600 ? 'running' : 'queued' }));
      if (!analysis.dependency_lookup) analysis.checks[1] = { ...analysis.checks[1], status: 'skipped', error: 'External dependency metadata lookup was not authorized. Dependencies were not assessed.' };
      if (elapsed >= 8500) {
        analysis.status = analysis.dependency_lookup ? 'completed' : 'partial';
        analysis.finished_at = new Date(now()).toISOString();
        analysis.findings = analysis.repository_id === 102 ? [] : clone(findings.filter(f => analysis.dependency_lookup || f.tool !== 'osv-scanner'));
        starts.delete(analysis.id);
      }
    }
  }
  return {
    async repositories() { await wait(); return { repositories: clone(repositories), total_count: repositories.length, page: 1 }; },
    async history() { await wait(); advance(); return { analyses: clone(analyses) }; },
    async report(id) { await wait(); advance(); const analysis = analyses.find(a => a.id === id); if (!analysis) throw new Error('This example analysis could not be found. Open the history or reset demo data.'); return { analysis: clone(analysis) }; },
    async start(payload) {
      await wait(); advance();
      const repo = repositories.find(r => r.id === payload.repository_id);
      if (!repo) throw new Error('Select one of the sample repositories.');
      if (!payload.authorization_confirmed) throw new Error('Confirm that you own the project or have written authorization.');
      const ref = payload.reference?.trim() || repo.default_branch;
      if (ref.length > 200 || /[\x00-\x20\x7f]/.test(ref)) throw new Error('Use a branch, tag, or commit without whitespace (up to 200 characters).');
      const existing = analyses.find(a => a.repository_id === repo.id && a.requested_ref === ref && ['queued', 'running'].includes(a.status));
      if (existing) return { analysis: clone(existing), created: false };
      const analysis = { id: `demo-${crypto.randomUUID()}`, repository_id: repo.id, repository: repo.full_name, requested_ref: ref, commit_sha: sha, status: 'queued', dependency_lookup: !!payload.dependency_lookup, created_at: new Date(now()).toISOString(), started_at: null, finished_at: null, findings: [], checks: [], error: null };
      analyses.unshift(analysis); starts.set(analysis.id, now());
      return { analysis: clone(analysis), created: true };
    },
    async delete(id) { await wait(); advance(); const analysis = analyses.find(a => a.id === id); if (!analysis) throw new Error('This example analysis has already been removed.'); if (analysis.status === 'running') throw new Error('Wait for the running example to finish before deleting it.'); analyses = analyses.filter(a => a.id !== id); starts.delete(id); },
    reset() { analyses = seed(); starts.clear(); },
  };
}
