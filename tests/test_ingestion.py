from pathlib import Path
import pytest
from rag.ingestion import ingest_document,DuplicateDocumentError,IngestionError
from rag.vector_store import VectorStore
from tests.fakes import FakeEmbeddings
import rag.ingestion as ingestion

@pytest.fixture
def isolated_store(tmp_path,monkeypatch):
    store=VectorStore(tmp_path/"faiss",FakeEmbeddings()); monkeypatch.setattr(ingestion,"vector_store",store); return store

def test_txt_ingestion_and_duplicate(tmp_path,isolated_store):
    path=tmp_path/"Ecommerce_Return_Policy.txt"; path.write_text("Defective products can be returned within thirty days. Refunds are issued after inspection.",encoding="utf-8")
    result=ingest_document(path)
    assert result["chunks"]==1 and result["category"]=="ecommerce_policy"
    with pytest.raises(DuplicateDocumentError):ingest_document(path)

def test_pdf_ingestion_page_metadata(tmp_path,isolated_store):
    path=tmp_path/"IT_Incident_Management_Policy.pdf"
    content=b"BT /F1 12 Tf 72 720 Td (Critical incidents require immediate escalation to the incident commander.) Tj ET"
    objects=[b"<< /Type /Catalog /Pages 2 0 R >>",b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",b"<< /Length "+str(len(content)).encode()+b" >>\nstream\n"+content+b"\nendstream"]
    data=bytearray(b"%PDF-1.4\n"); offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(data)); data.extend(f"{i} 0 obj\n".encode()+obj+b"\nendobj\n")
    xref=len(data); data.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()); path.write_bytes(data)
    result=ingest_document(path)
    hits=isolated_store.search("critical incidents escalation",collection="it_documentation",metadata_filter={"document_id":result["document_id"]})
    assert result["chunks"]==1 and hits[0]["metadata"]["page_number"]==1

def test_empty_and_unsupported_files(tmp_path,isolated_store):
    empty=tmp_path/"empty.txt"; empty.write_text(" ")
    with pytest.raises(IngestionError,match="no extractable text"):ingest_document(empty)
    bad=tmp_path/"bad.docx"; bad.write_text("not supported")
    with pytest.raises(IngestionError,match="Only PDF and TXT"):ingest_document(bad)
