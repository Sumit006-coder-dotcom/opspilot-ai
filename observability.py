"""Privacy-conscious structured operational events for the application."""
from __future__ import annotations

import contextvars
import json
import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
_workflow_id: contextvars.ContextVar[str] = contextvars.ContextVar("workflow_id", default="")
_logger = logging.getLogger("operlynt.events")


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S") + "Z",
                   "level": record.levelname, "event": record.getMessage(),
                   "request_id": _request_id.get() or None,
                   "workflow_id": _workflow_id.get() or None}
        fields = getattr(record, "event_fields", {})
        payload.update(fields)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    if not any(getattr(handler, "_operlynt_json", False) for handler in _logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter())
        handler._operlynt_json = True  # type: ignore[attr-defined]
        _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


def emit_event(event: str, *, level: int = logging.INFO, **fields: Any) -> None:
    """Emit only caller-selected metadata; never pass prompts, tokens, or payloads."""
    configure_logging()
    _logger.log(level, event, extra={"event_fields": fields})


@contextmanager
def event_context(*, request_id: str | None = None, workflow_id: str | None = None) -> Iterator[None]:
    request_token = _request_id.set(request_id or _request_id.get() or uuid.uuid4().hex)
    workflow_token = _workflow_id.set(workflow_id if workflow_id is not None else _workflow_id.get())
    try:
        yield
    finally:
        _request_id.reset(request_token)
        _workflow_id.reset(workflow_token)


@contextmanager
def timed_event(event: str, **fields: Any) -> Iterator[dict[str, Any]]:
    started = time.perf_counter()
    outcome: dict[str, Any] = {"status": "success"}
    try:
        yield outcome
    except Exception as exc:
        outcome.update(status="error", error_type=type(exc).__name__)
        raise
    finally:
        emit_event(event, duration_ms=round((time.perf_counter() - started) * 1000, 3), **fields, **outcome)
