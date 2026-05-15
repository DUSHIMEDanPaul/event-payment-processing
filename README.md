# Event-Driven Order Processing System

A distributed backend system engineered with **FastAPI**, **RabbitMQ**, **PostgreSQL**, **Redis**, **SQLAlchemy**, and **WebSockets**.

## Architecture Overview

This project demonstrates a high-level microservices architecture for processing orders asynchronously:

1.  **Order Service**: 
    - Tech: FastAPI, SQLAlchemy, PostgreSQL, RabbitMQ.
    - Role: Accepts new orders via HTTP, persists them to Postgres, and publishes an `order.created` event.
2.  **Payment Service**:
    - Tech: Python (pika), Redis, RabbitMQ.
    - Role: Consumes `order.created`, performs idempotency checks via Redis, simulates payment, and publishes `payment.processed` or `payment.failed`.
3.  **Inventory Service**:
    - Tech: Python (pika), SQLAlchemy, PostgreSQL, RabbitMQ.
    - Role: Consumes `payment.processed` and deducts stock from the inventory table in Postgres.
4.  **Notification Service**:
    - Tech: FastAPI, WebSockets, RabbitMQ.
    - Role: Consumes all events (`order.*`, `payment.*`) and broadcasts real-time updates to connected clients via WebSockets.
5.  **Infrastructure**:
    - **RabbitMQ**: The central message broker (Topic Exchange).
    - **PostgreSQL**: Primary persistence for orders and inventory.
    - **Redis**: Fast caching for idempotency and future Pub/Sub scaling.

## Project Structure

```text
├── order-service/         # FastAPI, DB migrations, RabbitMQ publishing
├── payment-service/       # Event consumer, Redis idempotency
├── inventory-service/     # Event consumer, stock management
├── notification-service/  # WebSocket server, real-time broadcasts
├── docker-compose.yml     # Infrastructure and service orchestration
└── .env.example           # Environment variable template
```

## How to Run

1.  **Clone the repository** (if applicable).
2.  **Copy the environment file**:
    ```bash
    cp .env.example .env
    ```
3.  **Start the system**:
    ```bash
    docker-compose up --build
    ```
4.  **Access the services**:
    - Order Service: `http://localhost:8001/docs`
    - RabbitMQ Management: `http://localhost:15672` (guest/guest)
    - Notification Service (WebSockets): `ws://localhost:8004/ws/test-client`

## Event Flow

1. Client POSTs to `/orders` (Order Service).
2. Order is saved (Postgres) and `order.created` is published (RabbitMQ).
3. **Notification Service** receives `order.created` → broadcasts to WebSockets.
4. **Payment Service** receives `order.created` → checks Redis → simulates payment → publishes `payment.processed`.
5. **Notification Service** receives `payment.processed` → broadcasts to WebSockets.
6. **Inventory Service** receives `payment.processed` → updates stock (Postgres).
