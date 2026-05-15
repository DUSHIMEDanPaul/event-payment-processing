"""
Inventory Service — Consumer

Consumes : payment.processed   (from payments_exchange)

On each event:
  1. Look up the product in the inventory table.
  2. Deduct the ordered quantity.
  3. Log the result.

In production you would also publish an inventory.updated event
for downstream services (e.g., shipping, analytics).
"""

import json
import time
import pika

from config import settings
from database import engine, SessionLocal
from models import Base, InventoryItem

PAYMENTS_EXCHANGE = "payments_exchange"
QUEUE_NAME = "inventory_queue"
ROUTING_KEY = "payment.processed"


# ── Message handler ──────────────────────────────────────────────────────────

def handle_payment_processed(channel, method, properties, body):
    event = json.loads(body)
    order_id = event["order_id"]
    product_id = event.get("product_id", "unknown")
    quantity = event.get("quantity", 1)

    print(f"[Inventory] payment.processed received — order={order_id}, product={product_id}, qty={quantity}")

    db = SessionLocal()
    try:
        item = db.query(InventoryItem).filter(InventoryItem.product_id == product_id).first()

        if item:
            if item.quantity_available >= quantity:
                item.quantity_available -= quantity
                db.commit()
                print(f"[Inventory] Stock updated — product={product_id}, remaining={item.quantity_available}")
            else:
                # In production: publish inventory.insufficient event
                print(f"[Inventory] Insufficient stock for product={product_id}")
        else:
            # Stub: create a placeholder record so the flow completes
            print(f"[Inventory] Product {product_id} not in inventory — skipping deduction")
    finally:
        db.close()

    channel.basic_ack(delivery_tag=method.delivery_tag)


# ── Consumer setup ───────────────────────────────────────────────────────────

def start_consuming():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    while True:
        try:
            params = pika.URLParameters(settings.rabbitmq_url)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()

            channel.exchange_declare(
                exchange=PAYMENTS_EXCHANGE,
                exchange_type="topic",
                durable=True,
            )
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.queue_bind(
                queue=QUEUE_NAME,
                exchange=PAYMENTS_EXCHANGE,
                routing_key=ROUTING_KEY,
            )

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=handle_payment_processed)

            print("[Inventory] Waiting for payment.processed events …")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError:
            print("[Inventory] RabbitMQ not ready — retrying in 5 s …")
            time.sleep(5)


if __name__ == "__main__":
    start_consuming()
