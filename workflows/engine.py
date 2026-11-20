"""Shared LangGraph StateGraph, routing, persistence, and approval gate."""
from __future__ import annotations
import hashlib, json, sqlite3, time, uuid
from pathlib import Path
from typing import Any
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import MemorySaver
from config import settings
from workflows.state import WorkflowState
from agents import orchestrator, ecommerce_agent, it_operations_agent, data_analyst_agent, research_agent, rag_agent, decision_agent, execution_agent
from database.connection import SessionLocal
from database.models import AgentLog
from observability import event_context, emit_event

_CHECKPOINTER = None
_PERSISTENCE = "memory_fallback"
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    _db_path = Path(settings.workflow_checkpoint_path)
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(str(_db_path), check_same_thread=False)
    _CHECKPOINTER = SqliteSaver(_conn)
    _CHECKPOINTER.setup()
    _PERSISTENCE = "sqlite"
except ImportError:
    # Requirements include the SQLite saver. This fallback keeps demo mode usable
    # in lean test environments that have not installed the optional dependency.
    _CHECKPOINTER = MemorySaver()

def persistence_backend() -> str: return _PERSISTENCE

def scoped_thread_id(thread_id: str | None, user_id: str = "default", domain: str | None = None) -> str:
    user_scope = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16]
    domain_scope = f":{domain}" if domain else ""
    return f"{user_scope}{domain_scope}:{thread_id or uuid.uuid4().hex}"

def _log(agent: str, fn):
    started = time.perf_counter()
    emit_event("agent.started", agent=agent)
    last_error = None
    for attempt in range(2):
        try:
            result = fn()
            emit_event("agent.completed", agent=agent, duration_ms=round((time.perf_counter()-started)*1000,3), attempt=attempt+1, status="success")
            db = SessionLocal()
            try:
                db.add(AgentLog(agent=agent, status="success", duration_ms=int((time.perf_counter()-started)*1000), detail=f"completed; attempt={attempt+1}")); db.commit()
            finally: db.close()
            return result
        except Exception as exc:
            last_error = exc
            if attempt == 1:
                emit_event("agent.completed", level=__import__("logging").ERROR, agent=agent, duration_ms=round((time.perf_counter()-started)*1000,3), attempt=attempt+1, status="error", error_type=type(exc).__name__)
                db = SessionLocal()
                try:
                    db.add(AgentLog(agent=agent, status="error", duration_ms=int((time.perf_counter()-started)*1000), detail=type(exc).__name__)); db.commit()
                finally: db.close()
    raise last_error

def _append(state: WorkflowState, name: str, result: dict) -> dict:
    results = dict(state.get("agent_results", {})); results[name] = result
    findings = list(state.get("findings", [])); findings.append({"agent": name, "result": result})
    ran = list(state.get("agents", [])); ran.append(name)
    errors = list(state.get("errors", []))
    if result.get("error"):
        errors.append({"agent": name, "error": result["error"], "retryable": False})
    return {"agent_results": results, "findings": findings, "agents": ran, "errors": errors}

def _safe(agent: str, fn):
    try: return _log(agent, fn)
    except Exception as exc: return {"error": type(exc).__name__, "message": f"{agent} could not complete after retry."}

