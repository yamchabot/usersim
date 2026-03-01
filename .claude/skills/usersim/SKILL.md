# usersim — Project Setup

> Agent instructions for setting up usersim on a new project.
> This file covers planning and documentation. Load sub-skills for implementation.

---

## Sub-skills — load these when you reach each phase

| When you're about to... | Load this file |
|------------------------|---------------|
| Write `instrumentation.py` or `collect.js` | `.claude/skills/usersim/INSTRUMENTATION.md` |
| Write `perceptions.py` | `.claude/skills/usersim/PERCEPTIONS.md` |
| Write persona constraint files | `.claude/skills/usersim/CONSTRAINTS.md` |
| Application runs in a browser | `.claude/skills/usersim/web.md` (replaces INSTRUMENTATION.md) |

Read the sub-skill **before** writing the code for that layer, not after.
Each sub-skill is self-contained — you don't need to hold the others in context simultaneously.

---

## What usersim is

usersim is a **coverage engine**. It answers: for every type of person who uses this system,
across every scenario it can be in, do the things that person care about hold true?

The combinatorial power is Z3. A constraint `wall_ms <= persons * scenarios * 3000` isn't
one test — it's satisfiability over the full domain of those variables. 15 personas × 6
scenarios × ~50 constraints × avg 3 variables ≈ 86,000 effective test assertions from a
single run. Not test count. **Coverage of relationships.**

### The three layers

```
instrumentation  →  perceptions  →  Z3 judgement
  (witness)          (analyst)        (ruling)
```

Each has a strict job. A layer doing another's job produces results harder to inspect and trust.

- **Instrumentation** witnesses: records raw facts, no interpretation
- **Perceptions** interprets: compresses raw facts into meaningful signals
- **Z3** rules: evaluates every boolean claim against those signals

---

## Before you write any code: explore the application

Read every source file. Understand what the application does, what it stores, how it behaves
when things go wrong, and what kind of person would actually use it. You cannot write good
user constraints without knowing the application.

**Do not skip this.** Everything downstream depends on it.

---

## Phase 1 — Persona brainstorming

### Step 1: Identify 10–15 user types

Think broadly about who would use this application:
- Who has the problem this app solves most acutely?
- Who would care most if it broke, leaked data, ran slowly, or was confusing?
- Who would choose this over alternatives, and why?
- What contexts would someone be in when they reach for this tool?

Write each as a label and a one-sentence personal goal statement.
> **The Privacy-First User** — *"Use a notes app that never transmits data externally."*

Write about the person's situation, not the app's features.

### Step 2: Select 5–8 representative personas

Choose personas whose perspectives are meaningfully different from each other. Aim to cover
at least four of these concern dimensions:

| Concern | Example | What they add |
|---------|---------|--------------|
| Operational | SRE, DevOps | Timing SLOs, exit-code contracts, artifacts |
| Correctness | QA, Researcher | Coverage completeness, soundness, schema |
| Safety | Security, Compliance | Denial paths, no leakage, audit trail |
| Experience | DevEx, TechWriter | Onboarding friction, clarity, self-documentation |
| Outcome | PM, ML Engineer | Story satisfaction, behavioral contracts |
| Extension | OSS Contributor | Non-regression, extension surface, docs |

If two personas would write identical constraints, they are not both needed.

### Step 3: Write 7 user benefits per persona

For each persona, write 7 statements in their voice describing what they get out of the app.
These are outcomes, not features:

- ❌ Feature: *"The app auto-saves."*
- ✅ Benefit: *"I switch away from the tab and trust that what I wrote is still there."*

First person, present tense, concrete situation.

### Step 4: Expand each benefit

For each of the 7 benefits, write a paragraph describing which specific behaviour of this
application produces that outcome. Ground it in the app — not in vague UX principles.

**Artifact:** `user_simulation/docs/USER_PERSONAS.md` (overview) and
`user_simulation/docs/personas/<name>.md` (one file per persona, all 7 benefits expanded).

---

## Phase 2 — Metrics

### Step 5: Derive measurable quantities from the benefit descriptions

Read the persona files and ask: *what would you actually observe to confirm this benefit
is being delivered?* Produce a flat list of things instrumentation can measure.

**Rules:**
- Every metric is a count (`_count`), measurement (`_ms`, `_bytes`), or raw integer
- **No booleans.** A boolean is an answer. Metrics report evidence; Z3 gives answers.
- Convert every boolean you think of into a count of failures or a raw code:
  - `auth_required: false` → `auth_prompt_count` (Z3 constraint: `== 0`)
  - `data_survived: true` → `reload_loss_count` (Z3 constraint: `== 0`)
  - `pipeline_passed: true` → `pipeline_exit_code` (Z3 constraint: `== 0`)

