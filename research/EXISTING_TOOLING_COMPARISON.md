# Existing Tooling Comparison

Notes from discussion on 2026-03-01.

---

## Code quality / static analysis

- **SonarQube Quality Gate** — closest analog: define metric thresholds, gate CI on pass/fail. Static only, no behavioral/runtime dimensions.
- **ESLint / Pylint / RuboCop** — rule-per-pattern linters. The "no class > 8 public methods" use case lives here. Widely deployed, not thought of as constraint systems.
- **NDepend (CQLinq)** — relational queries over code structure. Most Z3-like of the static tools.
- **ArchUnit / NetArchTest / Dependency Cruiser** — executable cross-dimensional architecture rules in tests.
- **jQAssistant** — Neo4j + Cypher queries over codebase graph. Richest expression of structural constraints.
- **Semgrep** — semantic pattern rules, community-contributed libraries. Closest to modular constraint library idea in static analysis.

## Runtime behavioral constraints

- **SLOs** — production analog of usersim constraints: behavioral dimensions + thresholds + continuous checking. For reliability, not UX. Same conceptual model.
- **Lighthouse CI** — runtime UX metric thresholds (LCP, INP, CLS) with p10/median calibration. Predefined dimensions only.
- **Chaos Engineering (LitmusChaos, Gremlin)** — "steady-state hypothesis" = runtime behavioral constraint under adversarial scenarios.
- **Pact** — consumer-driven contract testing. Consumer ≈ persona, contract ≈ constraints, runs against real system. About API shape, not aggregate behavioral metrics.

## Test quality

- **Mutation testing (Pitest, mutmut, Stryker)** — measures constraint coverage empirically. High mutation score = tight constraint system = high conflict density.

## Conceptual predecessor

- **Architectural Fitness Functions** ("Building Evolutionary Architectures", Ford/Parsons/Kua 2017) — define measurable architectural properties as automatically-evaluated functions to guide evolution over time. The direct conceptual predecessor to usersim applied to UX.

---

## Summary table

| Tool | Substrate | Constraint type | Runtime? | AI loop? |
|---|---|---|---|---|
| SonarQube Quality Gate | Static code | Threshold per metric | No | No |
| ESLint / Pylint | Static code | Rule per pattern | No | No |
| NDepend CQLinq | Static code | Relational queries | No | No |
| ArchUnit | Static code | Cross-dimensional structural | No | No |
| Pact | API execution | Contract shape | Yes | No |
| SLOs | Production telemetry | Threshold + proportional | Yes | No |
| Lighthouse CI | Browser execution | Calibrated UX thresholds | Yes | No |
| Chaos Engineering | Fault-injected execution | Steady-state behavioral | Yes | No |
| Mutation testing | Code variants | Coverage sensitivity | Partial | No |
| Fitness functions | Mixed | Architectural characteristics | Mixed | No |
| **usersim** | **Scenario execution** | **Cross-dimensional behavioral** | **Yes** | **Planned** |

## The gap

Every existing tool reports violations. None generate target assignments for an AI agent
to converge on. SonarQube tells an agent "these 12 issues need fixing" — a list. usersim's
planned Z3 model generation output says "here are the target metric values you need to
reach" — a direction. That is the gap.
