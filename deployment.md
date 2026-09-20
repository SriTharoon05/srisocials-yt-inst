# Deployment: Supabase + Render + two static frontends

## 1. Check free-plan suitability

Supabase Free limits each stored object to 50 MB and includes 1 GB total file
storage: roughly 20 maximum-size clips before other usage. Preview, platform
downloads and uploads consume quotas. Delete unneeded copies and keep originals.
Render Free sleeps after idle periods and has ephemeral disk; neither SQLite nor
local uploads are production storage. Cold starts and quota pauses can interrupt
testing. Do not configure an artificial keep-alive to defeat the free plan.

Vercel Hobby is restricted to personal non-commercial projects. If this is a
business/monetized workflow, select a compliant plan or a static hosting provider
whose free terms cover your use. The supplied Vercel configuration is technically
ready but does not waive those terms. Platform approval is not guaranteed by code.

## 2. Supabase

1. Create a project; retain its database password securely.
2. Run `backend/supabase-storage.sql` in SQL Editor. The `videos` bucket must be
   **private**, with maximum size 52,428,800 bytes and `video/mp4` MIME type.
3. Copy the project URL and server-only service-role key into backend secrets.
   Never use this key in any `VITE_*` variable or browser source.
4. In **Connect**, get the Postgres **session pooler** connection string (IPv4
   compatible, normally port 5432). Use the exact host/user supplied by Supabase;
   URL-encode special characters in the password. Set `sslmode=require`.
   Example shape only:
   `postgresql+psycopg://postgres.PROJECT:PASSWORD@POOLER:5432/postgres?sslmode=require`
5. Set this as `DATABASE_URL`. Startup creates app tables and enables RLS. There
   are intentionally no anon/authenticated browser policies on app tables.
   The server database role must be able to create/alter its tables and use them.
   App table names are `srisocials_channel`, `srisocials_video`,
   `srisocials_teamuser`, `srisocials_adminuser`, and `srisocials_oauthattempt`. All foreign keys point to
   these prefixed tables. Other projects' tables are not renamed or changed.
   To apply and verify the schema now, run from `backend`:
   `.venv/Scripts/python migrate_supabase.py`.
   The project URL and service key alone cannot create SQL tables; a Postgres
   connection string with its database password is required.
6. Do not enable public Storage SELECT/INSERT policies. Backend authorization
   and signed URLs handle access. Check Supabase Security Advisor before review.

## 3. Render backend

Push the source to your own repository without `.env`, `.venv`, database, uploads,
or build output. Create a Web Service with `backend` as Root Directory, Python
3.12, Free instance, build `pip install -r requirements.txt`, start:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --no-access-log
```

Alternatively use root `render.yaml`. Use **one worker** for this small service.
Health check: `/health`. Disabling access logs prevents callback codes and signed
preview query strings from being written to ordinary request logs.

Set backend secrets/environment values:

| Variable | Value |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Supabase session-pooler URL, SSL required |
| `SUPABASE_URL` | `https://PROJECT.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side key |
| `SUPABASE_STORAGE_BUCKET` | `videos` |
| `PUBLIC_BACKEND_URL` | `https://YOUR-API.onrender.com` (no trailing slash) |
| `FRONTEND_USER_ORIGIN` | Exact user frontend HTTPS origin, no trailing slash |
| `FRONTEND_ADMIN_ORIGIN` | Exact admin frontend HTTPS origin, no trailing slash |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Admin account; password at least 12 characters |
| `ADMIN_SESSION_SECRET` | Random stable secret, at least 32 characters |
| `TOKEN_ENCRYPTION_KEY` | Stable Fernet key; reuse securely when moving existing encrypted channel data |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Existing Google web OAuth credentials |
| `GOOGLE_REDIRECT_URI` | `https://YOUR-API.onrender.com/auth/google/callback` |
| `META_APP_ID`, `META_APP_SECRET` | Instagram-specific App ID/secret; may stay blank until setup |
| `META_REDIRECT_URI` | `https://YOUR-API.onrender.com/auth/meta/callback` |
| `META_API_VERSION` | `v25.0` (supported version pinned for this integration; review Meta version lifecycle) |
| `OPERATOR_NAME`, `PRIVACY_CONTACT_EMAIL` | Actual responsible operator and monitored email |

