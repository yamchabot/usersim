# Setting Up Usersim for a New Project

> Agent instructions. You are configuring usersim for a project that has a working prototype
> but no usersim defined anywhere. Follow these steps in order. Each step produces artifacts
> that the next step depends on.

---

## The Method

**Plan in markdown first. Write code second.**

The value of usersim comes from thinking carefully about who uses this application and what
they actually need — before touching any code. The planning documents are the deliverables.
Once you have good markdown, the code is transcription.

Do not skip phases or combine them. Each phase depends on the output of the previous one.
If a later phase feels hard, it usually means an earlier phase was incomplete.

---

## The Pipeline

usersim has three layers. Each has a strict job and must not do the job of another.

**Instrumentation** is the witness. It connects to the application — through whatever
interface the application exposes — and records what happened. Raw counts, timings, state
snapshots, emitted events. No interpretation. A witness who draws conclusions is out of
order; instrumentation that computes answers has overstepped.

**Perceptions** is the analyst. It reads the raw witness record and compresses it into
meaningful signals: aggregations, ratios, derived quantities that no single measurement
expresses alone. The analyst explains what the evidence means — still without rendering
a verdict. A perception that returns a boolean has made a decision it shouldn't make.

**Judgement** is the ruling. Z3 evaluates each user's constraints against the perceptions.
Given what the analyst reported, was this person's standard met? Every boolean claim —
"this was too slow", "this should never happen", "if X then Y must hold" — lives here and
only here. This is where the constraint solver earns its place.

The discipline: **stay in your lane.** Raw data belongs in instrumentation. Computation
belongs in perceptions. Decisions belong in Z3.

---

## Before You Start

Explore the prototype. Read every source file. Understand what it does, what it stores,
how it behaves when things go wrong, and what kind of person would actually use it. You
cannot write good user constraints without knowing the application.

**Do not skip this.** Everything downstream depends on it.

---

## Phase 1 — Users

### Step 1: Identify user types

Brainstorm 10–15 types of people who would want this application. Think about:
- What problem does this app solve, and who has that problem most acutely?
- What contexts would someone be in when they reach for this kind of tool?
- Who would care most if it broke, leaked data, ran slowly, or was confusing?
- Who would choose this over alternatives, and why?

Write each as a short label and a one-sentence personal goal statement. Example:
> **The Privacy-First User** — *"Use a notes app that never transmits data externally."*

Do not write about the app's features. Write about the person's situation.

### Step 2: Select 5 representative personas

Choose 5 whose perspectives are meaningfully different from each other. Diversity matters —
if two personas would write identical constraints, they are not both needed.

### Step 3: Write 7 User Benefits per persona

For each persona, write 7 statements in their voice describing what they get out of the app.
These are not features. They are outcomes. Examples of the difference:

- ❌ Feature: *"The app auto-saves."*
- ✅ Benefit: *"I switch away from the tab and trust that what I wrote is still there."*

Format: first person, present tense, concrete situation.

### Step 4: Expand each benefit into how the app delivers it

For each of the 7 benefits, write a paragraph describing which specific behaviour of this
specific application produces that outcome. Ground it in the app — not in vague UX principles.

**Artifact:** `user_simulation/docs/USER_PERSONAS.md` (overview) and
`user_simulation/docs/personas/<name>.md` (one file per persona with all 7 benefits expanded).

---

## Phase 2 — Metrics

### Step 5: Derive measurable quantities from the benefit descriptions

Read the persona files and ask: *what would you actually observe to confirm this benefit is
being delivered?* Produce a flat list of things that can be measured by instrumentation.

**Rules:**
- Every metric is a count (`_count`) or a measurement (`_ms`, `_days`, `_bytes`, `_ratio`)
- No booleans. A boolean is an answer. Metrics report evidence; judgements give answers.
- Convert every boolean you think of into a count of failures or occurrences.
  - `auth_required: false` → `auth_prompt_count` (constraint will be `== 0`)
  - `data_survived: true` → `reload_loss_count` (constraint will be `== 0`)

**Artifact:** `user_simulation/docs/METRICS.md` — table of metric names, types, descriptions,
and which persona benefit motivated each one.

---

## Phase 3 — Perceptions

### Step 6: Name the perceptions as verb phrases

Perceptions are the analyst layer — they read the raw witness record and extract meaningful
signals. Name each one as a verb phrase describing what the function does:

