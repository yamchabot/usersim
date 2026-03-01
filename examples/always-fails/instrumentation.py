"""
Simulates an app with high error rate, slow responses, and data loss.
Used to test that usersim correctly reports constraint violations.
"""
import json, sys, os

SCENARIO = os.environ.get("USERSIM_PATH", "normal_load")

DATA = {
    "normal_load": {
        "request_count":  20,
        "error_count":    8,
        "p99_latency_ms": 4200,
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
json.dump({"schema": "usersim.metrics.v1", "path": SCENARIO, "metrics": metrics}, sys.stdout)
