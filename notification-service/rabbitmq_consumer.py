import json
import pika
import asyncio
from config import settings
from websocket_manager import manager

def start_rabbitmq_consumer(loop):
    """
    Consumes events from both orders_exchange and payments_exchange.
    Uses an event loop to call the broadcast method on the websocket manager.
    """
    def callback(ch, method, properties, body):
        message = body.decode()
        print(f"[Notification] Received event: {message}")
        # Schedule the broadcast on the main event loop
        asyncio.run_coroutine_threadsafe(manager.broadcast(message), loop)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    params = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    # Declare exchanges
    channel.exchange_declare(exchange=settings.orders_exchange, exchange_type="topic", durable=True)
    channel.exchange_declare(exchange=settings.payments_exchange, exchange_type="topic", durable=True)

    # Declare queue
    queue_name = "notification_queue"
    channel.queue_declare(queue=queue_name, durable=True)

    # Bind to all relevant routing keys
    channel.queue_bind(queue=queue_name, exchange=settings.orders_exchange, routing_key="order.*")
    channel.queue_bind(queue=queue_name, exchange=settings.payments_exchange, routing_key="payment.*")

    channel.basic_consume(queue=queue_name, on_message_callback=callback)

    print("[Notification] Waiting for events to notify clients …")
    channel.start_consuming()
