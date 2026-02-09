import json
import os
import time
import random
from datetime import datetime, timezone

LOG_PATH = os.environ.get("LOG_PATH", "/var/log/app/app.log")
SERVICE = os.environ.get("SERVICE_NAME", "dummy-backend")

ROUTES = ["/login", "/checkout", "/search", "/profile", "/logout"]
LEVELS = ["INFO", "WARN", "ERROR"]

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def make_log():
    route = random.choice(ROUTES)
    level = random.choices(LEVELS, weights=[85, 10, 5])[0]
    latency_ms = random.randint(5, 1200)

    status = 200
    msg = "ok"

    if route == "/login" and level == "ERROR":
        status = random.choice([401, 403, 500])
        msg = random.choice(["invalid_password", "token_expired", "db_timeout"])
    elif route == "/checkout" and level in ["WARN", "ERROR"]:
        status = random.choice([409, 422, 500])
        msg = random.choice(["payment_retry", "insufficient_stock", "gateway_error"])

    log = {
        "@timestamp": now_iso(),

        # ECS-friendly:
        "service": {"name": SERVICE},
        "log": {"level": level},

        # your fields (fine as custom)
        "route": route,
        "status": status,
        "latency_ms": latency_ms,
        "user_id": f"u{random.randint(1, 200):03d}",
        "message": msg,
        "trace": {"id": f"{random.getrandbits(64):016x}"},
    }

    return log

def ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def main():
    ensure_dir(LOG_PATH)
    print(f"[backend] writing logs to {LOG_PATH}")
    while True:
        log = make_log()
        line = json.dumps(log, ensure_ascii=False)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        time.sleep(0.5)

if __name__ == "__main__":
    main()
