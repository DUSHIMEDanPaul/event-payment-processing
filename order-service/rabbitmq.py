"""
RabbitMQ publisher helper.

Exchange layout (Topic exchange):
  Exchange : orders_exchange  (type=topic)
  Routing keys published here:
    order.created   ← published by Order Service
"""

import json
import pika

from config import settings

EXCHANGE_NAME = "orders_exchange"


def get_channel():
    """Open a blocking connection and return a channel."""
    params = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(params)
    return connection, connection.channel()


def publish_event(routing_key: str, payload: dict) -> None:
    """
    Publish a JSON-encoded event to the orders topic exchange.

    Args:
        routing_key: e.g. "order.created"
        payload:     dict that will be serialised to JSON
    """
    connection, channel = get_channel()

    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="topic",
        durable=True,
    )

    channel.basic_publish(
        exchange=EXCHANGE_NAME,
        routing_key=routing_key,
        body=json.dumps(payload),
        properties=pika.BasicProperties(
            delivery_mode=2,          # Persistent message
            content_type="application/json",
        ),
    )

    connection.close()
