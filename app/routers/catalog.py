from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.centre import Centre
from app.models.offering import Offering
from app.models.test import Test
from app.schemas.catalog import CentreDetailOut, CentreOut, CentreTestOut, TestOut

router = APIRouter(tags=["catalog"])


@router.get("/centres/", response_model=list[CentreOut])
def list_centres(db: Session = Depends(get_db)) -> list[Centre]:
    return db.query(Centre).order_by(Centre.id).all()


@router.get("/centres/{centre_id}/", response_model=CentreDetailOut)
def get_centre(centre_id: int, db: Session = Depends(get_db)) -> CentreDetailOut:
    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if centre is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centre not found")
    offerings = (
        db.query(Offering, Test)
        .join(Test, Test.id == Offering.test_id)
        .filter(Offering.centre_id == centre_id)
        .order_by(Test.id)
        .all()
    )
    return CentreDetailOut(
        id=centre.id,
        name=centre.name,
        location=centre.location,
        tests=[CentreTestOut(id=t.id, name=t.name, price=float(o.price)) for o, t in offerings],
    )


@router.get("/tests/", response_model=list[TestOut])
def list_tests(
    centre_id: int | None = None,
    location: str | None = None,
    db: Session = Depends(get_db),
) -> list[TestOut]:
    q = db.query(Offering, Test).join(Test, Test.id == Offering.test_id)
    if centre_id is not None:
        q = q.filter(Offering.centre_id == centre_id)
    if location is not None:
        q = q.join(Centre, Centre.id == Offering.centre_id).filter(Centre.location == location)
    rows = q.order_by(Test.id).all()
    return [
        TestOut(id=t.id, name=t.name, price=float(o.price), centre_id=o.centre_id) for o, t in rows
    ]
