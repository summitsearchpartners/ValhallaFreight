import WarehouseUsersPage from './features/warehouse/WarehouseUsersPage';
import TruckloadPage from './features/truckload/TruckloadPage';
import SafeLoadPage from './features/safeLoad/SafeLoadPage';
import CarrierSubmission from './features/safeLoad/CarrierSubmission';
import CustomerPricing from './features/pricing/CustomerPricing';
import CustomerBilling from './features/finance/CustomerBilling';
import MusePortal from './features/muse/MusePortal';
import MuseCreditPage from './features/muse/MuseCreditPage';
import {canAccessMuse,canAdministerCompany,canOpenWorkspacePage,isBroker,pricingUsesVisibility} from './shared/workspaceAccess';
import PortalAccessPage from './features/admin/PortalAccessPage';
import PortalSupportGate from './features/portal/PortalSupportGate';
import {usePreferences} from './context/PreferencesContext';
import UsersPage from './features/admin/UsersPage';
import {Routes,Route,Navigate,useLocation} from 'react-router-dom';
import {useState,useEffect,type ReactNode} from 'react';
import {api} from './services/api';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Quotes from './pages/Quotes';
import Login from './pages/Login';
import ResetPassword from './pages/ResetPassword';
import {Shipments,Prospects} from './pages/Tables';
import PricingPage from './features/pricing/PricingPage';
import AnalyticsPage from './features/analytics/AnalyticsPage';
import AutomationCenterPage from './features/automation/AutomationCenterPage';
import CustomersPage from './features/customers/CustomersPage';
import CustomerDetailPage from './features/customers/CustomerDetailPage';
import ShipmentDetailPage from './features/shipments/ShipmentDetailPage';
import CreateShipmentPage from './features/shipments/CreateShipmentPage';
import QuoteBucketPage from './features/quotes/QuoteBucketPage';
import QuoteDetailPage from './features/quotes/QuoteDetailPage';
import CarrierNetworkPage from './features/carriers/CarrierNetworkPage';
import CarrierDetailPage from './features/carriers/CarrierDetailPage';
import CapacityPage from './features/capacity/CapacityPage';
import FinancePage from './features/finance/FinancePage';
import ClaimsPage from './features/claims/ClaimsPage';
import IntegrationHubPage from './features/integrations/IntegrationHubPage';
import IntelligencePage from './features/intelligence/IntelligencePage';
import VisibilityPage from './features/visibility/VisibilityPage';
import PortalAdminPage from './features/portal/PortalAdminPage';
import CustomerPortalApp from './features/portal/CustomerPortalApp';
import FreightPlannerPage from './features/planner/FreightPlannerPage';
import {useAuth} from './context/AuthContext';
import WorkspaceSettings from './features/settings/WorkspaceSettings';

