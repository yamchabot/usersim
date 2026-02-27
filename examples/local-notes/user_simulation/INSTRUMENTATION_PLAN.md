# Instrumentation Plan — Local Notes
> For each perception, what would browser automation actually do to collect the data.
> This is a design sketch — not implementation yet.

---

## Detecting

**detecting outbound activity**
Register a request interceptor before the page loads. Bucket every intercepted request by phase: load phase (before `DOMContentLoaded`), idle phase, and typing phase (defined as a window around simulated keystrokes). Count totals per bucket. Tag requests by destination domain to separate external service calls from resource loads.

**detecting arrival friction**
Navigate to the page and immediately freeze — no clicks, no keypresses. Query the DOM for visible dialogs, overlays, modals (`role="dialog"`, `aria-modal`, common class patterns). Query for signup or login forms. Count everything visible before the user has done anything.

**detecting keystroke exposure**
With the request interceptor already running, focus a text input and simulate typing a short string. Collect every network request that fires within a short window (e.g. 2 seconds) of each keystroke. Count them.

**detecting vendor dependency**
During page load, collect all resource requests (scripts, stylesheets, fonts, images). Filter for requests to domains other than the app's own origin. Count external scripts and stylesheets separately from external service calls.

**detecting data loss**
Create a known set of notebooks and notes. Record their titles and content. Call `location.reload()`. After reload, read back the note list and compare against the recorded set. Count anything missing or corrupted.

**detecting storage failures**
Wrap `localStorage.setItem` and `localStorage.getItem` with try/catch before the app runs. Count thrown exceptions. Also listen for `storage` event errors and any console errors mentioning storage or quota.

**detecting sort violations**
Create several notes with deliberate time gaps between edits (edit note A, wait, edit note B, wait, edit note C). Record the expected recency order. Query the rendered note list. Walk the list top to bottom and count any note that appears above a note it should appear below.

**detecting isolation failures**
Create two notebooks and add notes to each. Enumerate all localStorage keys. For each key containing note data, check which notebook ID it belongs to. Count any notes or data blobs accessible under another notebook's key.

**detecting offline failures**
Set the browser context offline. Attempt each core feature in sequence: create a notebook, create a note, type in the note, switch notebooks, reload. Count any that produce a visible error state, throw an exception, or silently fail (content not saved).

---

## Measuring

**measuring startup responsiveness**
Record a high-resolution timestamp immediately before `page.goto()`. Listen for `DOMContentLoaded`. Then poll for when the first focusable text input exists and is not disabled. Record that timestamp. Separately record when the first simulated keystroke is accepted by a text field. Count load-phase requests from the interceptor.

**measuring capture path length**
Start from a state with at least one notebook but no active note. Record the sequence of interactions needed to reach a state where the cursor is in a text field ready to write a new note. Count discrete interaction events (clicks, keypresses). Also record elapsed time from start to cursor ready.

**measuring write latency**
Patch `localStorage.setItem` to record the timestamp of every write. Type a single character and record the timestamp of that keystroke event. Wait for the next localStorage write to a note key. Compute the delta. Repeat a few times and take the median.

**measuring surface density**
After load, with no user interaction, query all interactive elements visible in the viewport: `button`, `input`, `textarea`, `select`, `[role="button"]`, `a[href]`. Count only those with non-zero bounding boxes.

**measuring dependency footprint**
From the request interceptor, collect all script and stylesheet loads during the page load phase. Filter for those coming from an external origin. Count them. Also count inline script tags that reference external URLs.

**measuring context switch speed**
With two notebooks populated, record a timestamp before clicking the second notebook in the sidebar. Poll for when the note list finishes updating (last rendered note item stabilises). Record that timestamp. Compute the delta.

**measuring note accumulation**
Read the note list from the DOM after the app has loaded. Count visible note items. Also read localStorage directly and count note entries per notebook. Compare session start count to session end count to derive notes created this session.

**measuring persistence age**
Read localStorage directly and deserialise all note objects. Find the minimum `createdAt` timestamp. Compute elapsed days from that timestamp to now.

---

## Inferring

**inferring trust posture**
Run detecting outbound activity, detecting keystroke exposure, detecting vendor dependency, detecting storage failures, and the auth/account prompt counts. Produce a single composite object with all those counts — no aggregation yet. The Z3 constraints in each user file apply the thresholds.

**inferring capture readiness**
Run measuring startup responsiveness, measuring capture path length, measuring write latency, and detecting arrival friction. Same pattern — produce a composite, let the judgement layer decide what's acceptable.

---

## Implementation Notes

- The `localStorage` patching approach (write latency, storage failures) requires the instrumentation script to be injected before the app initialises — it must run in `page.addInitScript()` or equivalent, not after page load
- The offline test must be a separate scenario run — setting the browser context offline permanently changes state for that context
- Request interception must be registered before `page.goto()` to catch load-phase requests
- Detecting sort violations requires deliberate time gaps between note edits to produce a testable recency order — automated waits between actions, not just rapid-fire creates
