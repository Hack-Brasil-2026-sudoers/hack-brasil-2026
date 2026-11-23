# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Independent developers and small teams reviewing authorized Python repositories. DAVI (Davi Braz) owns the operational demo interface and the separate deliberately vulnerable test project.

## Product Purpose

Help developers identify potential security issues, understand the evidence, and decide what to fix first. The detailed product authority remains [PROJETO.md](../markdown/PROJETO.md); task ownership and the backlog remain in the existing workstream and next-step documents.

## Operating Context

The current task is a local frontend demo in `demo-front/`, separate from the presentation site in `website/`. Its six views are overview, repositories, analysis progress, report, finding details, and history. The application at /app/ uses the main GitHub OAuth/session API. Integrações provides connection and installation selection; ?demo=1 keeps simulated mode available.

## Capabilities and Constraints

- Preserve explicit real and simulated modes; repository access and scanners run on the backend.
- Keep repository, full commit SHA, explicit time zones, evidence, uncertainty, and incomplete coverage visible.
- Keep confidence separate from priority. Do not assign a security score.
- Follow the consolidated main backend contracts. Use HTML/CSS and browser JavaScript without a new framework or build system.
- Preserve existing English app text and the user-requested Portuguese Integrações labels. Run locally; public hosting remains deferred.

## Brand Commitments

The user confirmed a minimal professional dark interface in black and dark navy, Inter with JetBrains Mono for code and technical identifiers, discreet borders, and semantic priority colors. Avoid decorative neon, excessive gradients, and unnecessary ornament. The existing six Figma screens establish the flow and content hierarchy; the first Figma refinement remained partially completed when the MCP quota was exhausted.

## Evidence on Hand

The demo fixtures in `demo-front/demo-service.js` are authored examples, not scanner results. Package names and advisory IDs are fictional. API-shaped methods ease future integration but do not establish that the current backend contract is final.

The selected visual combination is Trace’s evidence-first layout, Guide’s palette, and Index’s outlined button. DAVI handles the project symbol.
