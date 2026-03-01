# Formal Analysis Methods: Comparison with Constraint-Based Testing

Notes from discussion on 2026-03-01.

---

## The landscape by analysis substrate

The fundamental split is what the method actually operates on:

| Substrate | Methods | When |
|---|---|---|
| Formal system model | TLA+, Alloy, Event-B, CSP | Design time |
| Source code (static) | Abstract interpretation, symbolic execution, Dafny | Pre-deploy |
| Hazard/causal structure | STPA/STAMP, FTA, FMEA, HAZOP | Design time |
| Running system (runtime) | Runtime verification, property-based testing, usersim | Test/deploy |

usersim is in the last row. It does not require a formal model of the system and does not
analyze source code. It observes real behavior and checks constraints against measurements.

---

## Method-by-method comparison

### TLA+ (Temporal Logic of Actions — Lamport)

Write a formal specification of the system — valid states, allowed transitions, initial
conditions. The TLC checker exhaustively explores all reachable states and verifies temporal
properties: "it is always the case that after a write, any subsequent read returns at least
that value." AWS uses this for distributed protocol design; it caught 10 serious bugs in
their internal systems that code review missed.

**Coverage model:** Complete over the state space of the formal model. For a model with
10^8 states, all states are checked. If the property holds in the model, it holds for any
execution consistent with the model.

**The gap:** TLA+ proves properties about the *specification*, not the running system. The
running system may not implement the spec correctly. Requires deep formal modeling expertise.

**vs. usersim:** TLA+ is pre-implementation, model-level, with complete guarantees over
the model. usersim is post-implementation, measurement-level, with partial guarantees over
observed scenarios. TLA+ asks "can this ever break?" usersim asks "did this break in any
of these scenarios?"

---

### Alloy (Daniel Jackson, MIT)

Relational first-order logic over bounded domains. Specifies data structure invariants and
object relationships; the Alloy Analyzer finds counterexamples within a bounded scope
(e.g., up to 4 instances of each type). Key insight: "small scope hypothesis" — most bugs
show up with small instances, so bounded checking is sufficient in practice.

**Coverage model:** Exhaustive within the scope bound. Not complete, but high confidence
from the small-scope hypothesis.

**vs. usersim:** Structurally the closest in spirit — both write relational constraints and
ask a solver to check them. The difference: Alloy checks a formal model for
satisfiability/counterexamples; usersim checks concrete measurements for constraint
satisfaction. Alloy finds whether a property CAN be violated; usersim checks whether it
WAS violated in a specific run.

---

### Abstract Interpretation (Astrée, PolySpace, IKOS)

Statically computes an over-approximation of all possible program states without running
the code. Represents variable values as abstract domains (intervals, polyhedra) and
propagates them through the control flow graph. Can prove "this variable is always in
[0, 100]" for ALL inputs. Sound but incomplete: no false negatives, but may report false
alarms. Airbus used Astrée on A380 flight software — proved absence of all runtime errors
in ~130,000 lines of C.

**Coverage model:** Sound over ALL inputs within the abstract domain.

**vs. usersim:** White-box (requires source), proves properties for all inputs, targets
code-level properties (no null dereference, no overflow). usersim is black-box, checks
properties for observed scenarios, targets behavioral properties (friction, data loss,
privacy). The domains don't overlap — you would use both.

---

### Dafny / F* / Why3 / SPARK (Deductive Verification / Design by Contract)

Annotate each function with preconditions, postconditions, and loop invariants. A
verification condition generator extracts proof obligations, which an SMT solver (often Z3)
proves correct. If verification passes, the function is provably correct with respect to
its specification for all inputs satisfying the precondition.

**Coverage model:** Complete for specified functions — the proof covers all inputs.

**vs. usersim:** DBC is per-function and proves functional correctness. usersim is
per-scenario and checks behavioral properties of the whole running system. A function can
be deductively verified correct and still contribute to a system that fails usersim's
constraints — usersim's constraints describe emergent behavior across scenarios, not
individual function behavior. Complementary layers.

