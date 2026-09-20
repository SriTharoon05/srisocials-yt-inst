# Create the Meta app for srisocials (Instagram only)

This integration uses **Instagram API with Instagram Login**, not Instagram
Basic Display and not the Facebook Login variant. It supports Business/Creator
Instagram accounts and does not require a linked Facebook Page. Reels are public.

Facebook Page publishing is deliberately excluded: it uses additional Page
permissions and a different connection flow, and broad access can require its
own permission review. It is not included in the two Instagram permissions below.

## 1. Prepare your account and URLs

1. Use the real Facebook account belonging to the responsible app administrator
   to register at [Meta for Developers](https://developers.facebook.com/).
   Complete any identity/contact/security requirements Meta presents.
2. Switch the target Instagram account to a **Professional** account (Business or
   Creator) in Instagram account settings. Keep its sign-in credentials available.
3. Deploy the backend and dashboards using `deployment.md`; configure private
   Supabase Storage. You need a publicly reachable HTTPS backend for hosted OAuth
   and an HTTPS signed video URL that Instagram's servers can fetch.
4. Configure real `OPERATOR_NAME` and `PRIVACY_CONTACT_EMAIL`. Open your backend's
   `/privacy`, `/terms` and `/data-deletion` without signing in and review the text.

## 2. Create an app and add Instagram

1. Open **My Apps → Create App** in the developer dashboard.
2. Enter the app name (for example, srisocials), monitored app contact email and
   the business portfolio if required for your chosen setup.
3. Select the use case for managing Instagram content/presence. Dashboard labels
   vary: if Instagram isn't available at the initial screen, use the available
   **Other / Business** creation route and add the **Instagram** product afterward.
   Choose the setup explicitly labeled **Instagram API with Instagram Login**.
4. Open the Instagram product's API setup. Locate the **Instagram App ID** and
   **Instagram App Secret**. These may differ from the general Meta App ID/secret
   shown in Settings → Basic. Use the credentials for this Instagram Login setup.
5. Set on the Render backend (and local backend when testing):

```dotenv
META_APP_ID=YOUR_INSTAGRAM_APP_ID
META_APP_SECRET=YOUR_INSTAGRAM_APP_SECRET
META_REDIRECT_URI=https://YOUR-API.onrender.com/auth/meta/callback
META_API_VERSION=v25.0
```

Do not place these in frontend environment variables, source control or a
review recording. A pasted manually generated access token is not required:
the implemented OAuth flow exchanges and stores tokens for each connected account.

## 3. Configure Instagram Business Login / OAuth

In Instagram → API setup → Business login settings (wording may differ):

1. Register the **exact** redirect URI:
   `https://YOUR-API.onrender.com/auth/meta/callback`.
   Match HTTPS, hostname, path and trailing slash exactly.
2. Set the website/homepage to your admin dashboard's public origin where asked.
   Add app domains where required by Meta's UI. Do not include URL paths in a
   field that requests only a domain.
3. Save. Restart/redeploy the backend after changing environment values.
4. Use a stable hosted URL for review. Localhost redirects may have product-specific
   restrictions; if testing locally, register an HTTPS tunnel URL and use it
   consistently for `PUBLIC_BACKEND_URL` and `META_REDIRECT_URI`. Never tunnel
   an unauthenticated uploads directory.

The backend requests only:

| Permission | Purpose |
| --- | --- |
| `instagram_business_basic` | Identify the connected professional account and read published media links |
| `instagram_business_content_publish` | Create/process/publish the approved Reel to that account |

Do not request Facebook Page, ads, messages, comments or insights permissions for
this implementation. Do not substitute `instagram_basic` or
`instagram_content_publish`; those belong to the Facebook Login variant.

## 4. Development access and account connection

1. Add the account/person as an app role/tester and as an Instagram test account
   wherever the Instagram setup asks. Accept invitations from the invited account
   (Instagram website permissions / Apps and websites / tester invitations, as
   presented by the current UI). The dashboard may ask you to add the professional
   account directly during API setup.
2. Standard/development access is for eligible accounts you own/manage and app
   roles; it does not automatically authorize arbitrary external customers.
3. In srisocials admin → Channels → **Connect Instagram**, sign in to the intended
   professional account and grant both requested permissions.
4. On return, verify the username displayed. Repeat for each destination account.
5. From a team login, select that Instagram account and submit a small MP4. Admin
   reviews, approves, then chooses **Publish public Reel**. The processing tab
   automatically checks and finishes previously requested publishes while open.
6. Confirm the public Reel on the actual profile and verify the returned link.

Use a short portrait 9:16 MP4 with H.264 video and AAC audio for the first test.
The app checks the MP4 container and its own 50 MB limit; Meta checks the actual
codec, duration, aspect ratio and other publishing requirements. It does not
transcode invalid media. Ensure title plus description fits 2,200 characters.

The backend exchanges short-lived credentials for a long-lived token, encrypts
it, and refreshes near expiry when publishing. If unused long enough to expire
or if the user revokes access, reconnect. The app removes unused connections
after 30 days without validation, so do not treat tokens as permanent.

## 5. Public app settings and review

In Settings → Basic / relevant use-case settings, complete the items Meta asks
for, including name/icon/category/contact, domains and these public URLs:

- Privacy policy: `https://YOUR-API.onrender.com/privacy`
- Terms: `https://YOUR-API.onrender.com/terms`
- User data deletion: choose **Data deletion instructions URL** and enter
  `https://YOUR-API.onrender.com/data-deletion`.

This URL is a human-readable instructions page, **not a signed-request deletion
callback**. Do not configure it as a callback. The operator must handle requests
using the app's delete/disconnect/account-management tools within the stated
deadline. If your app configuration mandates callbacks, that configuration needs
additional callback implementation before submission.

For use outside eligible app-role/owned accounts, request the access level Meta
requires for the two permissions through App Review. Complete business
verification, access verification or other requirements when the dashboard asks;
an App ID/secret alone cannot bypass them. The exact requirements depend on the
app/account/use case and are decided by Meta.

Prepare a recording that shows:

1. Admin signs in and connects the professional Instagram account through OAuth.
2. The requested permissions are granted and the correct username appears.
3. A team user signs in and uploads a video to that destination.
4. Admin plays the preview and approves it.
5. Admin clicks Publish public Reel; processing completes and the Reel appears
   on that Instagram account. No automatic posting occurs before admin action.
6. Admin shows disconnect/data-deletion controls and the public policy pages.

Provide clear reviewer credentials for a dedicated srisocials admin/team account,
test instructions and suitable Instagram assets through Meta's approved reviewer
access process. Do not expose your production passwords or client secrets in the
recording. Ensure sleeping/free services are reachable during the review.

Suggested permission explanations (adapt truthfully):

- Basic: “Identify and display the professional Instagram account explicitly
  connected by its owner so our internal team can choose the correct destination.”
- Publish: “Publish a team-submitted Reel only after an administrator previews,
  approves and clicks Publish for that account.”

Complete any required data-use checkups and keep the app's access level current.
Do not promise Meta approval or tell reviewers unsupported features are available.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Connect button reports missing config | Instagram-specific ID/secret, token encryption key, redeploy |
| Redirect rejected | Exact registered HTTPS callback and selected login product |
| Invalid scope | Use `instagram_business_*` with Instagram Login |
| Account unavailable | Professional account, accepted tester/app role invitation, requested access level |
| Container fails | Signed HTTPS video URL, private bucket object exists, codec/length/caption requirements |
| Connection expired | Reconnect the Instagram account from Channels |
| Processing paused after closing browser | Return to Instagram processing; the container is stored in the DB |
| Publish result uncertain | Check Instagram before resetting; never blindly re-upload |
| Need Facebook publishing | Separate Pages integration/permissions; not part of this setup |

## Official references

- [Instagram API with Instagram Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login)
- [Business Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login)
- [Content Publishing](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing)
- [Meta's official Instagram API examples](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api)
- [Meta App Review](https://developers.facebook.com/docs/app-review)
- [Permissions reference](https://developers.facebook.com/docs/permissions)

Meta changes dashboard labels and review requirements. Follow the selected
Instagram Login product's current dashboard prompts where labels differ.
