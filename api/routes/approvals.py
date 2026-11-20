"""Human review and single-execution approval routes."""
from datetime import datetime
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import update
from api.auth import require_roles
from database.connection import SessionLocal
from database.models import Approval, AuditEvent
from workflows.engine import resume_approval
from observability import emit_event

router=APIRouter(prefix="/api/approvals",tags=["approvals"])

def _record_audit(db, user, request, approval, payload, decision, result):
    uid=user.get("id") if isinstance(user,dict) else user.id
    db.add(AuditEvent(user_id=uid,request_id=request.state.request_id,
        workflow_id=payload.get("thread_id",f"approval:{approval.id}"),agent_name="execution",tool_name=approval.action,
        proposed_action=json.dumps(payload,ensure_ascii=False),approval_decision=decision,
        execution_result=json.dumps(result,ensure_ascii=False,default=str)))

@router.get("")
def list_approvals(user=Depends(require_roles("admin","manager"))):
    db=SessionLocal()
    try:
        rows=db.query(Approval).order_by(Approval.id.desc()).all()
        return [{"id":r.id,"request":r.request,"action":r.action,"payload":json.loads(r.payload or "{}"),
            "status":r.status,"created_at":r.created_at.isoformat()} for r in rows]
    finally: db.close()

@router.get("/{approval_id}")
def approval_details(approval_id:int,user=Depends(require_roles("admin","manager"))):
    db=SessionLocal()
    try: row=db.get(Approval,approval_id)
    finally: db.close()
    if not row: raise HTTPException(404,"Approval not found")
    return {"id":row.id,"request":row.request,"action":row.action,"payload":json.loads(row.payload or "{}"),
        "status":row.status,"created_at":row.created_at.isoformat(),"resolved_at":row.resolved_at.isoformat() if row.resolved_at else None}

def _resolve(approval_id:int, approved:bool, request:Request, user):
    emit_event("approval.started", approval_id=approval_id, decision="approved" if approved else "rejected")
    db=SessionLocal(); approval=db.get(Approval,approval_id)
    if not approval: db.close(); raise HTTPException(404,"Approval not found")
    status="approved" if approved else "rejected"
    update_result=db.execute(update(Approval).where(Approval.id==approval_id,Approval.status=="pending").values(status=status,resolved_at=datetime.utcnow()))
    if not update_result.rowcount:
        db.rollback(); db.close(); raise HTTPException(409,"Approval already resolved")
    payload=json.loads(approval.payload or "{}")
    db.commit(); db.close()
    if payload.get("thread_id"):
        resumed=resume_approval(payload["thread_id"],approved,approval_id,user_id=payload.get("user_id","default"))
    elif approved:
        from agents.execution_agent import execute_approved
        resumed={"execution_results":execute_approved({"type":approval.action,**payload},approval_id=approval_id)}
    else: resumed=None
    result=(resumed or {}).get("execution_results") or {"status":"not_executed" if not approved else "pending"}
    audit=SessionLocal()
    try: _record_audit(audit,user,request,approval,payload,status,result); audit.commit()
    finally: audit.close()
    emit_event("approval.completed", approval_id=approval_id, decision=status, execution_status=result.get("status"))
    return {"id":approval_id,"status":status,"execution":(resumed or {}).get("execution_results"),"workflow":resumed}

@router.post("/{approval_id}/approve")
def approve(approval_id:int,request:Request,user=Depends(require_roles("admin","manager"))):
    return _resolve(approval_id,True,request,user)

@router.post("/{approval_id}/reject")
def reject(approval_id:int,request:Request,user=Depends(require_roles("admin","manager"))):
    return _resolve(approval_id,False,request,user)
