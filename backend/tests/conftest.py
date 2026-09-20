"""Isolate test configuration before any application module is imported."""
import os
from cryptography.fernet import Fernet

os.environ.update(DATABASE_URL="sqlite://", GOOGLE_CLIENT_ID="test", GOOGLE_CLIENT_SECRET="test",
    ADMIN_USERNAME="admin", ADMIN_PASSWORD="test-password-123", ADMIN_SESSION_SECRET="test-session-secret-which-is-long-enough",
    TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode(), SUPABASE_URL="", SUPABASE_SERVICE_ROLE_KEY="",
    ENVIRONMENT="development", PUBLIC_BACKEND_URL="http://testserver", META_APP_ID="test", META_APP_SECRET="test",
    GOOGLE_REDIRECT_URI="http://testserver/auth/google/callback", META_REDIRECT_URI="http://testserver/auth/meta/callback")
