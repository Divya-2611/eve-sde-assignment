from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.bookings import router as bookings_router
from app.routers.catalog import router as catalog_router
from app.routers.payments import router as payments_router


def create_app() -> FastAPI:
    app = FastAPI(title="EVE Healthcare")

    # Browsers block cross-origin fetch without CORS headers; the SPA
    # (vite dev :5173, compose web :3000) needs explicit opt-in.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(bookings_router)
    app.include_router(catalog_router)
    app.include_router(payments_router)

    return app


app = create_app()
