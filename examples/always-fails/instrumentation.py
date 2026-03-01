"""
always-fails/instrumentation.py

Simulates an app with a high error rate and slow responses.
Used to test that usersim correctly reports constraint violations
and produces a valid report.html for the failing case.
"""
import json, sys, os

SCENARIO = os.environ.get("USERSIM_SCENARIO", "normal_load")

DATA = {
    "normal_load": {
        "request_count":  20,
        "error_count":    8,    # 40% error rate — unacceptable
        "p99_latency_ms": 4200, # way over budget
        "data_loss_count": 3,
    },
    "low_load": {
        "request_count":  5,
        "error_count":    2,
        "p99_latency_ms": 1800,
        "data_loss_count": 1,
    },
}

metrics = DATA.get(SCENARIO, DATA["normal_load"])
json.dump({"schema": "usersim.metrics.v1", "scenario": SCENARIO, "metrics": metrics}, sys.stdout)
