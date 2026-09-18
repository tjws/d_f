"""检查容器环境的最低鉴权边界；只读，不写业务数据。"""

from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _status(base_url: str, path: str, token: str | None = None) -> int:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    request = Request(f"{base_url.rstrip('/')}{path}", headers=headers)
    try:
        with urlopen(request, timeout=10) as response:
            return response.status
    except HTTPError as exc:
        return exc.code
    except URLError as exc:
        raise RuntimeError(f"无法连接 {base_url}: {exc.reason}") from exc


def _login(base_url: str, username: str, password: str) -> str:
    request = Request(
        f"{base_url.rstrip('/')}/auth/token",
        data=urlencode({"username": username, "password": password}).encode(),
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return str(payload["access_token"])


def main() -> int:
    base_url = os.getenv("SECURITY_BASE_URL", "http://localhost:8001")
    sales_username = os.getenv("SECURITY_SALES_USERNAME", "demo_sales")
    try:
        anonymous_customers = _status(base_url, "/customers?page=1&page_size=1")
        anonymous_pending = _status(base_url, "/pending-actions")
        if anonymous_customers != 401 or anonymous_pending != 401:
            raise RuntimeError(f"anonymous boundary failed: customers={anonymous_customers}, pending={anonymous_pending}")

        sales_token = _login(
            base_url,
            sales_username,
            os.getenv("SECURITY_SALES_PASSWORD", "Demo123456!"),
        )
        dashboard = _status(base_url, "/admin/ai-dashboard", sales_token)
        audit_logs = _status(base_url, "/audit-logs?page=1&page_size=1", sales_token)
        if dashboard != 403 or audit_logs != 403:
            raise RuntimeError(f"sales role boundary failed: dashboard={dashboard}, audit_logs={audit_logs}")
    except HTTPError as exc:
        if exc.code == 401:
            print(
                f"security_failed=sales login failed for '{sales_username}'; "
                "set SECURITY_SALES_USERNAME/SECURITY_SALES_PASSWORD or run "
                "python -m scripts.ensure_demo_accounts --apply --reset-passwords",
                file=sys.stderr,
            )
        else:
            print(f"security_failed={exc}", file=sys.stderr)
        return 1
    except (RuntimeError, KeyError, URLError) as exc:
        print(f"security_failed={exc}", file=sys.stderr)
        return 1
    print("security_ok=anonymous_401,sales_admin_403,APP_DEV_AUTH_BYPASS must remain 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
