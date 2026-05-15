from uuid import UUID
from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    """Request body for creating an order."""
    customer_id: str = Field(..., example="cust-001")
    product_id: str = Field(..., example="prod-abc")
    quantity: float = Field(..., gt=0, example=2)
    total_amount: float = Field(..., gt=0, example=49.99)


class OrderResponse(BaseModel):
    """Response returned after order creation."""
    id: UUID
    customer_id: str
    product_id: str
    quantity: float
    total_amount: float
    status: str

    class Config:
        from_attributes = True  # Pydantic v2 ORM mode
