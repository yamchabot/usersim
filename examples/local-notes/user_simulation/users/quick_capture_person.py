from usersim.judgement.person import Person
from usersim.judgement.z3_compat import Implies, And, named


class QuickCapturePerson(Person):
    name    = "Quick-Capture Person"
    role    = "Productivity-focused professional"
    goal    = "Capture thoughts instantly with zero friction"
    pronoun = "they"

    def constraints(self, P):
        return [
            # friction
            named("friction/zero-arrival-barriers",   P.arrival_friction_total == 0),
            named("friction/minimal-steps-to-note",   P.new_note_step_count <= 2),
            named("friction/time-to-first-keystroke", P.time_to_first_keystroke_ms <= 500),
            named("friction/capture-readiness-score", P.capture_readiness_score <= 2000),

            # persistence
            named("persistence/no-reload-loss",    P.reload_loss_count == 0),
            named("persistence/data-integrity",    P.data_integrity_rate >= 1.0),
            named("persistence/bulk-autosave-ok",
                  Implies(P.session_note_create_count >= 5, P.storage_error_count == 0)),
            named("persistence/bulk-no-data-loss",
                  Implies(P.session_note_create_count >= 5, P.data_integrity_rate >= 1.0)),

            # search
            named("search/responsive",
                  Implies(P.search_hit_count + P.search_miss_count >= 1,
                          P.search_latency_ms <= 500)),
        ]
