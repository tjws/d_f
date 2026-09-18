import sys

from scripts import demo_e2e_smoke


def test_demo_e2e_smoke_checks_seeded_business_surfaces_without_model_call(monkeypatch, capsys):
    def fake_request(base_url, path, **kwargs):
        token = kwargs.get("token")
        if path == "/health/ready":
            return 200, {"status": "ready"}
        if path == "/customers?page=1&page_size=1":
            return 401, {"detail": "Not authenticated"}
        if path == "/customers?page=1&page_size=100":
            return 200, {"items": [{"id": 1}, {"id": 2}, {"id": 3}], "total": 3}
        if path == "/auth/token":
            body = kwargs.get("payload", b"")
            username = body.decode() if isinstance(body, bytes) else str(body)
            return 200, {"access_token": "sales-token" if "demo_sales" in username else "admin-token"}
        if path.startswith("/admin/") or path == "/knowledge/admin":
            if token == "sales-token":
                return 403, {"detail": "forbidden"}
            return 200, {}
        if path in {"/customers/1", "/customers/2", "/customers/3"}:
            return 200, {"id": int(path.rsplit("/", 1)[1])}
        if path.startswith("/customers/") and path.endswith("/students"):
            return 200, [{"id": 10}]
        if path.startswith("/customers/") and path.endswith("/chat-messages"):
            return 200, [{"id": 21, "message_type": "voice", "content": None}]
        if path.startswith("/customers/") and path.endswith("/timeline-events"):
            return 200, [{"id": 31}]
        if path.startswith("/customers/") and path.endswith("/sidebar-sync"):
            return 200, {"messages": [], "timeline_events": [], "next_message_id": 21, "next_timeline_id": 31}
        if path.startswith("/customers/") and path.endswith("/suggestions"):
            return 200, [{"id": 41, "suggestion_type": "reply"}]
        if path.endswith("/orders"):
            return 200, [{"id": 51}] if "/2/" not in path and "/3/" not in path else []
        if path.endswith("/service-tickets"):
            return 200, [{"id": 61}] if "/2/" in path else []
        if path == "/":
            return 200, "index.html"
        if path == "/api/health/ready":
            return 200, {"status": "ready"}
        raise AssertionError(f"unexpected smoke request: {path}")

    monkeypatch.setattr(demo_e2e_smoke, "_request", fake_request)
    monkeypatch.setattr(
        sys,
        "argv",
        ["demo_e2e_smoke.py", "--base-url", "http://backend", "--frontend-url", "http://frontend"],
    )

    assert demo_e2e_smoke.main() == 0
    assert "demo_e2e_ok=" in capsys.readouterr().out
