# Setting Up Usersim for a New Project
> Agent instructions. You are configuring usersim for a project that has a working prototype
> but no usersim defined anywhere. Follow these steps in order. Each step produces artifacts
> that the next step depends on.

---

## Before You Start

Explore the prototype. Read the source code. Understand what it does, what it stores, how it
behaves when things go wrong, and what kind of person would actually use it. You cannot write
good user constraints without knowing the application.

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

**Artifact:** `user_simulation/docs/METRICS.md` — table of metric names, types, descriptions.

---

## Phase 3 — Perceptions

### Step 6: Name the perceptions as transformation functions

Perceptions are the layer between raw metrics and user judgements. Name each one as a verb
phrase that describes what the function *does*:

- **detecting** — looks for presence or count of something (`detecting outbound activity`)
- **measuring** — quantifies something experienced directly (`measuring write latency`)
- **inferring** — composite derived from multiple metrics (`inferring trust posture`)

Do not put threshold comparisons in perceptions. Those belong in Z3 constraints.

### Step 7: Map each perception to its input metrics

Make a table: perception → which metrics it reads. Some metrics will feed multiple
perceptions. Some perceptions will be pass-through (one metric in, same value out).
That is fine — the naming and grouping still carries meaning.

**Artifact:** `user_simulation/docs/PERCEPTION_PLAN.md`

### Step 8: Update each persona doc with its relevant metrics

Add a table to each persona file listing which metrics that persona cares about and what
constraint value they would expect (e.g. `== 0`, `<= 2`, `>= 1.0`). This is the bridge
between the planning documents and the code you will write.

---

## Phase 4 — Instrumentation

### Step 9: Plan the instrumentation

For each perception, describe what browser automation would actually do to collect its
input metrics. Think in terms of:
- What actions to perform (navigate, click, type, reload, go offline)
- What to observe (DOM queries, localStorage reads, request interception, timing)
- What needs to run before app code (monitoring hooks injected via `addInitScript`)
- Which metrics need their own scenario vs. which can share one

Watch for dependencies: some metrics require a fresh browser state, some require seeded data,
and the offline scenario must be isolated (it changes browser context state).

**Artifact:** `user_simulation/docs/INSTRUMENTATION_PLAN.md`

### Step 10: Implement instrumentation

Create `user_simulation/instrumentation/` with:

- **`monitor.js`** — Pre-init hooks injected before app code runs. Patches `fetch`,
  `XMLHttpRequest`, and `localStorage.setItem`/`getItem` to record events into
  `window.__monitor`. This file must work identically in jsdom and Playwright.

- **`collect.js`** — Scenario runner. Loads the app, injects monitor.js, performs
  actions, reads results, outputs a `usersim.metrics.v1` JSON document to stdout.

  Output schema:
  ```json
  {
    "schema": "usersim.metrics.v1",
    "scenario": "<name>",
    "metrics": { "<metric_name>": <number>, ... }
  }
  ```

  The scenario name comes from `process.argv[2]` or `process.env.USERSIM_SCENARIO`.

**Implementation notes:**
- Use jsdom (`npm install jsdom`) in sandboxed or CI environments without a display
- Use Playwright (`page.addInitScript()`) for real browser testing — `monitor.js` is identical
- Share a single localStorage shim object across DOM instances to simulate reloads
- For `autosave_latency_ms`: patch `localStorage.setItem` to record timestamps, then
  compare write timestamp to keystroke timestamp
- For external dependencies: static analysis of the HTML source is sufficient and more
  reliable than runtime interception
- For offline simulation: monitor.js already rejects all fetch/XHR — just test that
  core operations still succeed

**Test each scenario independently before moving on:**
```
node user_simulation/instrumentation/collect.js baseline
node user_simulation/instrumentation/collect.js capture_path
...
```

---

## Phase 5 — Perceptions Code

### Step 11: Write `user_simulation/perceptions.py`

