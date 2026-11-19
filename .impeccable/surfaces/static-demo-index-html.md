---
version: 1
slug: "static-demo-index-html"
primary_target: "static/demo/index.html"
related_targets: ["static/demo/app.js","static/demo/styles.css","static/demo/demo-service.js"]
---

# CyberCheck demo interface

Mode: Operate. Scope: local frontend only, six existing product views, simulated data. The user's confirmed direction and Figma flow govern this implementation; there is no new visual-world selection.

## Direction contract

THESIS: Make the next security investigation easy to identify, with evidence and coverage ahead of decoration. Counts describe findings, never an overall security score.

OWN-WORLD: Black canvas, dark navy surfaces, fine cool borders, Inter UI text, JetBrains Mono technical values. Selected identity: Trace evidence structure, Guide palette, Index outlined actions. Pale blue-gray identifies actions and selections; red, orange, yellow, pale blue, and lavender retain stable priority roles.

STORY: Select a sample repository, confirm authorization, follow a simulated queue and checks, inspect a report and finding, filter results, and delete or restore sample history. No backend requests or credential entry.

FIRST VIEWPORT: A 232px desktop sidebar, compact breadcrumb/demo bar, heading and primary action, revision summary, and compact priority counts lead directly into a finding list. A narrow secondary column carries check coverage and category counts. On mobile the sidebar becomes a four-item navigation bar and the content stacks without page-wide horizontal scrolling.

FORM: seed: none (pinned). The user requested “Dark mode com preto e tons de azul-escuro”, “Tipografia Inter e JetBrains Mono”, and preservation of the six existing Figma screens; the later request explicitly authorizes a frontend-first implementation before API integration.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Constraints

No shipping raster assets. Fonts are local and include their original licenses. Keep the presentation website and Python modules untouched. The browser connection is unavailable; use Impeccable's screenshot helpers for rendered evidence and identify DOM-emulated tests separately from real-browser interaction coverage.
