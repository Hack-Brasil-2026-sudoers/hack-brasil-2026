import { createDemoService, PRIORITIES, CATEGORY_LABELS, categoryGroup, toolLabel } from './demo-service.js';
import { createApiService } from './api-service.js';

const live = location.pathname.startsWith('/app/');
const service = live ? createApiService() : createDemoService();
const copy = (real, demo) => live ? real : demo;
const main = document.querySelector('#main');
const state = { repositories: [], selectedRepository: live ? null : 101, installations: [], installation: null,
  user: null, analyses: [], category: 'all', priority: 'all', search: '', historyStatus: 'all' };
let routeEpoch = 0;
let pollTimer;
let toastTimer;
let dialogAction;
let focusedBeforeDialog;

const e = value => String(value ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]);
const titleCase = value => ({ review: 'To review', version_match: 'Version match', unknown: 'Not assessed', potential: 'Potential issue' })[value] ?? (value ? value[0].toUpperCase() + value.slice(1) : 'Unknown');
const paths = {
  shield: '<path d="m12 3 8 3v6c0 5-5 8-8 10-3-2-8-5-8-10V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
  overview: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  repository: '<path d="M4 6a3 3 0 0 1 3-3h13v18H7a3 3 0 0 1-3-3Zm0 0v12a3 3 0 0 1 3-3h13"/><path d="M8 7h8M8 10h5"/>',
  analysis: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
  history: '<path d="M3 11a9 9 0 1 1 2.6 7.4M3 4v7h7M12 7v5l3 2"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  branch: '<circle cx="6" cy="5" r="2"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="6" r="2"/><path d="M6 7v10M18 8a6 6 0 0 1-6 6H6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  chevron: '<path d="m9 5 7 7-7 7"/>',
  back: '<path d="m15 5-7 7 7 7"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  code: '<path d="m8 6-6 6 6 6m8-12 6 6-6 6m-3-15-2 18"/>',
  package: '<path d="m12 3 9 5v8l-9 5-9-5V8l9-5Zm0 10v8M3 8l9 5 9-5M7.5 5.5l9 5"/>',
  key: '<circle cx="8" cy="9" r="5"/><path d="m12 13 8 8 2-2-2-2 1-1-3-3-1 1-2-2"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  warning: '<path d="m10.3 4-8 14a2 2 0 0 0 1.7 3h16a2 2 0 0 0 1.7-3l-8-14a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/>',
  trash: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
  copy: '<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
  search: '<circle cx="10.5" cy="10.5" r="7"/><path d="m16 16 5 5"/>',
  lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4M12 14v3"/>',
  pause: '<path d="M9 5v14M15 5v14"/>',
};
const icon = name => `<svg class="icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] ?? paths.info}</svg>`;
const status = value => `<span class="status ${e(value)}"><span class="status-dot"></span>${e(titleCase(value))}</span>`;
const priority = value => `<span class="priority-badge ${e(value)}"><span class="priority-mark" aria-hidden="true"><i></i><i></i><i></i></span>${e(titleCase(value))}</span>`;
const route = () => (location.hash.slice(1) || 'overview').split('/').map(part => { try { return decodeURIComponent(part); } catch { return ''; } });
const reportLink = id => `#report/${encodeURIComponent(id)}`;
const activeLink = analysis => ['queued', 'running'].includes(analysis.status) ? `#analyses/${encodeURIComponent(analysis.id)}` : reportLink(analysis.id);
const date = iso => new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(new Date(iso));
const timestamp = iso => `${date(iso)} · ${new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }).format(new Date(iso))} UTC`;
const repositoryName = name => { const [owner, ...parts] = name.split('/'); return `<span class="owner">${e(owner)} / </span>${e(parts.join('/'))}`; };
const button = (label, href, type = '', symbol = '') => `<a class="button ${type}" href="${e(href)}">${symbol ? icon(symbol) : ''}${e(label)}</a>`;
const heading = (title, subtitle, actions = '') => `<div class="page-heading"><div><h1>${e(title)}</h1><p>${e(subtitle)}</p></div>${actions ? `<div class="heading-actions">${actions}</div>` : ''}</div>`;
const notice = (title, content, variant = '') => `<div class="notice ${variant}">${icon(variant === 'warning' || variant === 'error' ? 'warning' : 'info')}<div>${title ? `<strong>${e(title)}</strong>` : ''}${e(content)}</div></div>`;
const empty = (title, description, action = '', symbol = 'search') => `<div class="empty-state"><div class="empty-icon">${symbol === 'shield' ? '<img class="brand-icon" src="./assets/brand/logo-icon.svg" width="242" height="298" alt="">' : icon(symbol)}</div><h2>${e(title)}</h2><p>${e(description)}</p>${action}</div>`;

function signedOut(message = 'Sign in to select authorized repositories and view your reports.') {
  state.user = null; state.repositories = []; state.analyses = []; state.installations = [];
  state.installation = null; state.selectedRepository = null;
  document.querySelector('.workspace-label').textContent = 'Your workspace';
  document.querySelector('#reset-demo').hidden = true;
  return heading('Connect your GitHub account', 'Analyze repositories you own or are authorized to assess.')
    + `<section class="panel">${empty('Sign in with GitHub', message, button('Sign in with GitHub', service.loginUrl), 'repository')}</section>`;
}

