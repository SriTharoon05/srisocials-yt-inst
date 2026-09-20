import React, {useEffect} from "react";
import {Brand} from "./ui";
import "./legal.css";

export default function HomePage() {
  useEffect(() => { document.title = "Sri Socials Publisher | Video review and publishing"; }, []);
  return <div className="policy-page">
    <header className="policy-header"><a href="/about" aria-label="Sri Socials Publisher homepage"><Brand/></a><a className="button" href="/">Open workspace</a></header>
    <main className="policy-main">
      <nav className="policy-nav" aria-label="Public information"><a href="/about" aria-current="page">About the app</a><a href="/privacy">Privacy policy</a><a href="/terms">Terms of service</a><a href="/data-deletion">Data deletion</a></nav>
      <article className="policy-card"><span className="eyebrow">SRI SOCIALS PUBLISHER</span><h1>Create together. Review before publishing.</h1>
        <div className="policy-content">
          <p>Sri Socials Publisher is a team workspace operated by sritharoon. Creators submit finished videos, administrators review them, and account owners connect their YouTube channels or professional Instagram accounts for publishing and performance reports.</p>
          <h2>What the app does</h2>
          <p>Our team creates short stories using AI-generated images, editing and voiceovers outside the app. Creators upload a finished MP4 of up to 50 MB and select a YouTube destination, an Instagram destination, or both. The app does not generate the images or voiceovers.</p>
          <p>Each destination receives a separate review. An administrator previews the video, checks its title, description and audience, and approves or rejects it. Publishing requires an administrator action. YouTube visibility defaults to Private; administrators can select Unlisted or Public where their API project permits it. Instagram publishes public Reels.</p>
          <p>Administrators can request channel performance reports for selected dates. YouTube reports show views, watch time, average view duration, subscriber changes and top videos. Instagram Insights shows views, reach, engaged accounts and interactions when the connected account grants Insights access. Reports can be delayed or unavailable depending on provider permissions and activity.</p>
          <h2>Why we request Google account access</h2>
          <p>Only account owners or authorized administrators connect a channel through Google's authorization screen. Creator login uses a team account supplied by the administrator; a creator does not need to grant Google access to submit a video.</p>
          <ul>
            <li><strong>YouTube upload access:</strong> sends the reviewed video and its title, description, audience and chosen visibility to the connected channel after the administrator clicks Publish.</li>
            <li><strong>Read-only YouTube access:</strong> identifies the authorized channel, verifies the publishing destination, and retrieves channel statistics and video titles for reports.</li>
            <li><strong>Read-only YouTube Analytics access:</strong> retrieves performance reports when an administrator requests them.</li>
          </ul>
          <h2>How connected-account data is used</h2>
          <p>We store channel identifiers and encrypted authorization tokens so the app can act on the connected account without asking for its password. Team credentials, submissions and review records support the review workflow. Analytics reports are displayed to administrators and are not cached in our database. Google account data is used for the publishing and reporting features described here, not sold or used for advertising.</p>
          <p>You can disconnect an account and delete its app data from Channels, or revoke Google's access in your <a href="https://security.google.com/settings/security/permissions">Google account permissions</a>. Removing the app copy does not delete a video already posted on YouTube or Instagram. Our <a href="/privacy">Privacy policy</a> explains storage, sharing and retention, and our <a href="/data-deletion">data deletion instructions</a> explain how to request removal.</p>
          <p>This app uses YouTube API Services and the Instagram API. Connecting accounts and publishing are available to authorized team members. You do not need to sign in to read this page or our policies.</p>
        </div>
        <section className="policy-contact"><h2>Contact</h2><p>Operator: sritharoon<br/><a href="mailto:srisocials05@gmail.com">srisocials05@gmail.com</a></p><a className="button" href="/">Open workspace</a></section>
      </article>
    </main>
  </div>;
}
