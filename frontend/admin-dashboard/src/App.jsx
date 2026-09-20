import React, {useEffect, useState, useRef} from "react";

import {Routes, Route, NavLink, useNavigate, useLocation, Navigate, Link} from "react-router-dom";

import {login, logout, isLoggedIn, listVideos, approveVideo, rejectVideo, publishVideo, previewUrl,

  listChannels, channelStats, channelAnalytics, startGoogleConnect, startMetaConnect,

  deleteVideo, disconnectChannel, resetPublish, API_BASE} from "./api";

import {Icon, Brand, LegalLinks, Empty, Notice, Stat, LoginArt} from "./ui";



const LABELS={pending:"In review",approved:"Approved",published:"Published",rejected:"Rejected",processing:"Processing",publishing:"Publishing",publish_unknown:"Needs attention"};

const TABS=["pending","approved","published","rejected","processing","publishing","publish_unknown"];

const number=value=>Number(value || 0).toLocaleString();

const dateLabel=value=>new Date(value.endsWith?.("Z")?value:`${value}Z`).toLocaleDateString(undefined,{month:"short",day:"numeric"});



function Shell({children}){

  const loc=useLocation(), navigate=useNavigate();

  if(!isLoggedIn()) return <Navigate to="/login" replace/>;

  const title=loc.pathname==="/channels"?"Channels":loc.pathname==="/analytics"?"Analytics":"Review queue";

  return <div className="workspace"><aside className="sidebar"><Brand/><div className="sidebar-label">WORKSPACE</div>

    <nav className="side-nav" aria-label="Main navigation">

      {[['/','grid','Review queue'],['/channels','link','Channels'],['/analytics','chart','Analytics']].map(([to,icon,label])=><NavLink key={to} end={to==='/'} to={to}><Icon name={icon}/>{label}<Icon name="arrow" size={13} className="nav-arrow"/></NavLink>)}

    </nav><div className="sidebar-note"><Icon name="spark"/><strong>A little care before every share.</strong>Great stories start with your team. You give them the final look.</div>

    <div className="sidebar-account"><span className="avatar">AD</span><div><strong>Admin workspace</strong><small>Review & publish</small></div><button title="Log out" aria-label="Log out" onClick={()=>{logout();navigate('/login');}}><Icon name="logout" size={16}/></button></div>

  </aside><header className="topbar"><div className="breadcrumb">Workspace<span>/</span><strong>{title}</strong></div><span className="workspace-label"><span className="dot"/>Admin workspace</span></header>

  <main className="layout">{children}</main><LegalLinks/></div>;

}



function LoginPage(){

  const [username,setUsername]=useState(''),[password,setPassword]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);

  const navigate=useNavigate();

  if(isLoggedIn()) return <Navigate to="/" replace/>;

  return <div className="login-page"><LoginArt admin/><main className="login-main"><div className="login-box"><span className="eyebrow">ADMIN WORKSPACE</span><h2>Welcome back.</h2><p className="lede">Your team's next great story is waiting.<br/>Sign in to take a look.</p>

  <form className="form" onSubmit={async e=>{e.preventDefault();setBusy(true);setError('');try{await login(username,password);navigate('/');}catch(err){setError(err.message);}finally{setBusy(false);}}}>

    <label className="field">Username<input autoComplete="username" placeholder="Enter your username" value={username} onChange={e=>setUsername(e.target.value)} required/></label>

    <label className="field">Password<input type="password" autoComplete="current-password" placeholder="Enter your password" value={password} onChange={e=>setPassword(e.target.value)} required/></label>

    <Notice message={error?{text:error}:null}/><button className="primary" disabled={busy}>{busy?<span className="spinner"/>:null}{busy?'Signing in…':'Sign in to your workspace'}<Icon name="arrow"/></button>

  </form><div className="login-lock"><Icon name="lock" size={12}/>A private workspace for your team.</div></div><LegalLinks/></main></div>;

}