---

### STPA / STAMP (Leveson, MIT)

STAMP reframes accidents as control failures: the system is a hierarchy of controllers
(humans, software, hardware) that issue commands and receive feedback. STPA identifies
Unsafe Control Actions (UCAs) — four types: action not provided when needed, wrong action
provided, wrong timing, wrong duration.

From UCAs, STPA builds causal scenarios: what conditions in the control structure could
lead each UCA to occur? Produces a set of design constraints that, if satisfied, prevent
the hazard. Used in aviation (NASA, Boeing), automotive (ISO 26262 complement), medical
devices, cybersecurity.

**vs. usersim:** STPA is pre-implementation, produces design requirements, applies to
safety-critical hazards. usersim is post-implementation, verifies behavioral constraints,
applies to UX properties. They work together: STPA identifies what constraints matter
(what UCAs would hurt users), usersim tests whether those constraints hold at runtime.
STPA produces the *list of properties to check*; usersim does the *checking*.

---

### HAZOP (Hazard and Operability Study)

Systematic brainstorming using guidewords (MORE, LESS, NO, REVERSE, OTHER THAN, AS WELL
AS, PART OF) applied to design intentions. A multidisciplinary team assesses each
(parameter, guideword) combination: what deviation could occur, what are its consequences,
what safeguards exist? Produces a risk register. Developed at ICI in the 1960s for
chemical plant design; now used in oil and gas, pharmaceuticals, nuclear. Has been adapted
for software (Software HAZOP).

**vs. usersim:** HAZOP is structured human elicitation — it generates the question list,
not the answers. No computation involved. Excellent at finding scenarios that automated
methods miss (unexpected human+system combinations) but produces no formal guarantees.
usersim is the automated checking step after HAZOP identifies what to check.

---

### FTA (Fault Tree Analysis) / FMEA (Failure Mode and Effects Analysis)

**FTA** is top-down: start from a top-level failure event, decompose into contributing
causes connected by AND/OR gates. Boolean algebra gives minimal cut sets (minimum
combinations of component failures causing the top event). Quantitative FTA assigns failure
probabilities.

**FMEA** is bottom-up: enumerate every component's failure modes, assess severity,
occurrence, and detectability, compute Risk Priority Numbers. Standard in automotive
(DFMEA, PFMEA), aerospace, medical devices.

**vs. usersim:** Both FTA and FMEA model causal chains to failure. usersim does not model
causation — it measures outcomes. FTA can tell you that "search failure AND data loss" is
a minimal cut set; usersim checks whether S > 0 AND D > 0 was observed in any scenario.
FTA is predictive (what could happen); usersim is verificatory (did it happen).

---

### Model Checking (SPIN, NuSMV, UPPAAL)

Exhaustively explores all reachable states of a finite state machine and checks temporal
logic properties. SPIN checks concurrent systems with message passing (LTL). NuSMV handles
synchronous hardware-like models (CTL/LTL). UPPAAL handles timed automata with real-time
constraints. State space explosion limits practical application to ~10^8–10^9 states,
handled by symbolic techniques (BDD-based) and abstraction.

**vs. usersim:** Complete over the formal model but requires the state machine to be
written. usersim has no state machine model and checks nothing about event ordering or
concurrency. UPPAAL could check timing properties across all scenarios; usersim checks
relational properties (friction proportional to session size). Both use constraint-solving
internally but address different properties.

---

### Runtime Verification (RV-Monitor, Larva, E-ACSL)

Generates monitors from formal property specifications (LTL, regular expressions, temporal
patterns) that run alongside the system at runtime. The monitor receives event streams and
checks whether the execution trace satisfies the specified properties.

**Coverage model:** All events in the observed execution, for the specified properties.

