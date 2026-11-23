# CyberCheck frontend demo

A buildless HTML/CSS/JavaScript preview of the six operational views: overview, repositories, simulated progress, report, finding details, and history. All data is fictional and lives in browser-tab memory. Reloading restores the initial fixtures.

## Directory structure

```text
demo-front/
  index.html          # Operational demo entry point
  app.js              # Views, navigation, and browser interactions
  styles.css          # Shared visual tokens and responsive components
  demo-service.js     # In-memory data adapter; replace during API integration
  assets/
    brand/            # Original logo kit supplied by DAVI
    fonts/            # Self-hosted fonts and their licenses
  design-study/       # Separate identity exploration, outside the app flow
  tests/              # Frontend demo-service tests
  DESIGN.md           # Agreed visual system
  PRODUCT.md          # Frontend context; product scope remains in markdown/PROJETO.md
```

The application backend remains in `cybercheck/`, its tests in the root `tests/`, and the presentation site in `website/`. A deliberately vulnerable test project is a separate pending deliverable; it does not belong in this frontend directory.

From the repository root:

```bash
python3 -m http.server 8081 --bind 127.0.0.1 --directory demo-front
```

Open **http://127.0.0.1:8081/**. No Python application dependencies, API token, GitHub App, scanners, or backend process are needed. The existing presentation site remains in `website/`.

The separate [visual identity study](design-study/index.html) compares three proposed directions (Trace, Index, and Guide) using the same simulated finding. Open `http://127.0.0.1:8081/design-study/`; use the view control to compare them side by side. No proposal includes a symbol. The selected combination—Trace structure, Guide colors, and Index outlined button—is applied to the operational demo.

## Try the flow

1. Open Repositories and select a sample project.
2. Confirm authorization. Enable dependency lookup to simulate full coverage; leave it unchecked to simulate partial coverage. Neither option sends data anywhere.
3. Start the simulated analysis. After about nine seconds, the report opens.
4. Filter findings by category, priority, file, or rule. Open a finding to inspect evidence, uncertainty, and suggested remediation.
5. Open History to inspect complete, partial, failed, or zero-finding examples. Delete an example after confirmation, or use Reset examples to restore the workspace.

The fixed fixtures can also be opened directly:

- `#report/demo-completed`
- `#report/demo-partial`
- `#report/demo-clean`
- `#report/demo-failed`
- `#finding/demo-completed/0`

## API integration

`demo-service.js` provides in-memory examples. `api-service.js` uses main's same-origin session/CSRF API at `/app/`, including installation and repository pagination, analysis creation, polling, history, reports and deletion. No GitHub or operator token is embedded in frontend source. Integrações provides the connection UI; `/app/?demo=1` explicitly uses examples without API calls.

The browser hash router and rendering helpers live in `app.js`. `styles.css` provides shared tokens, components, responsive layouts, keyboard focus, and reduced-motion support. Inter and JetBrains Mono are self-hosted; their original licenses are in `assets/fonts/`. Font sources: [Inter](https://github.com/rsms/inter) and [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono).

## Brand assets

DAVI supplied the original SVG kit in `assets/brand/`. The demo and identity study use `logo-horizontal.svg` in their header and the supplied `favicon.svg` in the browser tab. `logo-icon.svg` is used in compact branded empty states. Preserve the assets' transparency, original colors, and proportions. `logo-monochrome-white.svg` and `logo-monochrome-black.svg` remain available for dark and light applications respectively. `preview.png` is a reference board, not a UI asset.

## Verification

With Node.js 22 or later, run the demo-service tests from the repository root:

```bash
node --test demo-front/tests/demo-service.test.mjs
```

These tests verify simulated lifecycle, authorization validation, coverage, fixture consistency, and deletion/reset behavior. They do not test the real backend, GitHub, or scanner accuracy. Rendering and DOM-emulated interaction checks are separate evidence; they are not full real-browser keyboard or assistive-technology validation.

## Consolidated integration

Open `http://127.0.0.1:8000/app/#integrations` for GitHub login, installation selection and sign-out. The frontend uses the main API contracts (`/auth/me`, `/api/github/installations`, repository pagination by installation and CSRF-protected writes). The previous local bearer-token form is not an alternate login path when OAuth is enabled.

Demo mode remains available at `/app/?demo=1#overview` and through the standalone static server. Historical website reports are rendered with null repository/commit fields. The global visual design and brand assets are preserved. See [the consolidation guide](../markdown/GITHUB-INTEGRATION.md) for configuration, migration and live validation.