if (live) {
  document.querySelector('.demo-badge').textContent = 'GitHub connected workspace';
  document.querySelector('.demo-label').textContent = 'Your repository analyses';
  document.querySelector('.sidebar-footer p').textContent = 'Real reports from authorized repositories.';
  document.querySelector('#reset-demo').textContent = 'Sign out';
  document.querySelector('meta[name="description"]').content = 'Analyze authorized GitHub repositories with CyberCheck.';
}

function showToast(message) {
  clearTimeout(toastTimer);
  const element = document.querySelector('#toast');
  element.textContent = message; element.hidden = false;
  toastTimer = setTimeout(() => { element.hidden = true; }, 5000);
}

function navigation(active) {
  const links = [['overview', 'Overview', 'overview'], ['repositories', 'Repositories', 'repository'], ['analyses', 'Analyses', 'analysis'], ['history', 'History', 'history']];
  document.querySelector('#navigation').innerHTML = links.map(([path, label, symbol]) => `<a class="nav-link" href="#${path}"${path === active ? ' aria-current="page"' : ''}>${icon(symbol)}<span>${label}</span></a>`).join('');
  const name = links.find(([path]) => path === active)?.[1] ?? 'Workspace';
  document.querySelector('#breadcrumb').innerHTML = `Workspace <span>/</span> ${name}`;
}

function priorityStrip(findings) {
  return `<div class="priority-strip" aria-label="Finding counts by priority">${PRIORITIES.map(p => `<div class="priority-stat"><span>${e(titleCase(p))}</span><strong class="${p}">${findings.filter(f => f.priority === p).length}</strong></div>`).join('')}</div>`;
}

function repositorySummary(a, action = false) {
  return `<div class="repository-summary"><div class="repository-identity"><span class="repo-mark">${icon('repository')}</span><div><div class="repo-name">${repositoryName(a.repository)}</div><div class="repo-meta"><span>${icon('branch')}${e(a.requested_ref)}</span><span class="mono">${e(a.commit_sha.slice(0, 7))}</span><span>${icon('clock')}${e(timestamp(a.created_at))}</span></div></div></div><div class="summary-meta">${status(a.status)}${action ? button('View report', activeLink(a), 'secondary') : ''}</div></div>`;
}

