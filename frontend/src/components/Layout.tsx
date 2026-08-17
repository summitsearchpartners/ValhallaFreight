import {NavLink,useLocation,useNavigate} from 'react-router-dom';
import {LayoutDashboard, Calculator, Truck, Users, Building2, SlidersHorizontal, BarChart3, FileSearch, ReceiptText, ShieldCheck, Bell, Search, ChevronDown, ChevronLeft, ChevronRight, LogOut, Command, CircleDollarSign, MapPin, PackageSearch, Settings, UserRound, CheckCheck} from 'lucide-react';
import {useEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {useAuth} from '../context/AuthContext';

const nav=[
  ['Operations',[[LayoutDashboard,'Command Center','/'],[Calculator,'Quote Studio','/quotes'],[Truck,'Shipments','/shipments']]],
  ['Network',[[Users,'Customers','/customers'],[Building2,'Carriers','/carriers'],[SlidersHorizontal,'Pricing Engine','/pricing']]],
  ['Intelligence',[[BarChart3,'Analytics','/analytics'],[FileSearch,'Prospect Analysis','/prospects'],[ReceiptText,'Billing & Audit','/billing']]],
] as const;

const searchItems=[
  {label:'Command Center',detail:'Operations overview',path:'/',icon:LayoutDashboard},
  {label:'Quote Studio',detail:'Create and compare LTL rates',path:'/quotes',icon:Calculator},
  {label:'Shipments',detail:'Track active and completed freight',path:'/shipments',icon:PackageSearch},
  {label:'Customers',detail:'Accounts, locations and contacts',path:'/customers',icon:Users},
  {label:'Carriers',detail:'Carrier network and performance',path:'/carriers',icon:Building2},
  {label:'Pricing Engine',detail:'Markup, margin and lane rules',path:'/pricing',icon:CircleDollarSign},
  {label:'Analytics',detail:'Network and customer intelligence',path:'/analytics',icon:BarChart3},
  {label:'Prospect Analysis',detail:'Analyze prospect freight history',path:'/prospects',icon:FileSearch},
  {label:'Billing & Audit',detail:'Invoice and carrier cost controls',path:'/billing',icon:ReceiptText},
];

const notifications=[
  {title:'Margin exception detected',body:'Shipment VFH-260817-0142 is $96 above expected carrier cost.',time:'4m',tone:'warning'},
  {title:'Shipment delivered',body:'VFH-260816-0127 delivered in Denver, CO. POD is ready.',time:'18m',tone:'success'},
  {title:'Quote expiring soon',body:'Quote VFQ-260817-0088 expires in 42 minutes.',time:'31m',tone:'info'},
];

export default function Layout({children}:{children:ReactNode}){
  const {user,logout}=useAuth();
  const navigate=useNavigate();
  const location=useLocation();
  const wideCustomerWorkspace=/^\/customers\/\d+/.test(location.pathname);
  const [collapsed,setCollapsed]=useState(false);
  const [searchOpen,setSearchOpen]=useState(false);
  const [search,setSearch]=useState('');
  const [noticeOpen,setNoticeOpen]=useState(false);
  const [profileOpen,setProfileOpen]=useState(false);
  const [unread,setUnread]=useState(notifications.length);
  const searchRef=useRef<HTMLInputElement>(null);
  const initials=(user?.full_name||'VF').split(' ').slice(0,2).map((x:string)=>x[0]).join('').toUpperCase();
  const filtered=useMemo(()=>searchItems.filter(x=>(x.label+' '+x.detail).toLowerCase().includes(search.toLowerCase())),[search]);

  useEffect(()=>{
    const handler=(e:KeyboardEvent)=>{
      if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();setSearchOpen(true);setTimeout(()=>searchRef.current?.focus(),50)}
      if(e.key==='Escape'){setSearchOpen(false);setNoticeOpen(false);setProfileOpen(false)}
    };
    window.addEventListener('keydown',handler);return()=>window.removeEventListener('keydown',handler);
  },[]);

  function go(path:string){navigate(path);setSearchOpen(false);setSearch('')}

  return <div className={`shell ${collapsed?'shellCollapsed':''}`}>
    <aside className="sidebar">
      <div className="brand">
        <img className="brandLogo" src="/valhalla-freight-logo.png" alt="Valhalla Freight"/>
        <div className="brandWords"><strong>Valhalla Freight</strong><small>Transportation Management System</small></div>
        <button className="sideCollapse" onClick={()=>setCollapsed(v=>!v)} title={collapsed?'Expand navigation':'Collapse navigation'}>{collapsed?<ChevronRight size={16}/>:<ChevronLeft size={16}/>}</button>
      </div>
      <nav>{nav.map(([section,items])=><div className="navsection" key={section}><span>{section}</span>{items.map(([Icon,label,path])=><NavLink key={path} to={path} end={path==='/' } title={collapsed?label:undefined}><Icon size={18}/><b>{label}</b></NavLink>)}</div>)}</nav>
      <div className="sidefoot"><ShieldCheck size={17}/><div><b>System healthy</b><span>All services operational</span></div></div>
      <div className="sideVersion">VF TMS · v0.4.3</div>
    </aside>

    <main>
      <header>
        <button className="globalsearch" onClick={()=>{setSearchOpen(true);setTimeout(()=>searchRef.current?.focus(),50)}}>
          <Search size={17}/><span>Search shipments, PROs, customers, quotes...</span><kbd>Ctrl K</kbd>
        </button>
        <div className="headright">
          <div className="headerStatus"><i/>Live operations</div>
          <div className="dropdownWrap">
            <button className={`iconbtn ${noticeOpen?'active':''}`} onClick={()=>{setNoticeOpen(v=>!v);setProfileOpen(false)}} aria-label="Notifications"><Bell size={19}/>{unread>0&&<span className="noticeCount">{unread}</span>}</button>
            {noticeOpen&&<div className="dropdown notificationPanel">
              <div className="dropHead"><div><b>Notifications</b><span>{unread} unread</span></div><button onClick={()=>setUnread(0)}><CheckCheck size={14}/>Mark all read</button></div>
              <div className="noticeList">{notifications.map((n,i)=><button className="noticeItem" key={i} onClick={()=>setUnread(Math.max(0,unread-1))}><i className={n.tone}/><div><b>{n.title}</b><p>{n.body}</p><span>{n.time} ago</span></div></button>)}</div>
              <button className="dropFooter">View notification center</button>
            </div>}
          </div>
          <div className="dropdownWrap">
            <button className="profile" onClick={()=>{setProfileOpen(v=>!v);setNoticeOpen(false)}}>
              <div className="avatar">{initials}</div><div className="profileWords"><b>{user?.full_name}</b><span>{user?.role==='admin'?'Administrator':user?.role}</span></div><ChevronDown size={15}/>
            </button>
            {profileOpen&&<div className="dropdown profileMenu">
              <div className="profileMenuHead"><div className="avatar lg">{initials}</div><div><b>{user?.full_name}</b><span>{user?.email}</span></div></div>
              <button><UserRound size={15}/><div><b>My profile</b><span>Account and personal settings</span></div></button>
              <button><Settings size={15}/><div><b>System settings</b><span>Users, roles and integrations</span></div></button>
              <button className="danger" onClick={logout}><LogOut size={15}/><div><b>Sign out</b><span>End this Valhalla Freight session</span></div></button>
            </div>}
          </div>
        </div>
      </header>
      <div className={`content ${wideCustomerWorkspace?'contentWide customerWorkspaceContent':''}`}>{children}</div>
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
