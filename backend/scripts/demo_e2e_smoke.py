"""演示数据的本地端到端验收。

这套检查只访问已经存在的业务接口，不调用百炼、Qdrant Embedding 或真实企业微信。
默认只读；``--apply`` 只会把一条 Mock 语音转成文字，方便验证“语音 -> 时间线”闭环。
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
    payload: object | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, object]:
    body = (
        payload
        if isinstance(payload, bytes)
        else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if payload is not None
        else None
    )
    request_headers = dict(headers or {})
    if body is not None:
        request_headers.setdefault("Content-Type", "application/json")
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{base_url.rstrip('/')}{path}", data=body, method=method, headers=request_headers)
    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return response.status, {}
            try:
                return response.status, json.loads(raw)
            except json.JSONDecodeError:
                # 前端首页是 HTML；验收脚本只需确认 HTTP 200，不应要求它是 JSON。
                return response.status, raw
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload_value: object = json.loads(raw)
        except json.JSONDecodeError:
            payload_value = raw
        return exc.code, payload_value
    except URLError as exc:
        raise RuntimeError(f"无法连接 {base_url}: {exc.reason}") from exc


def _expect(base_url: str, path: str, expected_status: int, *, token: str | None = None) -> object:
    status, payload = _request(base_url, path, token=token)
    if status != expected_status:
        raise RuntimeError(f"{path} 预期 HTTP {expected_status}，实际 {status}: {payload}")
    return payload


def _login(base_url: str, username: str, password: str) -> str:
    status, payload = _request(
        base_url,
        "/auth/token",
        method="POST",
        payload=urlencode({"username": username, "password": password}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if status != 200 or not isinstance(payload, Mapping) or not payload.get("access_token"):
        raise RuntimeError(f"账号 {username!r} 登录失败：HTTP {status}")
    return str(payload["access_token"])


def _items(payload: object, label: str) -> list[Mapping[str, object]]:
    if not isinstance(payload, list):
        raise RuntimeError(f"{label} 返回格式不是列表：{payload}")
    return [item for item in payload if isinstance(item, Mapping)]


def main() -> int:
    parser = argparse.ArgumentParser(description="验收本地演示数据和主要业务闭环")
    parser.add_argument("--base-url", default=os.getenv("DEMO_BASE_URL", "http://localhost:8001"))
    parser.add_argument("--frontend-url", default=os.getenv("DEMO_FRONTEND_URL", "http://localhost:5174"))
    parser.add_argument("--admin-username", default=os.getenv("DEMO_ADMIN_USERNAME", "demo_admin"))
    parser.add_argument("--admin-password", default=os.getenv("DEMO_ADMIN_PASSWORD", "Demo123456!"))
    parser.add_argument("--sales-username", default=os.getenv("DEMO_SALES_USERNAME", "demo_sales"))
    parser.add_argument("--sales-password", default=os.getenv("DEMO_SALES_PASSWORD", "Demo123456!"))
    parser.add_argument("--customer-id", type=int, default=None)
    parser.add_argument("--apply", action="store_true", help="转写一条 Mock 语音并验证幂等性")
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument(
        "--skip-readiness",
        action="store_true",
        help="仅用于未启动 Redis 的 SQLite 学习环境；Compose 验收不要跳过",
    )
    args = parser.parse_args()

    try:
        if not args.skip_readiness:
            ready = _expect(args.base_url, "/health/ready", 200)
            if not isinstance(ready, Mapping) or ready.get("status") != "ready":
                raise RuntimeError(f"readiness 未就绪：{ready}")

        anonymous_status, _ = _request(args.base_url, "/customers?page=1&page_size=1")
        if anonymous_status != 401:
            raise RuntimeError(f"匿名客户列表应为 401，实际 {anonymous_status}")

        admin_token = _login(args.base_url, args.admin_username, args.admin_password)
        customer_payload = _expect(args.base_url, "/customers?page=1&page_size=100", 200, token=admin_token)
        if not isinstance(customer_payload, Mapping) or not isinstance(customer_payload.get("items"), list):
            raise RuntimeError(f"客户列表格式不正确：{customer_payload}")
        customers = [item for item in customer_payload["items"] if isinstance(item, Mapping)]
        if len(customers) < 3:
            raise RuntimeError(f"演示客户不足 3 个，当前 {len(customers)} 个；请先运行 seed_demo_data --apply")
        # 列表可能包含用户之前手动创建的客户；无参数时优先选 seed 标记的完整样例。
        demo_customer = next((item for item in customers if item.get("source") == "demo-seed"), None)
        customer_id = args.customer_id or int((demo_customer or customers[0])["id"])

        detail = _expect(args.base_url, f"/customers/{customer_id}", 200, token=admin_token)
        if not isinstance(detail, Mapping) or detail.get("id") != customer_id:
            raise RuntimeError("客户详情与请求 ID 不一致")
        students = _items(_expect(args.base_url, f"/customers/{customer_id}/students", 200, token=admin_token), "学生")
        messages = _items(_expect(args.base_url, f"/customers/{customer_id}/chat-messages", 200, token=admin_token), "聊天")
        timeline = _items(_expect(args.base_url, f"/customers/{customer_id}/timeline-events", 200, token=admin_token), "时间线")
        sidebar = _expect(args.base_url, f"/customers/{customer_id}/sidebar-sync", 200, token=admin_token)
        if not isinstance(sidebar, Mapping) or not isinstance(sidebar.get("messages"), list) or not isinstance(sidebar.get("timeline_events"), list):
            raise RuntimeError("侧边栏同步结果缺少 messages 或 timeline_events")
        suggestions = _items(_expect(args.base_url, f"/customers/{customer_id}/suggestions", 200, token=admin_token), "AI 建议")

        voice = next((message for message in messages if message.get("message_type") == "voice"), None)
        if voice is None:
            raise RuntimeError("演示客户没有 voice Mock 消息")
        voice_result = "pending_manual_transcription"
        if args.apply:
            before_timeline_count = len(timeline)
            transcribe_path = f"/customers/{customer_id}/chat-messages/{voice['id']}/transcribe"
            transcribe_status, transcribed = _request(
                args.base_url, transcribe_path, token=admin_token, method="POST"
            )
            if transcribe_status != 200:
                raise RuntimeError(f"{transcribe_path} 预期 HTTP 200，实际 {transcribe_status}: {transcribed}")
            if not isinstance(transcribed, Mapping) or not transcribed.get("content"):
                raise RuntimeError("Mock 语音转写没有返回内容")
            repeat_status, repeat = _request(
                args.base_url, transcribe_path, token=admin_token, method="POST"
            )
            if repeat_status != 200:
                raise RuntimeError(f"重复调用 {transcribe_path} 预期 HTTP 200，实际 {repeat_status}: {repeat}")
            if not isinstance(repeat, Mapping) or repeat.get("content") != transcribed.get("content"):
                raise RuntimeError("重复转写没有保持幂等")
            after_timeline = _items(_expect(args.base_url, f"/customers/{customer_id}/timeline-events", 200, token=admin_token), "转写后时间线")
            expected_delta = 0 if voice.get("content") else 1
            if len(after_timeline) != before_timeline_count + expected_delta:
                raise RuntimeError("语音转写时间线事件数量不符合幂等预期")
            voice_result = "transcribed_and_idempotent"

        order_count = 0
        ticket_count = 0
        for item in customers:
            item_id = item.get("id")
            if item_id is None:
                continue
            order_count += len(_items(_expect(args.base_url, f"/customers/{item_id}/orders", 200, token=admin_token), "订单"))
            ticket_count += len(_items(_expect(args.base_url, f"/customers/{item_id}/service-tickets", 200, token=admin_token), "工单"))
        if order_count < 1 or ticket_count < 1:
            raise RuntimeError(f"演示订单/工单不足：orders={order_count}, tickets={ticket_count}")

        for path in (
            "/admin/ai-dashboard",
            "/admin/operations",
            "/admin/system-status",
            "/admin/data-export/policy",
            "/knowledge/admin",
        ):
            _expect(args.base_url, path, 200, token=admin_token)

        sales_token = _login(args.base_url, args.sales_username, args.sales_password)
        for path in ("/admin/ai-dashboard", "/admin/system-status", "/admin/data-export/policy"):
            denied_status, _ = _request(args.base_url, path, token=sales_token)
            if denied_status != 403:
                raise RuntimeError(f"sales 访问 {path} 应为 403，实际 {denied_status}")

        if not args.skip_frontend:
            _expect(args.frontend_url, "/", 200)
            _expect(args.frontend_url, "/api/health/ready", 200)

        print(
            "demo_e2e_ok="
            f"customers:{len(customers)},students:{len(students)},messages:{len(messages)},"
            f"timeline:{len(timeline)},suggestions:{len(suggestions)},orders:{order_count},"
            f"tickets:{ticket_count},voice:{voice_result},admin_403:ok,frontend:{not args.skip_frontend}"
        )
        return 0
    except (RuntimeError, HTTPError, URLError, KeyError, TypeError, ValueError) as exc:
        print(f"demo_e2e_failed={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