**vs. usersim:** Runtime verification checks *temporal* properties over event sequences:
"A is always followed by B before C." usersim checks *relational* properties over aggregate
measurements: "data loss count bounded proportionally by session size." RV sees individual
events; usersim sees accumulated metrics. They can be stacked: RV generates the event
trace, usersim's perceptions layer aggregates it into dimensions.

---

### Property-Based Testing (QuickCheck, Hypothesis)

Generate random inputs according to a strategy, check that properties hold. Hypothesis adds
stateful machines with @invariant decorators. When a failure is found, the framework
shrinks the input to the minimal counterexample.

**Coverage model:** Random over the input space with bias toward edge cases. Not exhaustive,
but coverage grows with examples run.

**vs. usersim:** PBT generates inputs, runs code, checks properties on outputs — all at
the function level. usersim runs designed scenarios, measures system behavior, checks
constraints on measurements — at the system level. Hypothesis's @invariant is the closest
structural analog to usersim's constraints. Key difference: Hypothesis properties are about
function outputs (is_sorted(sort(xs))); usersim constraints are about behavioral dimensions
(D * 20 <= N).

---

### Symbolic Execution (KLEE, angr, SAGE)

Executes code with symbolic inputs. Every branch condition becomes a constraint over the
symbolic inputs. At each branch, both directions are explored by solving the accumulated
constraint system. Generates concrete test inputs that trigger each path. SAGE (Microsoft)
found 1/3 of all bugs found by fuzzing in Windows 7.

**vs. usersim:** White-box, works at the instruction level, finds specific inputs that
trigger bugs. usersim is black-box, works at the behavioral measurement level, checks
invariants over designed scenarios. Different domains entirely — symbolic execution for
correctness and security, usersim for behavioral/UX properties.

---

## Summary table

| Method | When | Operates on | Coverage model | Guarantee | Barrier |
|---|---|---|---|---|---|
| TLA+ | Design | Formal model | Complete over model state space | Properties hold for all model executions | Very high |
| Alloy | Design | Formal model | Exhaustive within scope bound | Counterexample-complete for small scope | High |
| Abstract Interpretation | Pre-deploy | Source code | Sound over all inputs | No false negatives | High |
| Dafny / DBC | Implementation | Annotated source | Complete for specified functions | Proved correct for all inputs | Medium-high |
| Model Checking | Design | Formal state machine | Complete up to state explosion | Properties hold for all reachable states | High |
| STPA/STAMP | Design | Control structure | Systematic over UCAs | All UCAs identified | Medium |
| HAZOP | Design | Process intent | Guideword-systematic | All deviations enumerated | Medium |
| FTA/FMEA | Design | Component failures | Enumerated failure modes | Cut sets / RPN computed | Medium |
| Property-Based Testing | Test | Functions + generated inputs | Random with shrinking | Confidence grows with examples | Low |
| Symbolic Execution | Test | Source code | All control-flow paths | Path-complete bug finding | High |
| Runtime Verification | Runtime | Event trace | All observed events | Temporal property violations detected | Medium |
| **usersim** | **Test/runtime** | **Behavioral measurements** | **Cross-dimensional constraint regions** | **Observed scenarios satisfy invariants** | **Low** |

---

## Where usersim sits uniquely

No other method in this landscape simultaneously:
1. Runs against the real system (not a model)
2. Checks behavioral/UX properties (not functional correctness, not safety hazards, not code properties)
3. Uses cross-dimensional constraint satisfaction over aggregate measurements
4. Requires no formal system model, no source access, no annotations

The closest structural relatives are Alloy (relational constraints, SMT-backed) and Runtime
Verification (real system, property checking). usersim is roughly "Alloy's constraint logic
applied to Runtime Verification's measurement stream, for UX properties instead of data
structure invariants."

The practical gap it fills: after STPA tells you what behavioral constraints matter, and
before formal verification proves individual functions correct, usersim checks whether the
running system's behavioral measurements satisfy those constraints across the scenario space.
It is the middle layer that currently has no standard occupant.
