# srisocials

Internal team video review and publishing: React user/admin dashboards, FastAPI,
Supabase Postgres + private Storage in production. Local development can use SQLite
and local files. Maximum video size: **50 MiB**, MP4 (H.264/AAC recommended).

## Workflow

1. The administrator creates team accounts in the database using `manage_user.py`.
   Passwords are scrypt hashes, never plaintext. There is no public registration.
2. Admin → Channels → connect each YouTube channel or professional Instagram
   account. OAuth credentials are encrypted on the backend, never sent to either dashboard.
3. A team member signs in, selects a destination, and uploads a video. It appears
   as **Pending review** in admin. Users see only their own submission history.
4. Admin watches the signed preview, checks title/description/destination and,
   for YouTube, chooses the made-for-kids audience designation. Approve or reject.
5. Approved → **Publish**. YouTube visibility defaults to **Private**; an explicit
   selector supports Unlisted/Public. YouTube may restrict unaudited projects to
   private regardless of the selection. The returned visibility is shown after upload.
6. Instagram publishes a **public Reel**. There is no YouTube-style private Reel
   mode here. Keep the Instagram processing tab open for automatic completion,
   or return to it later. Container IDs survive server restarts.

The destination cannot be overridden at publish time. The backend validates the
authorized account, claims the submission atomically, and refuses concurrent
publishes. If a network interruption leaves the outcome uncertain, check the
provider first. **Reset after checking channel** is allowed only after confirming
the post does not exist (wait 15 minutes for an interrupted in-progress request).
Do not reset a successfully posted video: that could create a duplicate.

## Local setup (PowerShell)

Use Python 3.12 and Node.js 22.12+ (or current Node.js 24).

```powershell
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
# Only if .env does not exist:
Copy-Item .env.example .env
.venv/Scripts/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Put that key in TOKEN_ENCRYPTION_KEY. Keep it stable and back it up securely.
.venv/Scripts/python manage_user.py alice --name "Alice"
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000 --no-access-log
```

The existing local Google client ID/secret have been preserved. A missing local
token encryption key was generated during this integration. Set a strong admin
password and session secret in `.env`. Do not commit `.env`, databases, or uploads.

In separate terminals:

```powershell
cd frontend/user-dashboard
npm ci
npm run dev
# http://localhost:5173
```

```powershell
cd frontend/admin-dashboard
npm ci
npm run dev
# http://localhost:5174
```

Sign in to admin with `ADMIN_USERNAME`/`ADMIN_PASSWORD`, then connect a channel.
Google redirect: `http://localhost:8000/auth/google/callback`.
Instagram requires a registered redirect and externally reachable HTTPS media;
use the hosted backend + Supabase for its first real test.

Create additional users with `manage_user.py username --name "Display Name"`.
Create database-backed admins with `manage_user.py admin1 --admin --name "Admin 1"`.
Add `--admin` when resetting, disabling or deleting an admin. Admins are stored in
`srisocials_adminuser`; use admin usernames different from `ADMIN_USERNAME`.
The original `.env` admin remains available. Restart the backend after upgrading.
Re-running it resets their password and invalidates their existing sessions.
Use `--disable` to block sign-in, or `--delete` to remove their account and stored
submissions (published platform posts remain). Run these commands from your
computer against the production database when using Render Free, which does not
provide the paid service shell workflow. Never put passwords in shell arguments.

## Deployment and provider setup

- [Deployment guide](deployment.md): Supabase, Render, Vercel, configuration and acceptance test.
- [Meta app from scratch](metaappsteps.md): Instagram App ID/secret, redirects,
  professional account, test access, permissions and review evidence.
- Backend policy URLs: `/privacy`, `/terms`, `/data-deletion`.
  Configure the actual operator name/contact email before using them for review.

**Vercel Hobby is only for personal, non-commercial use.** If this is a business
or monetized team workflow, do not assume the requested all-free Vercel setup
meets its terms. Choose an eligible hosting plan/provider before production use.
The frontends are ordinary static Vite builds and are portable.

## Google/YouTube configuration and review

