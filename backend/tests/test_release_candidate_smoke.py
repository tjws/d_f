import sys

from scripts import release_candidate_smoke


def test_release_candidate_smoke_is_read_only_and_checks_all_boundaries(monkeypatch, capsys):
    calls: list[tuple[str, str]] = []

    def fake_request(base_url, path, **kwargs):
        calls.append((path, kwargs.get("method", "GET")))
        if path == "/auth/token":
            username = kwargs["body"].decode()
            return 200, {"access_token": "admin-token" if "demo_admin" in username else "sales-token"}
        if path == "/customers?page=1&page_size=1":
            return 401, {"detail": "unauthorized"}
        if path == "/customers?page=1&page_size=20":
            return 200, {"items": [{"id": 7}], "total": 1}
        if path.startswith("/admin/"):
            token = kwargs.get("token")
            return (403, {"detail": "forbidden"}) if token == "sales-token" else (200, {})
        if path == "/health":
            return 200, {"status": "ok"}
        if path == "/health/ready" or path == "/api/health/ready":
            return 200, {"status": "ready"}
        if path == "/":
            return 200, {"status": "ok"}
        if path.endswith("/sidebar-sync"):
            return 200, {"messages": [], "timeline_events": []}
        if path.endswith("/chat-messages") or path.endswith("/timeline-events"):
            return 200, {"items": []}
        return 200, {}

    monkeypatch.setattr(release_candidate_smoke, "_request", fake_request)
    monkeypatch.setattr(
        sys,
        "argv",
        ["release_candidate_smoke.py", "--base-url", "http://backend", "--frontend-url", "http://frontend"],
    )

    assert release_candidate_smoke.main() == 0
    output = capsys.readouterr().out
    assert "release_candidate_ok=" in output
    assert all(method == "GET" or path == "/auth/token" for path, method in calls)
