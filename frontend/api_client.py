"""Reusable, session-backed client for the Operlynt FastAPI service."""
from __future__ import annotations
from typing import Any
from urllib.parse import urljoin
import requests

class APIError(RuntimeError):
    def __init__(self,status_code:int,message:str,path:str):
        self.status_code=status_code;self.path=path
        super().__init__(f"API request failed ({status_code}) for {path}: {message}")

class OperlyntAPI:
    def __init__(self,base_url:str,token:str|None=None,timeout:float=20.0,session:requests.Session|None=None):
        self.base_url=base_url.rstrip("/")+"/";self.token=token;self.timeout=timeout
        self.session=session or requests.Session()

    def _request(self,method:str,path:str,**kwargs)->Any:
        headers=dict(kwargs.pop("headers",{}))
        if self.token:headers["Authorization"]=f"Bearer {self.token}"
        try:response=self.session.request(method,urljoin(self.base_url,path.lstrip("/")),headers=headers,timeout=kwargs.pop("timeout",self.timeout),**kwargs)
        except requests.Timeout as exc:raise APIError(0,"The backend request timed out",path) from exc
        except requests.RequestException as exc:raise APIError(0,"The backend could not be reached",path) from exc
        if not response.ok:
            try:message=response.json().get("detail","Request rejected")
            except (ValueError,AttributeError):message="Request rejected"
            if response.status_code==401:message="Session expired or credentials were rejected. Sign in again."
            raise APIError(response.status_code,str(message)[:300],path)
        if response.status_code==204:return None
        try:return response.json()
        except ValueError as exc:raise APIError(response.status_code,"Backend returned an invalid response",path) from exc

    def get(self,path:str,params:dict|None=None,timeout:float|None=None):
        return self._request("GET",path,params=params,timeout=timeout or self.timeout)
    def post(self,path:str,payload:dict|None=None,timeout:float|None=None):
        return self._request("POST",path,json=payload or {},timeout=timeout or self.timeout)
    def upload(self,path:str,uploaded_file,extra:dict|None=None,timeout:float=300):
        files={"file":(uploaded_file.name,uploaded_file.getvalue(),uploaded_file.type or "application/octet-stream")}
        return self._request("POST",path,data=extra or {},files=files,timeout=timeout)

    @classmethod
    def login(cls,base_url:str,username:str,password:str,timeout:float=20):
        return cls(base_url,timeout=timeout).post("/api/auth/login",{"username":username,"password":password})

# Compatibility alias for existing scripts importing the previous class name.
OpsPilotAPI = OperlyntAPI

