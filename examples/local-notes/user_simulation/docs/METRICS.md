# Measurable Quantities — Local Notes
> Observable facts about the app that users would use to judge whether their needs are being met.
> All are measurable by browser instrumentation. Booleans live in judgements — everything here is a count or measurement.

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
| `outbound_request_count` | count | Total HTTP requests made by the app at any point during a session |
| `load_request_count` | count | HTTP requests made during initial page load |
| `typing_request_count` | count | HTTP requests made during an active typing session |
| `external_resource_count` | count | Scripts, fonts, stylesheets, or images loaded from external domains |
| `external_service_call_count` | count | Calls made to third-party services at any point |

---

## Storage & Persistence

| Name | Type | Description |
|------|------|-------------|
| `storage_error_count` | count | Read/write errors against localStorage |
| `notebook_count` | count | Number of notebooks currently stored |
| `total_note_count` | count | Total notes across all notebooks |
| `active_notebook_note_count` | count | Notes in the currently selected notebook |
| `total_storage_bytes` | number | Total bytes occupied in localStorage by the app |
| `oldest_note_age_days` | number | Age in days of the oldest note |
| `reload_loss_count` | count | Notes or notebooks present before reload that were missing after |
| `recency_violation_count` | count | Notes appearing above a note they should appear below by last-updated time |

---

## Data Isolation

| Name | Type | Description |
|------|------|-------------|
| `notebook_key_count` | count | Distinct localStorage keys used for notebook data |
| `shared_notebook_key_count` | count | Notebook pairs sharing a storage key (should be 0) |
| `auth_prompt_count` | count | Authentication prompts displayed to the user |
| `account_prompt_count` | count | Account creation dialogs shown at any point |

---

## UI Complexity

| Name | Type | Description |
|------|------|-------------|
| `interactive_element_count` | count | Buttons, inputs, and controls visible on screen at rest |
| `load_modal_count` | count | Modals or overlays that appeared without user action on load |
| `onboarding_step_count` | count | Onboarding screens or tutorial steps displayed |
| `new_note_step_count` | count | User interactions required to create a new note from scratch |

---

## Self-Containment

| Name | Type | Description |
|------|------|-------------|
| `offline_failure_count` | count | Features that fail when network is disconnected |
| `external_dependency_count` | count | External JavaScript or CSS libraries loaded from outside the app file |

---

## Session Activity

| Name | Type | Description |
|------|------|-------------|
| `session_note_create_count` | count | Notes created since the page was opened |
| `session_note_edit_count` | count | Notes modified since the page was opened |
| `time_since_last_autosave_ms` | number | Milliseconds since the last successful write to localStorage |
