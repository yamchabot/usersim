from usersim.judgement.person import Person
from usersim.judgement.z3_compat import Implies, And


class QuickCapturePerson(Person):
    name    = "Quick-Capture Person"
    role    = "Productivity-focused professional"
    goal    = "Capture thoughts instantly with zero friction"
    pronoun = "they"

    def constraints(self, P):
        return [
            # Always: zero friction to start typing
            P.arrival_friction_total         == 0,
            P.new_note_step_count            <= 2,
            P.reload_loss_count              == 0,
            P.data_integrity_rate            >= 1.0,
            P.time_to_first_keystroke_ms     <= 500,
            P.capture_readiness_score        <= 2000,

            # bulk_import: rapid note creation must not produce errors
            Implies(P.session_note_create_count >= 5,
                    P.storage_error_count == 0),

            # bulk_import: autosave must work even under back-to-back creation
            Implies(P.session_note_create_count >= 5,
                    P.data_integrity_rate >= 1.0),

            # search_heavy: search must stay responsive (< 500ms avg)
            Implies(P.search_hit_count + P.search_miss_count >= 1,
                    P.search_latency_ms <= 500),
        ]
