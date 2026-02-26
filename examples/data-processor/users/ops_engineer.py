"""
Ops engineer running the processor as a scheduled batch job.
Billed by CPU time, has downstream jobs waiting on the output.
Cares about throughput and completion within the job window.
Will page if error rate crosses 0.1%.
"""
from usersim import Person


class OpsEngineer(Person):
    name        = "ops_engineer"
    description = "Batch jobs; needs pipeline to finish on time with high throughput."

    def constraints(self, P):
        return [
            P.error_rate      <= 0.001,     # pages at 0.1% error rate
            P.total_ms        <= 30_000,    # job window is 30s
            P.sort_throughput >= 100,       # at least 100 records/ms sorted
        ]
