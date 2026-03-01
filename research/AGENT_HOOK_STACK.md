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

## Expanded check inventory

### Code quality
- **SonarQube / CodeClimate / Codacy** — complexity, duplication, smell scoring, quality gates
- **Mutation testing** (Stryker, Pitest, mutmut) — measures test suite sensitivity; agents sometimes write tests that pass but don't constrain behavior
- **Dead code detection** (knip, ts-prune, vulture)
- **Cyclomatic / cognitive complexity thresholds**
- **Coverage gates with diff tracking** (Codecov) — "did this PR reduce coverage?"

### Security
- **SAST**: CodeQL (GitHub native), Checkmarx, Veracode
- **DAST**: OWASP ZAP — runs the actual app and probes it; catches injection vectors agents introduce
- **Container scanning**: Trivy, Grype
- **Secret detection**: GitLeaks, TruffleHog — catches committed credentials
- **IaC scanning**: Checkov, tfsec
- **License compliance**: FOSSA — catches GPL in commercial code
- **SCA**: Snyk, Black Duck — deeper than npm audit

### Visual regression
- **Percy, Chromatic (Storybook), Applitools, BackstopJS** — screenshot diffs between branches; agents frequently shift layouts unintentionally

### Performance beyond Lighthouse
- **k6 / Gatling** — load testing, catches throughput regressions
- **WebPageTest** — more detailed than Lighthouse, real browser, waterfall analysis
- **Bundle size budgets** (size-limit) — per-route size tracking

### Accessibility
- **axe-core / Pa11y** — automated WCAG checks, separate from Lighthouse's basic pass

### API contracts
- **Pact** — consumer-driven contract tests between services
- **OpenAPI spec validation** — does the implementation match the declared spec?

### Architecture
- **Dependency Cruiser / ArchUnit** — no circular deps, no layer violations
- **Import structure enforcement**

### Infrastructure
- `terraform plan` validation
- **Database migration safety** — destructive ops flagged before apply

### Documentation
- **Broken link checker**
- **cspell** — spell check in code comments and docs

---

## Most likely to catch agent-introduced regressions specifically

- **Visual regression** — agents frequently shift layouts
- **DAST** — agents sometimes introduce injection vectors
- **Contract tests** — agents break API shapes
- **Mutation score** — agents write tests that pass but don't actually constrain behavior

---

## Key principle: re-trigger payload matters as much as the gate

Each check should emit: current value, threshold, and ideally a target.

- Weak: "LCP: 3200ms, threshold: 2500ms"
- Strong: "LCP: 3200ms, threshold: 2500ms, likely cause: image added in hero section has no explicit dimensions"

The stronger the payload, the faster the agent converges.

Lighthouse + usersim together cover the gap that static analysis cannot: whether the
*running* app behaves correctly for users. Everything in tiers 1–2 can pass while
tiers 3–4 fail.
