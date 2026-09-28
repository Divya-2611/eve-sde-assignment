from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BookingCreate(BaseModel):
    centre_id: int
    test_id: int
    appointment_datetime: datetime


class BookingReschedule(BaseModel):
    appointment_datetime: datetime


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    centre_id: int
    test_id: int
    appointment_datetime: datetime
    status: str
    amount: float