def build_workflow(domain: str):
    builder = StateGraph(WorkflowState)
    def orchestrator_node(s):
        out = _safe("orchestrator", lambda: orchestrator.route(s.get("user_query", s.get("query", "")), domain))
        if out.get("error"):
            out = {"business_domain": domain, "domain": domain, "execution_plan": ["ecommerce" if domain == "ecommerce" else "it_operations", "decision"], "plan": ["ecommerce" if domain == "ecommerce" else "it_operations", "decision"], "orchestration": {"error": out["error"]}}
        return {**out, "execution_plan": out["execution_plan"], "agents": ["orchestrator"], "agent_results": {"orchestrator": out["orchestration"]}, "errors": s.get("errors", [])}
    def specialist_node(s):
        agent = ecommerce_agent if domain == "ecommerce" else it_operations_agent
        name = "ecommerce" if domain == "ecommerce" else "it_operations"
        return _append(s, name, _safe(name, lambda: agent.investigate(s.get("user_query", s.get("query", "")))))
    def analytics_node(s):
        metrics = _safe("data_analyst", lambda: data_analyst_agent.analyze(domain, s.get("user_query", "")))
        result = {"metrics": metrics, "query_focus": s.get("user_query", ""), "source": "SQLAlchemy operational database"}
        if metrics.get("error"): result["error"] = metrics["error"]
        out = _append(s, "data_analyst", result)
        return {**out, "analytics_results": metrics}
    def research_node(s):
        records = _safe("research", lambda: research_agent.research(s.get("user_query", ""), domain))
        result = {"records": records, "query_focus": s.get("user_query", "")}
        if isinstance(records, dict) and records.get("error"): result["error"] = records["error"]
        return _append(s, "research", result)
    def rag_node(s):
        result = _safe("rag", lambda: rag_agent.run(s.get("user_query", ""), domain))
        result.setdefault("documents", []); result.setdefault("references", []); result.setdefault("evidence", [])
        out = _append(s, "rag", result)
        return {**out, "retrieved_documents": result["documents"]}
    def decision_node(s):
        result = _safe("decision", lambda: decision_agent.decide(s.get("user_query", ""), domain, s.get("findings", [])))
        result.setdefault("answer", "The investigation completed with partial agent results."); result.setdefault("recommendations", []); result.setdefault("sources", [])
        out = _append(s, "decision", result)
        actions = list(s.get("proposed_actions", []))
        if s.get("action"): actions = [dict(s["action"])]
        return {**out, "recommendations": result["recommendations"], "proposed_actions": actions,
                "answer": result["answer"], "final_response": result["answer"], "sources": result["sources"]}
    def prepare_approval(s):
        action = (s.get("proposed_actions") or [])[0]
        approval = _log("execution", lambda: execution_agent.create_approval(s.get("user_query", ""), action, s.get("thread_id", ""), s.get("user_id", "default")))
        out = _append(s, "execution", {"prepared": execution_agent.prepare(s.get("user_query", ""), action), **approval})
        return {**out, "needs_approval": True, "approval_status": "pending", "action_result": approval}
    def approval_gate(s):
        decision = interrupt({"type": "approval_required", "approval_id": s.get("action_result", {}).get("approval_id"), "action": (s.get("proposed_actions") or [{}])[0], "thread_id": s.get("thread_id")})
        status = "approved" if decision and decision.get("approved") else "rejected"
        return {"approval_status": status, "action_result": {**s.get("action_result", {}), "status": status}}
    def execute_node(s):
        action = (s.get("proposed_actions") or [{}])[0]
        approval_id = s.get("action_result", {}).get("approval_id")
        result = _log("execution", lambda: execution_agent.execute_approved(action, approval_id=approval_id))
        out = _append(s, "execution", {"execution": result})
        return {**out, "execution_results": result, "action_result": {**s.get("action_result", {}), "execution": result},
                "final_response": s.get("final_response", "") + " Approved action result: " + json.dumps(result, ensure_ascii=False)}
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("ecommerce", specialist_node); builder.add_node("it_operations", specialist_node)
    builder.add_node("data_analyst", analytics_node); builder.add_node("research", research_node); builder.add_node("rag", rag_node)
    builder.add_node("decision", decision_node); builder.add_node("prepare_approval", prepare_approval)
    builder.add_node("approval_gate", approval_gate); builder.add_node("execution", execute_node)
    builder.add_edge(START, "orchestrator")
    def first(s): return "ecommerce" if domain == "ecommerce" else "it_operations"
    builder.add_conditional_edges("orchestrator", first, {"ecommerce":"ecommerce", "it_operations":"it_operations"})
    def after_specialist(s): return "data_analyst" if "data_analyst" in s.get("execution_plan", []) else "research" if "research" in s.get("execution_plan", []) else "rag" if "rag" in s.get("execution_plan", []) else "decision"
    def after_analytics(s): return "research" if "research" in s.get("execution_plan", []) else "rag" if "rag" in s.get("execution_plan", []) else "decision"
    def after_research(s): return "rag" if "rag" in s.get("execution_plan", []) else "decision"
    builder.add_conditional_edges("ecommerce", after_specialist, {"data_analyst":"data_analyst", "research":"research", "rag":"rag", "decision":"decision"})
    builder.add_conditional_edges("it_operations", after_specialist, {"data_analyst":"data_analyst", "research":"research", "rag":"rag", "decision":"decision"})
    builder.add_conditional_edges("data_analyst", after_analytics, {"research":"research", "rag":"rag", "decision":"decision"})
    builder.add_conditional_edges("research", after_research, {"rag":"rag", "decision":"decision"})
    builder.add_conditional_edges("rag", lambda s:"decision", {"decision":"decision"})
    builder.add_conditional_edges("decision", lambda s:"prepare_approval" if s.get("proposed_actions") else END, {"prepare_approval":"prepare_approval", END:END})
    builder.add_edge("prepare_approval", "approval_gate")
    builder.add_conditional_edges("approval_gate", lambda s:"execution" if s.get("approval_status")=="approved" else END, {"execution":"execution", END:END})
    builder.add_edge("execution", END)
    return builder.compile(checkpointer=_CHECKPOINTER)