**Artifact:** `user_simulation/docs/METRICS.md`

| metric_name | type | description | persona benefit |
|-------------|------|-------------|----------------|
| `exit_code` | int | main process exit code | All personas |
| `wall_ms` | int | total wall clock time ms | SRE, DevOps |
| `file_count` | int | files created by init | DevEx, OSS |

---

## Phase 3 — Perception planning

### Step 6: Map metrics to perception signals

Perceptions are the analyst layer. Name each one as a verb phrase:
- **detecting** — looks for presence or count (`detecting_outbound_requests`)
- **measuring** — quantifies something experienced directly (`measuring_write_latency`)
- **inferring** — composite derived from multiple metrics (`inferring_data_integrity`)

The naming signals the transformation type and keeps the analyst honest about its role.

**Rules:**
- No threshold comparisons — those belong in Z3
- No booleans — pass the raw number, Z3 decides if it's acceptable
- One entry per meaningful signal

**Artifact:** `user_simulation/docs/PERCEPTION_PLAN.md`

| perception_name | reads from | notes |
|----------------|-----------|-------|
| `pipeline_exit_code` | `exit_code` | pass-through |
| `pipeline_wall_clock_ms` | `wall_ms` | pass-through |
| `results_satisfied` | `satisfied_count` | pass-through |
| `results_total` | `total_count` | **don't** compute ratio here |

### Step 7: Update each persona doc with its relevant perceptions

Add a table to each persona file listing which perceptions that persona cares about and what
constraint value they would expect (e.g. `== 0`, `<= 500ms`, `>= 1`). This is the bridge
from planning docs to persona constraint code.

---

## Phase 4 — Implementation

At this point you have all the planning docs. Implementation is transcription.

**Load the sub-skills as you reach each layer:**

```
instrumentation.py  →  read INSTRUMENTATION.md (or web.md for browser apps)
perceptions.py      →  read PERCEPTIONS.md
users/*.py          →  read CONSTRAINTS.md
```

---

## usersim.yaml

```yaml
version: 1

instrumentation: "python3 user_simulation/instrumentation.py"
perceptions: user_simulation/perceptions.py

users:
  - user_simulation/users/*.py

scenarios:
  - name: normal_run
    description: "Full pipeline on example input — verifies end-to-end output"
  - name: bad_config
    description: "Broken config — verify clean non-zero exit"
  - name: full_integration
    description: "All subsystems in one pass — no vacuous antecedents"

output:
  results: user_simulation/results.json
  report:  user_simulation/report.html
```

---

## Checking a completed setup

```bash
# Full run
usersim run --config usersim.yaml

# Check effective test count and pass rate
python3 -c "import json; print(json.load(open('user_simulation/results.json'))['summary'])"

# Check for vacuous constraints (should be 0 on full_integration)
python3 -c "
import json
r = json.load(open('user_simulation/results.json'))
vac = [(x['person'], x['scenario'], c['label'])
       for x in r['results']
       for c in x.get('constraints', [])
       if c.get('antecedent_fired') is False]
print(f'{len(vac)} vacuous')
for p,s,l in vac[:20]: print(f'  {p}/{s}: {l}')
"
```

---

## File structure

```
my-project/
  src/                              ← the application
  user_simulation/
    docs/
      USER_PERSONAS.md              ← persona overview
      METRICS.md                    ← measurable quantities
      PERCEPTION_PLAN.md            ← metric → perception mapping
      personas/
        <persona_name>.md           ← one per persona, 7 benefits expanded
    users/
      <persona_name>.py             ← one per persona
    constraint_library.py           ← shared constraint groups
    instrumentation.py              ← scenario runner (or collect.js for web)
    perceptions.py                  ← signal computation
    results.json                    ← gitignore
    report.html                     ← gitignore
  usersim.yaml
```

---

## Principles

**The plan is the hard part.** If the persona docs and metrics table are right, the code
is transcription. If the code is hard to write, the plan is probably incomplete.

**People first, metrics second.** Constraints should feel like a natural expression of what
a real person cares about — not a technical checklist.

**Diverse personas produce diverse constraints.** If two personas have nearly identical
constraint sets, one of them is not doing useful work.

**Booleans belong in Z3.** Every boolean you're tempted to compute in instrumentation or
perceptions is a constraint in disguise. Pass the raw value; let Z3 decide.

**Stay in your lane.** Instrumentation witnesses. Perceptions interprets. Z3 decides.