function Preview({id}){

  const [url,setUrl]=useState(''),[error,setError]=useState('');

  useEffect(()=>{let active=true;previewUrl(id).then(u=>{if(active)setUrl(u);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[id]);

  return <div className="preview-wrap">{error?<p>{error}</p>:url?<video src={url} controls preload="metadata" aria-label="Submission video preview"/>:<p>Loading preview…</p>}</div>;

}



function ReviewQueue(){

  const [tab,setTab]=useState('pending'),[videos,setVideos]=useState([]),[loading,setLoading]=useState(true),[busyId,setBusyId]=useState(null),[message,setMessage]=useState(null),[search,setSearch]=useState('');

  const [audiences,setAudiences]=useState({}),[visibility,setVisibility]=useState({});

  const mounted=useRef(true);

  async function refresh(){try{const data=await listVideos();if(mounted.current)setVideos(data);}catch(e){if(mounted.current)setMessage({text:e.message});}finally{if(mounted.current)setLoading(false);}}

  useEffect(()=>{mounted.current=true;refresh();const timer=setInterval(refresh,15000);return()=>{mounted.current=false;clearInterval(timer);};},[]);

  useEffect(()=>{if(tab!=='processing')return;let stopped=false,running=false;const timer=setInterval(async()=>{if(running)return;running=true;try{const pending=await listVideos('processing');for(const v of pending){if(stopped)break;await publishVideo(v.id);}if(!stopped)refresh();}catch(e){if(!stopped)setMessage({text:e.message});}finally{running=false;}},10000);return()=>{stopped=true;clearInterval(timer);};},[tab]);

  async function act(fn,id,...args){setBusyId(id);setMessage(null);try{const result=await fn(id,...args);setMessage({type:'success',text:result.message || (result.status==='published'?'Video published. Find it in the Published tab.':`Submission ${result.status}.`)});if(result.status==='processing')setTab('processing');await refresh();}catch(e){setMessage({text:e.message});await refresh();}finally{setBusyId(null);}}

  const count=status=>videos.filter(v=>v.status===status).length;

  const filtered=videos.filter(v=>v.status===tab && `${v.title} ${v.uploader_name} ${v.channel?.display_name}`.toLowerCase().includes(search.toLowerCase()));

  return <><div className="page-heading"><div><span className="eyebrow">THE FINAL LOOK</span><h1>Good stories, ready for review.</h1><p className="lede">A little feedback. A final check. Then out into the world.</p></div><button className="button" onClick={refresh}><Icon name="refresh"/>Refresh queue</button></div>

    <div className="stats-grid"><Stat label="Awaiting review" icon="clock" value={loading?'—':count('pending')} note="Ready for your first look"/><Stat label="Ready to publish" icon="check" value={loading?'—':count('approved')} note="Approved and ready to go"/><Stat label="Published" icon="play" value={loading?'—':count('published')} note="Shared to your channels"/><Stat label="All submissions" icon="film" value={loading?'—':videos.length} note="Currently in your workspace"/></div>

    <section className="panel"><div className="panel-head"><div><h2>Your review queue</h2><p>Finished cuts from your creative team.</p></div><label className="search"><Icon name="search" size={15}/><input aria-label="Search submissions" placeholder="Search submissions…" value={search} onChange={e=>setSearch(e.target.value)}/></label></div>

    <div className="tabs" role="tablist" aria-label="Submission status">{TABS.map(status=><button role="tab" aria-selected={status===tab} key={status} className={status===tab?'active':''} onClick={()=>setTab(status)}>{LABELS[status]}<span className="tab-count">{count(status)}</span></button>)}</div>

    <Notice message={message}/>{tab==='processing'&&<p className="info-note"><Icon name="clock"/>Previously requested Reels finish automatically while this tab is open.</p>}

    {loading?<div className="loading"><span className="spinner"/> Loading your submissions…</div>:<div className="cards">{!filtered.length&&<Empty icon="check" title={search?'No matching stories':'You’re all caught up'}>{search?'Try another title, channel, or team member.':`There are no ${LABELS[tab].toLowerCase()} submissions here yet.`}</Empty>}

    {filtered.map(v=><article className="card" key={v.id}><Preview id={v.id}/><div className="card-detail"><span className={`badge platform-${v.channel?.platform}`}><Icon name="play" size={10}/>{v.channel?.platform==='youtube'?'YouTube':'Instagram'}</span><h3 className="card-title">{v.title}</h3><div className="card-meta">{v.channel?.display_name} · {v.genre}<br/>{v.uploader_name} · {dateLabel(v.created_at)}</div>{v.description&&<p className="card-desc">{v.description}</p>}<span className={`status status-${v.status}`}>{LABELS[v.status]}</span>{v.privacy_status&&<span className="card-meta"> · {v.privacy_status}</span>}{v.publish_error&&<Notice message={{text:v.publish_error}}/>}{v.published_url&&<p className="card-desc"><a href={v.published_url} target="_blank" rel="noreferrer">View on {v.channel?.platform==='youtube'?'YouTube':'Instagram'} ↗</a></p>}</div>

      <div className="actions">{tab==='pending'&&<>{v.channel?.platform==='youtube'&&<label>Audience<select value={audiences[v.id]??''} onChange={e=>setAudiences({...audiences,[v.id]:e.target.value})}><option value="">Choose audience</option><option value="no">Not made for kids</option><option value="yes">Made for kids</option></select></label>}<div className="action-pair"><button className="btn-approve" disabled={busyId===v.id||(v.channel?.platform==='youtube'&&!audiences[v.id])} onClick={()=>act(approveVideo,v.id,audiences[v.id]==='yes')}><Icon name="check" size={14}/>Approve</button><button className="btn-reject" disabled={busyId===v.id} onClick={()=>act(rejectVideo,v.id)}><Icon name="close" size={14}/>Reject</button></div></>}

      {['approved','processing'].includes(tab)&&<>{v.channel?.platform==='youtube'&&<label>Visibility<select value={visibility[v.id]||'private'} onChange={e=>setVisibility({...visibility,[v.id]:e.target.value})}><option value="private">Private</option><option value="unlisted">Unlisted</option><option value="public">Public</option></select></label>}<button className="btn-publish" disabled={busyId===v.id} onClick={()=>act(publishVideo,v.id,visibility[v.id]||'private')}><Icon name="upload" size={14}/>{busyId===v.id?'Publishing…':tab==='processing'?'Finish publishing':v.channel?.platform==='youtube'?`Publish ${visibility[v.id]||'private'}`:'Publish public Reel'}</button></>}

      {['publishing','publish_unknown'].includes(tab)&&<button className="button" disabled={busyId===v.id} onClick={()=>{if(window.confirm('Check the destination first. Confirm this video was NOT posted before allowing another upload.'))act(resetPublish,v.id);}}>Reset after checking channel</button>}

      {!['publishing','processing'].includes(tab)&&<button className="text-button" disabled={busyId===v.id} onClick={()=>{if(window.confirm('Delete this submission and stored video? Published platform posts remain unchanged.'))act(deleteVideo,v.id);}}>Delete app copy</button>}</div></article>)}

    </div>}<p className="info-note"><Icon name="lock"/>YouTube uploads default to Private. Public and Unlisted may be restricted until your API project passes its audit. Instagram Reels are public.</p></section></>;

}



function ChannelsPage(){

  const [channels,setChannels]=useState([]),[stats,setStats]=useState({}),[loading,setLoading]=useState(true),[busy,setBusy]=useState(''),[message,setMessage]=useState(()=>{const p=new URLSearchParams(location.search);return p.get('error')?{text:p.get('error')}:p.get('connected')?{type:'success',text:`Connected ${p.get('connected')}.`}:null;});

  async function refresh(){try{setChannels((await listChannels()).sort((a,b)=>a.display_name.localeCompare(b.display_name)));}catch(e){setMessage({text:e.message});}finally{setLoading(false);}}

  useEffect(()=>{refresh();},[]);

  async function connect(fn,name){setBusy(name);setMessage(null);try{await fn();}catch(e){setMessage({text:e.message});setBusy('');}}

  return <><div className="page-heading"><div><span className="eyebrow">YOUR STORY’S NEXT STOP</span><h1>Connected channels</h1><p className="lede">The places your team's stories call home.</p></div><button className="button" onClick={refresh}><Icon name="refresh"/>Refresh</button></div><Notice message={message}/>

  <div className="connect-banner"><div><h2>Make a new connection.</h2><p>Connect an account you manage. Your team can choose its name when submitting their next story.</p></div><div className="button-row"><button className="primary" disabled={!!busy} onClick={()=>connect(startGoogleConnect,'youtube')}><Icon name="play"/>{busy==='youtube'?'Connecting…':'Connect YouTube'}</button><button className="button" disabled={!!busy} onClick={()=>connect(startMetaConnect,'instagram')}><Icon name="link"/>{busy==='instagram'?'Connecting…':'Connect Instagram'}</button></div></div>

  {loading?<div className="loading">Loading channels…</div>:!channels.length?<section className="panel"><Empty icon="link" title="Your first connection starts here">Connect a channel to start receiving and publishing your team's videos.</Empty></section>:<div>{['youtube','instagram'].map(platform=><section key={platform} className="channel-section"><div className="panel-head"><h2>{platform==='youtube'?'YouTube channels':'Instagram accounts'}</h2><span className="badge">{channels.filter(c=>c.platform===platform).length} accounts</span></div><div className="channel-grid">{channels.filter(c=>c.platform===platform).map(c=><article key={c.id} className="channel-card"><div className="panel-head"><span className={`channel-icon platform-${c.platform}`}><Icon name={c.platform==='youtube'?'play':'link'}/></span><span className={`badge platform-${c.platform}`}>{c.platform==='youtube'?'YouTube':'Instagram'}</span></div><h3>{c.display_name}</h3><div className={`connect-status ${c.is_connected?'connected':''}`}><span className="dot"/>{c.is_connected?'Connected and ready':'Connection needed'}</div>{c.is_connected&&<><Link className="button" to={`/analytics?channel=${c.id}`}><Icon name="chart"/>View analytics</Link>{c.platform==='youtube'&&<button className="text-button" onClick={async()=>{try{const data=await channelStats(c.id);if(data.error)throw new Error(data.error);setStats({...stats,[c.id]:data});}catch(e){setMessage({text:e.message});}}}>Load channel totals</button>}{stats[c.id]&&<div className="stats">{Object.entries(stats[c.id]).map(([key,value])=><span key={key}>{key.replace(/([A-Z])/g,' $1')}: {number(value)}</span>)}</div>}</>}<div className="channel-bottom"><button className="text-button" onClick={async()=>{if(window.confirm('Disconnect this channel and delete its app data? Published posts will remain.')){try{const r=await disconnectChannel(c.id);setMessage({type:'success',text:r.message});refresh();}catch(e){setMessage({text:e.message});}}}}>Disconnect & delete app data</button></div></article>)}</div></section>)}</div>}

  <p className="info-note"><Icon name="lock"/>Each account is authorized separately. Reconnect accounts to grant the required Analytics / Insights permissions.</p></>;

}



function iso(d){return d.toISOString().slice(0,10);}

function defaultDates(days=28){const end=new Date();end.setUTCDate(end.getUTCDate()-1);const start=new Date(end);start.setUTCDate(start.getUTCDate()-days+1);return [iso(start),iso(end)];}

function ViewsChart({daily}){

  if(!daily.length)return <Empty icon="chart" title="No daily data yet">YouTube may take a few days to process recent activity.</Empty>;

  const peak=Math.max(...daily.map(d=>Number(d.views)),0), max=Math.max(peak,1), n=daily.length;

  const points=daily.map((d,i)=>`${30+(n===1?440:i/(n-1)*880)},${195-(Number(d.views)/max)*160}`).join(' ');

  return <><svg className="chart" viewBox="0 0 940 230" role="img" aria-label={`Daily YouTube views, maximum ${number(peak)} views`}><defs><linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#78a65e" stopOpacity=".2"/><stop offset="100%" stopColor="#78a65e" stopOpacity="0"/></linearGradient></defs>{[35,75,115,155,195].map(y=><line key={y} x1="30" y1={y} x2="910" y2={y} stroke="#e9eee3" strokeDasharray="4 5"/>)}<polygon points={`30,195 ${points} 910,195`} fill="url(#chart-fill)"/><polyline points={points} fill="none" stroke="#5e8b4a" strokeWidth="3" strokeLinejoin="round"/>{daily.map((d,i)=><circle key={d.day} cx={30+(n===1?440:i/(n-1)*880)} cy={195-(Number(d.views)/max)*160} r="3" fill="#5e8b4a"><title>{d.day}: {number(d.views)} views</title></circle>)}</svg><div className="chart-labels"><span>{daily[0].day}</span><span>Peak: {number(peak)} views</span><span>{daily.at(-1).day}</span></div><details className="chart-note"><summary>View daily data</summary><div className="table-wrap"><table><thead><tr><th>Date</th><th>Views</th><th>Watch time (min)</th></tr></thead><tbody>{daily.map(d=><tr key={d.day}><td>{d.day}</td><td>{number(d.views)}</td><td>{number(d.estimatedMinutesWatched)}</td></tr>)}</tbody></table></div></details></>;

}



function InstagramReport({report}){

  const metric=(name)=>report.summary?.[name] == null ? '—' : number(report.summary[name]);

  return <><div className="stats-grid"><Stat icon="play" label="Views" value={metric('views')} note="During the selected period"/><Stat icon="users" label="Accounts reached" value={metric('reach')} note="Unique accounts"/><Stat icon="users" label="Accounts engaged" value={metric('accounts_engaged')} note="Accounts that interacted"/><Stat icon="chart" label="Total interactions" value={metric('total_interactions')} note="Reported by Instagram"/></div><section className="panel"><div className="panel-head"><div><h2>Daily reach</h2><p>{report.channel.name} · {report.start_date} to {report.end_date}</p></div></div>{report.daily.length?<div className="table-wrap"><table><thead><tr><th>PERIOD END</th><th>ACCOUNTS REACHED</th></tr></thead><tbody>{report.daily.map((d,i)=><tr key={i}><td>{d.day}</td><td>{d.reach==null?'—':number(d.reach)}</td></tr>)}</tbody></table></div>:<Empty icon="chart" title="No daily reach data">Instagram may not return metrics for recent activity or small accounts.</Empty>}</section>{report.warnings?.map(w=><p className="info-note" key={w}>{w}</p>)}<p className="info-note">Insights come directly from Instagram and may be delayed. Daily reach is not added together because the same account can appear on several days.</p></>;

}



function AnalyticsPage(){

  const [channels,setChannels]=useState([]),[channel,setChannel]=useState(new URLSearchParams(location.search).get('channel')||''),[dates,setDates]=useState(()=>defaultDates()),[report,setReport]=useState(null),[busy,setBusy]=useState(false),[loading,setLoading]=useState(true),[message,setMessage]=useState(null);

  useEffect(()=>{let active=true;listChannels().then(data=>{if(!active)return;const connected=data.filter(c=>c.is_connected);setChannels(connected);setChannel(current=>connected.some(c=>String(c.id)===current)?current:String(connected[0]?.id||''));}).catch(e=>{if(active)setMessage({text:e.message});}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[]);

  async function load(e){e.preventDefault();setBusy(true);setMessage(null);setReport(null);try{setReport(await channelAnalytics(channel,...dates));}catch(e){setMessage({text:e.message});}finally{setBusy(false);}}

  const summary=report?.summary;

  const instagram=channels.find(c=>String(c.id)===channel)?.platform==='instagram';

  return <><div className="page-heading"><div><span className="eyebrow">BEYOND THE PUBLISH BUTTON</span><h1>See how your stories grow.</h1><p className="lede">Channel performance from YouTube Analytics and Instagram Insights.</p></div><span className={`badge platform-${instagram?'instagram':'youtube'}`}><Icon name="chart" size={12}/>{instagram?'Instagram Insights':'YouTube Analytics'}</span></div>

  <form className="panel analytics-controls" onSubmit={load}><label className="field">Channel / account<select required disabled={busy||loading} value={channel} onChange={e=>{setChannel(e.target.value);setReport(null);setMessage(null);}}><option value="">Select a channel</option>{['youtube','instagram'].map(p=><optgroup key={p} label={p==='youtube'?'YouTube':'Instagram'}>{channels.filter(c=>c.platform===p).map(c=><option key={c.id} value={c.id}>{c.display_name}</option>)}</optgroup>)}</select></label><label className="field">From<input type="date" required disabled={busy} max={dates[1]} value={dates[0]} onChange={e=>{setDates([e.target.value,dates[1]]);setReport(null);}}/></label><label className="field">To<input type="date" required disabled={busy} min={dates[0]} max={iso(new Date())} value={dates[1]} onChange={e=>{setDates([dates[0],e.target.value]);setReport(null);}}/></label><button className="primary" disabled={!channel||busy||loading}>{busy?<span className="spinner"/>:<Icon name="chart"/>}{busy?'Loading report…':'Load report'}</button></form>{instagram&&<p className="info-note">Instagram: up to 30 days within the last 90 days. Missing metrics stay unavailable.</p>}

  <Notice message={message}/>{message&&<p className="info-note"><Link to="/channels">Go to Channels to reconnect →</Link></p>}

  {loading?<div className="loading">Loading your connected accounts…</div>:!channels.length?<section className="panel"><Empty icon="chart" title="Connect an account first">Once connected, your performance reports will appear here.</Empty><Link className="button" to="/channels">Connect a channel<Icon name="arrow"/></Link></section>:!report&&!busy&&!message?<section className="panel"><Empty icon="chart" title="A clearer picture of your audience">Choose a channel and dates, then load your report. Nothing is estimated or filled with demo data.</Empty></section>:null}

  {report?.platform==='instagram'&&<InstagramReport report={report}/>}

  {report&&report.platform!=='instagram'&&<><div className="stats-grid"><Stat icon="play" label="Views" value={summary?number(summary.views):'—'} note="During the selected period"/><Stat icon="clock" label="Watch time (hours)" value={summary?(Number(summary.estimatedMinutesWatched)/60).toLocaleString(undefined,{maximumFractionDigits:1}):'—'} note="Estimated by YouTube"/><Stat icon="film" label="Average view duration" value={summary?`${Math.floor(summary.averageViewDuration/60)}:${String(Math.floor(summary.averageViewDuration%60)).padStart(2,'0')}`:'—'} note="Minutes : seconds"/><Stat icon="users" label="Net subscribers" value={summary?number(summary.subscribersGained-summary.subscribersLost):'—'} note={summary?`${number(summary.subscribersGained)} gained · ${number(summary.subscribersLost)} lost`:'No report data'}/></div><section className="panel chart-panel"><div className="panel-head"><div><h2>Views over time</h2><p>{report.channel.name} · {report.start_date} to {report.end_date}</p></div><span className="badge status-approved">Daily views</span></div><ViewsChart daily={report.daily}/></section>

    <section className="panel"><div className="panel-head"><div><h2>Your top stories</h2><p>Up to 10 videos, ranked by views in this period.</p></div></div>{!report.top_videos.length?<Empty icon="film" title="No video data in this period">Try a wider date range after YouTube processes your activity.</Empty>:<div className="table-wrap"><table><thead><tr><th>VIDEO</th><th>VIEWS</th><th>WATCH TIME (MIN)</th><th>AVG. DURATION (SEC)</th></tr></thead><tbody>{report.top_videos.map((v,i)=><tr key={v.video}><td><span className="rank">{String(i+1).padStart(2,'0')}</span><a href={`https://www.youtube.com/watch?v=${encodeURIComponent(v.video)}`} target="_blank" rel="noreferrer">{v.title||v.video} ↗</a></td><td>{number(v.views)}</td><td>{number(v.estimatedMinutesWatched)}</td><td>{number(v.averageViewDuration)}</td></tr>)}</tbody></table></div>}</section><p className="info-note"><Icon name="clock"/>YouTube Analytics is not real time. {report.last_reported_day?`Last reported day: ${report.last_reported_day}.`:'No daily data returned.'} Recent days may be incomplete. Reports use YouTube’s reporting time zone.</p></>}

  </>;

}



export default function App(){return <Routes><Route path="/login" element={<LoginPage/>}/><Route path="/" element={<Shell><ReviewQueue/></Shell>}/><Route path="/channels" element={<Shell><ChannelsPage/></Shell>}/><Route path="/analytics" element={<Shell><AnalyticsPage/></Shell>}/></Routes>;}