- **detecting** — looks for presence or count of something (`detecting outbound activity`)
- **measuring** — quantifies something experienced directly (`measuring write latency`)
- **inferring** — composite derived from multiple metrics (`inferring trust posture`)

The naming matters: it keeps perceptions honest about their role. An `inferring` perception
is explicitly a derived signal, not a raw observation. A `detecting` perception is explicitly
counting evidence, not deciding whether that evidence is acceptable.

Do not put threshold comparisons in perceptions. Those belong in Z3 constraints.

### Step 7: Map each perception to its input metrics

Make a table: perception → which metrics it reads. Some metrics will feed multiple
perceptions. Some perceptions will be pass-through (one metric in, same value out).
That is fine — the naming and grouping still carries meaning.

**Artifact:** `user_simulation/docs/PERCEPTION_PLAN.md`

### Step 8: Update each persona doc with its relevant perceptions

Add a table to each persona file listing which perceptions that persona cares about and what
constraint value they would expect (e.g. `== 0`, `<= 2`, `>= 1.0`). This is the bridge
between the planning documents and the code you will write next.

---

## Phase 4 — Instrumentation

> **Web project?** If the application runs in a browser, read `.claude/skills/web.md`
> before implementing this phase. It provides a ready-made scenario runner and page
> automation API so you don't have to write that boilerplate yourself.

### Step 9: Plan the scenarios

For each perception, describe what the instrumentation would actually do to collect its
input metrics. Think in terms of:
- What actions to perform (navigate, click, type, reload, simulate offline)
- What to observe (DOM state, storage reads, request counts, timing)
- What needs to be captured before or alongside application code
- Which metrics need their own isolated scenario vs. which can share one

Group related metrics into named scenarios. Watch for dependencies: some metrics require
a fresh state, some require seeded data, and some (like offline simulation) must be isolated
because they alter the environment.

**Artifact:** `user_simulation/docs/INSTRUMENTATION_PLAN.md` — one section per scenario,
listing which metrics it collects and what actions it performs.

### Step 10: Implement the instrumentation

Instrumentation connects to the application through whatever interface it exposes. The
interface depends entirely on what the application is:

- **Browser app** — DOM queries, network interception, storage reads, timing APIs
- **React or stateful frontend** — the app developer registers data with usersim via hooks
  (see embedded hooks below), because internal component state is not queryable from outside
- **Canvas or SVG rendering** — intercept the data going *into* the renderer, not the pixels
  coming out; hook the draw calls or the data structures feeding them
- **REST API or backend service** — an HTTP client making scripted requests, recording
  response bodies, status codes, and latency
- **Microcontroller or embedded device** — read from serial/UART, parse protocol frames,
  record sensor values
- **Kubernetes or distributed system** — query the metrics API, watch events, record
  pod counts and error rates
- **Bluetooth or radio protocol** — intercept the packet stream, log connection events
  and payload content

In all cases, instrumentation is a witness: it records what it observed without
summarising, filtering, or deciding what matters. If you are not sure whether a data
point is relevant, include it — the perceptions layer will decide.

**Embedded hooks**

When the application's internal state is not observable from outside — component trees,
in-memory data structures, renderer inputs — the application developer adds small
registration points that emit data to usersim:

```js
// In the application code:
window.__usersim?.emit('habit_saved', { id, streak });
window.__usersim?.register('habit_count', () => store.habits.length);
```

The instrumentation layer reads these emitted events and registered values. This keeps
the hooks in the application thin (one line per data point) while letting instrumentation
collect them without modifying application behaviour in any other way.

**Scenario runner**

The scenario runner loads the application, connects monitoring, performs the actions
described in the plan, collects the recorded values, and writes a metrics document
to stdout:

```json
{
  "schema":   "usersim.metrics.v1",
  "scenario": "<name>",
  "metrics":  { "<metric_name>": <number> }
}
```

The scenario name comes from a command-line argument or environment variable
(`USERSIM_SCENARIO`). One runner file should support all scenarios via a branch or
dispatch table — not separate files per scenario.

**Test each scenario independently before moving on:**
```
<runner command> baseline
<runner command> persistence
...
```

Each should print valid JSON with no errors before you proceed.

---

## Phase 5 — Perceptions Code

### Step 11: Write `user_simulation/perceptions.py`

