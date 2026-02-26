"""
perceptions.py — graph visualization example

Translates raw layout metrics (produced by instrumentation.js) into
human-meaningful boolean facts about what a user would perceive.

This is the "What does a human see?" layer.
It knows nothing about users or satisfaction — just physics and geometry.
"""
from usersim.perceptions.library import threshold, in_range, flag


def compute(metrics: dict, scenario: str = "default", person: str = None) -> dict:
    """
    metrics keys (produced by layout_metrics.js):
      node_count, edge_count, module_count, is_blob_mode,
      layout_stress, edge_crossing_ratio, blob_separation, hub_centrality_error,
      node_size_cv, blob_edge_routing, inter_module_crossings
    """
    m = metrics

    return {
        # ── Structure perceptions ──────────────────────────────────────────
        "graph_is_small":    threshold(m, "node_count",    max=50),
        "graph_is_medium":   in_range(m,  "node_count",   51, 300),
        "graph_is_large":    threshold(m, "node_count",    min=301),
        "is_multi_module":   threshold(m, "module_count",  min=2),
        "has_many_modules":  threshold(m, "module_count",  min=5),
        "is_blob_layout":    flag(m, "is_blob_mode"),

        # ── Legibility perceptions ─────────────────────────────────────────
        "layout_is_clear":      threshold(m, "layout_stress",         max=1.5),
        "blobs_are_separated":  threshold(m, "blob_separation",       min=0.6),
        "hubs_are_centred":     threshold(m, "hub_centrality_error",  max=0.35),
        "node_sizes_vary":      threshold(m, "node_size_cv",          min=0.25),
        "edges_route_cleanly":  threshold(m, "blob_edge_routing",     max=0.30),
        "few_crossings":        threshold(m, "edge_crossing_ratio",   max=0.15),
        "no_spaghetti":         threshold(m, "edge_crossing_ratio",   max=0.50),

        # ── Navigability perceptions ───────────────────────────────────────
        "can_follow_chains":    flag(m, "has_linear_chains"),
        "clusters_visible":     threshold(m, "blob_separation",       min=0.40),
    }
