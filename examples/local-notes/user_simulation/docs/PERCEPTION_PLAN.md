# Perception Plan — Local Notes
> Perceptions are transformation functions. Each one takes raw metrics as input and produces
> a domain-meaningful value. They are verb phrases — they describe what the function does.
> Booleans live in judgements (Z3 constraints), not here.

---

## Detecting

These perceptions look for the presence or count of something that should or shouldn't be there.

| Perception | Input Metrics |
|------------|--------------|
| `detecting outbound activity` | `outbound_request_count`, `load_request_count`, `typing_request_count`, `external_service_call_count` |
| `detecting arrival friction` | `load_modal_count`, `onboarding_step_count`, `auth_prompt_count`, `account_prompt_count` |
| `detecting keystroke exposure` | `typing_request_count` |
| `detecting vendor dependency` | `external_service_call_count`, `external_resource_count`, `external_dependency_count` |
| `detecting data loss` | `reload_loss_count` |
| `detecting storage failures` | `storage_error_count` |
| `detecting sort violations` | `recency_violation_count` |
| `detecting isolation failures` | `shared_notebook_key_count` |
| `detecting offline failures` | `offline_failure_count` |

---

## Measuring

These perceptions quantify something the user experiences directly.

| Perception | Input Metrics |
|------------|--------------|
| `measuring startup responsiveness` | `time_to_interactive_ms`, `time_to_first_keystroke_ms`, `load_request_count` |
| `measuring capture path length` | `new_note_step_count`, `time_to_first_keystroke_ms` |
| `measuring write latency` | `autosave_latency_ms`, `time_since_last_autosave_ms` |
| `measuring surface density` | `interactive_element_count` |
| `measuring dependency footprint` | `external_dependency_count`, `external_resource_count` |
| `measuring context switch speed` | `notebook_switch_time_ms` |
| `measuring note accumulation` | `total_note_count`, `active_notebook_note_count`, `session_note_create_count` |
| `measuring persistence age` | `oldest_note_age_days` |

---

## Inferring

These perceptions are composites — derived from multiple metrics that individually don't tell the whole story.

| Perception | Input Metrics |
|------------|--------------|
| `inferring trust posture` | `outbound_request_count`, `typing_request_count`, `external_service_call_count`, `auth_prompt_count`, `account_prompt_count`, `storage_error_count` |
| `inferring capture readiness` | `time_to_interactive_ms`, `new_note_step_count`, `autosave_latency_ms`, `load_modal_count` |

---

## Notes

- `typing_request_count` appears in both **detecting outbound activity** and **detecting keystroke exposure** — the latter may be the same perception at a finer granularity, or could be collapsed into outbound activity
- `load_request_count` appears in both **detecting outbound activity** and **measuring startup responsiveness** — this is intentional; the same metric can feed different perceptions
- `total_storage_bytes` has no perception yet — no persona currently cares about storage quota, but could be added
- The **inferring** perceptions take raw metrics directly rather than composing other perceptions — worth deciding whether inferring should be allowed to call other perceptions as inputs, or always reads raw metrics only