Generate keys locally with the installed backend Python:

```powershell
.venv/Scripts/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
.venv/Scripts/python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Keep keys out of recordings and screenshots. Startup deliberately fails on unsafe
production defaults. Leave `UPLOAD_DIR` as temporary local working storage.

## 4. Vercel frontends (only if your use is eligible)

Create two Vercel projects from the same repository:

- User Root Directory: `frontend/user-dashboard`
- Admin Root Directory: `frontend/admin-dashboard`

Framework: Vite. Install: `npm ci`. Build: `npm run build`. Output: `dist`.
Select Node.js 24 (or 22.12+) for the frontend build environment.
Set **only** `VITE_API_BASE=https://YOUR-API.onrender.com` as the API configuration.
Redeploy after changing it because Vite embeds this at build time. Add both exact
origins to Render environment values. The included rewrites support direct visits
to `/login` and `/channels`. Do not put provider secrets on Vercel.

## 5. Accounts and provider callbacks

Using a trusted local backend shell with `DATABASE_URL` temporarily set to your
Supabase connection, run `manage_user.py alice --name "Alice"` for each team member.
Passwords are prompted, hashed and stored. The same environment can run
`manage_user.py alice --disable` or `--delete` later. When deleting stored videos,
also supply the production Supabase URL/service key. Clear temporary shell secrets
afterward; do not accidentally point local testing at production.

Register the exact Google/Instagram callback URLs above with their providers.
Enable **YouTube Analytics API** alongside YouTube Data API v3 in the same Google
Cloud project. Add `https://www.googleapis.com/auth/yt-analytics.readonly` to the
consent screen's requested scopes and reconnect existing channels to grant it.
The admin Analytics tab requests live reports through
`GET /admin/channels/{id}/analytics`; no extra environment secret is required.
Populate the provider app's homepage, privacy, terms and data-deletion URLs.
Use `/privacy`, `/terms`, `/data-deletion` on the backend for the latter three.
Then connect accounts from admin. Credentials alone never replace owner consent.

## 6. Acceptance test before review

1. Open `/health` and policy pages. Check real operator/contact details.
2. Sign in to admin; connect the intended Google/Brand channel. Confirm its name.
3. Sign in as a team member; upload a small MP4. Check that another user cannot
   see it in their history, and unauthenticated uploads fail.
4. Open Pending review; play and seek the video. Choose its audience and approve.
5. Leave YouTube visibility on Private. Click Publish once. Verify in YouTube
   Studio that it reached the correct channel as private. Keep a review recording.
6. Connect a professional Instagram account; upload an owned test Reel. Approve,
   click Publish public Reel, and leave Processing open until published. Verify
   the actual public post. Do not use private/confidential media for this test.
7. Test deletion of the app copy and disconnect. Check provider permissions too.
8. Test a backend restart: pending videos must still play from private Storage.

Mock tests verify application behavior but cannot prove credentials, account
eligibility, provider review status, actual video codecs or real quotas.

## 7. Operations

No paid background worker is required. YouTube uploads run in the publish request;
an interrupted result requires reconciliation. Instagram processing uses persisted
containers and short requests while the admin queue is open. Never use blind
automatic retries after a potentially successful publish.

Maintenance starts on wake and hourly while running. To perform cleanup manually
against production, use a correctly configured local backend shell:

```powershell
.venv/Scripts/python -c "from app.maintenance import cleanup; cleanup()"
```

Watch storage/egress and free-service availability. If a service pauses, process
deletion requests directly within the stated deadline rather than waiting for
the scheduled maintenance task. Reconnect expired Instagram tokens and Google
Testing-mode tokens from Channels. Back up keys and DB securely, not public files.