```python
def compute(metrics, scenario=None, person=None):
    def get(key, default=0.0):
        v = metrics.get(key, default)
        return float(v) if v is not None else default

    # Pass-through: relay single metrics directly
    # Combining: produce values that no single metric expresses alone
    # Inferring: composite scores from multiple metrics

    return { ... }
```

**Combining perception examples worth building:**
- Sum of all request counts across phases → total network exposure regardless of timing
- Sum of all arrival barriers → total friction before the user can do anything
- Ratio of `notebook_key_count / notebook_count` → isolation quality (1.0 = perfect)
- Ratio of `notes_after_reload / notes_before_reload` → data integrity rate
- Weighted composite of speed + steps + latency + barriers → capture readiness score

**Rule:** return `1.0` (not `0.0`) for ratios when neither input metric was measured in
the current scenario. A missing measurement is not a failure.

---

## Phase 6 — User Constraint Files

### Step 12: Write one Python file per persona in `user_simulation/users/`

```python
from usersim.judgement.person import Person

class MyPersona(Person):
    name    = "Display Name"
    role    = "Job title / description"
    goal    = "One sentence personal goal"
    pronoun = "they"  # or "he", "she"

    def constraints(self, P):
        return [
            P.some_perception == 0,
            P.another_perception <= 2,
            P.ratio_perception >= 1.0,
        ]
```

Write constraints that reflect what this person actually cares about — not a generic
checklist. A constraint that every persona shares is probably not doing useful work.

Calibrate thresholds to what the instrumentation actually produces. Run a scenario first,
read the perception values, then set constraints that should pass for a working app and
fail if the app regresses on that dimension.

---

## Phase 7 — Configuration and First Run

### Step 13: Write `usersim.yaml` at the project root

```yaml
version: 1

instrumentation: node user_simulation/instrumentation/collect.js

perceptions: user_simulation/perceptions.py

users:
  - user_simulation/users/*.py

scenarios:
  - baseline
  - capture_path
  - persistence
  - ...

output:
  results: user_simulation/results.json
  report:  user_simulation/report.html
```

The instrumentation command runs from the directory containing `usersim.yaml`.
`USERSIM_SCENARIO` is set automatically by the runner for each scenario.

### Step 14: Run and verify

```
usersim run --verbose
```

All checks should pass before committing. If any fail:
1. Check whether the constraint threshold is wrong (too strict for what the app produces)
2. Check whether the perception is computing correctly (intermediate values)
3. Check whether the instrumentation is actually measuring the thing (not returning 0 by default)

---

## File Structure Reference

```
my-app/
  src/                               ← the application
  user_simulation/
    docs/
      USERSIM_SETUP.md               ← this file
      METRICS.md
      PERCEPTION_PLAN.md
      INSTRUMENTATION_PLAN.md
      USER_PERSONAS.md
      personas/
        <persona-name>.md            ← one per persona
    instrumentation/
      monitor.js                     ← pre-init hooks (browser-agnostic)
      collect.js                     ← scenario runner
      package.json
    users/
      <persona_name>.py              ← one per persona
    perceptions.py
    results.json                     ← gitignore
    report.html                      ← gitignore
  usersim.yaml
```

---

## Principles to Keep in Mind

- **People first, metrics second.** The constraint system should feel like a natural
  expression of what a real person would care about — not a technical checklist.

- **Measurements report. Judgements decide.** A metric says what happened.
  A Z3 constraint says whether that is acceptable. Never conflate the two.

- **Booleans belong in Z3.** If you find yourself writing a boolean metric, convert it
  to a count. The Z3 constraint `count == 0` is more expressive and composable.

- **Perceptions are verb phrases.** `detecting outbound activity`, `measuring write latency`,
  `inferring trust posture`. The verb tells you what kind of transformation it is.

- **Test the instrumentation before writing the constraints.** You cannot write good
  thresholds without seeing what the app actually produces.

- **Diverse personas produce diverse constraints.** If two personas have identical
  constraint sets, one of them is not pulling its weight.
