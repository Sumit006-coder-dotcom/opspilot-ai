"""Persistent FAISS cosine-similarity collections with JSON metadata sidecars."""
from __future__ import annotations
import json, re, threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from config import settings
from rag.embeddings import HuggingFaceEmbeddings

class VectorStoreError(RuntimeError): pass
_LOCK=threading.RLock()

def _key(name:str)->str:
    value=re.sub(r"[^a-zA-Z0-9_-]+","_",name.strip().lower()).strip("_")
    return value or "general"

class VectorStore:
    def __init__(self,root:Path|str|None=None,embeddings=None):
        self.root=Path(root or settings.vector_dir); self.embeddings=embeddings or HuggingFaceEmbeddings()
        self._indices:dict[str,Any]={}; self._records:dict[str,list[dict]]={}

    def _paths(self,collection:str)->tuple[Path,Path]:
        key=_key(collection); return self.root/f"{key}.faiss",self.root/f"{key}.json"

    def load(self,collection:str="general"):
        import faiss
        idx_path,meta_path=self._paths(collection); key=_key(collection)
        with _LOCK:
            if key in self._indices:return self._indices[key]
            if not idx_path.exists() or not meta_path.exists():
                index=faiss.IndexFlatIP(384); records=[]
            else:
                try:
                    index=faiss.read_index(str(idx_path)); payload=json.loads(meta_path.read_text(encoding="utf-8"))
                    if isinstance(payload,dict):
                        saved_model=payload.get("embedding_model")
                        active_model=getattr(self.embeddings,"model_name",type(self.embeddings).__name__)
                        if saved_model and saved_model!=active_model:raise VectorStoreError(f"Collection {key} was embedded with {saved_model}; configured model is {active_model}")
                        records=payload.get("records",[])
                    else:records=payload
                except Exception as exc: raise VectorStoreError(f"Could not load FAISS collection {key}: {type(exc).__name__}") from exc
                if index.ntotal!=len(records): raise VectorStoreError(f"FAISS metadata mismatch in collection {key}")
            self._indices[key]=index; self._records[key]=records; return index

    def _save(self,collection:str)->None:
        import faiss
        key=_key(collection); idx_path,meta_path=self._paths(key); self.root.mkdir(parents=True,exist_ok=True)
        faiss.write_index(self._indices[key],str(idx_path.with_suffix(".faiss.tmp")))
        idx_path.with_suffix(".faiss.tmp").replace(idx_path)
        tmp=meta_path.with_suffix(".json.tmp")
        payload={"embedding_model":getattr(self.embeddings,"model_name",type(self.embeddings).__name__),"records":self._records[key]}
        tmp.write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8"); tmp.replace(meta_path)

    def create(self,collection:str="general"):
        return self.load(collection)

    def has_document(self,document_id:str)->bool:
        with _LOCK:
            if not self.root.exists():return False
            for meta in self.root.glob("*.json"):
                try:
                    payload=json.loads(meta.read_text(encoding="utf-8")); records=payload.get("records",[]) if isinstance(payload,dict) else payload
                    if any(r.get("metadata",{}).get("document_id")==document_id for r in records):return True
                except (OSError,json.JSONDecodeError):continue
        return False

    def add_chunks(self,chunks:list[dict],collection:str="general",*,replace_document_id:str|None=None)->int:
        if not chunks:return 0
        import numpy as np
        key=_key(collection); index=self.load(key)
        with _LOCK:
            if replace_document_id:
                keep=[r for r in self._records[key] if r.get("metadata",{}).get("document_id")!=replace_document_id]
                if len(keep)!=len(self._records[key]):
                    self._records[key]=keep
                    if keep:
                        vec=self.embeddings.embed_documents([r["text"] for r in keep]); index.reset(); index.add(np.asarray(vec,dtype="float32"))
                    else:index.reset()
            vectors=self.embeddings.embed_documents([item["text"] for item in chunks])
            if not vectors:return 0
            if index.d==0: raise VectorStoreError("FAISS embedding dimension is zero")
            if len(vectors[0])!=index.d:
                if index.ntotal: raise VectorStoreError(f"Embedding dimension changed in collection {key}")
                self._indices[key]=index=__import__("faiss").IndexFlatIP(len(vectors[0]))
            normalized=[]
            for item in chunks:
                meta=dict(item.get("metadata",{})); normalized.append({"text":item["text"],"metadata":meta})
            index.add(np.asarray(vectors,dtype="float32")); self._records[key].extend(normalized); self._save(key)
            return len(normalized)

    def search(self,query:str,k:int=4,metadata_filter:dict|None=None,threshold:float=0.0,collection:str="general")->list[dict]:
        if k<1:return []
        import numpy as np
        key=_key(collection); index=self.load(key)
        if index.ntotal==0:return []
        try: vector=self.embeddings.embed_query(query)
        except Exception as exc: raise VectorStoreError(f"Query embedding failed ({type(exc).__name__})") from exc
        if len(vector)!=index.d: raise VectorStoreError("Query and index embedding dimensions differ")
        # Search the full collection so metadata filtering does not discard relevant later neighbors.
        scores,ids=index.search(np.asarray([vector],dtype="float32"),index.ntotal)
        hits=[]
        for score,idx in zip(scores[0],ids[0]):
            if idx<0 or float(score)<threshold:continue
            record=self._records[key][int(idx)]; meta=record["metadata"]
            if metadata_filter and any(meta.get(k)!=v for k,v in metadata_filter.items()):continue
            hits.append({"text":record["text"],"metadata":dict(meta),"score":float(score)})
            if len(hits)>=k:break
        return hits

    def list_documents(self)->list[dict]:
        if not self.root.exists():return []
        docs={}
        for path in self.root.glob("*.json"):
            try:
                payload=json.loads(path.read_text(encoding="utf-8")); records=payload.get("records",[]) if isinstance(payload,dict) else payload
            except (OSError,json.JSONDecodeError):continue
            for r in records:
                m=r.get("metadata",{}); did=m.get("document_id")
                if not did:continue
                item=docs.setdefault(did,{k:m.get(k) for k in ("document_id","document_name","category","upload_timestamp","sha256")})
                item["chunk_count"]=item.get("chunk_count",0)+1
        return list(docs.values())

    def delete_document(self,document_id:str)->bool:
        removed=False
        for path in self.root.glob("*.json") if self.root.exists() else []:
            key=path.stem
            index=self.load(key); records=self._records[key]
            keep=[r for r in records if r.get("metadata",{}).get("document_id")!=document_id]
            if len(keep)==len(records):continue
            import numpy as np, faiss
            self._records[key]=keep; new=faiss.IndexFlatIP(index.d)
            if keep:new.add(np.asarray(self.embeddings.embed_documents([r["text"] for r in keep]),dtype="float32"))
            self._indices[key]=new; self._save(key); removed=True
        return removed

    def build(self,documents:list[dict])->None:
        """Compatibility method for Phase 1 callers; build a general collection."""
        chunks=[]
        for i,d in enumerate(documents):
            chunks.append({"text":d["text"],"metadata":dict(d.get("metadata",{"document_name":d.get("document","unknown"),"chunk_id":i+1}))})
        self.add_chunks(chunks,"general")

vector_store=VectorStore()