function findingTable(a, rows, { compact = false } = {}) {
  if (!rows.length) return empty('No matching findings', 'Try another category, priority, or search term.', '<button class="text-button" type="button" data-action="clear-filters">Clear filters</button>');
  return `<div class="table-scroll"><table class="finding-table"><caption class="sr-only">Security findings</caption><thead><tr><th scope="col">Finding</th><th scope="col">Priority</th>${compact ? '' : '<th class="category-column" scope="col">Category</th><th class="confidence-column" scope="col">Confidence</th>'}<th class="table-action" scope="col"><span class="sr-only">Details</span></th></tr></thead><tbody>${rows.map(f => {
    const index = a.findings.indexOf(f);
    const href = `#finding/${encodeURIComponent(a.id)}/${index}`;
    return `<tr><td><div class="finding-title"><a href="${href}">${e(f.title)}</a></div><div class="finding-meta"><span class="mono">${e(f.path)}</span>${f.line ? ` · Line ${f.line}` : ''} · ${e(toolLabel(f.tool))}</div><div class="finding-confidence${compact ? '' : ' responsive-confidence'}">Confidence: ${e(titleCase(f.confidence))}</div></td><td>${priority(f.priority)}</td>${compact ? '' : `<td class="category-column muted">${e(CATEGORY_LABELS[categoryGroup(f.category)])}</td><td class="confidence-column muted">${e(titleCase(f.confidence))}</td>`}<td class="table-action"><a class="icon-button" href="${href}" aria-label="View ${e(f.title)}">${icon('chevron')}</a></td></tr>`;
  }).join('')}</tbody></table></div>`;
}

function overview() {
  const a = state.analyses.find(a => ['completed', 'partial'].includes(a.status));
  const intro = heading('Security overview', 'Review the latest revision and decide what to fix next.', button('New analysis', '#repositories', '', 'plus'));
  if (!a) return intro + `<div class="panel">${empty('No analyses yet', 'Choose a repository to start an analysis.', button('Choose a repository', '#repositories'), 'repository')}</div>`;
  const urgent = a.findings.filter(f => ['critical', 'high'].includes(f.priority));
  const selected = urgent.length ? urgent : a.findings.slice(0, 4);
  const completed = a.checks.filter(c => c.status === 'completed').length;
  return intro + `<div class="stack overview-stack">
    <section class="revision-surface" aria-label="Latest repository analysis">${repositorySummary(a, true)}</section>
    ${a.status === 'partial' ? notice('Incomplete coverage', `${completed} of 3 checks completed. Some categories were not assessed; finding counts do not describe the full repository.`, 'warning') : ''}
    ${priorityStrip(a.findings)}
    <div class="investigation-layout">
      <section class="findings-surface">
        <div class="investigation-heading"><div><h2>What to fix first</h2><p>${urgent.length ? `${urgent.length} critical and high-priority findings. Review the evidence before making changes.` : 'Review the findings alongside the scope of the completed checks.'}</p></div></div>
        ${selected.length ? findingTable(a, selected, { compact: true }) : empty('No findings reported', 'No alerts were returned. Review coverage before drawing a security conclusion.', '', 'shield')}
        <div class="list-footer"><a class="section-link" href="${reportLink(a.id)}">View all ${a.findings.length} findings</a></div>
      </section>
      <aside class="analysis-sidebar">
        <section><h2>Analysis coverage<span class="section-count">${completed}/3</span></h2><ul class="coverage-summary">${a.checks.map(c => `<li><span>${e(toolLabel(c.tool))}</span>${status(c.status)}</li>`).join('')}</ul></section>
        <section><h2>By category<span class="section-count">${a.findings.length} total</span></h2><dl class="category-counts">${Object.entries(CATEGORY_LABELS).map(([key,label]) => `<div><dt>${label}</dt><dd>${a.findings.filter(f => categoryGroup(f.category) === key).length}</dd></div>`).join('')}</dl></section>
        <p class="subtle-note">This report describes the revision above. It does not establish the repository’s current security.</p>
      </aside>
    </div>
  </div>`;
}

function repoOptions() {
  const list = state.repositories.filter(repo => repo.full_name.toLowerCase().includes(state.search.toLowerCase()));
  return list.length ? list.map(repo => `<button class="repo-option" type="button" data-repository="${repo.id}" aria-pressed="${state.selectedRepository === repo.id}"><span class="repo-mark">${icon(repo.private ? 'lock' : 'repository')}</span><div class="repo-option-content"><div class="repo-name">${repositoryName(repo.full_name)}</div><div class="repo-meta"><span>Python checks</span><span>${icon('branch')}${e(repo.default_branch)}</span><span class="visibility-label">${repo.private ? 'Private' : 'Public'}</span></div><p class="repo-description">${e(repo.description)}</p></div><span class="selection-mark" aria-hidden="true"></span></button>`).join('') : empty('No repositories match', 'Try another repository name or clear your search.');
}

function repositoriesView() {
  const selected = state.repositories.find(r => r.id === state.selectedRepository) ?? state.repositories[0];
  const installationPicker = live ? `<label class="field" for="installation">GitHub account or organization<select id="installation"><option value="">Select an installation</option>${state.installations.map(item => `<option value="${item.id}"${state.installation === item.id ? ' selected' : ''}${item.suspended ? ' disabled' : ''}>${e(item.account)}${item.suspended ? ' (suspended)' : ''}</option>`).join('')}</select></label>` : '';
  if (!selected) return heading('Repositories', 'Choose a repository and configure your next analysis.') + installationPicker + `<section class="panel">${empty('No repositories available', 'Select an installation with repository access. If none is listed, install the CyberCheck GitHub App on selected repositories or ask your organization owner to grant access.', '<button class="button secondary" type="button" data-action="retry">Refresh access</button>', 'repository')}</section>`;
  state.selectedRepository = selected.id;
  return heading('Repositories', 'Choose a repository and configure your next analysis.') + installationPicker + `<div class="stack"><div class="repo-layout"><section><div class="toolbar"><label class="search-field">${icon('search')}<input id="repository-search" type="search" placeholder="Search repositories…" aria-label="Search repositories" value="${e(state.search)}"></label></div><div class="panel"><div class="panel-header"><div><h2>Available repositories<span class="section-count">${state.repositories.length}</span></h2><p>${copy("Authorized GitHub installation \u00b7 Read-only access", "Example GitHub installation \u00b7 Read-only access")}</p></div>${icon('repository')}</div><div id="repository-options">${repoOptions()}</div></div></section><section class="panel"><div class="panel-header"><h2>Configure analysis</h2></div><form class="panel-body analysis-form" id="analysis-form"><label class="field">Selected repository<span class="selected-repo-field" id="selected-repository">${icon('repository')}${e(selected.full_name)}</span></label><label class="field" for="reference">Reference <span class="muted">(optional)</span><input id="reference" name="reference" maxlength="200" autocomplete="off" spellcheck="false" placeholder="${e(selected.default_branch)}"><small>A branch, tag, or full commit SHA. Defaults to the selected repository’s default branch.</small></label><label class="checkbox-field"><input type="checkbox" id="authorization" name="authorization" required><span>I own this project or have written authorization.<small>Analyses are limited to repositories you are allowed to assess.</small></span></label><label class="checkbox-field"><input type="checkbox" id="dependency-lookup" name="dependency_lookup"><span>Allow external dependency metadata lookup.<small>${copy("When enabled, dependency names and versions may be sent to vulnerability databases. Project source is not sent for this lookup.", "In a real analysis, dependency names and versions may be sent to vulnerability databases. This demo sends nothing.")}</small></span></label><p id="form-error" class="form-error" role="alert"></p><div class="form-actions"><button class="button" id="start-analysis" type="submit" disabled>${icon('analysis')}Start analysis</button><a class="button ghost" href="#overview">Cancel</a></div><p class="subtle-note">${copy("The worker downloads the selected revision temporarily and removes source files after execution.", "No repository is downloaded and no scanner runs. This preview demonstrates the intended workflow.")}</p></form></section></div>${notice(copy('Authorized access', 'A controlled workspace'), copy('Repository access is checked again when the worker downloads the commit.', 'These example repositories are fictional. No GitHub account is accessed.'))}</div>`;
}

const toolDescriptions = { bandit: ['Code analysis', 'Python source security', 'code'], 'osv-scanner': ['Dependency analysis', 'Known dependency vulnerabilities', 'package'], betterleaks: ['Secrets & configuration', 'Potentially exposed credentials', 'key'] };
function checks(a) {
  return `<ul class="checks-list">${Object.entries(toolDescriptions).map(([tool, [title, description, symbol]]) => {
    const c = a.checks.find(c => c.tool === tool) ?? { tool, status: 'queued', version: null, error: null };
    return `<li class="check-row"><span class="check-icon ${e(c.status)}">${icon(c.status === 'completed' ? 'check' : c.status === 'skipped' ? 'pause' : symbol)}</span><div class="check-copy"><strong>${title}</strong><p>${e(toolLabel(tool))}${c.version ? ` ${e(c.version)}` : ''} · ${e(c.error || description)}</p></div>${status(c.status)}</li>`;
  }).join('')}</ul>`;
}

function progressView(a) {
  const completed = a.checks.filter(c => c.status === 'completed').length;
  return heading(a.status === 'queued' ? 'Analysis queued' : 'Analysis in progress', 'Follow the checks for the selected repository.', button('View history', '#history', 'secondary')) + `<div class="stack"><section class="panel"><div class="progress-intro"><div><div class="repo-name">${repositoryName(a.repository)}</div><div class="repo-meta"><span>${icon('branch')}${e(a.requested_ref)}</span><span class="mono">${e(a.commit_sha.slice(0, 7))}</span><span>Recorded revision</span></div></div>${status(a.status)}</div><div class="panel-header"><h2>Configured checks</h2><div class="progress-summary"><div class="progress-track" aria-hidden="true">${[0, 1, 2].map((_, i) => `<span class="${i < completed ? 'done' : ''}"></span>`).join('')}</div><span><strong>${completed}</strong> of 3 finished</span></div></div>${checks(a)}</section>${notice(copy('Worker execution', 'A simulated run'), copy('A stopped worker leaves requests queued. Per-tool results appear after the worker saves the report; no live percentage is inferred.', 'This sequence takes about nine seconds. No repository is accessed. The example report opens when the sequence finishes.'))}${notice('Coverage matters', 'Skipped or failed checks remain visible in the report. An analysis with incomplete coverage is marked partial.')}</div>`;
}

function analysisIndex() {
  const active = state.analyses.filter(a => ['queued', 'running'].includes(a.status));
  return heading('Analyses', 'Follow active runs or inspect stored reports.', button('New analysis', '#repositories', '', 'plus')) + `<div class="stack">${active.length ? `<section class="panel"><div class="panel-header"><h2>Active analyses</h2></div>${active.map(a => repositorySummary(a, true)).join('')}</section>` : `<section class="panel">${empty('No analyses running', 'Choose a repository to see the queue, checks, and report flow.', button('Start an analysis', '#repositories'), 'analysis')}</section>`}<section class="panel"><div class="panel-header"><div><h2>Recent reports</h2><p>See how complete, partial, and failed analyses are presented.</p></div></div>${state.analyses.filter(a => !['queued', 'running'].includes(a.status)).slice(0, 4).map(a => repositorySummary(a, true)).join('') || empty('No reports yet', 'Start an analysis to create a report.')}</section></div>`;
}

function revision(a) {
  return `<section class="panel" aria-label="Analysis revision">${repositorySummary(a)}<div class="revision-details"><div class="metadata-item"><span>Full commit SHA · Recorded revision</span><div class="commit-line"><code>${e(a.commit_sha)}</code><button class="icon-button" type="button" data-copy="${e(a.commit_sha)}" aria-label="Copy full commit SHA">${icon('copy')}</button></div></div><div class="metadata-item"><span>Finished at</span><span class="text-primary">${a.finished_at ? e(timestamp(a.finished_at)) : 'Not finished'}</span></div></div><details class="coverage-details"><summary>Check coverage · ${a.checks.filter(c => c.status === 'completed').length} of 3 checks completed</summary>${checks(a)}</details></section>`;
}

function filteredFindings(a) {
  return a.findings.filter(f => (state.category === 'all' || categoryGroup(f.category) === state.category) && (state.priority === 'all' || (state.priority === 'urgent' ? ['critical', 'high'].includes(f.priority) : f.priority === state.priority)) && `${f.title} ${f.path} ${f.rule_id}`.toLowerCase().includes(state.search.toLowerCase()));
}
function reportResults(a) {
  const list = filteredFindings(a);
  return `<div class="results-heading"><span>${list.length} of ${a.findings.length} findings</span><span>Ordered by priority</span></div>${findingTable(a, list)}`;
}
function reportView(a) {
  const failed = a.status === 'failed';
  return heading('Analysis report', 'Findings and coverage for the exact revision analyzed.', button('New analysis', '#repositories', '', 'plus')) + `<div class="stack">${revision(a)}${a.status === 'partial' ? notice('Partial analysis', 'One or more checks were skipped or incomplete. Unassessed categories must not be interpreted as having no vulnerabilities.', 'warning') : failed ? notice('Analysis could not finish', a.error || 'The analysis failed. Review coverage and request a new analysis.', 'error') : notice('', 'All configured checks finished. This does not guarantee security or confirm that any finding is exploitable.')}${failed ? `<div class="panel">${empty('No results are available', 'Review the error and available coverage. Request another analysis after resolving the failure.', button('Choose a repository', '#repositories'), 'warning')}</div>` : `${priorityStrip(a.findings)}<section class="panel"><div class="report-toolbar"><h2>All findings<span class="section-count">${a.findings.length}</span></h2><div class="filter-group"><label class="filter-label" for="category-filter">Category<select id="category-filter"><option value="all">All categories</option>${Object.entries(CATEGORY_LABELS).map(([v, label]) => `<option value="${v}"${state.category === v ? ' selected' : ''}>${label}</option>`).join('')}</select></label><label class="filter-label" for="priority-filter">Priority<select id="priority-filter"><option value="all">All priorities</option><option value="urgent"${state.priority === 'urgent' ? ' selected' : ''}>Critical & high</option>${PRIORITIES.map(v => `<option value="${v}"${state.priority === v ? ' selected' : ''}>${titleCase(v)}</option>`).join('')}</select></label></div></div>${a.findings.length ? `<div class="panel-search"><label class="search-field">${icon('search')}<input id="finding-search" type="search" value="${e(state.search)}" placeholder="Search findings, files, or rules…" aria-label="Search findings"></label></div><div id="report-results" aria-live="polite">${reportResults(a)}</div>` : empty('No findings reported', 'The configured checks returned no alerts for this revision. Review skipped checks and scope; no findings does not establish safety.', '', 'shield')}</section>`}<p class="subtle-note">${copy("Reports describe the recorded commit and require context review. No security score is assigned.", "Demonstration only. Package names and advisory identifiers are fictional; priorities and explanations are illustrative.")}</p></div>`;
}

function findingView(a, index) {
  const f = a.findings[index];
  if (!f) throw new Error('This finding does not exist. Return to the analysis report.');
  const isSql = f.category === 'sql_injection';
  const details = {
    sql_injection: ['User input may be inserted directly into a database query.', 'An attacker could potentially change the query’s meaning and access or modify information. Whether this is possible depends on the input source and query context.'],
    command_injection: ['A command execution pattern needs review for user-controlled arguments.', 'If untrusted data reaches a shell, an attacker may be able to run unintended commands. The pattern alone does not confirm exploitability.'],
    vulnerable_dependency: [`The dependency ${f.evidence.package} ${f.evidence.version} matches an advisory record.`, 'Review the advisory and how the affected functionality is used. Affected versions do not prove exploitation.'],
    exposed_secret: ['A credential-like value was reported. Its value is redacted.', 'An exposed credential could allow unauthorized access. Review whether it is real and reachable. It has not been tested against its provider.'],
    insecure_configuration: ['A configuration pattern needs review. Check the reported rule and deployment context.', 'Debugging features intended for development may expose information when enabled in production. A test or development setting alone does not establish exposure.'],
    unsafe_deserialization: ['A data-loading pattern may be unsafe for untrusted input.', 'Some deserialization functions can create objects or execute behavior while loading data. Review the input source and accepted format before assessing exposure.'],
    unsafe_execution: ['A pattern that evaluates text as executable code was reported.', 'If the evaluated text can be influenced by an untrusted source, unexpected operations may run. Review the actual data flow.'],
  };
  const [problem, impact] = details[f.category] ?? ['A potentially unsafe pattern was reported.', 'Investigate the evidence and deployment context before deciding the impact.'];
  const reference = `CC-${String(index + 14).padStart(3, '0')}`;
  const evidence = f.evidence.secret
    ? 'Credential value: [REDACTED]. It has not been validated against a provider.'
    : f.evidence.package
      ? `Package: ${f.evidence.package} ${f.evidence.version}. Advisory: ${f.evidence.advisory}. Fixed versions: ${f.evidence.fixed_versions.length ? f.evidence.fixed_versions.join(', ') : 'none provided'}.`
      : `Rule ${f.rule_id}${f.evidence.cwe ? ` · CWE-${f.evidence.cwe}` : ''}. Review the file and input context; exposure has not been confirmed.`;
  return `<a class="back-link" href="${reportLink(a.id)}">${icon('back')}Back to analysis report</a>`
    + heading(f.title, `${CATEGORY_LABELS[categoryGroup(f.category)]} · Potential issue`)
    + `<div class="detail-layout">
      <section class="panel detail-content trace-detail">
        <div class="detail-status"><span class="finding-reference">${reference}</span>${priority(f.priority)}</div>
        <dl class="trace-context">
          <div><dt>Source</dt><dd class="mono">${e(f.path)}${f.line ? `:${f.line}` : ''}</dd></div>
          <div><dt>Rule</dt><dd class="mono">${e(toolLabel(f.tool))} · ${e(f.rule_id)}</dd></div>
          <div><dt>Confidence</dt><dd>${e(titleCase(f.confidence))}</dd></div>
        </dl>
        <section class="trace-evidence"><header><h2>Evidence</h2><span>Exposure not confirmed</span></header><p>${e(evidence)}</p></section>
        <section class="detail-section trace-problem"><h2>What is the problem?</h2><p>${e(problem)}</p></section>
        <div class="trace-explanation">
          <section class="detail-section"><h2>Potential impact</h2><p>${e(impact)}</p></section>
          <section class="detail-section"><h2>Suggested correction</h2><p>${e(f.recommendation)}</p></section>
        </div>
        ${isSql ? `<details class="trace-correction"><summary class="button">Compare correction</summary><div class="code-example"><header>Illustrative correction · Python</header><pre><code><span class="code-comment"># Keep user input separate from SQL</span>\ncursor.execute(\n    <span class="code-string">"SELECT * FROM users WHERE id = ?"</span>,\n    (user_id,),\n)</code></pre></div></details>` : ''}
        <section class="detail-section trace-priority"><h2>Why this priority?</h2><p>${e(f.priority_reason)}</p></section>
      </section>
      <aside class="detail-aside stack-small"><section class="panel panel-body"><h2>Finding context</h2><dl class="evidence-list"><div><dt>Location</dt><dd class="mono">${e(f.path)}${f.line ? `:${f.line}` : ''}</dd></div><div><dt>Tool</dt><dd>${e(toolLabel(f.tool))}</dd></div><div><dt>Rule</dt><dd class="mono">${e(f.rule_id)}</dd></div><div><dt>Repository</dt><dd>${e(a.repository)}</dd></div><div><dt>Commit SHA</dt><dd class="mono">${e(a.commit_sha)}</dd></div><div><dt>Analyzed at</dt><dd>${e(timestamp(a.created_at))}</dd></div></dl>${button('View full report', reportLink(a.id), 'secondary')}</section>${notice(copy('Rule-based guidance', 'Simulated finding'), copy('Review scanner evidence and context. No exploit has been confirmed. No external AI service is used.', 'This explanation is illustrative. No exploit has been confirmed, and no external AI service is connected.'))}</aside>
    </div>`;
}

function historyRows() {
  const rows = state.analyses.filter(a => (state.historyStatus === 'all' || a.status === state.historyStatus) && a.repository.toLowerCase().includes(state.search.toLowerCase()));
  if (!rows.length) return empty('No analyses to show', state.analyses.length ? 'Try a different status or repository search.' : 'Start a simulated run or reset demo data to restore sample reports.', button('New analysis', '#repositories'), 'history');
  return `<div class="table-scroll"><table class="history-table"><caption class="sr-only">Analysis history</caption><thead><tr><th scope="col">Repository</th><th scope="col" class="hide-compact">Revision</th><th scope="col">Status</th><th scope="col" class="hide-mobile">Findings</th><th scope="col" class="hide-mobile">Created at · UTC</th><th scope="col" class="table-action">Actions</th></tr></thead><tbody>${rows.map(a => `<tr><td><div class="repository-identity"><span class="repo-mark">${icon('repository')}</span><div><a class="repo-name" href="${activeLink(a)}">${repositoryName(a.repository)}</a><div class="repo-meta">${icon('branch')}${e(a.requested_ref)}</div></div></div></td><td class="hide-compact mono muted">${e(a.commit_sha.slice(0, 7))}</td><td>${status(a.status)}</td><td class="hide-mobile muted">${['queued', 'running', 'failed'].includes(a.status) ? '—' : a.findings.length}</td><td class="history-date hide-mobile muted">${e(timestamp(a.created_at))}</td><td><div class="row-actions"><a class="section-link" href="${activeLink(a)}">${['queued', 'running'].includes(a.status) ? 'View run' : 'View report'}</a><button class="icon-button destructive" type="button" data-delete="${e(a.id)}" aria-label="Delete analysis for ${e(a.repository)} from ${e(timestamp(a.created_at))}"${a.status === 'running' ? ' disabled title="Wait for the running analysis to finish"' : ''}>${icon('trash')}</button></div></td></tr>`).join('')}</tbody></table></div>`;
}
function historyView() {
  return heading('Analysis history', 'Revisit the evidence. Every report belongs to a specific revision.', button('New analysis', '#repositories', '', 'plus')) + `<div class="stack"><section class="panel"><div class="panel-header"><div><h2>Past analyses<span class="section-count">${state.analyses.length}</span></h2><p>${copy("Reports stay in your history until you delete them.", "Example reports stay in memory until deleted or the page is reloaded.")}</p></div>${live ? '' : '<button class="button secondary" type="button" data-action="reset">Reset examples</button>'}</div><div class="report-toolbar"><label class="search-field">${icon('search')}<input id="history-search" type="search" value="${e(state.search)}" placeholder="Search repositories…" aria-label="Search analysis history"></label><label class="filter-label" for="status-filter">Status<select id="status-filter"><option value="all">All statuses</option>${['completed', 'partial', 'failed', 'queued', 'running'].map(s => `<option value="${s}"${state.historyStatus === s ? ' selected' : ''}>${titleCase(s)}</option>`).join('')}</select></label></div><div id="history-results" aria-live="polite">${historyRows()}</div></section>${notice('Partial is not complete', 'A partial report contains findings from the checks that finished. Review skipped and failed checks before interpreting the results.', 'warning')}</div>`;
}

async function render({ focus = true } = {}) {
  const epoch = ++routeEpoch;
  clearTimeout(pollTimer);
  const [page, id, detail] = route();
  const active = ['report', 'finding'].includes(page) ? 'analyses' : page;
  navigation(active);
  main.setAttribute('aria-busy', 'true');
  main.innerHTML = '<div class="loading-state" role="status">Loading workspace…<div class="skeleton short"></div><div class="skeleton"></div></div>';
  try {
    if (live) {
      const session = await service.session(); if (epoch !== routeEpoch) return;
      if (state.user?.id !== session.user.id) {
        state.installation = null; state.selectedRepository = null;
        state.repositories = []; state.analyses = [];
      }
      state.user = session.user;
      document.querySelector('.workspace-label').textContent = session.user.login;
      document.querySelector('#reset-demo').hidden = false;
    }
    let html;
    let analysis;
    if (page === 'repositories') {
      if (live) {
        const result = await service.installations(); if (epoch !== routeEpoch) return;
        state.installations = result.installations;
        if (!state.installations.some(item => item.id === state.installation && !item.suspended)) {
          state.installation = state.installations.find(item => !item.suspended)?.id ?? null;
        }
        service.selectInstallation(state.installation);
      }
      const result = await service.repositories(); if (epoch !== routeEpoch) return;
      state.repositories = result.repositories; html = repositoriesView();
    } else if (['report', 'finding', 'analyses'].includes(page) && id) {
      ({ analysis } = await service.report(id)); if (epoch !== routeEpoch) return;
      if (live && analysis.kind !== 'repository') throw new Error('This workspace displays repository reports. Website reports remain available through the API.');
      if (page === 'finding') html = findingView(analysis, Number(detail));
      else if (['queued', 'running'].includes(analysis.status)) html = progressView(analysis);
      else html = reportView(analysis);
    } else if (['overview', 'history', 'analyses'].includes(page)) {
      ({ analyses: state.analyses } = await service.history()); if (epoch !== routeEpoch) return;
      if (live) state.analyses = state.analyses.filter(item => item.kind === 'repository');
      html = page === 'overview' ? overview() : page === 'history' ? historyView() : analysisIndex();
    } else html = heading('Page not found', 'This view is unavailable.') + `<div class="panel">${empty('Let’s get you back', 'Open the overview to continue.', button('Open overview', '#overview'))}</div>`;
    if (epoch !== routeEpoch) return;
    if (live && analysis?.limitations?.length) html += notice('Analysis limits', analysis.limitations.join(' '));
    main.innerHTML = `<div class="${focus ? 'view-enter' : ''}">${html}</div>`;
    document.title = `${main.querySelector('h1')?.textContent || 'Workspace'} · CyberCheck${live ? '' : ' demo'}`;
    bindView(analysis);
    if (analysis && ['queued', 'running'].includes(analysis.status)) schedulePoll(analysis.id, epoch);
    if (page === 'analyses' && !id && state.analyses.some(a => ['queued', 'running'].includes(a.status))) pollTimer = setTimeout(() => render({ focus: false }), 1500);
    if (page === 'history' && state.analyses.some(a => ['queued', 'running'].includes(a.status))) pollTimer = setTimeout(() => render({ focus: false }), 2000);
  } catch (error) {
    if (epoch !== routeEpoch) return;
    if (live) {
      main.innerHTML = error.status === 401 ? signedOut() : heading('Could not load this page', 'Your stored reports have not been changed.')
        + notice('Request failed', error.message, 'error') + '<button class="button secondary" data-action="retry" type="button">Try again</button>';
    } else main.innerHTML = heading('This example is unavailable', 'Your demo workspace can be restored at any time.') + notice('Could not load the view', error.message, 'error') + `<div class="error-actions">${button('Open history', '#history', 'secondary')}<button class="button" data-action="reset" type="button">Reset demo data</button></div>`;
  } finally {
    if (epoch === routeEpoch) { main.setAttribute('aria-busy', 'false'); if (focus) { main.focus({ preventScroll: true }); window.scrollTo({ top: 0, behavior: 'instant' }); } }
  }
}

function schedulePoll(id, epoch) {
  pollTimer = setTimeout(async () => {
    try {
      const { analysis } = await service.report(id);
      if (epoch !== routeEpoch) return;
      if (!['queued', 'running'].includes(analysis.status)) {
        showToast('Analysis finished. Review the status, findings, and coverage.');
        if (location.hash === reportLink(id)) await render({ focus: false });
        else location.hash = reportLink(id);
        return;
      }
      // Keep keyboard focus stable while the status and checks update.
      const wrapper = document.createElement('div'); wrapper.innerHTML = progressView(analysis);
      const oldPanel = main.querySelector('.stack');
      oldPanel.replaceWith(wrapper.querySelector('.stack'));
      main.querySelector('h1').textContent = analysis.status === 'queued' ? 'Analysis queued' : 'Analysis in progress';
      schedulePoll(id, epoch);
    } catch (error) { if (epoch === routeEpoch) { showToast(error.message); render({ focus: false }); } }
  }, 1100);
}

function bindView(analysis) {
  document.querySelector('#installation')?.addEventListener('change', async event => {
    state.installation = Number(event.target.value) || null; state.selectedRepository = null;
    service.selectInstallation(state.installation);
    await render({ focus: false });
  });
  const refreshResults = () => { const el = document.querySelector('#report-results'); if (el) el.innerHTML = reportResults(analysis); };
  document.querySelector('#repository-search')?.addEventListener('input', event => { state.search = event.target.value; document.querySelector('#repository-options').innerHTML = repoOptions(); });
  document.querySelector('#authorization')?.addEventListener('change', event => { document.querySelector('#start-analysis').disabled = !event.target.checked; });
  document.querySelector('#analysis-form')?.addEventListener('submit', async event => {
    event.preventDefault(); const form = event.currentTarget; if (!form.reportValidity()) return;
    const start = document.querySelector('#start-analysis'); const error = document.querySelector('#form-error');
    start.disabled = true; start.textContent = 'Queuing analysis…'; error.textContent = '';
    const epoch = routeEpoch;
    try {
      const result = await service.start({ repository_id: state.selectedRepository, reference: form.elements.reference.value.trim() || undefined, authorization_confirmed: form.elements.authorization.checked, dependency_lookup: form.elements.dependency_lookup.checked });
      if (epoch !== routeEpoch) return;
      if (!result.created) showToast('An analysis for this revision is already queued or running.');
      location.hash = `#analyses/${result.analysis.id}`;
    } catch (exception) { if (epoch === routeEpoch) { error.textContent = exception.message; start.disabled = false; start.innerHTML = `${icon('analysis')}Start analysis`; } }
  });
  document.querySelector('#category-filter')?.addEventListener('change', event => { state.category = event.target.value; refreshResults(); });
  document.querySelector('#priority-filter')?.addEventListener('change', event => { state.priority = event.target.value; refreshResults(); });
  document.querySelector('#finding-search')?.addEventListener('input', event => { state.search = event.target.value; refreshResults(); });
  document.querySelector('#status-filter')?.addEventListener('change', event => { state.historyStatus = event.target.value; document.querySelector('#history-results').innerHTML = historyRows(); });
  document.querySelector('#history-search')?.addEventListener('input', event => { state.search = event.target.value; document.querySelector('#history-results').innerHTML = historyRows(); });
}

