import React, {useEffect} from "react";
import {Brand} from "./ui";
import "./legal.css";

const pages = {
  "/privacy": {title: "Privacy policy", content: <>
<p>Sri Socials Publisher is an internal team video review and publishing service. We use YouTube API Services and the Instagram API.</p>
    <p>We store team usernames, display names, password hashes, submitted videos, titles, descriptions, review decisions, destination account identifiers and encrypted OAuth tokens. Administrators can review team submissions. We use these data only for authentication, review and publishing to accounts explicitly connected by their owners. We do not sell data or use it for advertising.</p>
    <p>Render processes backend requests, Supabase stores application data and submitted videos, and Vercel hosts the dashboards. Approved videos and their metadata are sent to the selected Google/YouTube or Meta/Instagram account when an administrator clicks Publish. YouTube uploads default to Private and use the visibility explicitly selected by the administrator; Instagram Reels are public. Temporary signed file links let authorized reviewers and Instagram fetch videos. If the operator configures a public storage bucket, anyone with a source file URL can access that file.</p>
    <p>When an administrator requests a report, we read authorized YouTube channel analytics including views, watch time, average view duration, subscriber changes and top videos. Instagram Insights reads views, reach, engaged accounts and interactions. Reports are displayed in the administrator's browser and are not cached in our database. Analytics and Insights access can be revoked with the channel connection.</p>
    <p>Session tokens remain in browser session storage until logout or tab closure and expire after 12 hours. OAuth cookies expire after 10 minutes. Submission files and records are removed after 30 days by maintenance while the service is awake. Unused provider connections are removed after 30 days without authorization validation. Team accounts remain until the administrator deletes them. Provider-hosted posts remain until removed on the provider.</p>
    <p>Request access, correction or deletion through the contact below. The administrator must handle requests within 7 days. See <a href="/data-deletion">deletion instructions</a>. You can also revoke access in <a href="https://security.google.com/settings/security/permissions">Google security settings</a> or Instagram Settings → Website permissions → Apps and websites. Revocation stops future authorized access; request deletion to remove app-held data sooner.</p>
    <p>See the <a href="https://policies.google.com/privacy">Google Privacy Policy</a> and <a href="https://privacycenter.instagram.com/policy/">Meta Privacy Policy</a>. This service is intended for authorized adult team members, not for children. Contact the operator about policy updates or data questions.</p>
  </>},
  "/terms": {title: "Terms of service", content: <>
<p>Only authorized team members may use srisocials. Submit only content you have permission to upload and distribute, including music and appearances. Do not submit unlawful content or violate platform rules.</p>
    <p>Administrators review the destination, title, description and audience designation before publishing. YouTube uploads default to Private; the administrator may explicitly choose Unlisted or Public, subject to YouTube project restrictions. Instagram publishing creates a public Reel. Each channel owner must authorize access. You are responsible for accurate made-for-kids declarations and content rights.</p>
    <p>By using this service you also agree to the <a href="https://www.youtube.com/t/terms">YouTube Terms of Service</a> and applicable <a href="https://help.instagram.com/581066165581870">Instagram Terms</a>. Free hosting can sleep, pause or reach quotas. Keep original files and verify platform results before retrying uncertain uploads.</p>
  </>},
  "/data-deletion": {title: "Data deletion instructions", content: <>
<p>Contact the operator below with your team username or connected channel name. Do not send passwords or access tokens. The operator verifies the request and deletes the requested app data within 7 days.</p>
    <p>Administrators can delete an individual submission from the review queue, or use Channels → Disconnect and delete app data to erase a connection, its tokens and associated submissions. Team accounts can be deleted with the account management command. Published YouTube or Instagram videos must be removed in YouTube Studio or Instagram; deleting the app copy does not remove the platform post.</p>
    <p>Revoke provider access through <a href="https://security.google.com/settings/security/permissions">Google account permissions</a> or Instagram → Settings → Website permissions → Apps and websites. A provider outage does not prevent local deletion; verify revocation in provider settings.</p>
  </>},
};

export function legalPagePath(path) {
  const normalized = path.replace(/\/+$/, "") || "/";
  return Object.hasOwn(pages, normalized) ? normalized : null;
}

export default function LegalPage({path}) {
  const page = pages[path];
  useEffect(() => { document.title = `${page.title} | Sri Socials Publisher`; }, [page.title]);
  return <div className="policy-page">
    <header className="policy-header"><a href="/" aria-label="Back to workspace"><Brand/></a><a className="button" href="/">Back to workspace</a></header>
    <main className="policy-main">
      <nav className="policy-nav" aria-label="Legal information"><a href="/about">About the app</a>
        {Object.entries(pages).map(([href, item]) => <a key={href} href={href} aria-current={href===path?'page':undefined}>{item.title}</a>)}
      </nav>
      <article className="policy-card"><span className="eyebrow">SRI SOCIALS PUBLISHER</span><h1>{page.title}</h1>
        <div className="policy-content">{page.content}</div>
        <section className="policy-contact"><h2>Contact the operator</h2><p>Operator: sritharoon<br/><a href="mailto:srisocials05@gmail.com">srisocials05@gmail.com</a></p></section>
      </article>
    </main>
  </div>;
}
