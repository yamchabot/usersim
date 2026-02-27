# Persona: The Quick-Capture Person

## Metrics That Matter to This User

| Metric | Constraint | Why It Matters |
|--------|-----------|----------------|
| `time_to_interactive_ms` | < 500 | Every millisecond of loading is a window for the thought to escape |
| `time_to_first_keystroke_ms` | < 500 | Capture starts when typing starts — not when the page finishes loading |
| `autosave_latency_ms` | < 1000 | Switching away from the tab shouldn't risk losing what was just typed |
| `new_note_step_count` | ≤ 2 | Friction in capture means things don't get captured |
| `load_modal_count` | == 0 | Any modal on load is a barrier before the user can type |
| `onboarding_step_count` | == 0 | An onboarding flow is the opposite of instant capture |
| `reload_loss_count` | == 0 | The point of the app is that things stay — it must survive tab close |
| `total_note_count` | > 0 | If this number grows over time, the capture habit is forming |
| `notebook_switch_time_ms` | < 300 | Context switching must be instant — delay breaks the capture flow |
| `time_since_last_autosave_ms` | < 2000 | Indicates the app is reliably keeping up with input |

---

## User Benefits — How the App Delivers Them

---

**1. The thought is captured before it's gone — nothing loads, nothing asks me to sign in**

You bookmark the page. When a thought hits, you switch to that tab — or open a new one — and start typing immediately. There is no splash screen, no loading spinner, no authentication step. The app opens into whatever notebook and note you had open last, cursor ready.

---

**2. I stop losing good ideas to the gap between having them and finding somewhere to put them**

The app restores your last open note automatically. If you left a scratch note open, it's still there. If you've been building a running list, you can add to it in two seconds. The gap between "I have a thought" and "I have captured the thought" collapses to the time it takes to switch browser tabs.

---

**3. I keep one tab open all day and it's always ready, like a notepad on a desk**

The app is designed to live permanently in your browser. Because it stores everything locally, refreshing the page or reopening the tab costs nothing — your state is always restored. It behaves like a physical notepad: always open, always where you left it, never asking you anything.

---

**4. I never have to decide where to put something — I just put it somewhere and deal with it later**

You can dump a thought into any open note without worrying about categorisation. You can have a notebook called "Inbox" or "Scratch" that you use as a landing zone. The organisational decisions can happen later — or never. The app doesn't force structure on you.

---

**5. I get out of the app as fast as I got in — no menus, no prompts, no friction on exit**

After typing, you switch back to whatever you were doing. There's no save button to remember — the app auto-saves as you type. No dialog box appears. Nothing asks you to confirm or sync. You close the tab and everything is already saved.

---

**6. I stop using random text files, chat messages to myself, and email drafts as a scratch pad**

The app gives you a named, persistent, organised alternative to all of those. Instead of a cluttered desktop of `.txt` files or a chat thread you scroll back through, you have notebooks with actual notes, each with a title and a timestamp, searchable and browsable.

---

**7. The bar to capture is low enough that I actually capture things instead of telling myself I'll remember**

Every additional step in a capture workflow is a thought that doesn't get written down. This app has none of those steps. The lower the friction, the more you capture. The more you capture, the more useful the habit becomes — and the app grows into a real record of your thinking over time.
