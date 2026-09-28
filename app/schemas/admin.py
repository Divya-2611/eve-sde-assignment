from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _require_non_blank(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    if not value.strip():
        raise ValueError(f"{field} must not be blank")
    return value


class AdminBookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user_email: str
    centre_id: int
    centre_name: str
    test_id: int
    test_name: str
    appointment_datetime: datetime
    status: str
    amount: float


class AdminPaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    amount: float
    status: str
    provider_reference: str


class AdminCentreCreate(BaseModel):
    name: str = Field(min_length=1)
    location: str = Field(min_length=1)

    @field_validator("name", "location")
    @classmethod
    def _non_blank(cls, v: str) -> str:
        return _require_non_blank(v, "value")  # type: ignore[return-value]


class AdminCentreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    location: str | None = Field(default=None, min_length=1)

    @field_validator("name", "location")
    @classmethod
    def _non_blank_opt(cls, v: str | None) -> str | None:
        return _require_non_blank(v, "value")


class AdminCentreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str


class AdminTestCreate(BaseModel):
    name: str = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def _non_blank(cls, v: str) -> str:
        return _require_non_blank(v, "value")  # type: ignore[return-value]


class AdminTestUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)

    @field_validator("name")
    @classmethod
    def _non_blank_opt(cls, v: str | None) -> str | None:
        return _require_non_blank(v, "value")


class AdminTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class AdminOfferingUpsert(BaseModel):
    centre_id: int
    test_id: int
    price: float = Field(gt=0)


class AdminOfferingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    centre_id: int
    test_id: int
    price: float


class AdminBookingStatsOut(BaseModel):
    total: int
    counts: dict[str, int]
    confirmed_sum: float
