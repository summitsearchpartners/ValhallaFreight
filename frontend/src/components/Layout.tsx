import {NavLink} from 'react-router-dom';
import {LayoutDashboard, Calculator, Truck, Users, Building2, SlidersHorizontal, BarChart3, FileSearch, ReceiptText, ShieldCheck, Bell, Search, ChevronDown, Zap} from 'lucide-react';
import type {ReactNode} from 'react';
const nav=[
  ['Overview',[[LayoutDashboard,'Command Center','/'],[Calculator,'Quote Studio','/quotes'],[Truck,'Shipments','/shipments']]],
  ['Network',[[Users,'Customers','/customers'],[Building2,'Carriers','/carriers'],[SlidersHorizontal,'Pricing Engine','/pricing']]],
  ['Intelligence',[[BarChart3,'Analytics','/analytics'],[FileSearch,'Prospect Analysis','/prospects'],[ReceiptText,'Billing & Audit','/billing']]],
];
export default function Layout({children}:{children:ReactNode}){return <div className="shell"><aside className="sidebar"><div className="brand"><div className="brandmark"><Zap size={22}/></div><div><strong>FreightForge</strong><small>Transportation Intelligence</small></div></div><nav>{nav.map(([section,items]:any)=><div className="navsection" key={section}><span>{section}</span>{items.map(([Icon,label,path]:any)=><NavLink key={path} to={path} end={path==='/'}><Icon size={18}/><b>{label}</b></NavLink>)}</div>)}</nav><div className="sidefoot"><ShieldCheck size={17}/><div><b>System healthy</b><span>All services operational</span></div></div></aside><main><header><div className="globalsearch"><Search size={17}/><input placeholder="Search shipments, PROs, customers, quotes..."/><kbd>⌘ K</kbd></div><div className="headright"><button className="iconbtn"><Bell size={19}/><i/></button><div className="profile"><div className="avatar">TM</div><div><b>Thom Monterville Jr.</b><span>Administrator</span></div><ChevronDown size={15}/></div></div></header><div className="content">{children}</div></main></div>}
