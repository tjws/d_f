"""发布候选版只读验收。

脚本只读取健康状态、演示客户工作台和管理接口，不创建客户、不触发 AI
工作流，也不会发送企业微信消息。它适合在 Docker 容器启动后从宿主机运行。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _request(
    base_url: str,
    path: str,
    *,
    token: str | None = None,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, object]:
    request_headers = dict(headers or {})
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        method=method,
        headers=request_headers,
    )
    try:
        with urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return response.status, {}
            try:
                return response.status, json.loads(raw)
            except json.JSONDecodeError:
                # 前端根路径返回 index.html；验收这里只需检查 HTTP 状态。
                return response.status, raw
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            payload: object = json.loads(detail)
        except json.JSONDecodeError:
            payload = detail
        return exc.code, payload
    except URLError as exc:
        raise RuntimeError(f"{base_url} unavailable: {exc.reason}") from exc


def _expect(
    base_url: str,
    path: str,
    expected_status: int,
    *,
    token: str | None = None,
) -> object:
    actual_status, payload = _request(base_url, path, token=token)
    if actual_status != expected_status:
        raise RuntimeError(f"{path} expected HTTP {expected_status}, got {actual_status}: {payload}")
    return payload


def _login(base_url: str, username: str, password: str) -> str:
    status, payload = _request(
        base_url,
        "/auth/token",
        method="POST",
        body=urlencode({"username": username, "password": password}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if status != 200 or not isinstance(payload, Mapping) or not payload.get("access_token"):
        raise RuntimeError(f"login failed for '{username}': HTTP {status}")
    return str(payload["access_token"])


def _items(payload: object, key: str = "items") -> list[object]:
    if isinstance(payload, list):
        return list(payload)
    if not isinstance(payload, Mapping) or not isinstance(payload.get(key), list):
        raise RuntimeError(f"response does not contain a {key} list")
    return list(payload[key])


def main() -> int:
    parser = argparse.ArgumentParser(description="运行发布候选版只读验收")
    parser.add_argument("--base-url", default=os.getenv("RC_BASE_URL", "http://localhost:8001"))
    parser.add_argument("--frontend-url", default=os.getenv("RC_FRONTEND_URL", "http://localhost:5174"))
    parser.add_argument("--admin-username", default=os.getenv("RC_ADMIN_USERNAME", "demo_admin"))
    parser.add_argument("--admin-password", default=os.getenv("RC_ADMIN_PASSWORD", "Demo123456!"))
    parser.add_argument("--sales-username", default=os.getenv("RC_SALES_USERNAME", "demo_sales"))
    parser.add_argument("--sales-password", default=os.getenv("RC_SALES_PASSWORD", "Demo123456!"))
    parser.add_argument("--customer-id", type=int, default=None)
    parser.add_argument("--skip-frontend", action="store_true")
    args = parser.parse_args()

    try:
        health = _expect(args.base_url, "/health", 200)
        if not isinstance(health, Mapping) or health.get("status") != "ok":
            raise RuntimeError(f"health payload is not ok: {health}")

        ready = _expect(args.base_url, "/health/ready", 200)
        if not isinstance(ready, Mapping) or ready.get("status") != "ready":
            raise RuntimeError(f"readiness payload is not ready: {ready}")

        anonymous_status, _ = _request(args.base_url, "/customers?page=1&page_size=1")
        if anonymous_status != 401:
            raise RuntimeError(f"anonymous customers expected HTTP 401, got {anonymous_status}")

        admin_token = _login(args.base_url, args.admin_username, args.admin_password)
        customers = _items(_expect(args.base_url, "/customers?page=1&page_size=20", 200, token=admin_token))
        if not customers:
            raise RuntimeError("customer list is empty; seed local demo data before release smoke")
        first_customer = customers[0]
        if not isinstance(first_customer, Mapping) or "id" not in first_customer:
            raise RuntimeError("customer list item does not contain id")
        customer_id = args.customer_id or int(first_customer["id"])

        _expect(args.base_url, f"/customers/{customer_id}", 200, token=admin_token)
        _items(_expect(args.base_url, f"/customers/{customer_id}/chat-messages", 200, token=admin_token), key="items")
        _items(_expect(args.base_url, f"/customers/{customer_id}/timeline-events", 200, token=admin_token), key="items")
        sidebar = _expect(args.base_url, f"/customers/{customer_id}/sidebar-sync", 200, token=admin_token)
        if not isinstance(sidebar, Mapping) or not isinstance(sidebar.get("messages"), list) or not isinstance(sidebar.get("timeline_events"), list):
            raise RuntimeError("sidebar sync payload is incomplete")

        for path in (
            "/admin/ai-dashboard",
            "/admin/ai-workflow-runs?limit=1",
            "/admin/system-settings",
            "/admin/system-status",
            "/admin/operations",
            "/admin/permissions",
            "/admin/data-export/policy",
            "/knowledge/admin",
        ):
            _expect(args.base_url, path, 200, token=admin_token)

        sales_token = _login(args.base_url, args.sales_username, args.sales_password)
        for path in ("/admin/ai-dashboard", "/admin/system-status"):
            _expect(args.base_url, path, 403, token=sales_token)

        if not args.skip_frontend:
            _expect(args.frontend_url, "/", 200)
            _expect(args.frontend_url, "/api/health/ready", 200)
    except (RuntimeError, HTTPError, URLError) as exc:
        print(f"release_candidate_failed={exc}", file=sys.stderr)
        return 1

    print(
        "release_candidate_ok="
        "health,readiness,anonymous_401,admin_workspace,admin_governance,sales_403,frontend_proxy"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
