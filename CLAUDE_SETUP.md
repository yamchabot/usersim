# Using usersim as a Claude Code Stop Hook

Configure `usersim run` as a Claude Code Stop hook so the agent cannot
finish a task until all user simulation checks pass.

When Claude tries to stop, usersim runs the full pipeline. If any persona's
constraints fail, the hook exits 2 and the narrative (who is unsatisfied,
which constraints failed, in which scenarios) is written to stderr — where
Claude reads it and knows what to fix before it can finish.

---

## Prerequisites

1. usersim installed and `usersim.yaml` configured in your project root
2. All scenarios run cleanly (`usersim run` exits 0 before you add the hook)

---

## Configuration

Add a Stop hook to `.claude/settings.json` in your project root:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "usersim run"
          }
        ]
      }
    ]
  }
}
```

The command runs from the directory containing `.claude/settings.json`,
which should be the same directory as your `usersim.yaml`.

---

## How it works

| Exit code | Meaning                                      |
|-----------|----------------------------------------------|
| `0`       | All checks pass — Claude may stop            |
| `2`       | One or more checks failed — Claude is blocked |

On failure, usersim writes to stderr:
- Which personas are unsatisfied
- Their role, goal, and pronoun
- The exact constraints that failed
- Which scenarios triggered the failures

Claude reads this and continues working until all checks pass.

---

## Verifying the hook

Ask Claude to finish a task while a constraint is intentionally failing.
It should respond with something like:

> I can't stop yet — usersim reports that `streak_chaser` is unsatisfied:
> `measuring_persistence_fidelity >= 1.0` failed in the `persistence` scenario.
> I'll fix the persistence issue first.

---

## Tips

- **Keep scenarios fast.** The Stop hook runs every time Claude tries to finish.
  Slow instrumentation (real browser, network calls) adds up. Under 10 seconds
  total is a good target.
- **Start with one persona.** Add all personas once the hook is working reliably.
- **Use `--scenario` to debug.** Run `usersim run --scenario persistence` to
  isolate a failing scenario without running the full matrix.
- **Don't block on flaky checks.** A check that fails intermittently will trap
  Claude in a loop. Make sure every constraint is deterministic before enabling
  the hook.
