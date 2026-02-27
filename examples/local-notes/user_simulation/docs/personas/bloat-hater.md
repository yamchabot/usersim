# Persona: The Bloat-Hater

## Metrics That Matter to This User

| Metric | Constraint | Why It Matters |
|--------|-----------|----------------|
| `interactive_element_count` | low | Every extra button is a feature that wasn't asked for |
| `load_modal_count` | == 0 | A modal on load is the definition of the app getting in the way |
| `onboarding_step_count` | == 0 | An onboarding tour means the app doesn't trust the user to figure it out |
| `new_note_step_count` | ≤ 2 | If it takes more than two clicks to write a note, something has gone wrong |
| `external_dependency_count` | == 0 | External dependencies mean the app is already more complex than it needs to be |
| `external_service_call_count` | == 0 | Any required vendor is a future liability — updates, outages, pricing changes |
| `offline_failure_count` | == 0 | An app that requires the internet for notes has already over-engineered itself |
| `time_to_interactive_ms` | < 500 | A slow load is a sign of unnecessary weight |
| `load_request_count` | == 0 | Network requests on load mean the app is doing things it doesn't need to do |

---

## User Benefits — How the App Delivers Them

---

**1. I open the app and it does the thing — no onboarding, no tour, no "what are you trying to do today?"**

The app opens into your notes. There is no welcome screen, no feature tour, no modal asking what kind of user you are. The first time you open it, you get a default notebook and a blank note. That's it. The entire surface area of the app is visible immediately and fits in one browser tab.

---

**2. I stop paying for features I resent being there**

There is no pricing page. The app has no features you didn't ask for — no AI writing assistant, no collaboration mode, no templates gallery, no integrations panel. Everything visible in the app is something you might actually use. Nothing is there because a product manager needed to justify a tier.

---

**3. I get the version of the tool that existed before someone added a database, a marketplace, and a mobile app**

Local Notes is deliberately minimal — notebooks, notes, titles, text. That's the whole product. It's what every notes app was before it became a platform. If you remember when Evernote was good, this is closer to that than Evernote currently is.

---

**4. I write notes without the app suggesting I turn them into a wiki, a board, or a template**

There are no slash commands, no block types, no drag-and-drop content modules. You type text. The app stores text. There are no affordances nudging you toward a "better" way to structure your notes. Structure is entirely your choice, and the app will never second-guess it.

---

**5. Nothing has changed the next time I open it — no forced update, no redesign, no feature that moved**

Because the app is a static file with no backend, there is nothing to update without your involvement. No one can push a redesign to your tab overnight. No feature moves because the product team reorganised. The app you bookmarked is the app you get, every time.

---

**6. I feel in control again, which I didn't realize I'd lost until I had it back**

The app has no telemetry, no feature flags, no A/B tests, no remote configuration. Its behaviour is entirely determined by what's in the file. You can inspect it, understand it completely, and trust that it does exactly what it appears to do. That feeling of legibility and control is what every tool used to feel like.

---

**7. I recommend it to people without embarrassment — it does exactly what it says**

"It's a notes app. You type notes. They save. That's it." That sentence is the whole pitch and it's entirely true. There's no asterisk, no "but you need the pro plan for X," no caveat about which browser it works best in. It's the kind of tool you can recommend confidently because it won't let the person down.
