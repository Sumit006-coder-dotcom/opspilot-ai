from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from database.connection import Base

class User(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(primary_key=True)
    username: Mapped[str]=mapped_column(String(80), unique=True)
    password_hash: Mapped[str]=mapped_column(String(255))
    role: Mapped[str]=mapped_column(String(30), default="analyst")
class Product(Base):
    __tablename__="products"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(160)); category: Mapped[str]=mapped_column(String(80))
    price: Mapped[float]=mapped_column(Float); return_rate: Mapped[float]=mapped_column(Float, default=0)
class Seller(Base):
    __tablename__="sellers"
    id: Mapped[int]=mapped_column(primary_key=True); name: Mapped[str]=mapped_column(String(120)); rating: Mapped[float]=mapped_column(Float)
class Order(Base):
    __tablename__="orders"
    id: Mapped[int]=mapped_column(primary_key=True); product_id: Mapped[int]=mapped_column(ForeignKey("products.id")); seller_id: Mapped[int]=mapped_column(ForeignKey("sellers.id")); status: Mapped[str]=mapped_column(String(40)); returned: Mapped[bool]=mapped_column(Boolean, default=False); created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
class Complaint(Base):
    __tablename__="complaints"
    id: Mapped[int]=mapped_column(primary_key=True); order_id: Mapped[int]=mapped_column(ForeignKey("orders.id")); category: Mapped[str]=mapped_column(String(80)); text: Mapped[str]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
class Inventory(Base):
    __tablename__="inventory"
    id: Mapped[int]=mapped_column(primary_key=True); product_id: Mapped[int]=mapped_column(ForeignKey("products.id")); quantity: Mapped[int]=mapped_column(Integer); reorder_point: Mapped[int]=mapped_column(Integer)
class Ticket(Base):
    __tablename__="tickets"
    id: Mapped[int]=mapped_column(primary_key=True); title: Mapped[str]=mapped_column(String(200)); category: Mapped[str]=mapped_column(String(80)); severity: Mapped[str]=mapped_column(String(20)); status: Mapped[str]=mapped_column(String(30)); description: Mapped[str]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
class Incident(Base):
    __tablename__="incidents"
    id: Mapped[int]=mapped_column(primary_key=True); title: Mapped[str]=mapped_column(String(200)); severity: Mapped[str]=mapped_column(String(20)); status: Mapped[str]=mapped_column(String(30)); service: Mapped[str]=mapped_column(String(100)); description: Mapped[str]=mapped_column(Text)
class Approval(Base):
    __tablename__="approvals"
    id: Mapped[int]=mapped_column(primary_key=True); request: Mapped[str]=mapped_column(Text); action: Mapped[str]=mapped_column(String(100)); payload: Mapped[str]=mapped_column(Text); status: Mapped[str]=mapped_column(String(20), default="pending"); created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow); resolved_at: Mapped[datetime|None]=mapped_column(DateTime)
class AgentLog(Base):
    __tablename__="agent_logs"
    id: Mapped[int]=mapped_column(primary_key=True); agent: Mapped[str]=mapped_column(String(80)); tool: Mapped[str]=mapped_column(String(120), default=""); status: Mapped[str]=mapped_column(String(30)); duration_ms: Mapped[int]=mapped_column(Integer, default=0); detail: Mapped[str]=mapped_column(Text, default=""); created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class AuditEvent(Base):
    __tablename__="audit_events"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int|None]=mapped_column(Integer, nullable=True)
    request_id: Mapped[str]=mapped_column(String(80), default="")
    workflow_id: Mapped[str]=mapped_column(String(160), default="")
    agent_name: Mapped[str]=mapped_column(String(80), default="api")
    tool_name: Mapped[str]=mapped_column(String(120), default="")
    proposed_action: Mapped[str]=mapped_column(Text, default="")
    approval_decision: Mapped[str]=mapped_column(String(30), default="")
    execution_result: Mapped[str]=mapped_column(Text, default="")
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
