import React from "react";

const paths = {
  grid: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
  film: <><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M7 4v16M17 4v16M3 9h4m-4 6h4m10-6h4m-4 6h4"/></>,
  chart: <><path d="M4 4v16h17M8 16v-5m5 5V7m5 9V4"/></>,
  link: <><path d="m10 13 4-4m-5 7-2 2a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2 0 2-2a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0" transform="translate(1 0)"/></>,
  upload: <><path d="M12 16V3m-5 5 5-5 5 5M4 15v5h16v-5"/></>,
  arrow: <path d="M4 12h16m-6-6 6 6-6 6"/>,
  check: <path d="m5 12 4 4L19 6"/>,
  clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
  search: <><circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/></>,
  refresh: <><path d="M20 7v5h-5M4 17v-5h5M6 6a8 8 0 0 1 13 2M5 16a8 8 0 0 0 13 2"/></>,
  logout: <><path d="M9 4H4v16h5m0-8h12m-4-4 4 4-4 4"/></>,
  play: <path d="m9 5 10 7-10 7z"/>,
  lock: <><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/></>,
  spark: <><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z"/></>,
  users: <><circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3m1-17a3 3 0 0 1 0 6m3 11v-3a6 6 0 0 0-3-5"/></>,
  close: <path d="m6 6 12 12M6 18 18 6"/>,
};
export function Icon({name="film",size=20,...props}) {return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name] || paths.film}</svg>;}
export function Brand(){return <div className="brand"><span className="brand-symbol"><Icon name="play" size={21}/></span><span><span className="brand-light">Sri Socials Publisher</span><small>THE CONTENT WORKSPACE</small></span></div>;}
export function LegalLinks(){return <footer className="legal"><span>Made for stories worth sharing.</span><div><a href="/privacy" target="_blank" rel="noreferrer">Privacy</a><a href="/terms" target="_blank" rel="noreferrer">Terms</a><a href="/data-deletion" target="_blank" rel="noreferrer">Data & deletion</a></div></footer>;}
export function Empty({icon="film",title="A little quiet here",children}){return <div className="empty"><span className="empty-icon"><Icon name={icon} size={28}/></span><h3>{title}</h3><p>{children}</p></div>;}
export function Notice({message}){return message ? <div role="status" className={`notice ${message.type || "error"}`}><Icon name={message.type==="success"?"check":"clock"}/><span>{message.text || message}</span></div> : null;}
export function Stat({icon,label,value,note}){return <div className="stat"><div className="stat-top"><span>{label}</span><Icon name={icon}/></div><strong>{value}</strong><small>{note}</small></div>;}
export function LoginArt({admin=false}){return <aside className="login-art"><Brand/><div className="login-story"><span className="eyebrow">CREATE. COLLABORATE. SHARE.</span><h1>Your next story<br/>starts <em>here.</em></h1><p>{admin ? "A thoughtful space to review your team's work, publish with confidence, and see what resonates." : "You've made the story. Give it a home. Share your finished cut with the team and follow it from review to release."}</p><div className="story-art" aria-hidden="true"><div className="art-grid"/><div className="art-frame back"><span>THE FIRST IDEA</span><div className="art-sun"/><div className="art-hill"/></div><div className="art-frame front"><div className="frame-top"><span>YOUR NEXT STORY</span><Icon name="spark" size={15}/></div><div className="art-orbit"/><div className="art-play"><Icon name="play" size={24}/></div><div className="art-timeline"><i/><i/><i/><i/><i/></div></div><div className="art-label"><span className="tiny-check"><Icon name="check" size={12}/></span> A story, ready to share.</div></div></div><div className="login-art-bottom">A small team. A world of stories.<span>✦</span></div></aside>;}