function Protected({children}:{children:ReactNode}){const {user,loading,logout}=useAuth();const location=useLocation();if(loading)return <div className="authLoading"><img src="/valhalla-tms-powered.webp"/><span>Loading Valhalla TMS…</span></div>;if(!user)return <Navigate to="/login" replace state={{from:location.pathname}}/>;if(user.role==='warehouse')return <div className='authLoading'><h2>Safe Load mobile access only</h2><p>This account cannot access the Valhalla TMS web portal. Sign in through the Safe Load mobile app.</p><button className='btn secondary' onClick={logout}>Sign out</button></div>;if(user.role==='muse_admin')return user.muse_partner_access?<Navigate to='/muse' replace/>:<div className='authLoading'><h2>Muse company assignment required</h2><p>Ask Super Admin to designate the Muse partner company for this account.</p><button onClick={logout}>Sign out</button></div>;if(user.role==='customer')return <Navigate to="/portal" replace/>;if(isBroker(user.role)&&!user.customer_id)return <div className="authLoading"><h2>Company assignment required</h2><p>Ask your Valhalla TMS administrator to assign this account to a company.</p><button className="btn secondary" onClick={logout}>Sign out</button></div>;return <>{children}</>}
function AdminOnly({children}:{children:ReactNode}){const {user}=useAuth();const {pathname}=useLocation();return canOpenWorkspacePage(pathname,user?.role)?<>{children}</>:<Navigate to='/' replace/>}
function PricingAccess(){const {user}=useAuth();const [enabled,setEnabled]=useState<boolean|null>(null);const manufacturer=pricingUsesVisibility(user?.role);useEffect(()=>{if(!manufacturer)return;const load=()=>api<any>('/workspace/settings').then(x=>setEnabled(x.show_pricing)).catch(()=>setEnabled(false));load();const timer=setInterval(load,30000);window.addEventListener('workspace-updated',load);return()=>{clearInterval(timer);window.removeEventListener('workspace-updated',load)}},[manufacturer]);return !manufacturer?<PricingPage/>:enabled===null?<p>Loading permissions…</p>:enabled?<CustomerPricing/>:<Navigate to="/" replace/>}
function SuperOnly({children}:{children:ReactNode}){const {user}=useAuth();return user?.role==='admin'?<>{children}</>:<Navigate to='/' replace/>}
function FinanceAccess(){const {user}=useAuth();return ['manufacturer','manufacturer_admin'].includes(user?.role||'')?<CustomerBilling/>:<FinancePage/>}
function WarehouseAdminOnly({children}:{children:ReactNode}){const {user}=useAuth();return user?.role==='admin'||user?.role==='manufacturer_admin'?<>{children}</>:<Navigate to='/' replace/>}
function CompanyAdminOnly({children}:{children:ReactNode}){const {user}=useAuth();return canAdministerCompany(user?.role)?<>{children}</>:<Navigate to='/' replace/>}
function CustomerProtected(){const {user,loading}=useAuth();const location=useLocation();if(loading)return <div className="authLoading"><img src="/valhalla-tms-powered.webp"/><span>Loading customer workspace…</span></div>;if(!user)return <Navigate to="/customer-login" replace/>;if(user.role==='admin')return <PortalSupportGate/>;if(user.role!=='customer')return <Navigate to="/" replace/>;return <CustomerPortalApp/>}
function MuseGate(){const {user,loading}=useAuth();if(loading)return <p>Loading Muse Portal…</p>;if(!user)return <Navigate to="/login" replace/>;return canAccessMuse(user.role,user.muse_partner_access)?<MusePortal/>:<Navigate to="/" replace/>}
export default function App(){usePreferences();return <Routes><Route path="/safe-load/carrier" element={<CarrierSubmission/>}/><Route path="/login" element={<Login/>}/><Route path="/reset-password" element={<ResetPassword/>}/><Route path="/customer-login" element={<Login/>}/><Route path="/portal" element={<CustomerProtected/>}/><Route path="/muse" element={<MuseGate/>}/><Route path="/*" element={<Protected><Layout><Routes>
<Route path="/" element={<Dashboard/>}/><Route path="/muse-credit/:manufacturerId" element={<MuseCreditPage/>}/><Route path="/quotes" element={<Quotes/>}/><Route path="/quotes/bucket" element={<QuoteBucketPage/>}/><Route path="/quotes/:quoteRef" element={<QuoteDetailPage/>}/>
<Route path="/truckload" element={<AdminOnly><TruckloadPage/></AdminOnly>}/><Route path="/safe-load" element={<SafeLoadPage/>}/><Route path="/shipments" element={<Shipments/>}/><Route path="/shipments/new" element={<CreateShipmentPage/>}/><Route path="/shipments/:shipmentId" element={<ShipmentDetailPage/>}/>
<Route path="/customers" element={<CustomersPage/>}/><Route path="/customers/:customerId" element={<CustomerDetailPage/>}/>
<Route path="/carriers" element={<AdminOnly><CarrierNetworkPage/></AdminOnly>}/><Route path="/carriers/:carrierId" element={<AdminOnly><CarrierDetailPage/></AdminOnly>}/>
<Route path="/warehouse/users" element={<WarehouseAdminOnly><WarehouseUsersPage/></WarehouseAdminOnly>}/><Route path="/admin/portal-access" element={<SuperOnly><PortalAccessPage/></SuperOnly>}/><Route path="/admin/users" element={<SuperOnly><UsersPage/></SuperOnly>}/><Route path="/my-profile" element={<WorkspaceSettings mode="profile"/>}/><Route path="/system-settings" element={<WorkspaceSettings mode="settings"/>}/><Route path="/planner" element={<FreightPlannerPage/>}/><Route path="/capacity" element={<AdminOnly><CapacityPage/></AdminOnly>}/><Route path="/visibility" element={<VisibilityPage/>}/><Route path="/automation" element={<AdminOnly><AutomationCenterPage/></AdminOnly>}/><Route path="/pricing" element={<PricingAccess/>}/>
<Route path="/finance" element={<FinanceAccess/>}/><Route path="/billing" element={<Navigate to="/finance" replace/>}/><Route path="/claims" element={<ClaimsPage/>}/>
<Route path="/intelligence" element={<IntelligencePage/>}/><Route path="/analytics" element={<AnalyticsPage/>}/><Route path="/prospects" element={<AdminOnly><Prospects/></AdminOnly>}/>
<Route path="/integrations" element={<CompanyAdminOnly><IntegrationHubPage/></CompanyAdminOnly>}/><Route path="/portal-admin" element={<SuperOnly><PortalAdminPage/></SuperOnly>}/>
</Routes></Layout></Protected>}/></Routes>}
