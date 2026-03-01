from usersim.perceptions.library import run_perceptions

def compute(metrics, **_):
    def num(k, d=0): return float(metrics.get(k, d))
    return {
        "request_count":   num("request_count"),
        "error_count":     num("error_count"),
        "p99_latency_ms":  num("p99_latency_ms"),
        "data_loss_count": num("data_loss_count"),
    }

if __name__ == "__main__":
    run_perceptions(compute)
