from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.config import settings
from app.routers import uploads, channels, admin, auth_google, auth_meta, team, legal
from fastapi.responses import JSONResponse
import asyncio
from contextlib import suppress
from app.maintenance import cleanup
from app.middleware import RequestLimits

app = FastAPI(title="srisocials backend")
app.add_middleware(RequestLimits)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_user_origin, settings.frontend_admin_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(uploads.router)
app.include_router(channels.router)
app.include_router(admin.router)
app.include_router(auth_google.router)
app.include_router(auth_meta.router)
app.include_router(team.router)
app.include_router(legal.router)


@app.middleware("http")
async def response_headers(request, call_next):
    response = await call_next(request)
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.on_event("startup")
async def on_startup():
    if settings.environment == "production":
        if (settings.admin_password == "change_me" or len(settings.admin_password) < 12 or
            len(settings.admin_session_secret) < 32 or settings.admin_session_secret.startswith("change_") or
            not settings.token_encryption_key or not settings.supabase_url.startswith("https://") or
            not settings.supabase_service_role_key or not settings.privacy_contact_email or not settings.operator_name or
            not settings.frontend_user_origin.startswith("https://") or not settings.frontend_admin_origin.startswith("https://") or
            "sqlite" in settings.database_url or not settings.public_backend_url.startswith("https://")):
            raise RuntimeError("Production requires strong admin credentials, encryption, Supabase/Postgres, HTTPS and privacy contact settings")
        from cryptography.fernet import Fernet
        Fernet(settings.token_encryption_key.encode())
    init_db()
    async def maintain():
        while True:
            try:
                await asyncio.to_thread(cleanup)
            except Exception:
                import logging
                logging.warning("Maintenance failed; will retry")
            await asyncio.sleep(3600)
    app.state.maintenance_task = asyncio.create_task(maintain())


@app.on_event("shutdown")
async def on_shutdown():
    app.state.maintenance_task.cancel()
    with suppress(asyncio.CancelledError):
        await app.state.maintenance_task


@app.get("/health")
def health():
    return {"status": "ok"}
