import io
import pytest
import requests
from frontend.api_client import APIError, OperlyntAPI, OpsPilotAPI

def test_legacy_api_client_import_remains_compatible():
    assert OpsPilotAPI is OperlyntAPI

class FakeResponse:
    def __init__(self,status=200,payload=None):self.status_code=status;self.ok=status<400;self._payload=payload or {};self.headers={}
    def json(self):return self._payload

class FakeAPI:
    all_calls=[]
    def __init__(self,*args,**kwargs):pass
    def get(self,path,params=None,timeout=None):
        self.all_calls.append(("GET",path))
        if path=="/api/auth/me":return {"id":1,"username":"demo-user","role":"manager"}
        if path=="/api/analytics/ecommerce":return {"orders":5,"returns":1,"return_rate":20,"complaints":2,"low_inventory":1,"top_complaints":[{"category":"quality","count":2}],"complaint_trends":[{"month":"2026-01","complaints":2}],"product_return_distribution":[{"product":"Widget","return_rate":20}],"seller_performance":[],"inventory_risks":[]}
        if path=="/api/analytics/it":return {"open_tickets":2,"critical_incidents":1,"critical_open_tickets":1,"ticket_severity":[{"severity":"critical","count":1}],"ticket_trends":[{"month":"2026-01","created":2}],"categories":[{"category":"network","count":2}]}
        if path=="/api/analytics/products":return {"products":[{"id":1,"name":"Widget","return_rate":20,"orders":5,"returns":1}]}
        if path=="/api/analytics/complaints":return {"complaints":[{"id":1,"category":"quality","text":"test complaint"}]}
        if path=="/api/approvals":return [{"id":123,"request":"Test approval","action":"create_it_ticket","status":"pending","payload":{"title":"Test"}}]
        if path=="/api/tickets":return []
        if path=="/api/rag/documents":return {"documents":[]}
        if path=="/api/agents/activity":return []
        if path.startswith("/api/tickets/"):return {"id":1}
        if path=="/health":return {"status":"ok"}
        return {}
    def post(self,path,payload=None,timeout=None):
        self.all_calls.append(("POST",path,payload))
        return {"answer":"A live backend response","agents":["orchestrator"],"agent_results":{},"thread_id":"thread-123"}
    def upload(self,path,uploaded_file,extra=None,timeout=300):return {"document_name":uploaded_file.name,"chunks":1}

def test_client_auth_headers_errors_and_timeout(monkeypatch):
    seen={}
    def request(self,method,url,**kwargs):seen.update(method=method,url=url,**kwargs);return FakeResponse(payload={"ok":True})
    monkeypatch.setattr(requests.Session,"request",request)
    api=OperlyntAPI("http://localhost:8000","jwt-token")
    assert api.get("/health")=={"ok":True}
    assert seen["headers"]["Authorization"]=="Bearer jwt-token" and seen["timeout"]==20.0
    def denied(self,method,url,**kwargs):return FakeResponse(403,{"detail":"Insufficient role"})
    monkeypatch.setattr(requests.Session,"request",denied)
    with pytest.raises(APIError) as exc:api.get("/api/approvals")
    assert exc.value.status_code==403

def test_client_upload_uses_multipart_and_reports_result(monkeypatch):
    seen={}
    def request(self,method,url,**kwargs):seen.update(method=method,url=url,**kwargs);return FakeResponse(payload={"chunks":2})
    monkeypatch.setattr(requests.Session,"request",request)
    file=io.BytesIO(b"sample PDF text");file.name="policy.txt";file.type="text/plain";file.getvalue=lambda:b"sample PDF text"
    result=OperlyntAPI("http://localhost:8000","jwt").upload("/api/rag/upload",file,{"category":"general"})
    assert result=={"chunks":2} and seen["files"]["file"][0]=="policy.txt"

def test_streamlit_pages_render_without_exceptions(monkeypatch):
    import frontend.api_client as api_module
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(api_module,"OperlyntAPI",FakeAPI)
    for page in ["Overview Dashboard","E-commerce Intelligence","IT Operations Intelligence","AI Agent Chat","RAG Document Intelligence","Agent Execution Monitoring","Human Approval Center","Ticket Management","Settings"]:
        at=AppTest.from_file("frontend/app.py")
        at.session_state["token"]="test-jwt";at.session_state["user"]={"id":1,"username":"demo-user","role":"manager"};at.session_state["api_base"]="http://test"
        at.run(timeout=15)
        at.radio[0].set_value(page).run(timeout=15)
        assert not at.exception, f"Page {page} raised: {at.exception}"

def test_chat_and_approval_buttons_call_backend(monkeypatch):
    import frontend.api_client as api_module
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(api_module,"OperlyntAPI",FakeAPI)
    FakeAPI.all_calls.clear()
    at=AppTest.from_file("frontend/app.py");at.session_state["token"]="jwt";at.session_state["user"]={"id":1,"username":"manager","role":"manager"};at.session_state["api_base"]="http://test"
    at.run(timeout=15);at.radio[0].set_value("Human Approval Center").run(timeout=15)
    next(button for button in at.button if button.label=="Approve").click().run(timeout=15)
    assert any(call[0]=="POST" and call[1]=="/api/approvals/123/approve" for call in FakeAPI.all_calls)
    at.radio[0].set_value("AI Agent Chat").run(timeout=15)
    if at.chat_input:
        at.chat_input[0].set_value("Summarize the current operational risk").run(timeout=15)
        assert any(call[0]=="POST" and call[1]=="/api/chat" for call in FakeAPI.all_calls)

