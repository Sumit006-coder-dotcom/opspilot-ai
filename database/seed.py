"""Create deterministic, internally linked synthetic demonstration data."""
import random
from database.connection import Base, engine, SessionLocal
from database.models import Product, Seller, Order, Complaint, Inventory, Ticket, Incident

def seed(reset: bool=False) -> None:
    if reset: Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db=SessionLocal()
    try:
        if db.query(Product).count(): return
        rng=random.Random(731)
        products=[Product(name=f"{rng.choice(['Smart','Pro','Eco','Classic'])} {rng.choice(['Bottle','Headphones','Lamp','Backpack','Keyboard','Camera','Speaker','Watch','Chair','Router'])} {i+1}",category=rng.choice(["Electronics","Home","Accessories"]),price=round(rng.uniform(15,350),2)) for i in range(100)]
        sellers=[Seller(name=f"Seller {i+1:02d}",rating=round(rng.uniform(3.2,5),1)) for i in range(30)]
        db.add_all(products+sellers); db.flush()
        orders=[]
        for _ in range(1000):
            returned=rng.random()<0.12
            orders.append(Order(product_id=rng.choice(products).id,seller_id=rng.choice(sellers).id,status="returned" if returned else rng.choice(["delivered","shipped","processing"]),returned=returned))
        db.add_all(orders); db.flush()
        for p in products:
            product_orders=[o for o in orders if o.product_id==p.id]
            p.return_rate=round(sum(o.returned for o in product_orders)/max(1,len(product_orders))*100,2)
        complaints=[Complaint(order_id=o.id,category=rng.choice(["quality","delivery","refund","damaged"]),text=rng.choice(["Item arrived damaged","Delivery was late","Quality below expectations","Refund has not arrived"])) for o in rng.sample(orders,500)]
        db.add_all(complaints)
        db.add_all([Inventory(product_id=p.id,quantity=rng.randint(0,180),reorder_point=25) for p in products])
        cats=["network","access","endpoint","database","email","deployment"]
        db.add_all([Ticket(title=f"{rng.choice(cats).title()} issue #{i+1}",category=(c:=rng.choice(cats)),severity=rng.choice(["low","medium","high","critical"]),status=rng.choice(["open","open","in_progress","resolved"]),description=f"Synthetic demonstration ticket for {c} service") for i in range(300)])
        db.add_all([Incident(title=f"Service incident {i+1}",severity=rng.choice(["medium","high","critical"]),status=rng.choice(["open","investigating","resolved"]),service=rng.choice(["network","identity","payments","email"]),description="Synthetic demonstration incident") for i in range(50)])
        db.commit()
    finally: db.close()

if __name__=="__main__": seed()
