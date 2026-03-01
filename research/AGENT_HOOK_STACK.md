# Agent Finished Task Hook: Ideal Check Stack

Notes from discussion on 2026-03-01.

Ordered by speed and signal clarity — fastest/cheapest first, re-trigger as early as possible.

---

## Tier 1 — seconds, hard gates
- **Type checker** (tsc / mypy) — unambiguous signal, agent knows exactly what to fix
- **Linter** (ESLint / Pylint) with a minimal critical ruleset — not every style rule, just the ones that break things
- **Unit tests**

## Tier 2 — minutes, regression gates
- **Integration tests**
- **Bundle size budget** (bundlesize / size-limit) — per-entry-point thresholds, catches bloat
- **Dependency audit** (npm audit / safety) — new dependencies with known CVEs

## Tier 3 — 5–15 min, behavioral gates
- **Lighthouse CI** — LCP, INP, CLS, accessibility score, with thresholds calibrated to project baseline
- **Playwright / Cypress E2E** — critical user paths only, not full suite
- **Semgrep** with custom rules — project-specific patterns the linter doesn't cover

## Tier 4 — full behavioral check
- **usersim** — cross-dimensional constraint check across all scenarios

---

## Key principle: re-trigger payload matters as much as the gate

Each check should emit: current value, threshold, and ideally a target.

- Weak: "LCP: 3200ms, threshold: 2500ms"
- Strong: "LCP: 3200ms, threshold: 2500ms, likely cause: image added in hero section has no explicit dimensions"

The stronger the payload, the faster the agent converges.

Lighthouse + usersim together cover the gap that static analysis cannot: whether the
*running* app behaves correctly for users. Everything in tiers 1–2 can pass while
tiers 3–4 fail.
