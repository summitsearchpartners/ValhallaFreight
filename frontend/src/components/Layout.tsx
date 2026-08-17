import {NavLink} from 'react-router-dom';
import {LayoutDashboard, Calculator, Truck, Users, Building2, SlidersHorizontal, BarChart3, FileSearch, ReceiptText, ShieldCheck, Bell, Search, ChevronDown, LogOut} from 'lucide-react';
import type {ReactNode} from 'react';
import {useAuth} from '../context/AuthContext';
const nav=[
  ['Overview',[[LayoutDashboard,'Command Center','/'],[Calculator,'Quote Studio','/quotes'],[Truck,'Shipments','/shipments']]],
  ['Network',[[Users,'Customers','/customers'],[Building2,'Carriers','/carriers'],[SlidersHorizontal,'Pricing Engine','/pricing']]],
  ['Intelligence',[[BarChart3,'Analytics','/analytics'],[FileSearch,'Prospect Analysis','/prospects'],[ReceiptText,'Billing & Audit','/billing']]],
];
export default function Layout({children}:{children:ReactNode}){
  const {user,logout}=useAuth();
  const initials=(user?.full_name||'VF').split(' ').slice(0,2).map(x=>x[0]).join('').toUpperCase();
  return <div className="shell"><aside className="sidebar"><div className="brand"><img className="brandLogo" src="/valhalla-freight-logo.png" alt="Valhalla Freight"/><div><strong>Valhalla Freight</strong><small>Transportation Management System</small></div></div><nav>{nav.map(([section,items]:any)=><div className="navsection" key={section}><span>{section}</span>{items.map(([Icon,label,path]:any)=><NavLink key={path} to={path} end={path==='/'}><Icon size={18}/><b>{label}</b></NavLink>)}</div>)}</nav><div className="sidefoot"><ShieldCheck size={17}/><div><b>System healthy</b><span>All services operational</span></div></div></aside><main><header><div className="globalsearch"><Search size={17}/><input placeholder="Search shipments, PROs, customers, quotes..."/><kbd>⌘ K</kbd></div><div className="headright"><button className="iconbtn"><Bell size={19}/><i/></button><div className="profile"><div className="avatar">{initials}</div><div><b>{user?.full_name}</b><span>{user?.role==='admin'?'Administrator':user?.role}</span></div><ChevronDown size={15}/></div><button className="logoutBtn" onClick={logout} title="Sign out"><LogOut size={17}/></button></div></header><div className="content">{children}</div></main></div>}
