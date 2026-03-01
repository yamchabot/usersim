"""
usersim.constraints.throughput — throughput floor and queue depth.

Perceptions contract:
  items_processed   (int >= 0)  — items successfully handled
  items_total       (int >= 0)  — items submitted for processing
  elapsed_ms        (int >= 1)  — wall-clock time for the batch
  queue_depth       (int >= 0)  — current queue / backlog length
  worker_count      (int >= 1)  — active workers / threads / goroutines
  dropped_items     (int >= 0)  — items dropped due to overload
"""
from usersim.judgement.z3_compat import And, Implies, named


def throughput_floor(P, *, min_items_per_second: int = 100):
    """Throughput must meet a floor rate.

    Uses integer arithmetic: items_processed * 1000 >= min_rate * elapsed_ms

    Args:
        P:                   FactNamespace.
        min_items_per_second: Minimum sustained throughput (default 100/s).
    """
    return [
        named("throughput/floor-rate-met",
              Implies(And(P.items_processed >= 1, P.elapsed_ms >= 1),
                      P.items_processed * 1000 >= P.elapsed_ms * min_items_per_second)),
        named("throughput/processed-never-exceeds-total",
              Implies(P.items_total >= 1,
                      P.items_processed <= P.items_total)),
        named("throughput/no-dropped-without-submissions",
              Implies(P.items_total == 0, P.dropped_items == 0)),
        named("throughput/processed-plus-dropped-lte-total",
              Implies(And(P.items_total >= 1, P.dropped_items >= 0),
                      P.items_processed + P.dropped_items <= P.items_total)),
        named("throughput/elapsed-positive-when-work-done",
              Implies(P.items_processed >= 1, P.elapsed_ms >= 1)),
    ]


def queue_depth(P, *, max_depth: int = 1000, max_per_worker: int = 100):
    """Queue depth bounded absolutely and relative to worker count.

    Args:
        P:              FactNamespace.
        max_depth:      Absolute queue depth ceiling (default 1000).
        max_per_worker: Max queue items per worker (default 100).
    """
    return [
        named("throughput/queue-under-absolute-ceiling",
              Implies(P.queue_depth >= 0, P.queue_depth <= max_depth)),
        named("throughput/queue-scales-with-workers",
              Implies(And(P.queue_depth >= 0, P.worker_count >= 1),
                      P.queue_depth <= P.worker_count * max_per_worker)),
        named("throughput/workers-positive",
              Implies(P.worker_count >= 0, P.worker_count >= 1)),
        named("throughput/no-drops-under-half-capacity",
              Implies(And(P.queue_depth >= 0, P.worker_count >= 1,
                          P.queue_depth * 2 <= P.worker_count * max_per_worker),
                      P.dropped_items == 0)),
    ]
