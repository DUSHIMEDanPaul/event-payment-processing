from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # RabbitMQ
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    
    # Exchange names for the notification service to watch
    orders_exchange: str = "orders_exchange"
    payments_exchange: str = "payments_exchange"

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379

    @property
    def rabbitmq_url(self) -> str:
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/"
        )

    # Modern Pydantic v2 way to handle .env files
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
