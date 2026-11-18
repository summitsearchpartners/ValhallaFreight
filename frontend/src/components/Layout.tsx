import useSafeLoadEvents from '../features/safeLoad/useSafeLoadEvents';
import MusePoweredBy from './MusePoweredBy';
import {canOpenWorkspacePage,isBroker,isManufacturer,roleLabels} from '../shared/workspaceAccess';
import {OperationalStatus} from './OperationalStatus';
import {ManufacturerSupportBanner} from '../features/portal/ManufacturerSupportWindow';
import {useWorkspace} from '../context/WorkspaceContext';
import {formatDateTime as displayDateTime} from '../shared/display/preferences';
import HeaderClock from './HeaderClock';
import {NavLink,useLocation,useNavigate} from 'react-router-dom';
import {LayoutDashboard, Calculator, Truck, Users, Building2, SlidersHorizontal, BarChart3, FileSearch, ReceiptText, ShieldCheck, Bell, Search, ChevronDown, ChevronLeft, ChevronRight, LogOut, Command, CircleDollarSign, PackageSearch, Settings, UserRound, CheckCheck, RadioTower, MapPinned, WalletCards, ShieldAlert, BrainCircuit, PlugZap, Globe2, Workflow, CalendarDays} from 'lucide-react';
import {useEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {useAuth} from '../context/AuthContext';
import {api} from '../services/api';

const nav=[
  ['Operations',[[LayoutDashboard,'Command Center','/'],[Calculator,'Quote Studio','/quotes'],[Truck,'Truckload Command','/truckload'],[ShieldCheck,'Safe Load','/safe-load'],[Truck,'Shipments','/shipments'],[MapPinned,'Visibility Center','/visibility'],[CalendarDays,'Freight Planner','/planner'],[Workflow,'Automation Center','/automation']]],
  ['Network',[[Users,'Customers','/customers'],[Building2,'Carrier 360','/carriers'],[RadioTower,'Capacity Center','/capacity'],[SlidersHorizontal,'Pricing Engine','/pricing']]],
  ['Finance & Risk',[[WalletCards,'Finance Center','/finance'],[ShieldAlert,'Claims Center','/claims']]],
  ['Intelligence',[[BrainCircuit,'Valhalla Intelligence','/intelligence'],[BarChart3,'Analytics','/analytics'],[FileSearch,'Prospect Analysis','/prospects']]],
  ['Administration',[[Building2,'Muse Portal','/muse'],[Users,'Users & Company Access','/admin/users'],[ShieldCheck,'Portal Access','/admin/portal-access'],[PlugZap,'Integration Hub','/integrations'],[Globe2,'Customer Portal','/portal-admin']]],
] as const;

const searchItems=[
 {label:'Truckload Command',detail:'FTL order entry, carrier bids and dispatch',path:'/truckload',icon:Truck},
 {label:'Safe Load',detail:'Warehouse driver and VIN verification',path:'/safe-load',icon:ShieldCheck},
 {label:'Muse Portal',detail:'Muse manufacturer applications, rates and bookings',path:'/muse',icon:Building2},
 {label:'Portal Access',detail:'Verified super-user access to customer portals',path:'/admin/portal-access',icon:ShieldCheck},
 {label:'Users & Company Access',detail:'Roles, company assignments and user activity',path:'/admin/users',icon:Users},
  {label:'Command Center',detail:'Operations overview',path:'/',icon:LayoutDashboard},{label:'Quote Studio',detail:'Create and compare rates',path:'/quotes',icon:Calculator},{label:'Shipments',detail:'Shipment control tower',path:'/shipments',icon:PackageSearch},{label:'Visibility Center',detail:'Tracking and ETA exceptions',path:'/visibility',icon:MapPinned},{label:'Freight Planner',detail:'Inbound and outbound location calendar',path:'/planner',icon:CalendarDays},{label:'Automation Center',detail:'Six pillars of LTL automation',path:'/automation',icon:Workflow},{label:'Customers',detail:'Customer 360',path:'/customers',icon:Users},{label:'Carrier 360',detail:'Carrier compliance and performance',path:'/carriers',icon:Building2},{label:'Capacity Center',detail:'Load boards and digital freight matching',path:'/capacity',icon:RadioTower},{label:'Pricing Engine',detail:'Tariffs, contracts and margin rules',path:'/pricing',icon:CircleDollarSign},{label:'Finance Center',detail:'Freight audit, AR and AP',path:'/finance',icon:WalletCards},{label:'Claims Center',detail:'Cargo claims and insurance',path:'/claims',icon:ShieldAlert},{label:'Valhalla Intelligence',detail:'Operational intelligence and exceptions',path:'/intelligence',icon:BrainCircuit},{label:'Analytics',detail:'Network analytics',path:'/analytics',icon:BarChart3},{label:'Prospect Analysis',detail:'Analyze prospect freight history',path:'/prospects',icon:FileSearch},{label:'Integration Hub',detail:'Provider adapters and health',path:'/integrations',icon:PlugZap},{label:'Customer Portal',detail:'Branded self-service workspace',path:'/portal-admin',icon:Globe2},
];

type LiveNotification={notification_type?:string;can_authorize_release?:boolean;key:string;source:'finance'|'ops';id:number;title:string;body:string;severity:string;status:string;created_at:string;shipment_id?:number;target_path?:string};


export default function Layout({children}:{children:ReactNode}){
  const {user,logout}=useAuth();useSafeLoadEvents(user?.id);
  const navigate=useNavigate();
  const location=useLocation();
  const wideCustomerWorkspace=/^\/customers\/\d+/.test(location.pathname);
  const wideQuoteWorkspace=location.pathname==='/quotes';
  const wideShipmentWorkspace=/^\/shipments\/\d+/.test(location.pathname);
  const widePlatformWorkspace=['/carriers','/capacity','/visibility','/planner','/automation','/finance','/claims','/intelligence','/integrations','/portal-admin'].some(p=>location.pathname.startsWith(p));
  const [collapsed,setCollapsed]=useState(false);
  const [searchOpen,setSearchOpen]=useState(false);
  const [search,setSearch]=useState('');
  const [noticeOpen,setNoticeOpen]=useState(false);
  const [profileOpen,setProfileOpen]=useState(false);
  const {workspace}=useWorkspace();
  const manufacturer=isManufacturer(user?.role);
  const [notifications,setNotifications]=useState<LiveNotification[]>([]);
  const [financeExceptionCount,setFinanceExceptionCount]=useState(0);
  const unread=notifications.filter(n=>n.status==='unread').length;
  const searchRef=useRef<HTMLInputElement>(null);
  const initials=(user?.full_name||'VF').split(' ').slice(0,2).map((x:string)=>x[0]).join('').toUpperCase();
  const allowed=(path:string)=>canOpenWorkspacePage(path,user?.role,workspace.show_pricing,user?.muse_partner_access);
  const filtered=useMemo(()=>searchItems.filter(x=>allowed(x.path)).filter(x=>(x.label+' '+x.detail).toLowerCase().includes(search.toLowerCase())),[search,manufacturer,workspace.show_pricing,user?.role,user?.muse_partner_access]);

  useEffect(()=>{
    const handler=(e:KeyboardEvent)=>{
      if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();setSearchOpen(true);setTimeout(()=>searchRef.current?.focus(),50)}
      if(e.key==='Escape'){setSearchOpen(false);setNoticeOpen(false);setProfileOpen(false)}
    };
    window.addEventListener('keydown',handler);return()=>window.removeEventListener('keydown',handler);
  },[]);

  useEffect(()=>{
    let active=true;
    const load=()=>Promise.all([
      api<LiveNotification[]>('/notifications?audience=internal'),
      api<any[]>('/finance/audit'),
    ]).then(([noticeRows,auditRows])=>{
      if(!active)return;
      setNotifications(noticeRows);
      setFinanceExceptionCount(auditRows.filter((row:any)=>row.status==='exception').length);
    }).catch(()=>{});
    const refresh=()=>load();
    load(); const timer=window.setInterval(load,30000);
    window.addEventListener('finance-audit-updated',refresh);
    window.addEventListener('operational-notification-updated',refresh);
    return()=>{active=false;window.clearInterval(timer);window.removeEventListener('finance-audit-updated',refresh);window.removeEventListener('operational-notification-updated',refresh)};
  },[]);

  async function markAllNotificationsRead(){
    const unreadRows=notifications.filter(n=>n.status==='unread');
    await Promise.all(unreadRows.map(n=>api(`/notifications/${n.source}/${n.id}/read`,{method:'POST'}).catch(()=>null)));
    setNotifications(rows=>rows.map(n=>({...n,status:'read'})));
  }
  async function openNotification(n:LiveNotification){
    if(n.status==='unread')await api(`/notifications/${n.source}/${n.id}/read`,{method:'POST'}).catch(()=>null);
    setNotifications(rows=>rows.map(x=>x.key===n.key?{...x,status:'read'}:x));
    setNoticeOpen(false); navigate(n.target_path||(n.shipment_id?`/shipments/${n.shipment_id}`:'/finance'));
  }

  function go(path:string){navigate(path);setSearchOpen(false);setSearch('')}

  return <div className={`shell ${collapsed?'shellCollapsed':''}`}>
    <aside className="sidebar">
      <div className="brand">
        <div className="brandLogoFrame"><img className="brandLogo" src={workspace.logo_data||"/valhalla-freight-logo.png"} alt={`${workspace.company_name||"Valhalla Freight"} logo`}/></div>
        <div className="brandWords"><strong>{workspace.company_name||(manufacturer?"Manufacturer Workspace":isBroker(user?.role)?"Broker Workspace":"Valhalla Freight")}</strong><small>Transportation Operating System</small></div>
        <button className="sideCollapse" onClick={()=>setCollapsed(v=>!v)} title={collapsed?'Expand navigation':'Collapse navigation'}>{collapsed?<ChevronRight size={16}/>:<ChevronLeft size={16}/>}</button>
      </div>
      <nav>{nav.map(([section,items])=>items.some(([, ,path])=>allowed(path))&&<div className="navsection" key={section}><span>{section}</span>{items.filter(([, ,path])=>allowed(path)).map(([Icon,label,path])=>{const financeAlert=path==='/finance'&&financeExceptionCount>0;return <NavLink key={path} to={path} end={path==='/' } title={collapsed?`${label}${financeAlert?` · ${financeExceptionCount} margin exception${financeExceptionCount===1?'':'s'}`:''}`:undefined}><Icon size={18}/><b>{label}</b>{financeAlert&&<span className="navAlertBadge" aria-label={`${financeExceptionCount} margin protection exceptions`}>{financeExceptionCount>99?'99+':financeExceptionCount}</span>}</NavLink>})}</div>)}</nav>
      <div className="sidebarFooter">
       <div className="manufacturerPowered"><img src="/valhalla-freight-logo.png" alt="Valhalla Freight"/><span>Platform by<br/><b>Valhalla Freight</b></span></div>
       <OperationalStatus/>
       <MusePoweredBy/>
       <div className="sideVersion">VF TOS · v0.19.16</div>
      </div>
    </aside>

    <main><ManufacturerSupportBanner/>
      <header>
        <button className="globalsearch" onClick={()=>{setSearchOpen(true);setTimeout(()=>searchRef.current?.focus(),50)}}>
          <Search size={17}/><span>Search shipments, PROs, customers, quotes...</span><kbd>Ctrl K</kbd>
        </button>
        <div className="headright"><HeaderClock/>
          <div className="headerStatus"><i/>Operations workspace</div>
          <div className="dropdownWrap">
            <button className={`iconbtn ${noticeOpen?'active':''}`} onClick={()=>{setNoticeOpen(v=>!v);setProfileOpen(false)}} aria-label="Notifications"><Bell size={19}/>{unread>0&&<span className="noticeCount">{unread}</span>}</button>
            {noticeOpen&&<div className="dropdown notificationPanel">
              <div className="dropHead"><div><b>Notifications</b><span>{unread} unread</span></div><button onClick={markAllNotificationsRead}><CheckCheck size={14}/>Mark all read</button></div>
              <div className="noticeList">{notifications.length?notifications.map(n=><div key={n.key} className="noticeItemGroup"><button className="noticeItem" onClick={()=>openNotification(n)}><i className={n.severity||'warning'}/><div><b>{n.title}</b><p>{n.body}</p><span>{displayDateTime(n.created_at)}</span></div></button>{n.can_authorize_release&&n.notification_type==='safe_load'&&['admin','broker','broker_admin'].includes(user?.role||'')&&<button className="noticeResolveAction" onClick={()=>{setNoticeOpen(false);navigate(`/safe-load?shipment=${n.shipment_id}&resolve=1`)}}>Review rejection & authorize release →</button>}</div>):<div className="commandEmpty">No active notifications.</div>}</div>
              <button className="dropFooter" onClick={()=>{setNoticeOpen(false);navigate('/finance')}}>View Finance Center</button>
            </div>}
          </div>
          <div className="dropdownWrap">
            <button className="profile" onClick={()=>{setProfileOpen(v=>!v);setNoticeOpen(false)}}>
              {workspace.logo_data?<span className="headerCompanyLogo"><img src={workspace.logo_data} alt={`${workspace.company_name||"Company"} logo`}/></span>:<div className="avatar">{initials}</div>}<div className="profileWords"><b>{user?.full_name}</b><span>{roleLabels[user?.actual_role||user?.role||'']||user?.role}</span></div><ChevronDown size={15}/>
            </button>
            {profileOpen&&<div className="dropdown profileMenu">
              <div className="profileMenuHead"><div className="avatar lg">{initials}</div><div><b>{user?.full_name}</b><span>{user?.email}</span></div></div>
              <button onClick={()=>{navigate("/my-profile");setProfileOpen(false)}}><UserRound size={15}/><div><b>My profile</b><span>Account and personal settings</span></div></button>
              <button onClick={()=>{navigate("/system-settings");setProfileOpen(false)}}><Settings size={15}/><div><b>System settings</b><span>Users, roles and integrations</span></div></button>
              <button className="danger" onClick={logout}><LogOut size={15}/><div><b>{user?.actual_role==='admin'?'End support session':'Sign out'}</b><span>{user?.actual_role==='admin'?'Keep your main admin window signed in':'End this Valhalla Freight session'}</span></div></button>
            </div>}
          </div>
        </div>
      </header>
      <div className={`content ${wideCustomerWorkspace?'contentWide customerWorkspaceContent':''} ${wideQuoteWorkspace?'contentWide quoteWorkspaceContent':''} ${wideShipmentWorkspace?'contentWide shipmentWorkspaceContent':''} ${widePlatformWorkspace?'contentWide platformWorkspaceContent':''}`}>{children}</div>
    </main>

    {searchOpen&&<div className="commandOverlay" onMouseDown={e=>{if(e.currentTarget===e.target)setSearchOpen(false)}}>
      <div className="commandPalette">
        <div className="commandInput"><Search size={19}/><input ref={searchRef} value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search Valhalla Freight..."/><button onClick={()=>setSearchOpen(false)}>ESC</button></div>
        <div className="commandLabel"><Command size={12}/> Quick navigation</div>
        <div className="commandResults">{filtered.length?filtered.map(({label,detail,path,icon:Icon})=><button key={path} onClick={()=>go(path)}><span className="commandIcon"><Icon size={17}/></span><div><b>{label}</b><small>{detail}</small></div><span>↵</span></button>):<div className="commandEmpty">No Valhalla Freight results found.</div>}</div>
        <div className="commandHint"><span><kbd>↑</kbd><kbd>↓</kbd> Navigate</span><span><kbd>Enter</kbd> Open</span><span><kbd>Esc</kbd> Close</span></div>
      </div>
    </div>}
  </div>
}
