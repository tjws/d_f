"""本地 Mock 业务闭环验收。

默认只读检查；加入 ``--apply`` 才会为指定客户写入一条模拟销售出站消息，
并验证聊天消息与时间线是否一起落库。脚本不生成 AI、不调用百炼。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _request(base_url: str, path: str, token: str | None = None, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{base_url.rstrip('/')}{path}", data=body, method=method, headers=headers)
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{path} returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"无法连接 {base_url}: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="本地 Mock 客户沟通闭环验收")
    parser.add_argument("--base-url", default=os.getenv("E2E_BASE_URL", "http://localhost:8001"))
    parser.add_argument("--username", default=os.getenv("E2E_USERNAME", "demo_admin"))
    parser.add_argument("--password", default=os.getenv("E2E_PASSWORD", "Demo123456!"))
    parser.add_argument("--customer-id", type=int, default=None)
    parser.add_argument("--apply", action="store_true", help="写入一条 Mock 出站消息并验证时间线联动")
    args = parser.parse_args()

    try:
        # OAuth2 表单登录单独构造，避免在普通 JSON 请求中误传密码。
        login_request = Request(
            f"{args.base_url.rstrip('/')}/auth/token",
            data=urlencode({"username": args.username, "password": args.password}).encode(),
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urlopen(login_request, timeout=10) as response:
            login_status = response.status
            login = json.loads(response.read().decode("utf-8"))
        if login_status != 200 or not login.get("access_token"):
            raise RuntimeError("登录失败")
        token = str(login["access_token"])
        customers_status, customers = _request(args.base_url, "/customers?page=1&page_size=100", token)
        if customers_status != 200 or not customers.get("items"):
            raise RuntimeError("客户列表为空，无法执行闭环验收")
        customer_id = args.customer_id or int(customers["items"][0]["id"])
        before_messages = _request(args.base_url, f"/customers/{customer_id}/chat-messages", token)[1]
        before_timeline = _request(args.base_url, f"/customers/{customer_id}/timeline-events", token)[1]
        if args.apply:
            message_id = f"e2e-{uuid.uuid4().hex}"
            _request(
                args.base_url,
                f"/customers/{customer_id}/chat-messages/mock",
                token,
                method="POST",
                payload={
                    "wecom_message_id": message_id,
                    "direction": "outbound",
                    "message_type": "text",
                    "content": "本地 E2E 验收消息，不代表真实发送。",
                },
            )
            after_messages = _request(args.base_url, f"/customers/{customer_id}/chat-messages", token)[1]
            after_timeline = _request(args.base_url, f"/customers/{customer_id}/timeline-events", token)[1]
            if len(after_messages) != len(before_messages) + 1 or len(after_timeline) != len(before_timeline) + 1:
                raise RuntimeError("聊天消息与时间线未按同一事务各增加一条")
            print(f"e2e_apply_ok customer_id={customer_id} messages=+1 timeline=+1")
        else:
            print(f"e2e_readonly_ok customer_id={customer_id} messages={len(before_messages)} timeline={len(before_timeline)}")
    except (RuntimeError, HTTPError, URLError) as exc:
        print(f"e2e_failed={exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
