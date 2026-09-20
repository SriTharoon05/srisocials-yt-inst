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
        failures = []

        if settings.admin_password == "change_me":
            failures.append("ADMIN_PASSWORD is change_me")

        if len(settings.admin_password) < 12:
            failures.append("ADMIN_PASSWORD is less than 12 chars")

        if len(settings.admin_session_secret) < 32:
            failures.append("ADMIN_SESSION_SECRET is less than 32 chars")

        if settings.admin_session_secret.startswith("change_"):
            failures.append("ADMIN_SESSION_SECRET starts with change_")

        if not settings.token_encryption_key:
            failures.append("TOKEN_ENCRYPTION_KEY is empty")

        if not settings.supabase_url.startswith("https://"):
            failures.append("SUPABASE_URL must start with https://")

        if not settings.supabase_service_role_key:
            failures.append("SUPABASE_SERVICE_ROLE_KEY is empty")

        if not settings.privacy_contact_email:
            failures.append("PRIVACY_CONTACT_EMAIL is empty")

        if not settings.operator_name:
            failures.append("OPERATOR_NAME is empty")

        if not settings.frontend_user_origin.startswith("https://"):
            failures.append("FRONTEND_USER_ORIGIN must start with https://")

        if not settings.frontend_admin_origin.startswith("https://"):
            failures.append("FRONTEND_ADMIN_ORIGIN must start with https://")

        if "sqlite" in settings.database_url.lower():
            failures.append("DATABASE_URL is using SQLite")

        if not settings.public_backend_url.startswith("https://"):
            failures.append("PUBLIC_BACKEND_URL must start with https://")

        if failures:
            raise RuntimeError(
                "Production configuration errors: " + ", ".join(failures)
            )

        from cryptography.fernet import Fernet
        Fernet(settings.token_encryption_key.encode())

    init_db()


@app.on_event("shutdown")
async def on_shutdown():
    task = getattr(app.state, "maintenance_task", None)
    if task is not None:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


@app.get("/health")
def health():
    return {"status": "ok"}