```python
def compute(metrics, scenario=None, person=None):
    def get(key, default=0.0):
        v = metrics.get(key, default)
        return float(v) if v is not None else default

    return {
        # Pass-through: relay single metrics directly
        "detecting_outbound_requests": get("fetch_call_count") + get("xhr_call_count"),

        # Combining: produce values that no single metric expresses alone
        "inferring_data_integrity": (
            get("notes_after_reload", 1.0) / max(get("notes_before_reload", 1.0), 1.0)
        ),

        # ... one entry per perception from PERCEPTION_PLAN.md
    }
```

**Rules:**
- Return `1.0` (not `0.0`) for ratio perceptions when neither input metric was measured in
  the current scenario. A missing measurement is not evidence of failure.
- Every key in the returned dict must appear in `PERCEPTION_PLAN.md`. No extras, no missing.
- The function signature must accept `scenario` and `person` as keyword arguments even if
  unused — the runner passes them.

---

## Phase 6 — User Constraint Files

### Step 12: Write one Python file per persona in `user_simulation/users/`

```python
from usersim import Person

class StreakChaser(Person):
    name    = "streak_chaser"
    role    = "Daily habit tracker"
    goal    = "Never break a streak"
    pronoun = "they"

    def constraints(self, P):
        return [
            P.measuring_persistence_fidelity >= 1.0,
            P.detecting_duplicate_prevention == 0,
        ]
```

`P` is a namespace — access any perception by its exact key name as an attribute.
`P.some_perception` returns a Z3 expression. Use standard comparison operators.

For conditional constraints:
```python
from usersim.judgement.z3_compat import Implies

Implies(P.habit_count >= 10, P.measuring_render_time <= 200)
# "If there are 10+ habits, render time must be under 200ms"
```

**Calibration:** run a scenario first and read the actual perception values before setting
thresholds. A constraint that always passes or always fails is not providing signal.

**Diversity check:** if two personas have nearly identical constraint sets, one of them is
not doing useful work. Return to Phase 1 and reconsider.

---

## Phase 7 — Configuration and First Run

### Step 13: Write `usersim.yaml` at the project root

```yaml
version: 1

instrumentation: <command to run the scenario runner>

perceptions: user_simulation/perceptions.py

users:
  - user_simulation/users/*.py

scenarios:
  - baseline
  - persistence
  - ...

output:
  results: user_simulation/results.json
  report:  user_simulation/report.html
```

The instrumentation command runs from the directory containing `usersim.yaml`.
`USERSIM_SCENARIO` is injected automatically by the runner for each scenario.

### Step 14: Run and verify

```
usersim run
```

All checks should pass before committing. If any fail:
1. Check whether the threshold is wrong — run a scenario manually and read the raw values
2. Check whether the perception is computing correctly — print intermediate values
3. Check whether the instrumentation is actually measuring the intended thing (not returning
   a default zero because the hook never fired)

---

## File Structure Reference

```
my-app/
  src/                                    ← the application
  user_simulation/
    docs/
      USER_PERSONAS.md                    ← persona overview
      METRICS.md                          ← all measurable quantities
      PERCEPTION_PLAN.md                  ← metric → perception mapping
      INSTRUMENTATION_PLAN.md             ← scenarios and what they collect
      personas/
        <persona-name>.md                 ← one per persona
    instrumentation/
      <runner files>                      ← scenario runner + monitoring hooks
    users/
      <persona_name>.py                   ← one per persona
    perceptions.py
    results.json                          ← gitignore
    report.html                           ← gitignore
  usersim.yaml
```

---

## Principles

- **People first, metrics second.** The constraint system should feel like a natural
  expression of what a real person would care about — not a technical checklist.

- **Stay in your lane.** Instrumentation witnesses. Perceptions interprets. Z3 decides.
  A layer that does another layer's job produces results that are harder to inspect,
  harder to debug, and harder to trust.

- **Booleans belong in Z3.** If you find yourself writing a boolean metric or a boolean
  perception, convert it to a count or ratio. The Z3 constraint `count == 0` is more
  expressive, composable, and auditable than a flag that was set somewhere upstream.

- **Perceptions are verb phrases.** `detecting outbound activity`, `measuring write latency`,
  `inferring trust posture`. The verb signals what kind of transformation it is and keeps
  the analyst honest about what it is and isn't doing.

- **Test the instrumentation before writing the constraints.** You cannot set good
  thresholds without seeing what the app actually produces.

- **Diverse personas produce diverse constraints.** If two personas have identical
  constraint sets, one of them is not pulling its weight.

- **The plan is the hard part.** If the markdown is right, the code will follow easily.
  If the code is hard to write, the plan is probably incomplete.
