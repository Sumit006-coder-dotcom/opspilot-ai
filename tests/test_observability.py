import json
import logging

from observability import _JsonFormatter, event_context


def test_structured_events_carry_ids_and_explicit_fields_without_payloads():
    with event_context(request_id="req-test", workflow_id="wf-test"):
        record = logging.LogRecord("operlynt.events", logging.INFO, "", 0, "agent.completed", (), None)
        record.event_fields = {"agent": "rag", "duration_ms": 12.5, "provider": "demo"}
        row = json.loads(_JsonFormatter().format(record))
    assert row["event"] == "agent.completed"
    assert row["request_id"] == "req-test"
    assert row["workflow_id"] == "wf-test"
    assert row["duration_ms"] == 12.5
    assert "secret" not in json.dumps(row).lower()
