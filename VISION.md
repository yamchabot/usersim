# usersim — Vision & Philosophy

## The Problem

AI coding tools are compressing feature development timelines from months to days.
A single engineer with AI assistance can now ship 4–40x as many features as before.
Management is starting to expect what used to take 3–6 months to land in a week —
or a day.

This is genuinely exciting. It is also a reliability time bomb.

When features accumulate that fast, with no person or agent tracking the business
relationships between them, you get drift. You get silent regressions. You get
a codebase that technically works but slowly stops doing what users actually need.

The answer is more tests. A lot more. If you have 40x as many features, you need
at minimum 40x as many tests — and arguably exponentially more, because feature
interactions multiply. Think 100x. Think 1,000x. Think 10,000x.

The obvious problem: 40x more tests means 40x longer builds. That is untenable.
Nobody ships with a 4-day CI run.

---

## The Insight

Most of the cost in a test suite is *running the application*. The assertions
themselves are cheap. Traditional test frameworks waste this by coupling them
together: one run, one assertion, one pass/fail.

usersim decouples them.

You run a small number of *scenarios* — realistic end-to-end executions of your
application. At each step, you collect rich data: timings, counts, rates, flags,
derived values. This data becomes a set of *facts* about your system's current
behavior.

Then you hand those facts to Z3.

Z3 is a theorem prover and constraint satisfaction engine from Microsoft Research.
It is extraordinarily good at evaluating large numbers of logical assertions
against a fixed dataset — far faster than running any of those assertions
individually against a live system. Z3 does not need to touch your application
at all. It works purely on the facts you've already collected.

This is where the leverage comes from.

**One scenario run → thousands of constraint checks.**

Every persona, every threshold, every conditional rule, every interaction between
variables — Z3 evaluates them all simultaneously. The combinatorial space of
assertions that Z3 can cover from a single data collection run is enormous.
That is the point. That is the whole point.

---

## What Z3 Should Be Doing

Z3 is not just a fancy assertion library. It should be doing **heavy lifting**.

A well-designed usersim suite pushes as much logic as possible into the constraint
layer:

- **Thresholds** — `P.response_ms <= 200`, `P.error_rate <= 0.01`
- **Conditional rules** — `Implies(P.cache_warm, P.response_ms <= 50)`
- **Logical combinations** — `And(P.uptime >= 99.9, P.p99_ms <= 500)`
- **Cross-variable relationships** — `Implies(P.load_high, P.error_rate <= 0.05)`
- **Negations** — `Not(P.degraded_mode)` as a hard invariant
- **Persona-differentiated tolerances** — same facts, radically different constraint sets per user

The more constraints you express in Z3, the more effective test coverage you get
for free, with zero additional application runs. This is the combinatorial
amplification that makes usersim viable at scale.

The goal is to have constraint files that are *dense*. Many users. Many constraints
per user. Many scenarios. The scenario runs stay small; the coverage explodes.

---

## What the Perceptions Layer Is NOT For

The perceptions layer (Layer 2) is a translation step. It takes raw instrumentation
output and normalizes it into a stable set of named variables that Z3 can reason about.

It should be **thin**. Its job is:

- Rename/reshape metrics for clarity
- Compute simple derived values (rates, ratios, percentages)
- Surface facts that are definitionally binary (did the job complete? is the
  feature flag enabled?)

**What perceptions should not do:**

- Encode thresholds ("is 400ms fast?") — that belongs in persona constraints
- Make judgement calls — that is Z3's job
- Add complexity that could be expressed as Z3 constraints instead

The rule of thumb: **only add something to perceptions if it would be genuinely
awkward to express in Z3 constraints**. If you're computing a rolling percentile
from a time series, or extracting a value from a nested data structure, or doing
something stateful — that belongs in perceptions. If you're checking whether a
number is above a threshold, that belongs in Z3.

Keep perceptions boring. Let Z3 be interesting.

---

## The SRE Perspective

Traditional test suites check correctness: did this return 200? Did this render?
These are necessary but not sufficient. A system can be technically correct and
still be failing its users.

usersim checks *satisfaction*: would the on-call engineer trust this dashboard?
Would the CTO understand this screen under peak load? Would the power user tolerate
this response time in a degraded state?

These are the questions that matter for long-term reliability. They map directly
to business relationships — SLAs, user trust, churn risk. They are also the
questions that get silently broken when features ship at 40x velocity with no
one watching the aggregate.

By encoding these questions as Z3 constraints across a realistic persona space,
usersim makes them first-class citizens of your build pipeline. They run on every
commit. They fail loudly. They tell you exactly which user class breaks and under
which scenario.

That is regression coverage that scales.

---

## The Design Target

A mature usersim suite should look like this:

- **Small number of scenarios** (5–20) that exercise realistic application states
- **Rich instrumentation** that captures as many variables as the application exposes
- **Thin perceptions** that translate without editorializing
- **Many personas** (10–50+) with dense, differentiated constraint sets
- **Z3 doing thousands of checks** per run, for free, in milliseconds

The cost stays flat (bounded by scenario execution time). The coverage grows
without bound as you add personas and constraints. That is the only path to
10,000x test coverage without a 10,000x build time.
