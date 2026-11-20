"""Read-only business analytics endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case
from api.dependencies import require_auth
from database.connection import SessionLocal
from database.models import Order, Complaint, Inventory, Ticket, Incident, Product, Seller

router=APIRouter(prefix="/api/analytics",tags=["analytics"],dependencies=[Depends(require_auth)])

@router.get("/ecommerce")
def ecommerce_metrics():
    db=SessionLocal()
    try:
        total=db.query(Order).count(); returns=db.query(Order).filter_by(returned=True).count()
        complaints=db.query(Complaint).count(); low=db.query(Inventory).filter(Inventory.quantity<Inventory.reorder_point).count()
        complaint_rows=db.query(Complaint).all(); trends={}
        for row in complaint_rows:
            key=row.created_at.strftime("%Y-%m") if row.created_at else "unknown"
            trends[key]=trends.get(key,0)+1
        product_rows=db.query(Product.id,Product.name,func.count(Order.id),func.coalesce(func.sum(case((Order.returned.is_(True),1),else_=0)),0)).outerjoin(Order,Order.product_id==Product.id).group_by(Product.id).all()
        product_returns=[{"product_id":pid,"product":name,"orders":count,"returns":returned,"return_rate":round(returned/max(1,count)*100,2)} for pid,name,count,returned in product_rows if count]
        seller_rows=db.query(Seller.id,Seller.name,Seller.rating,func.count(Order.id),func.coalesce(func.sum(case((Order.returned.is_(True),1),else_=0)),0)).outerjoin(Order,Order.seller_id==Seller.id).group_by(Seller.id).all()
        sellers=[{"seller_id":sid,"seller":name,"rating":rating,"orders":count,"returns":returned,"return_rate":round(returned/max(1,count)*100,2)} for sid,name,rating,count,returned in seller_rows]
        inventory_rows=db.query(Inventory,Product).join(Product).filter(Inventory.quantity<Inventory.reorder_point).order_by(Inventory.quantity).limit(100).all()
        return {"orders":total,"returns":returns,"return_rate":round(returns/max(1,total)*100,2),"complaints":complaints,
            "low_inventory":low,"top_complaints":[{"category":c,"count":n} for c,n in db.query(Complaint.category,func.count(Complaint.id)).group_by(Complaint.category).all()],
            "complaint_trends":[{"month":k,"complaints":v} for k,v in sorted(trends.items())],
            "product_return_distribution":sorted(product_returns,key=lambda x:x["return_rate"],reverse=True),
            "seller_performance":sellers,"inventory_risks":[{"product_id":p.id,"product":p.name,"quantity":i.quantity,"reorder_point":i.reorder_point} for i,p in inventory_rows]}
    finally: db.close()

@router.get("/it")
def it_metrics():
    db=SessionLocal()
    try:
        tickets=db.query(Ticket).all(); by_month={}
        for ticket in tickets:
            month=ticket.created_at.strftime("%Y-%m") if ticket.created_at else "unknown"
            bucket=by_month.setdefault(month,{"month":month,"created":0,"currently_resolved":0})
            bucket["created"]+=1
            if ticket.status=="resolved":bucket["currently_resolved"]+=1
        return {"open_tickets":db.query(Ticket).filter(Ticket.status!="resolved").count(),
            "critical_incidents":db.query(Incident).filter(Incident.severity=="critical",Incident.status!="resolved").count(),
            "categories":[{"category":c,"count":n} for c,n in db.query(Ticket.category,func.count(Ticket.id)).group_by(Ticket.category).all()],
            "ticket_severity":[{"severity":s,"count":n} for s,n in db.query(Ticket.severity,func.count(Ticket.id)).group_by(Ticket.severity).all()],
            "ticket_trends":[by_month[k] for k in sorted(by_month)],
            "critical_open_tickets":db.query(Ticket).filter(Ticket.severity=="critical",Ticket.status!="resolved").count()}
    finally: db.close()

@router.get("/products")
def search_products(q:str=Query(default="",max_length=100),limit:int=Query(default=50,ge=1,le=200)):
    db=SessionLocal()
    try:
        query=db.query(Product)
        if q.strip(): query=query.filter(Product.name.ilike(f"%{q.strip()[:100]}%"))
        rows=query.outerjoin(Order,Order.product_id==Product.id).group_by(Product.id).order_by(Product.name).limit(limit).with_entities(Product.id,Product.name,Product.category,Product.price,func.count(Order.id),func.coalesce(func.sum(case((Order.returned.is_(True),1),else_=0)),0)).all()
        output=[{"id":pid,"name":name,"category":category,"price":price,"orders":orders,"returns":returns,"return_rate":round(returns/max(1,orders)*100,2)} for pid,name,category,price,orders,returns in rows]
        return {"products":output}
    finally:db.close()

@router.get("/complaints")
def search_complaints(q:str="",limit:int=Query(default=50,ge=1,le=200)):
    db=SessionLocal()
    try:
        query=db.query(Complaint)
        if q.strip():query=query.filter(Complaint.text.ilike(f"%{q.strip()[:100]}%"))
        return {"complaints":[{"id":c.id,"category":c.category,"text":c.text,"order_id":c.order_id,"created_at":c.created_at.isoformat() if c.created_at else None} for c in query.order_by(Complaint.id.desc()).limit(limit).all()]}
    finally:db.close()
