from pydantic import BaseModel


class CentreOut(BaseModel):
    id: int
    name: str
    location: str


class CentreTestOut(BaseModel):
    id: int
    name: str
    price: float


class CentreDetailOut(BaseModel):
    id: int
    name: str
    location: str
    tests: list[CentreTestOut]


class TestOut(BaseModel):
    id: int
    name: str
    price: float
    centre_id: int
