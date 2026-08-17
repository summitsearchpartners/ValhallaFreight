import {Routes,Route,Navigate,useLocation} from 'react-router-dom';
import type {ReactNode} from 'react';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Quotes from './pages/Quotes';
import Login from './pages/Login';
import {Shipments,Customers,Carriers,Pricing,Prospects,Analytics,Billing} from './pages/Tables';
import {useAuth} from './context/AuthContext';

function Protected({children}:{children:ReactNode}){
  const {user,loading}=useAuth(); const location=useLocation();
  if(loading) return <div className="authLoading"><img src="/valhalla-freight-logo.png"/><span>Loading Valhalla Freight…</span></div>;
  if(!user) return <Navigate to="/login" replace state={{from:location.pathname}}/>;
  return <>{children}</>;
}
export default function App(){return <Routes>
  <Route path="/login" element={<Login/>}/>
  <Route path="/*" element={<Protected><Layout><Routes><Route path="/" element={<Dashboard/>}/><Route path="/quotes" element={<Quotes/>}/><Route path="/shipments" element={<Shipments/>}/><Route path="/customers" element={<Customers/>}/><Route path="/carriers" element={<Carriers/>}/><Route path="/pricing" element={<Pricing/>}/><Route path="/analytics" element={<Analytics/>}/><Route path="/prospects" element={<Prospects/>}/><Route path="/billing" element={<Billing/>}/></Routes></Layout></Protected>}/>
</Routes>}
