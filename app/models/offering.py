from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.centre import Centre
    from app.models.test import Test


class Offering(Base):
    __tablename__ = "offerings"
    __table_args__ = (UniqueConstraint("centre_id", "test_id", name="uq_offering_centre_test"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    centre_id: Mapped[int] = mapped_column(ForeignKey("centres.id", ondelete="CASCADE"), nullable=False)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    centre: Mapped["Centre"] = relationship(back_populates="offerings")
    test: Mapped["Test"] = relationship(back_populates="offerings")