_WORKFLOWS = {"ecommerce": build_workflow("ecommerce"), "it": build_workflow("it")}

def run_workflow(query: str, domain: str, action: dict | None = None, *, thread_id: str | None = None, user_id: str = "default", request_id: str = "") -> dict:
    raw_id = thread_id or uuid.uuid4().hex
    scoped = scoped_thread_id(raw_id, user_id, domain)
    history = []
    if thread_id:
        old = get_workflow_state(thread_id, user_id=user_id).get("state", {})
        if old.get("business_domain") == domain:
            history = list(old.get("conversation_history", []))
    history.append({"query": query, "domain": domain, "timestamp": time.time()})
    state = {"user_query": query, "query": query, "business_domain": domain, "domain": domain,
             "thread_id": scoped, "user_id": user_id, "request_id":request_id, "action": action, "findings": [], "agents": [], "agent_results": {}, "errors": [],
             "proposed_actions": [], "analytics_results": {}, "retrieved_documents": [], "recommendations": [],
             "approval_status": None, "execution_results": {}, "action_result": {}, "needs_approval": False}
    state["conversation_history"] = history
    state["memory_context"] = [entry["query"] for entry in history[:-1]][-8:]
    started = time.perf_counter()
    with event_context(request_id=request_id or None, workflow_id=scoped):
        try:
            result = _WORKFLOWS[domain].invoke(state, config={"configurable": {"thread_id": scoped}})
        except Exception as exc:
            emit_event("workflow.error", level=__import__("logging").ERROR, domain=domain, error_type=type(exc).__name__, provider="demo" if settings.demo_mode else settings.llm_provider)
            raise
        finally:
            emit_event("workflow.completed", domain=domain, duration_ms=round((time.perf_counter()-started)*1000,3), provider="demo" if settings.demo_mode else settings.llm_provider)
    result["thread_id"] = raw_id
    result["persistence_backend"] = persistence_backend()
    if result.get("__interrupt__"):
        result["approval_interrupt"] = result["__interrupt__"][0].value
    return result

def resume_approval(thread_id: str, approved: bool, approval_id: int, user_id: str = "default") -> dict:
    if ":" in thread_id: scoped = thread_id
    else:
        prior = get_workflow_state(thread_id, user_id=user_id)
        scoped = scoped_thread_id(thread_id, user_id, prior.get("domain", "ecommerce"))
    config = {"configurable": {"thread_id": scoped}}
    state = _WORKFLOWS["ecommerce"].get_state(config)
    domain = state.values.get("business_domain", "ecommerce")
    result = _WORKFLOWS[domain].invoke(Command(resume={"approved": approved, "approval_id": approval_id}), config=config)
    result["thread_id"] = scoped.split(":", 1)[-1]
    result["persistence_backend"] = persistence_backend()
    return result

def get_workflow_state(thread_id: str, user_id: str = "default") -> dict:
    candidates = [(thread_id, None)] if thread_id.count(":") >= 2 else [(scoped_thread_id(thread_id, user_id, domain), domain) for domain in _WORKFLOWS]
    for scoped, candidate_domain in candidates:
        for domain, graph in _WORKFLOWS.items():
            if candidate_domain and candidate_domain != domain: continue
            snapshot = graph.get_state({"configurable": {"thread_id": scoped}})
            if snapshot.values: return {"thread_id": thread_id.split(":")[-1], "domain": domain, "next": list(snapshot.next), "state": snapshot.values}
    return {"thread_id": thread_id.split(":",1)[-1], "domain": None, "next": [], "state": {}}
