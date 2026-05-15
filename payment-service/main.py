"""
Payment Service — Consumer + Publisher

Consumes : order.created       (from orders_exchange)
Publishes: payment.processed   (to   payments_exchange)
           payment.failed      (to   payments_exchange)

Redis is used for idempotency — if an order_id was already
processed we ACK the message and skip re-processing.
"""

import json
import time
import pika

from config import settings
from redis_client import is_already_processed

ORDERS_EXCHANGE = "orders_exchange"
PAYMENTS_EXCHANGE = "payments_exchange"
QUEUE_NAME = "payment_queue"
ORDER_ROUTING_KEY = "order.created"


# ── Publisher helper ─────────────────────────────────────────────────────────

def publish_payment_event(channel: pika.channel.Channel, routing_key: str, payload: dict) -> None:
    channel.exchange_declare(
        exchange=PAYMENTS_EXCHANGE,
        exchange_type="topic",
        durable=True,
    )
    channel.basic_publish(
        exchange=PAYMENTS_EXCHANGE,
        routing_key=routing_key,
        body=json.dumps(payload),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
        ),
    )


# ── Message handler ──────────────────────────────────────────────────────────

def handle_order_created(channel, method, properties, body):
    """
    Called for every order.created message.

    Steps:
      1. Decode message.
      2. Idempotency check via Redis.
      3. Simulate payment gateway call.
      4. Publish payment.processed or payment.failed.
      5. ACK the message.
    """
    event = json.loads(body)
    order_id = event["order_id"]

    print(f"[Payment] Received order.created for order_id={order_id}")

    # ── Idempotency guard ────────────────────────────────────────────────────
    if is_already_processed(order_id):
        print(f"[Payment] Duplicate — skipping order_id={order_id}")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    # ── Simulate payment processing ──────────────────────────────────────────
    # Replace with real payment gateway integration (Stripe, Paystack, etc.)
    payment_success = True   # stub: always succeeds

    if payment_success:
        routing_key = "payment.processed"
        result_payload = {
            "event": "payment.processed",
            "order_id": order_id,
            "customer_id": event["customer_id"],
            "amount": event["total_amount"],
            "status": "success",
        }
        print(f"[Payment] Payment successful for order_id={order_id}")
    else:
        routing_key = "payment.failed"
        result_payload = {
            "event": "payment.failed",
            "order_id": order_id,
            "customer_id": event["customer_id"],
            "reason": "Insufficient funds",
        }
        print(f"[Payment] Payment failed for order_id={order_id}")

    publish_payment_event(channel, routing_key, result_payload)

    # ACK only after successfully publishing downstream event
    channel.basic_ack(delivery_tag=method.delivery_tag)


# ── Consumer setup ───────────────────────────────────────────────────────────

def start_consuming():
    while True:
        try:
            params = pika.URLParameters(settings.rabbitmq_url)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()

            # Declare source exchange + queue
            channel.exchange_declare(
                exchange=ORDERS_EXCHANGE,
                exchange_type="topic",
                durable=True,
            )
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.queue_bind(
                queue=QUEUE_NAME,
                exchange=ORDERS_EXCHANGE,
                routing_key=ORDER_ROUTING_KEY,
            )

            # One message at a time — fair dispatch
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=handle_order_created)

            print("[Payment] Waiting for order.created events …")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError:
            print("[Payment] RabbitMQ not ready — retrying in 5 s …")
            time.sleep(5)


if __name__ == "__main__":
    start_consuming()
