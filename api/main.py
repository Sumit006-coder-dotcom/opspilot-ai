from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import json
from config import settings
from database.connection import Base,engine,SessionLocal
from database.seed import seed
from database.models import Approval,AuditEvent
from api.dependencies import require_auth, require_roles
from api.auth import current_user
from api.routes.auth import router as auth_router
from api.routes.approvals import router as approvals_router
from api.routes.analytics import router as analytics_router
from api.routes.tickets import router as tickets_router
from workflows.ecommerce_workflow import run as run_ecommerce
from workflows.it_workflow import run as run_it
from workflows.engine import get_workflow_state
from rag.ingestion import ingest,ingest_document,IngestionError,DuplicateDocumentError,MAX_DOCUMENT_BYTES
from rag.retriever import search
from rag.vector_store import vector_store
from rag.chain import ask_question
from llm.provider import ProviderError,get_active_provider
from observability import event_context, emit_event
from sqlalchemy import text

app=FastAPI(title="Operlynt",version="0.2.0", description="Agentic AI Business Operations Intelligence Platform combining multi-agent orchestration, RAG, MCP tools, business analytics, and intelligent automation.")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()], allow_credentials=True, allow_methods=["GET","POST","OPTIONS"], allow_headers=["Authorization","Content-Type","X-Request-ID"])
app.include_router(auth_router)
app.include_router(approvals_router)
app.include_router(analytics_router)
app.include_router(tickets_router)

@app.middleware("http")
async def request_context(request: Request, call_next):
    import uuid, time
    request_id=request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id=request_id
    started=time.perf_counter()
    with event_context(request_id=request_id):
        try:
            response=await call_next(request)
            elapsed=round((time.perf_counter()-started)*1000,3)
            response.headers["X-Request-ID"]=request_id
            response.headers["X-Process-Time-Ms"]=str(int(elapsed))
            event_name="api.error" if response.status_code>=400 else "api.request"
            emit_event(event_name,level=__import__("logging").ERROR if response.status_code>=500 else __import__("logging").INFO,method=request.method,path=request.url.path,status_code=response.status_code,duration_ms=elapsed)
            return response
        except Exception as exc:
            emit_event("api.error",level=__import__("logging").ERROR,method=request.method,path=request.url.path,error_type=type(exc).__name__,duration_ms=round((time.perf_counter()-started)*1000,3))
            raise

@app.middleware("http")
async def auth_rate_limit(request: Request, call_next):
    # Small per-process throttle for password endpoints; production should use a shared limiter.
    import time
    now=time.monotonic(); key=(request.client.host if request.client else "unknown", request.url.path)
    if request.url.path in {"/api/auth/login","/api/auth/register"}:
        hits=_AUTH_HITS.setdefault(key,[]); hits[:]=[t for t in hits if now-t<60]
        if len(hits)>=20: return __import__("fastapi").responses.JSONResponse(status_code=429,content={"detail":"Too many authentication requests"})
        hits.append(now)
    return await call_next(request)

_AUTH_HITS={}
@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    seed()
class ChatRequest(BaseModel):
    query:str=Field(min_length=3,max_length=2000)
    domain:str=Field(pattern="^(ecommerce|it)$")
    action:dict|None=None
    thread_id:str|None=Field(default=None,min_length=1,max_length=120)
class RAGAskRequest(BaseModel):
    question:str=Field(min_length=3,max_length=2000)
    domain:str|None=Field(default=None,pattern="^(ecommerce|it|it_operations|historical_incidents)$")
    top_k:int=Field(default=4,ge=1,le=20)

def _audit(db, *, user_id=None, request_id="", workflow_id="", agent="api", tool="", action="", decision="", result=""):
    db.add(AuditEvent(user_id=user_id,request_id=request_id,workflow_id=workflow_id,agent_name=agent,tool_name=tool,
        proposed_action=json.dumps(action,ensure_ascii=False) if isinstance(action,(dict,list)) else str(action),
        approval_decision=decision,execution_result=json.dumps(result,ensure_ascii=False,default=str) if isinstance(result,(dict,list)) else str(result)))

def _owner_id(user):
    return str(user.get("id") if isinstance(user,dict) else user.id)
@app.get("/health")
def health():
    return {"status":"ok","demo_mode":settings.demo_mode}
