"""对运行中的 FastAPI 容器执行只读 smoke 检查。

不会创建客户、触发 AI 或修改数据库；只验证 readiness、登录、客户列表和本地知识库。
"""

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _request(base_url: str, path: str, method: str = "GET", body: bytes | None = None, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    request = Request(f"{base_url.rstrip('/')}{path}", data=body, method=method, headers=headers or {})
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"{path} returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"{path} unavailable: {exc.reason}") from exc


def main() -> int:
    base_url = os.getenv("SMOKE_BASE_URL", "http://localhost:8001")
    username = os.getenv("SMOKE_USERNAME", "demo_admin")
    password = os.getenv("SMOKE_PASSWORD", "Demo123456!")
    try:
        ready_status, ready = _request(base_url, "/health/ready")
        if ready_status != 200 or ready.get("status") != "ready":
            raise RuntimeError(f"readiness failed: {ready}")
        token_status, token_payload = _request(base_url, "/auth/token", "POST", urlencode({"username": username, "password": password}).encode(), {"Content-Type": "application/x-www-form-urlencoded"})
        if token_status != 200 or not token_payload.get("access_token"):
            raise RuntimeError("login failed")
        headers = {"Authorization": f"Bearer {token_payload['access_token']}"}
        customer_status, customers = _request(base_url, "/customers?page=1&page_size=5", headers=headers)
        # 生产 smoke 只验证本地关键词检索，避免验收脚本隐式调用百炼 Embedding。
        knowledge_path = "/knowledge/search?" + urlencode({"q": "试听收费", "limit": 3, "use_vector": "false"})
        knowledge_status, knowledge = _request(base_url, knowledge_path, headers=headers)
        if customer_status != 200 or knowledge_status != 200 or not isinstance(customers.get("items"), list) or not knowledge.get("items"):
            raise RuntimeError("business smoke check failed")
    except RuntimeError as exc:
        print(f"smoke_failed={exc}")
        return 1
    print(f"smoke_ok=ready:{ready_status},login:{token_status},customers:{customer_status},knowledge:{knowledge_status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
