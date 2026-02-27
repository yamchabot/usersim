# Persona: The Developer Scratchpad

## Metrics That Matter to This User

| Metric | Constraint | Why It Matters |
|--------|-----------|----------------|
| `notebook_count` | ≥ 2 | One notebook per project — multiple projects means multiple notebooks |
| `notebook_switch_time_ms` | < 300 | Context switching between projects must be instant |
| `reload_loss_count` | == 0 | Notes must be there next time — this is working memory, not scratch paper |
| `recency_violation_count` | == 0 | The most recently touched note should be at the top — it's the one being worked on |
| `outbound_request_count` | == 0 | Sensitive credentials and tokens must not leave the browser |
| `typing_request_count` | == 0 | Keystroke capture of tokens or connection strings is a security failure |
| `external_resource_count` | == 0 | External scripts loaded while sensitive content is in the DOM is unacceptable |
| `autosave_latency_ms` | < 1000 | The developer is already context-switching; they can't also remember to save |
| `shared_notebook_key_count` | == 0 | Projects must be isolated — a notebook's notes should not bleed into another's |
| `active_notebook_note_count` | > 0 | A useful scratchpad accumulates notes over the life of the project |

---

## User Benefits — How the App Delivers Them

---

**1. I have a place for all the stuff that doesn't belong in a file — half-formed commands, test values, debug traces**

A notebook called "Scratch" or "Debug" acts as a running working memory. You paste in a stack trace, jot the curl command that finally worked, or draft the regex you're building. It's not code — it doesn't go in the repo — but it's not nothing either. The app gives it a proper home without requiring it to be anything formal.

---

**2. I keep one notebook per project and switch contexts without losing my place**

You create a notebook for each project or client and keep their notes separate. Switching between them is a single click in the sidebar. When you come back to a project after two weeks away, your notes from last time are exactly where you left them — the commands, the gotchas, the things you had to look up.

---

**3. I stop pasting sensitive things into cloud tools that probably index them**

API keys, connection strings, internal hostnames, test credentials — the stuff you need to paste somewhere temporarily but shouldn't put in Notion or a Google Doc. Because the app stores only in localStorage, nothing leaves the browser. Paste it, use it, move on. The risk surface is your device, not a vendor's database.

---

**4. I find yesterday's curl command in three seconds without digging through terminal history**

You put it in a note with a title like "Auth API — working curl" and it's there next time. Notes are sorted by last updated, so recent things are always at the top. You don't have to remember which session, which terminal, or which history file it was in.

---

**5. It lives in the browser where I already am — no alt-tab, no app launch, no context switch**

Your workflow is already in the browser — docs, dashboards, GitHub, localhost. A pinned tab with Local Notes means your scratch space is one click away, not an application switch. It lives in the same environment as your work, not outside it.

---

**6. I can close and reopen the tab and everything is still there, exactly as I left it**

localStorage persists across tab closes, browser restarts, and reboots. Your notebooks and notes survive everything short of explicitly clearing browser storage. There's no "did I save that?" anxiety — the app writes every keystroke.

---

**7. I stop treating my clipboard as a short-term memory system**

The clipboard holds one thing and overwrites itself constantly. The app holds everything, indefinitely, organised by notebook and note. Instead of copying something and hoping you use it before you copy something else, you paste it into a note and it's there when you need it — even days later.
