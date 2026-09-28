from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class PaymentCreate(BaseModel):
    booking_id: int
    simulate: Literal["success", "fail"]


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    amount: float
    status: str
    provider_reference: str


class PaymentResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment: PaymentOut
    booking_status: str


class WebhookIn(BaseModel):
    event_id: str
    provider_reference: str
    status: str
    booking_id: int | None = None

    @field_validator("event_id", "provider_reference")
    @classmethod
    def _non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class MockChargeIn(BaseModel):
    booking_id: int


class MockChargeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    outcome: str
    event_id: str
    provider_reference: str
    payment_id: int
    booking_status: str
