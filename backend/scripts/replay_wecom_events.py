"""通过现有 Mock 回调管道回放一组家长消息。

默认只打印将要发送的事件；只有显式加入 ``--apply`` 才会请求后端，
避免在学习或排查时误写入数据库。重复回放同一组事件可以观察幂等结果。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.integrations.wecom.callback import build_mock_signature


DEFAULT_MESSAGES = (
    "您好，想了解一下初一数学课程和收费。",
    "孩子最近数学成绩不太稳定，老师有什么建议吗？",
    "这周末可以安排一次试听课吗？",
)


def build_payloads(
    customer_id: int,
    userid: str,
    messages: list[str],
    event_prefix: str,
) -> list[dict[str, object]]:
    """生成稳定的事件编号；重复发送同一 payload 才能验证幂等。"""

    start = datetime.now(timezone.utc)
    return [
        {
            "event_id": f"{event_prefix}-{index}",
            "event_type": "chat_message",
            "userid": userid,
            "customer_id": customer_id,
            "wecom_message_id": f"{event_prefix}-message-{index}",
            "direction": "inbound",
            "message_type": "text",
            "content": content,
            "sent_at": (start + timedelta(seconds=index)).isoformat(),
        }
        for index, content in enumerate(messages, start=1)
    ]


def _post_callback(base_url: str, token: str, payload: dict[str, object]) -> dict[str, object]:
    """使用与后端一致的签名算法发送一条回调。"""

    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    nonce = f"replay-{payload['event_id']}"
    request = Request(
        f"{base_url.rstrip('/')}/wecom/mock/callback",
        data=body.encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Mock-Timestamp": timestamp,
            "X-Mock-Nonce": nonce,
            "X-Mock-Signature": build_mock_signature(token, timestamp, nonce, body),
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{payload['event_id']} returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"无法连接 {base_url}: {exc.reason}") from exc


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="回放本地 Mock 企业微信家长消息")
    parser.add_argument("--customer-id", type=int, required=True, help="接收消息的本地客户 ID")
    parser.add_argument(
        "--userid",
        default=os.getenv("WECOM_REPLAY_USERID", "demo-user-001"),
        help="已存在用户的 Mock 企业微信 userid（默认 demo-user-001）",
    )
    parser.add_argument("--message", action="append", dest="messages", help="自定义消息；可重复指定")
    parser.add_argument("--event-prefix", default=None, help="事件编号前缀；不指定时自动生成")
    parser.add_argument("--repeat", type=int, choices=range(1, 4), default=1, help="同一组事件发送次数（1-3）")
    parser.add_argument("--base-url", default=os.getenv("WECOM_REPLAY_BASE_URL", "http://localhost:8001"))
    parser.add_argument("--token", default=os.getenv("WECOM_CALLBACK_TOKEN"), help="Mock 回调 token；仅从环境变量或命令行读取")
    parser.add_argument("--apply", action="store_true", help="真正请求后端；不加时只预览")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    messages = args.messages or list(DEFAULT_MESSAGES)
    prefix = args.event_prefix or f"replay-{int(datetime.now(timezone.utc).timestamp())}"
    payloads = build_payloads(args.customer_id, args.userid, messages, prefix)

    print(f"base_url={args.base_url}, customer_id={args.customer_id}, events={len(payloads)}, repeat={args.repeat}")
    for payload in payloads:
        print(f"preview event_id={payload['event_id']} message={payload['content']}")

    if not args.apply:
        print("预览模式：加入 --apply 才会写入后端数据库。")
        return 0
    if not args.token:
        print("缺少 Mock 回调 token：请设置 WECOM_CALLBACK_TOKEN，或用 --token 临时传入。", file=sys.stderr)
        return 2

    for attempt in range(1, args.repeat + 1):
        for payload in payloads:
            try:
                result = _post_callback(args.base_url, args.token, payload)
            except RuntimeError as exc:
                print(f"attempt={attempt} failed={exc}", file=sys.stderr)
                return 1
            print(f"attempt={attempt} event_id={payload['event_id']} status={result.get('status')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