function confirmAction(title, description, action, label = 'Delete analysis') {
  const dialog = document.querySelector('#confirmation');
  focusedBeforeDialog = document.activeElement;
  document.querySelector('#confirmation-title').textContent = title;
  document.querySelector('#confirmation-description').textContent = description;
  document.querySelector('#confirm-action').textContent = label;
  document.querySelector('#confirmation-icon').innerHTML = icon(label === 'Reset demo' ? 'history' : 'trash');
  dialogAction = action; dialog.returnValue = 'cancel'; dialog.showModal();
}
document.querySelector('#confirmation').addEventListener('close', async event => {
  const action = dialogAction; dialogAction = null;
  if (event.target.returnValue === 'confirm' && action) {
    try { await action(); } catch (error) { showToast(error.message); }
  } else if (focusedBeforeDialog?.isConnected) focusedBeforeDialog.focus();
});

function resetDemo() {
  confirmAction('Reset demo workspace?', 'This restores the original sample reports and clears simulated runs and deletions in this browser tab.', async () => {
    clearTimeout(pollTimer); service.reset(); state.search = ''; state.category = 'all'; state.priority = 'all'; state.historyStatus = 'all'; state.selectedRepository = 101;
    if (location.hash === '#overview') await render(); else location.hash = '#overview';
    showToast('Demo workspace restored. All data is simulated.');
  }, 'Reset demo');
}
document.querySelector('#reset-demo').addEventListener('click', async () => {
  if (!live) return resetDemo();
  clearTimeout(pollTimer);
  try { await service.logout(); } catch (error) { if (error.status !== 401) { showToast(error.message); return; } }
  ++routeEpoch;
  main.innerHTML = signedOut('You have signed out. Your stored reports have not been deleted.');
  main.setAttribute('aria-busy', 'false');
});
document.querySelector('.skip-link').addEventListener('click', event => { event.preventDefault(); main.focus(); });
document.addEventListener('click', async event => {
  const target = event.target.closest('button'); if (!target) return;
  if (target.dataset.repository) {
    state.selectedRepository = Number(target.dataset.repository);
    const selected = state.repositories.find(r => r.id === state.selectedRepository);
    document.querySelectorAll('[data-repository]').forEach(b => b.setAttribute('aria-pressed', String(Number(b.dataset.repository) === selected.id)));
    document.querySelector('#selected-repository').innerHTML = `${icon('repository')}${e(selected.full_name)}`;
    document.querySelector('#reference').placeholder = selected.default_branch;
  }
  if (target.dataset.delete) {
    const a = state.analyses.find(a => a.id === target.dataset.delete); if (!a) return;
    confirmAction(copy('Delete this analysis?', 'Delete this example analysis?'), copy(`Permanently remove the report for ${a.repository} (${timestamp(a.created_at)}) and its associated evidence from your history?`, `Remove the sample report for ${a.repository} (${timestamp(a.created_at)}) and its evidence? This affects demo data in this tab only.`), async () => { await service.delete(a.id); await render(); showToast(copy('Analysis deleted.', 'Example analysis deleted. Reset demo data to restore it.')); });
  }
  if (target.dataset.copy) {
    try { await navigator.clipboard.writeText(target.dataset.copy); showToast('Commit SHA copied.'); }
    catch { showToast('Clipboard access is unavailable. Select and copy the full SHA shown in the report.'); }
  }
  if (target.dataset.action === 'reset') resetDemo();
  if (target.dataset.action === 'retry') render();
  if (target.dataset.action === 'clear-filters') {
    state.category = 'all'; state.priority = 'all'; state.search = '';
    const { analysis } = await service.report(route()[1]);
    if (route()[0] !== 'report' || route()[1] !== analysis.id) return;
    document.querySelector('#category-filter').value = 'all'; document.querySelector('#priority-filter').value = 'all'; document.querySelector('#finding-search').value = '';
    document.querySelector('#report-results').innerHTML = reportResults(analysis); document.querySelector('#finding-search').focus();
  }
});
window.addEventListener('hashchange', () => {
  state.search = ''; state.category = 'all'; state.priority = route()[2] === 'urgent' ? 'urgent' : 'all'; state.historyStatus = 'all';
  render();
});
window.addEventListener('pagehide', () => { clearTimeout(pollTimer); clearTimeout(toastTimer); });
state.priority = route()[2] === 'urgent' ? 'urgent' : 'all';
render();
