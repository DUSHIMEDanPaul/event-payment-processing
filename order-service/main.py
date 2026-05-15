"""
Order Service — Entry Point

Flow:
  POST /orders
    → save order to PostgreSQL (status=pending)
    → publish  order.created  event to RabbitMQ
    → return   OrderResponse
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas
import rabbitmq
from config import settings
from database import engine, get_db

# ── Create tables on startup (use Alembic migrations in production) ──────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Order Service",
    description="Accepts new orders and publishes order.created events to RabbitMQ.",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "order-service"}


# ── Orders ───────────────────────────────────────────────────────────────────

@app.post(
    "/orders",
    response_model=schemas.OrderResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Orders"],
)
def create_order(payload: schemas.OrderCreate, db: Session = Depends(get_db)):
    """
    1. Persist the order with status='pending'.
    2. Publish an `order.created` event to RabbitMQ.
    3. Return the created order.
    """
    # ── Persist ──────────────────────────────────────────────────────────────
    order = models.Order(**payload.model_dump())
    db.add(order)
    db.commit()
    db.refresh(order)

    # ── Publish event ─────────────────────────────────────────────────────────
    event_payload = {
        "event": "order.created",
        "order_id": str(order.id),
        "customer_id": order.customer_id,
        "product_id": order.product_id,
        "quantity": order.quantity,
        "total_amount": order.total_amount,
    }
    try:
        rabbitmq.publish_event(routing_key="order.created", payload=event_payload)
    except Exception as exc:
        # Don't fail the request if the broker is temporarily unavailable;
        # in production use an outbox pattern or retry queue.
        print(f"[WARNING] Could not publish event: {exc}")

    return order


@app.get("/orders/{order_id}", response_model=schemas.OrderResponse, tags=["Orders"])
def get_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
