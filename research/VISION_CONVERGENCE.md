# usersim: Vision and Future Direction

Notes from discussion on 2026-03-01.

---

## The primary goal

"Cause convergence over multiple AI agent invocations on a codebase."

Everything else is instrumental to this. E2E tests don't cause convergence — they tell the
agent "this scenario failed" which is a data point, not a direction. For convergence, the
agent needs to know *where it is* in the behavioral space and *which direction to move*.
That's a fundamentally different output than pass/fail.

This reframes usersim's purpose. It is not primarily a testing framework. It is a
**specification oracle** — a system that takes behavioral measurements and outputs a
description of how far the current behavior is from the satisfying region, and in what
direction.

---

## The modular library architecture

The right architectural move is focused modules, not a single global constraint model.

Each module covers one domain — `retention`, `search`, `privacy`, `throughput`,
`resilience` — with 3–7 pre-defined dimensions and calibrated constraints already written.
The developer's job is to wire up their instrumentation to the module's expected variables,
not design the constraint system from scratch.

This solves both open problems simultaneously:

**Usability:** Developers aren't staring at a global constraint model trying to invent
dimensions. They pick a module. The constraint vocabulary already exists for their domain.

**Dimensionality coherence:** Within each module, the 5 dimensions are all about one topic.
Cross-dimensional conflicts are coherent. A `search` module doesn't need to know about
`retention` dimensions — those are separate modules that compose.

The library metaphor: modules are versioned, community-contributed, domain-specific.
Calibrated thresholds informed by real-world data (like Lighthouse's p10/median values).
Teams pick the modules relevant to their product and compose them. The selling conversation
becomes "which of these modules describes your product?" rather than "define your 5
dimensions."

---

## Hierarchical solver in perceptions: not worth it

The perceptions layer should stay computational — reshaping, aggregating, computing things
that are genuinely awkward in Z3. Adding constraint-solving there creates ambiguity about
which layer is authoritative. When a constraint fails, is it a Z3 constraint or a
perceptions constraint? Diagnostic value collapses.

If you're tempted to put a solver in perceptions, the right move is to push the logic up
to Z3 instead. The perceptions layer should remain thin.

---

## The E2E overlap insight

"5 E2E tests sharing 3 common steps — those edges get traversed redundantly, but you could
test properties about those 3 shared edges. Like 'this path can be crossed without server
error at least 4 times'."

This is a **cross-scenario aggregate constraint**: a property that is not about any single
test run, but about the test suite as a whole. No E2E test can express this. It requires a
layer that aggregates across runs.

If you add a dimension `common_path_success_count` — the count of scenarios that
successfully traversed the shared steps — you can constrain `common_path_success_count >= 4`.
This is a frequency constraint across scenarios, not a property of any individual scenario.

The implication: usersim is not a replacement for E2E tests. It is a constraint layer on
top of the E2E test suite, reasoning about properties of the entire suite at once. "Your
suite ran 6 scenarios, the common path succeeded in 5 of them, here's what that implies
about the constraint model." That framing is tractable to sell to a team that already has
E2E tests.

---

## The missing piece for convergence: solution space description

Z3 already has the machinery for this. Right now usersim uses Z3 as a checker — pass
specific values, get back pass/fail. But Z3 can also:

**Unsat core:** When a set of constraints is unsatisfiable with the current measurements,
find the minimal subset causing the contradiction. "These 3 constraints together are why
you're failing — if you fix any one of them, the others resolve."

**Model generation:** Given the constraints as a specification, ask Z3 for a satisfying
assignment. Z3 produces concrete target values: "you need D <= 2, N >= 40, F <= 4000,
P = 0." The AI agent can reason about those targets directly — "what code changes would
produce D <= 2 and N >= 40?" — rather than reasoning from a failure message.

**Distance to satisfying region:** Compute how far the current measurement vector is from
the nearest satisfying point. A scalar that tracks convergence progress across invocations.
If it is going down, the agent is moving in the right direction.

These three outputs — the unsat core (what's blocking you), the target assignment (where
you need to go), and the distance metric (how close you are) — constitute a feedback signal
that an AI coding agent can use to converge.

The existing pass/fail report is the worst possible feedback signal for an agent. It says
"these personas failed in these scenarios" which requires the agent to reverse-engineer
from persona semantics back to code changes. The target assignment says "you need N >= 40"
which the agent can map directly to "the session needs to write at least 40 notes in this
scenario."

---

## Selling it: the right frame

The 4^k coverage argument is the wrong pitch for a skeptical employer. It is too abstract
and does not explain why they should care.

**Part 1: The convergence problem.** You are running an AI coding agent. After each
invocation, you need to decide: is the code good enough, and if not, what feedback do you
give it? E2E tests give the agent a list of specific failures. The agent then attempts to
fix those specific failures, often breaking other things in the process. It is a random
walk. The more complex the codebase, the slower the convergence.

**Part 2: The specification oracle.** usersim gives the agent a description of the
behavioral region the code needs to occupy — not a list of failures. "You need session size
N >= 40 and data loss D <= 2 and friction F <= 4000." The agent can work backwards from
those targets to the code changes required. It is a gradient toward a known destination.

**The analogy:** E2E tests are like giving someone wrong turn-by-turn directions. usersim
is like giving someone a GPS destination. Same underlying technology, completely different
convergence behavior.

---

## What usersim needs to become

Given that convergence is the primary goal, the roadmap is:

1. **Modular library** — pre-built constraint modules for common domains. Reduces
   specification effort to "pick modules and wire instrumentation."

2. **Target assignment output** — Z3 model generation to produce concrete target
   measurement values when constraints fail. Agent-readable, not human-readable.

3. **Distance metric** — scalar convergence tracking across invocations. If it is going
   down, the agent is on track.

4. **Unsat core diagnosis** — identify the minimal constraint subset causing failure.
   Helps both the agent and the developer understand what is actually broken.

The current usersim is the foundation. These four additions turn it from a testing
framework into a convergence engine.

---

## On the core worry

A constraint system that is hard to populate will stay empty, and an empty constraint
system gives the agent no signal at all. That is worse than E2E tests.

The modular library directly addresses the population problem. The solution space output
directly addresses the convergence goal. The combination — pre-built modules that describe
the satisfying region, plus Z3 telling the agent the target values — is a coherent product
that solves a specific problem that nothing else addresses.

The future of usersim is not as a better test framework. It is as the feedback interface
between a running codebase and the AI agent trying to improve it.
