#!/usr/bin/env python3
"""生成示例日志文件，用于测试 log-analyzer 工具"""

import random
from datetime import datetime, timedelta

NORMAL_MESSAGES = [
    "INFO Request handled successfully in {ms}ms",
    "INFO User {user} logged in from {ip}",
    "INFO Database query completed in {ms}ms",
    "INFO Health check passed",
    "INFO Cache hit ratio: {pct}%",
    "DEBUG Processing message from queue",
    "INFO Scheduled task completed: cleanup_sessions",
    "INFO Connection pool stats: active=5 idle=15 total=20",
    "INFO API response sent: 200 OK",
    "DEBUG Loading configuration from /etc/app/config.yaml",
]

ERROR_MESSAGES = [
    "ERROR database connection refused: Connection timed out after 30000ms to db-primary:5432",
    "FATAL Out of memory: Java heap space - requested 512MB, available 128MB",
    "ERROR NullPointerException: Cannot invoke method on null object at com.app.service.UserService.getUser(UserService.java:142)",
    "ERROR connection reset by peer: 10.0.1.50:8080 - possible network partition",
    "CRITICAL deadlock detected between thread-pool-3 and thread-pool-7 on resource lock-orders-table",
    "ERROR disk usage at 95% on /data volume - immediate attention required",
    "ERROR failed to start service nginx: port 443 already in use by pid 12847",
    "ERROR SSL handshake failed: certificate expired on 2024-12-31",
    "ERROR authentication failed for user admin from 192.168.1.100 - 5 consecutive failures",
    "ERROR worker process exit with code 137 (SIGKILL) - possible OOM kill",
    "WARN timeout waiting for response from upstream service payment-api after 30s",
    "ERROR Traceback (most recent call last):\n  File \"/app/handlers/order.py\", line 89\n    raise ValueError(\"Invalid order state transition\")",
    "ERROR replication lag detected: slave is 120 seconds behind master",
    "WARN queue full: message-broker backlog exceeded 10000 messages",
    "ERROR segmentation fault in module libcrypto.so.1.1 at address 0x7f3a2b4c1000",
    "ERROR permission denied: cannot write to /var/log/app/audit.log - check file ownership",
    "ERROR too many open files (EMFILE): current limit 1024, attempted to open fd 1025",
    "ERROR core dumped: signal 11 (SIGSEGV) in thread main-worker-3",
]


def generate(output_path="sample_app.log", lines=5000, error_rate=0.03):
    """生成示例日志"""
    base_time = datetime(2024, 6, 15, 8, 0, 0)
    users = ["alice", "bob", "charlie", "diana", "eve"]
    ips = ["10.0.1.10", "10.0.1.20", "192.168.1.100", "172.16.0.5"]

    with open(output_path, "w") as f:
        for i in range(lines):
            ts = base_time + timedelta(seconds=i * 0.5 + random.uniform(0, 0.5))
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            if random.random() < error_rate:
                msg = random.choice(ERROR_MESSAGES)
            else:
                msg = random.choice(NORMAL_MESSAGES)
                msg = msg.format(
                    ms=random.randint(1, 500),
                    user=random.choice(users),
                    ip=random.choice(ips),
                    pct=random.randint(60, 99),
                )

            f.write(f"[{ts_str}] {msg}\n")

    print(f"Generated {lines} lines to {output_path}")


if __name__ == "__main__":
    generate()