@app.get("/health/ready")
def readiness():
    """Readiness probe includes the configured relational database."""
    db=SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status":"ready","database":"ok"}
    except Exception as exc:
        raise HTTPException(status_code=503,detail=f"Database unavailable ({type(exc).__name__})") from exc
    finally:
        db.close()
@app.post("/api/chat")
def chat(req:ChatRequest,request:Request,user=Depends(require_roles("admin","manager","analyst"))):
    import time
    started=time.perf_counter()
    owner=str(user.get("id") if isinstance(user,dict) else user.id)
    result=(run_ecommerce if req.domain=="ecommerce" else run_it)(req.query,req.action,thread_id=req.thread_id,user_id=owner,request_id=request.state.request_id)
    db=SessionLocal()
    try: _audit(db,user_id=int(owner) if owner.isdigit() else None,request_id=request.state.request_id,workflow_id=result.get("thread_id",""),agent="orchestrator",tool="langgraph_workflow",action=result.get("proposed_actions",req.action or []),decision=result.get("approval_status") or "",result={"agents":result.get("agents",[]),"errors":result.get("errors",[]),"duration_ms":int((time.perf_counter()-started)*1000)}); db.commit()
    finally: db.close()
    return result
@app.post("/api/ecommerce/investigate")
def ecommerce(req:ChatRequest,request:Request,user=Depends(require_roles("admin","manager","analyst"))):
    import time
    started=time.perf_counter()
    owner=str(user.get("id") if isinstance(user,dict) else user.id)
    result=run_ecommerce(req.query,req.action,thread_id=req.thread_id,user_id=owner,request_id=request.state.request_id)
    db=SessionLocal()
    try: _audit(db,user_id=int(owner) if owner.isdigit() else None,request_id=request.state.request_id,workflow_id=result.get("thread_id",""),agent="ecommerce",tool="langgraph_workflow",action=result.get("proposed_actions",req.action or []),decision=result.get("approval_status") or "",result={"agents":result.get("agents",[]),"errors":result.get("errors",[]),"duration_ms":int((time.perf_counter()-started)*1000)}); db.commit()
    finally: db.close()
    return result
@app.post("/api/it/investigate")
def it(req:ChatRequest,request:Request,user=Depends(require_roles("admin","manager","analyst"))):
    import time
    started=time.perf_counter()
    owner=str(user.get("id") if isinstance(user,dict) else user.id)
    result=run_it(req.query,req.action,thread_id=req.thread_id,user_id=owner,request_id=request.state.request_id)
    db=SessionLocal()
    try: _audit(db,user_id=int(owner) if owner.isdigit() else None,request_id=request.state.request_id,workflow_id=result.get("thread_id",""),agent="it_operations",tool="langgraph_workflow",action=result.get("proposed_actions",req.action or []),decision=result.get("approval_status") or "",result={"agents":result.get("agents",[]),"errors":result.get("errors",[]),"duration_ms":int((time.perf_counter()-started)*1000)}); db.commit()
    finally: db.close()
    return result
@app.get("/api/agents/activity")
def activity(user=Depends(current_user)):
    db=SessionLocal()
    query=db.query(AuditEvent).order_by(AuditEvent.id.desc())
    if not (isinstance(user,dict) and user.get("role")=="admin") and not (not isinstance(user,dict) and user.role=="admin"):
        query=query.filter(AuditEvent.user_id==int(_owner_id(user)))
    rows=query.limit(300).all()
    out=[{"user_id":r.user_id,"request_id":r.request_id,"workflow_id":r.workflow_id,"agent":r.agent_name,"tool":r.tool_name,
        "action":r.proposed_action,"approval_decision":r.approval_decision,"execution_result":r.execution_result,"created_at":r.created_at.isoformat()} for r in rows]
    db.close(); return out
@app.get("/api/workflows/{thread_id}/status")
def workflow_status(thread_id:str,user=Depends(current_user)):
    owner=_owner_id(user)
    return get_workflow_state(thread_id,user_id=owner)
@app.get("/api/workflows/{thread_id}/agents")
def workflow_agents(thread_id:str,user=Depends(current_user)):
    owner=_owner_id(user)
    state=get_workflow_state(thread_id,user_id=owner).get("state",{})
    return {"thread_id":thread_id,"agent_results":state.get("agent_results",{}),"agents":state.get("agents",[]),"errors":state.get("errors",[])}
