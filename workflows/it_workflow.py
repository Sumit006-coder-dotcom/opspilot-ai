"""Public IT workflow integration retained for existing callers."""
from workflows.engine import build_workflow, run_workflow
workflow = build_workflow("it")
def run(query: str, action: dict | None = None, *, thread_id: str | None = None, user_id: str = "default", request_id: str = "") -> dict:
    return run_workflow(query, "it", action, thread_id=thread_id, user_id=user_id,request_id=request_id)
