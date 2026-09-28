from app.routers.auth import router as auth_router
from app.routers.bookings import router as bookings_router
from app.routers.catalog import router as catalog_router
from app.routers.payments import router as payments_router

__all__ = ["auth_router", "bookings_router", "catalog_router", "payments_router"]
