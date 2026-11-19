---
name: CyberCheck operational demo
description: Trace evidence layout with the Guide palette and Index outlined actions.
colors:
  canvas: "#0c101a"
  sidebar: "#0a0e17"
  surface: "#181f30"
  raised: "#202a3e"
  border: "#364058"
  text: "#e9ecf5"
  muted: "#b0b9ce"
  accent: "#c1ccf0"
  action: "#485f9a"
  selected: "#25314a"
  critical: "#ff6978"
  high: "#ffa24b"
  medium: "#e7c665"
  low: "#90b6f2"
  review: "#b9ace6"
  success: "#85cfa4"
typography:
  headline:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "28px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.035em"
  title:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.015em"
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.5
  technical:
    fontFamily: "JetBrains Mono, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  badge: "4px"
  control: "6px"
  panel: "8px"
spacing:
  s1: "4px"
  s2: "8px"
  s3: "12px"
  s4: "16px"
  s5: "20px"
  s6: "24px"
  s8: "32px"
components:
  button-primary:
    backgroundColor: "transparent"
    textColor: "{colors.accent}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  button-danger:
    backgroundColor: "#c7354b"
    textColor: "#fff"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  input:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "9px 12px"
  navigation-selected:
    backgroundColor: "{colors.selected}"
    textColor: "#a6c8ff"
    rounded: "{rounded.control}"
    padding: "10px 13px"
  priority-critical:
    backgroundColor: "#301824"
    textColor: "{colors.critical}"
    rounded: "{rounded.badge}"
    padding: "3px 7px"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.panel}"
    padding: "24px"
---

# Design System: CyberCheck operational demo

## Overview

**Creative North Star: "The Investigation Workspace"**

User-selected identity: Trace’s evidence-first structure, Guide’s midnight/blue-gray palette, and Index’s outlined primary buttons. The symbol remains owned by DAVI and is outside this implementation.

This system describes only the operational demo in `demo-front/`. It does not govern the separate marketing website. The user's pinned identity is a minimal professional interface in black and dark navy, with Inter for interface text and JetBrains Mono for technical evidence.

The shipped workspace favors quiet investigation lists, precise revision context, and secondary coverage information. Containers organize forms, reports, and detail views without turning every metric into a card. The metaphor names the existing implementation; it is not a replacement visual identity.

**Key Characteristics:**
- Black canvas and tonal navy surfaces with discreet cool borders.
- Stable semantic priority colors, separate from confidence and analysis state.
- Inter hierarchy paired with monospaced identifiers and evidence.
- Investigation lists with compact counts and secondary coverage.
- Flat surfaces, visible keyboard focus, and restrained state transitions.

## Colors

Cool near-black and navy neutrals establish the workspace; blue marks action and selection, while semantic colors explain priority and state.

### Primary
- **Control Blue** (`action`): native control accents, including checkboxes.
- **Evidence Blue** (`accent`): pale blue-gray text and outlines on primary actions, links, focus, active technical symbols, and running state.
- **Selected Navy** (`selected`): selected navigation and repository options.

### Secondary
- **Critical Rose** (`critical`), **High Orange** (`high`), **Medium Gold** (`medium`), **Low Blue** (`low`), and **Review Lavender** (`review`): stable priority identities, always paired with a written label.
- **Completion Green** (`success`): completed analysis checks, not an overall security verdict.

### Neutral
- **Black Canvas** (`canvas`): page and inset code or form backgrounds.
- **Sidebar Navy** (`sidebar`): persistent navigation.
- **Surface Navy** (`surface`): grouped form and report containers.
- **Raised Navy** (`raised`): hover and supporting state surfaces.
- **Cool Border** (`border`): separators and quiet containment.
- **Evidence White** (`text`): primary readable content.
- **Context Slate** (`muted`): supporting context and labels.

**The Semantic Separation Rule.** Priority, confidence, and coverage retain separate labels. A completion color or finding count never implies a security score.

## Typography

**Display and Body Font:** Inter, with system UI and sans-serif fallbacks. There is no separate decorative display face.
**Label/Mono Font:** JetBrains Mono, with monospace fallback, for code and technical identifiers.

The pairing is compact and operational. Headings use restrained weight and tightened tracking; technical values preserve their literal shape. Both families are locally hosted, with their existing licenses alongside the font files.

### Hierarchy
- **Headline:** the frontmatter headline role leads pages; it reduces to (24px) at the mobile breakpoint.
- **Title:** the title role labels sections; smaller section headings also use (13–15px) where the context is secondary.
- **Body:** the body role establishes the root text rhythm. Detail prose uses (13px) with line-height (1.9) and a measure of (70ch); mobile detail prose rises to (14px).
- **Label:** the label role identifies controls and metadata; controls use weight (550). Compact desktop table and status annotations include (11px) text, rather than establishing a universal body size.
- **Technical:** the technical role is the default for code and identifiers; code blocks use line-height (1.9). Full commit values wrap rather than disappear.

**The Evidence Type Rule.** Reserve mono for literal code, paths, and identifiers; keep explanations and actions in Inter.

## Layout

The desktop shell pairs a navigation column (232px) with a flexible workspace. Main content has a maximum width (1400px), desktop horizontal padding (36px), and vertical padding (34px / 40px). At (1200px), navigation becomes (208px) and main horizontal padding becomes (24px). The reused spacing scale is recorded in the frontmatter.

