from scripts.replay_wecom_events import build_payloads


def test_replay_payloads_have_stable_event_and_message_ids():
    payloads = build_payloads(7, "mock-demo_sales", ["第一条", "第二条"], "replay-check")

    assert [item["event_id"] for item in payloads] == ["replay-check-1", "replay-check-2"]
    assert [item["wecom_message_id"] for item in payloads] == [
        "replay-check-message-1",
        "replay-check-message-2",
    ]
    assert all(item["direction"] == "inbound" for item in payloads)


def test_replay_payloads_change_ids_only_when_prefix_changes():
    first = build_payloads(1, "mock-demo_sales", ["同一条"], "run-a")
    second = build_payloads(1, "mock-demo_sales", ["同一条"], "run-b")

    assert first[0]["event_id"] != second[0]["event_id"]
    assert first[0]["content"] == second[0]["content"]
