"""
Ops engineer running the processor as a scheduled batch job.
Needs the full pipeline to complete within a tight time budget —
they're billed by CPU time and have downstream jobs waiting.
Fast is nice but their hard requirement is "finishes on time, no errors".
"""
from usersim import Person


class OpsEngineer(Person):
    name        = "ops_engineer"
    description = "Runs batch jobs; needs the pipeline to finish within SLA, no errors."

    def constraints(self, P):
        return [
            P.no_errors,
            P.pipeline_under_30s,    # must finish within the job window
            P.sort_finishes_in_time, # sort must not time out
        ]