@app.get("/api/executions/{approval_id}")
def execution_status(approval_id:int,user=Depends(current_user)):
    db=SessionLocal(); approval=db.get(Approval,approval_id)
    if not approval: db.close(); raise HTTPException(404,"Approval not found")
    payload=json.loads(approval.payload or "{}")
    role=user.get("role") if isinstance(user,dict) else user.role
    if role not in {"admin","manager"} and str(payload.get("user_id", "")) != _owner_id(user):
        db.close(); raise HTTPException(403,"Execution belongs to another user")
    thread_id=payload.get("thread_id"); status={"approval_id":approval_id,"approval_status":approval.status,"action":approval.action,"execution_results":None}
    db.close()
    if thread_id:
        owner=payload.get("user_id",_owner_id(user))
        state=get_workflow_state(thread_id,user_id=owner).get("state",{})
        status["execution_results"]=state.get("execution_results") or state.get("action_result",{}).get("execution")
        status["thread_id"]=thread_id.split(":")[-1]
    return status
@app.get("/api/agents/executions/{execution_id}",dependencies=[Depends(require_auth)])
def agent_execution_status(execution_id:int,user=Depends(current_user)):
    return execution_status(execution_id,user)
@app.post("/api/documents/upload",dependencies=[Depends(require_roles("admin","manager"))])
async def upload_document(file:UploadFile=File(...)):
    from pathlib import Path
    name=Path(file.filename or "").name
    if Path(name).suffix.lower() not in {".pdf",".txt"}: raise HTTPException(415,"Upload a PDF or TXT document")
    data=await file.read(10*1024*1024+1)
    if len(data)>10*1024*1024: raise HTTPException(413,"Document must be 10 MB or smaller")
    folder=Path(settings.upload_dir); folder.mkdir(parents=True,exist_ok=True); path=folder/name
    path.write_bytes(data)
    try: count=ingest(path)
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(400,f"Document ingestion failed: {type(exc).__name__}") from exc
    return {"filename":name,"chunks":count}
@app.get("/api/documents/search",dependencies=[Depends(require_auth)])
def document_search(q:str=Query(min_length=2,max_length=500)):
    return {"results":search(q)}
@app.post("/api/rag/ask",dependencies=[Depends(require_auth)])
def rag_ask(req:RAGAskRequest):
    try:return ask_question(req.question,domain=req.domain,top_k=req.top_k)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    except ProviderError as exc:raise HTTPException(503,str(exc)) from exc
    except Exception as exc:raise HTTPException(503,f"RAG retrieval failed ({type(exc).__name__})") from exc
@app.post("/api/rag/upload",dependencies=[Depends(require_roles("admin","manager"))])
async def rag_upload(file:UploadFile=File(...),category:str|None=Form(default=None)):
    from pathlib import Path
    import hashlib
    name=Path(file.filename or "").name
    if Path(name).suffix.lower() not in {".pdf",".txt"}:raise HTTPException(415,"Upload a PDF or TXT document")
    data=await file.read(MAX_DOCUMENT_BYTES+1)
    if len(data)>MAX_DOCUMENT_BYTES:raise HTTPException(413,"Document must be 10 MB or smaller")
    if not data:raise HTTPException(422,"Document is empty")
    digest=hashlib.sha256(data).hexdigest()
    if vector_store.has_document(digest):raise HTTPException(409,"This document has already been ingested")
    folder=Path(settings.upload_dir);folder.mkdir(parents=True,exist_ok=True)
    temp_path=folder/f".{digest[:12]}_{name}"
    try:
        temp_path.write_bytes(data)
        result=ingest_document(temp_path,category,document_name=name)
        return result
    except DuplicateDocumentError as exc:raise HTTPException(409,str(exc)) from exc
    except IngestionError as exc:raise HTTPException(422,str(exc)) from exc
    except Exception as exc:raise HTTPException(503,f"Document ingestion failed ({type(exc).__name__})") from exc
    finally:temp_path.unlink(missing_ok=True)
@app.get("/api/rag/documents",dependencies=[Depends(require_auth)])
def rag_documents():return {"documents":vector_store.list_documents()}
@app.get("/api/rag/health",dependencies=[Depends(require_auth)])
def rag_health():
    docs=vector_store.list_documents()
    return {"status":"ok","provider":get_active_provider(),"demo_mode":settings.demo_mode,"embedding_model":settings.embedding_model,"indexed_documents":len(docs),"vector_store":"faiss","persistent":True}
