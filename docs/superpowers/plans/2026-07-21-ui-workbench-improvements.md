# UI Workbench Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the document-checking UI easier to understand and operate by shrinking page titles, adding a guide and report navigation/download actions, explaining thresholds, replacing drag-to-add terminology with sentence-level actions, and polishing the report workspace.

**Architecture:** Keep the existing React Router, report API, term-library API, and DOCX analysis backend unchanged. Add one static `GuidePage`, pass selection state from `IssueContext` to `IssueList`, and let `ReportPage` compose navigation/download controls. Use focused CSS classes for the visual hierarchy and accessible tooltip state.

**Tech Stack:** React, TypeScript, React Router, Vitest, Testing Library, existing CSS token system.

---

### Task 1: Add route and navigation coverage

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/CheckPage.tsx`
- Create: `frontend/src/pages/GuidePage.tsx`
- Test: `frontend/tests/CheckPage.test.tsx`
- Create: `frontend/tests/GuidePage.test.tsx`

- [ ] Write a failing guide-page test that renders the four operation sections and a home link.
- [ ] Write a failing CheckPage assertion that the top navigation contains `使用说明` and points to `/guide`.
- [ ] Run the focused Vitest files and confirm the route/link assertions fail before implementation.
- [ ] Add `/guide` to `App.tsx`, create the concise four-step `GuidePage`, and add the nav link without changing upload behavior.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Add report navigation and downloads

**Files:**
- Modify: `frontend/src/pages/ReportPage.tsx`
- Modify: `frontend/tests/ReportPage.test.tsx`
- Modify: `frontend/src/styles.css`

- [ ] Add failing assertions for `返回首页`, existing HTML download, and a JSON download link targeting `/report.json`.
- [ ] Implement the report header action group and empty-filter state while preserving the current issue filters and term dialog.
- [ ] Style the action group and report workspace with the existing blue accent and status colors.
- [ ] Run the report-page test and confirm it passes.

### Task 3: Add threshold tips and title scale

**Files:**
- Modify: `frontend/src/pages/CheckPage.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/tests/CheckPage.test.tsx`

- [ ] Add failing tests that find two keyboard-focusable threshold help controls and their explanatory text.
- [ ] Implement an accessible `ThresholdTip` pattern locally in `CheckPage` using a button, `aria-label`, and a small toggled tooltip; keep slider values and requests unchanged.
- [ ] Reduce shared `h1` sizes and mobile overrides; add visible `:focus-visible` styles for tips and action links.
- [ ] Run focused tests, TypeScript lint, and verify both slider values still submit unchanged.

### Task 4: Replace drag-to-add terminology with sentence actions

**Files:**
- Modify: `frontend/src/components/IssueContext.tsx`
- Modify: `frontend/src/components/IssueList.tsx`
- Modify: `frontend/src/pages/ReportPage.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/tests/ReportPage.test.tsx`

- [ ] Add failing tests showing a `TEXT_CORRECTION` row has a disabled `添加为术语` button before selection, becomes enabled after a text selection, and non-text rows do not render it.
- [ ] Change `IssueContext` to report selected text through an explicit callback and stop making the entire context container the implicit action.
- [ ] Add per-row selected-term state in `IssueList`; render the button only for `TEXT_CORRECTION`, and pass the selected term to the existing `ReportPage` dialog callback.
- [ ] Add a clear selected-text visual state and disabled/hover/focus styles.
- [ ] Run focused report tests and verify existing `addTermAndRematch` behavior remains intact.

### Task 5: Polish report layout and verify

**Files:**
- Modify: `frontend/src/components/ReportSummary.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/tests/ReportPage.test.tsx`

- [ ] Add a failing assertion for a report summary heading/context and an empty filtered-results message.
- [ ] Add a compact report overview label and keep the existing three summary metrics; render an actionable empty state when filters match no issues.
- [ ] Refine cards, separators, metadata, action grouping, and responsive behavior without changing report data.
- [ ] Run all frontend tests, `npm run lint`, and `npm run build`.
- [ ] Review `git diff --check`, confirm only intended tracked files changed, and commit the implementation.

