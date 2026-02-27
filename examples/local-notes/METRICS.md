# Measurable Quantities — Local Notes
> These are the observable facts about the app that users would use to judge whether their needs are being met.
> All are measurable by browser instrumentation without modifying the app's core logic.

---

## Performance

| Name | Type | Description |
|------|------|-------------|
| `time_to_interactive_ms` | number | Milliseconds from page load until the app is ready to accept input |
| `time_to_first_keystroke_ms` | number | Milliseconds from page load until the cursor is active in an editable field |
| `autosave_latency_ms` | number | Milliseconds between last keystroke and localStorage write completing |
| `notebook_switch_time_ms` | number | Milliseconds to fully render a different notebook's note list after clicking it |

---

## Network

| Name | Type | Description |
|------|------|-------------|
| `outbound_request_count` | number | Total HTTP requests made by the app at any point during a session |
| `requests_on_load` | number | HTTP requests made during initial page load |
| `requests_while_typing` | number | HTTP requests made during an active typing session |
| `external_resource_count` | number | Scripts, fonts, stylesheets, or images loaded from external domains |

---

## Storage & Persistence

| Name | Type | Description |
|------|------|-------------|
| `localstorage_available` | boolean | Whether localStorage is accessible in the current browser context |
| `data_survives_reload` | boolean | Whether notebooks and notes are present and correct after a full page reload |
| `notebooks_count` | number | Number of notebooks currently stored |
| `notes_count_total` | number | Total notes across all notebooks |
| `notes_count_active_notebook` | number | Notes in the currently selected notebook |
| `total_storage_bytes` | number | Total bytes occupied in localStorage by the app |
| `oldest_note_age_days` | number | Age in days of the oldest note — proxy for long-term persistence reliability |
| `notes_sorted_by_recency` | boolean | Whether the note list is ordered by most recently updated first |

---

## Data Isolation

| Name | Type | Description |
|------|------|-------------|
| `notebook_key_count` | number | Number of distinct localStorage keys used for notebook data (should equal `notebooks_count`) |
| `notebook_keys_are_independent` | boolean | Whether each notebook's data is stored under its own separate key with no cross-contamination |
| `auth_required` | boolean | Whether the app requested any form of authentication |
| `account_required` | boolean | Whether the app prompted account creation at any point |

---

## UI Complexity

| Name | Type | Description |
|------|------|-------------|
| `interactive_element_count` | number | Number of buttons, inputs, and controls visible on screen at rest |
| `modal_shown_on_load` | boolean | Whether a modal or overlay appeared without user action on first load |
| `onboarding_shown` | boolean | Whether an onboarding flow, tutorial, or feature tour was displayed |
| `steps_to_new_note` | number | Number of distinct user interactions required to create a new note from scratch |

---

## Self-Containment

| Name | Type | Description |
|------|------|-------------|
| `runs_offline` | boolean | Whether the app is fully functional with no network connection |
| `external_dependency_count` | number | Number of external JavaScript or CSS libraries loaded from outside the app file |
| `vendor_dependency` | boolean | Whether the app requires any third-party service to function at all |

---

## Session Activity

| Name | Type | Description |
|------|------|-------------|
| `notes_created_this_session` | number | Notes created since the page was opened |
| `notes_edited_this_session` | number | Notes modified since the page was opened |
| `time_since_last_autosave_ms` | number | Milliseconds since the last successful write to localStorage |
