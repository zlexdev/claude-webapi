"""Baseline load test for the gateway. Run against a live instance with a real key.

    CLAUDE_GATEWAY_KEY=sk-... locust -f tests/gateway/load/locustfile.py \
        --host http://localhost:8081 --users 50 --spawn-rate 10

Covers the three hot paths: OpenAI completion, the simple text endpoint, and generic
method dispatch. Record req/s, p95 latency, and error rate in this folder's README.
"""

from __future__ import annotations

import os

from locust import HttpUser, between, task

_KEY = os.environ.get("CLAUDE_GATEWAY_KEY", "sk-replace-me")
_HEADERS = {"Authorization": f"Bearer {_KEY}", "Content-Type": "application/json"}


class GatewayUser(HttpUser):
    wait_time = between(0.5, 2.0)

    @task(3)
    def chat_completion(self) -> None:
        self.client.post(
            "/v1/chat/completions",
            headers=_HEADERS,
            json={"model": "gemini-3.5-flash", "messages": [{"role": "user", "content": "ping"}]},
            name="/v1/chat/completions",
        )

    @task(2)
    def prompt(self) -> None:
        self.client.post(
            "/v1/prompt", headers=_HEADERS, json={"text": "hello"}, name="/v1/prompt"
        )

    @task(1)
    def methods_invoke(self) -> None:
        self.client.post(
            "/v1/methods/invoke",
            headers=_HEADERS,
            json={"method": "ListConversations", "params": {"limit": 5}},
            name="/v1/methods/invoke",
        )
