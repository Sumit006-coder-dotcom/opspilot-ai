"""Historical evidence researcher over stored complaints, tickets, and incidents."""
from sqlalchemy import or_
from database.connection import SessionLocal
from database.models import Complaint, Incident, Ticket

def research(query: str, domain: str) -> list[dict]:
    db = SessionLocal()
    try:
        model = Complaint if domain == "ecommerce" else Ticket
        filters = []
        for word in [w.strip(".,?!:;") for w in query.split() if len(w.strip(".,?!:;") ) >= 4][:5]:
            filters.extend([model.category.ilike(f"%{word}%"), (model.text if domain == "ecommerce" else model.description).ilike(f"%{word}%")])
        query_rows = db.query(model)
        if filters:
            matching = query_rows.filter(or_(*filters)).order_by(model.id.desc()).limit(12).all()
        else: matching = []
        rows = matching or query_rows.order_by(model.id.desc()).limit(12).all()
        records = []
        for r in rows:
            if domain == "ecommerce": records.append({"record_type": "complaint", "id": r.id, "category": r.category, "text": r.text})
            else: records.append({"record_type": "ticket", "id": r.id, "category": r.category, "severity": r.severity, "status": r.status, "title": r.title, "description": r.description})
        if domain == "it":
            incidents = db.query(Incident).order_by(Incident.id.desc()).limit(8).all()
            records.extend({"record_type": "incident", "id": r.id, "service": r.service, "severity": r.severity, "status": r.status, "title": r.title, "description": r.description} for r in incidents)
        return records
    finally: db.close()
