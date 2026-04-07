from prometheus_client import Counter

REQUEST_COUNTER = Counter(
    "platform_requests_total",
    "Total platform requests",
    ["status", "request_type", "team", "environment"],
)