Enable YouTube Data API v3 and YouTube Analytics API. Configure an OAuth web
application and add the exact local/hosted backend callback URLs. The app requests
`youtube.upload`, `youtube.readonly`, and `yt-analytics.readonly`: uploading,
channel identity/statistics, and read-only channel performance reports.
Reconnect existing channels to grant Analytics access. Existing upload grants
continue to work without silently requesting broader permissions.

Admin → Analytics → choose a YouTube channel and date range → Load report.
The admin-only `GET /admin/channels/{id}/analytics?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
returns views, watch time, average view duration, subscribers gained/lost, daily
views, and top videos. Reports are requested on demand and not cached in the DB.
YouTube reporting can lag; missing data is shown as unavailable, not invented.
See [supported channel reports](https://developers.google.com/youtube/analytics/channel_reports).

OAuth consent verification and the YouTube API compliance audit are separate
processes. External Testing mode can limit eligible accounts and cause refresh
tokens to expire after seven days for these scopes. Testing is not an exemption
from policies. Projects subject to the upload restriction remain private until
the required YouTube audit is approved. Do not describe this app as already
verified or approved.

For review: publish real policy/contact URLs, configure your consent screen,
verify domains where required, use only necessary scopes, and provide a recording
showing connection, team upload, admin preview, audience/visibility choice,
publishing, provider result and disconnect/deletion. Reviewers need working
accounts and reachable services. Use a dedicated test channel and content you own.

## Storage, security and retention

- Browser uploads go directly to the Render API (not through Vercel functions).
  The API stores private Supabase objects; temporary local files are removed.
- Backend authenticates team/admin requests, limits body sizes, bounds login
  attempts, and validates MP4 headers. It does not transcode or guarantee codecs;
  the provider may reject an otherwise valid container. Keep source originals.
- Preview links expire in 15 minutes. Instagram gets a one-hour signed file URL.
  The storage bucket must remain private. No public Storage policies are needed.
- Database tables use RLS in Postgres with no browser access policies. Only the
  backend database role and backend service key access records/objects.
- OAuth uses one-time database state and a short-lived first-party browser cookie.
  Session tokens are kept in session storage, expire after 12 hours, and differ
  between admin and team roles. Logout removes the browser token.
- Delete app copies individually, or disconnect a channel to delete its stored
  tokens and submissions. Revocation is attempted; verify provider connected-app
  settings if the provider is unavailable. Published posts are never deleted by
  these actions. Requested account-data deletion must be handled within 7 days.
- Maintenance removes submission files/records older than 30 days and unused
  provider connections without authorization validation for 30 days. It runs
  when the service starts and hourly while awake. Free hosting sleeps/pauses:
  operators must execute overdue cleanup/deletion before review or responding to
  a deletion request, rather than rely on an always-running free worker.

App tables are named `srisocials_channel`, `srisocials_video`,
`srisocials_teamuser`, `srisocials_adminuser`, and `srisocials_oauthattempt`, including prefixed foreign
keys. Run `python migrate_supabase.py` from `backend` to create/verify the hosted
schema after setting the Postgres `DATABASE_URL`. Startup also applies additive
upgrades to these tables. Unprefixed tables are never automatically migrated or
modified because they may belong to another project. If you have old unprefixed
srisocials data, back it up and perform an explicit source-verified import.

## Tests

```powershell
cd backend
.venv/Scripts/python -m pytest -q
```

Provider and storage calls are mocked; tests never post content to real accounts.
Run `npm run build` in both frontend folders. A successful real OAuth connection
and private test upload are still needed with your hosted provider accounts.

## Official references

- [YouTube upload endpoint and private-upload restriction](https://developers.google.com/youtube/v3/docs/videos/insert)
- [YouTube minimum functionality](https://developers.google.com/youtube/terms/required-minimum-functionality)
- [YouTube developer policies](https://developers.google.com/youtube/terms/developer-policies)
- [Google OAuth token expiration](https://developers.google.com/identity/protocols/oauth2#expiration)
- [Meta Instagram API with Instagram Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login)
- [Supabase file size limits](https://supabase.com/docs/guides/storage/uploads/file-limits)
- [Render Free limitations](https://render.com/docs/free)
- [Vercel Hobby permitted use](https://vercel.com/docs/plans/hobby)