The overview's investigation list occupies the flexible column, with a secondary coverage column (260px), a gutter (40px), and a discreet vertical divider. At (1200px), the secondary column becomes (230px) with a gutter (24px). At (1000px), coverage moves below the list; repository and detail layouts also stack. This is the overview's composition, not a required arrangement for every screen.

At (760px), navigation becomes a sticky four-item horizontal bar, main padding becomes (26px 20px 32px), and coverage stacks into one column. Buttons and icon actions have a minimum mobile target (44px); navigation reaches (46px). At (390px), main horizontal padding becomes (16px). Wide tables and code use local scrolling; long technical strings wrap. Do not hide confidence when compact table columns disappear: the investigation list exposes a responsive confidence line.

## Elevation & Depth

The interface is flat at rest. Tonal navy layers, fine borders, and separators establish hierarchy. Ordinary panels and dialogs have no shadow. The transient toast alone uses a restrained shadow (`0 8px 28px #0005`); a dark dialog backdrop (`#02050cb8`) separates confirmation from the workspace.

**The Quiet Surface Rule.** Use separators for investigation rows and compact count groups. Add a container when it groups a form, report, or contextual detail, rather than as decoration around every datum.

## Shapes

Panels, report containers, dialogs, and code examples use 8px corners. Buttons and fields use 6px, and priority badges use 4px. Tables, investigation rows, and dividers remain square within their containers. Borders are typically (1px). The investigation overview deliberately removes the enclosing panel silhouette around its list and count strip. Repository symbols use transparent backgrounds in the final refinement. Icons are restrained inline SVG line drawings rather than decorative glyphs.

## Components

### Brand assets

Use DAVI's original SVG assets in `demo-front/assets/brand/` without recoloring, cropping, or stretching. The sidebar uses `logo-horizontal.svg`, up to 180px wide on desktop and 168px on mobile, preserving its `1478:298` aspect ratio. The study header uses the same logo. `favicon.svg` is the browser icon, and `logo-icon.svg` is used in compact branded empty states. The logo's supplied blue (`#265FDF`) is an asset color; it does not replace the Guide interface palette. White and black monochrome SVGs are available for contexts requiring those applications.

### Buttons

Compact and explicit. Primary actions use a transparent background with an Evidence Blue outline and matching text; secondary actions use Surface Navy with a cool border; ghost actions use muted text and a transparent background. The danger action uses the shipped deeper rose fill. Desktop controls have a minimum height (38px); mobile targets follow Layout. Hover changes background and, for secondary actions, border color. State transitions take (160ms). Keyboard focus uses an accent outline (2px) with an offset (4px). Destructive actions retain a written label and confirmation dialog.

### Priority badges and status

Priority badges pair a semantic foreground, a subdued tinted background, a written priority, and a small bar mark. Confidence stays in a distinct text label. Analysis status pairs a colored dot with words, so color is never its only signal. Compact counts are inline values separated from the investigation list by a rule, not large metric cards.

### Cards / Containers

Finding details follow Trace: a finding reference and priority precede aligned source/rule/confidence fields, then a highlighted evidence record. Impact and correction share two columns on desktop and stack on mobile. The illustrative correction is disclosed with a native details control.

Grouped panels use Surface Navy, a cool border, and the panel radius, usually with internal padding (24px), reducing to (20px) in compact contexts. Report and history tables may live inside panels; the overview investigation list stays unboxed. Neutral notices use a transparent surface and control-radius border in the final cascade; warning and error notices retain tinted semantic surfaces and explicit wording.

### Inputs / Fields

Fields use Black Canvas, readable light text, a stronger stroke (`#3a4960`), the control radius, and a minimum height (40px). Inputs use padding (9px 12px). Search fields add a small inline SVG and left padding (37px). Keep visible labels in addition to placeholders. Focus uses the shared accent outline. Inline errors use critical text and an explicit error message; disabled controls must remain understandable without relying on opacity alone.

### Navigation

Muted Inter links use a tonal hover surface, selected navy with pale blue text for the current page, and the same visible keyboard focus as controls. Desktop links have a minimum height (42px); mobile behavior follows Layout. Preserve `aria-current` on the active destination.

### Investigation list

The overview's signature is a quiet evidence list: heading and explanation, border-separated finding rows, compact labeled priority counts above, and coverage/category information to the side or below. Rows expose title, technical source, and confidence; hover adds only a slight tonal change. This pattern places investigation before summary ornament.

### Feedback and motion

A toast provides transient feedback; a native dialog handles destructive confirmation. View entry takes (180ms), with opacity and a translation of (4px), using `cubic-bezier(.16,1,.3,1)`. Reduced-motion preference removes animations and transitions.

## Do's and Don'ts

### Do:
- **Do** preserve the black and dark navy identity, Inter interface text, and JetBrains Mono technical values.
- **Do** pair semantic color with words and keep confidence separate from priority.
- **Do** preserve exact revision context, visible incomplete coverage, and explicit time zones.
- **Do** use quiet lists and discreet separators when presenting investigation work.
- **Do** keep keyboard focus visible and retain reduced-motion behavior.

### Don't:
- **Don't** introduce decorative neon, excessive gradients, or unnecessary ornament.
- **Don't** interpret a green completion state or a finding count as a security guarantee or score.
- **Don't** replace every information group with a dashboard card.
- **Don't** generalize compact footer text or opacity-only disabled styling into defaults for new screens.
- **Don't** apply this operational-demo system to the separate marketing website without its own design decision.
