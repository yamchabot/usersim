"""
perceptions.py — Local Notes perception layer

Transforms raw instrumentation metrics into domain-meaningful values.
Called by usersim for each scenario × person combination.

Rule: no threshold comparisons here — those belong in Z3 user constraints.
Perceptions return numbers. Judgements return booleans.
"""


def compute(metrics, scenario, person):
    def get(key, default=0.0):
        v = metrics.get(key, default)
        return float(v) if v is not None else default

    # ── Pass-through perceptions ─────────────────────────────────────────────
    # These relay a single metric directly. Named the same as their source
    # metric so users can write intuitive constraints.

    storage_error_count        = get("storage_error_count")
    reload_loss_count          = get("reload_loss_count")
    recency_violation_count    = get("recency_violation_count")
    shared_notebook_key_count  = get("shared_notebook_key_count")
    typing_request_count       = get("typing_request_count")
    load_request_count         = get("load_request_count")
    load_modal_count           = get("load_modal_count")
    onboarding_step_count      = get("onboarding_step_count")
    auth_prompt_count          = get("auth_prompt_count")
    account_prompt_count       = get("account_prompt_count")
    new_note_step_count        = get("new_note_step_count")
    interactive_element_count  = get("interactive_element_count")
    notebook_count             = get("notebook_count")
    total_note_count           = get("total_note_count")
    time_to_first_keystroke_ms = get("time_to_first_keystroke_ms")
    autosave_latency_ms        = get("autosave_latency_ms")
    notebook_switch_time_ms    = get("notebook_switch_time_ms")
    external_resource_count    = get("external_resource_count")
    external_dependency_count  = get("external_dependency_count")
    external_service_call_count = get("external_service_call_count")

    # ── Combining perceptions ────────────────────────────────────────────────
    # These produce values that can't be derived from any single metric alone.

    # Total network exposure regardless of timing phase.
    # A request is a request — when it happens matters less than that it happened.
    total_request_count = (
        get("outbound_request_count") +
        get("load_request_count") +
        get("typing_request_count") +
        get("external_service_call_count")
    )

    # Sum of all barriers between arriving and writing.
    # A user experiences all of these before they can do anything useful.
    arrival_friction_total = (
        get("load_modal_count") +
        get("onboarding_step_count") +
        get("auth_prompt_count") +
        get("account_prompt_count")
    )

    # Total external code surface — scripts, stylesheets, and service calls combined.
    # Any of these can send data or fail; total exposure is what matters.
    vendor_surface = (
        get("external_service_call_count") +
        get("external_resource_count") +
        get("external_dependency_count")
    )

    # Fraction of notes that survived a reload (1.0 = perfect, 0.0 = total loss).
    # Requires both before and after counts — neither alone tells you the rate.
    # Returns 1.0 when this scenario didn't measure persistence (not applicable).
    _before_key_present = "notes_before_reload" in metrics
    _after_key_present  = "notes_after_reload"  in metrics
    if _before_key_present and _after_key_present:
        notes_before = get("notes_before_reload") or 1.0  # avoid div-by-zero
        notes_after  = get("notes_after_reload")
        data_integrity_rate = notes_after / notes_before
    else:
        data_integrity_rate = 1.0  # not measured this scenario — assume fine

    # Ratio of storage keys to notebooks (1.0 = perfect isolation).
    # notebook_key_count and notebook_count are different things:
    # one is the number of storage keys, the other is the number of UI notebooks.
    # They should always be equal; a ratio below 1.0 means keys are missing,
    # above 1.0 means there is orphaned data.
    # Returns 1.0 when isolation wasn't measured this scenario.
    if "notebook_key_count" in metrics and "notebook_count" in metrics:
        nb_count = get("notebook_count") or 1.0
        nb_keys  = get("notebook_key_count")
        notebook_isolation_ratio = nb_keys / nb_count
    else:
        notebook_isolation_ratio = 1.0  # not measured this scenario — assume fine

    # Sum of all signals that indicate data is leaving or being controlled externally.
    # Used by privacy-conscious users to assess overall trust posture at a glance.
    trust_signal_violations = (
        get("outbound_request_count") +
        get("typing_request_count") +
        get("external_service_call_count") +
        get("auth_prompt_count") +
        get("account_prompt_count") +
        get("storage_error_count")
    )

    return {
        # Pass-through
        "storage_error_count":          storage_error_count,
        "reload_loss_count":            reload_loss_count,
        "recency_violation_count":      recency_violation_count,
        "shared_notebook_key_count":    shared_notebook_key_count,
        "typing_request_count":         typing_request_count,
        "load_request_count":           load_request_count,
        "load_modal_count":             load_modal_count,
        "onboarding_step_count":        onboarding_step_count,
        "auth_prompt_count":            auth_prompt_count,
        "account_prompt_count":         account_prompt_count,
        "new_note_step_count":          new_note_step_count,
        "interactive_element_count":    interactive_element_count,
        "notebook_count":               notebook_count,
        "total_note_count":             total_note_count,
        "time_to_first_keystroke_ms":   time_to_first_keystroke_ms,
        "autosave_latency_ms":          autosave_latency_ms,
        "notebook_switch_time_ms":      notebook_switch_time_ms,
        "external_resource_count":      external_resource_count,
        "external_dependency_count":    external_dependency_count,
        "external_service_call_count":  external_service_call_count,
        # Combining
        "total_request_count":          total_request_count,
        "arrival_friction_total":       arrival_friction_total,
        "vendor_surface":               vendor_surface,
        "data_integrity_rate":          data_integrity_rate,
        "notebook_isolation_ratio":     notebook_isolation_ratio,
        "trust_signal_violations":      trust_signal_violations,
    }
