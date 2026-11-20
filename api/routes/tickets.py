"""Ticket read routes and approval-gated ticket creation."""
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from api.auth import require_roles
from api.dependencies import require_auth
from database.connection import SessionLocal
from database.models import Ticket, Approval, AuditEvent

router=APIRouter(prefix="/api/tickets",tags=["tickets"])

class TicketCreate(BaseModel):
    title:str=Field(min_length=3,max_length=200)
    description:str=Field(min_length=3,max_length=2000)
    category:str=Field(default="other",min_length=2,max_length=80)
    severity:str=Field(default="medium",pattern="^(low|medium|high|critical)$")

@router.get("",dependencies=[Depends(require_auth)])
def tickets():
    db=SessionLocal()
    try:return [{"id":t.id,"title":t.title,"category":t.category,"severity":t.severity,"status":t.status} for t in db.query(Ticket).order_by(Ticket.id.desc()).limit(300).all()]
    finally:db.close()

@router.get("/{ticket_id}",dependencies=[Depends(require_auth)])
def ticket_details(ticket_id:int):
    db=SessionLocal()
    try:t=db.get(Ticket,ticket_id)
    finally:db.close()
    if not t:raise HTTPException(404,"Ticket not found")
    return {"id":t.id,"title":t.title,"description":t.description,"category":t.category,"severity":t.severity,"status":t.status,"created_at":t.created_at.isoformat()}

@router.post("",status_code=202)
def create_ticket(req:TicketCreate,request:Request,user=Depends(require_roles("admin","manager"))):
    db=SessionLocal()
    try:
        action={"type":"create_it_ticket",**req.model_dump()}
        row=Approval(request=f"Ticket creation requested: {req.title}",action="create_it_ticket",payload=json.dumps(action),status="pending")
        db.add(row);db.flush();uid=user.get("id") if isinstance(user,dict) else user.id
        db.add(AuditEvent(user_id=uid,request_id=request.state.request_id,workflow_id=f"approval:{row.id}",agent_name="api",tool_name="create_it_ticket",proposed_action=json.dumps(action),approval_decision="pending"))
        db.commit();return {"approval_id":row.id,"status":"pending","action":action}
    finally:db.close()
