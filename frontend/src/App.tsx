import {Routes,Route,Navigate,useLocation} from 'react-router-dom';
import type {ReactNode} from 'react';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Quotes from './pages/Quotes';
import Login from './pages/Login';
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
import {useAuth} from './context/AuthContext';

function Protected({children}:{children:ReactNode}){const {user,loading}=useAuth();const location=useLocation();if(loading)return <div className="authLoading"><img src="/valhalla-freight-logo.png"/><span>Loading Valhalla Freight…</span></div>;if(!user)return <Navigate to="/login" replace state={{from:location.pathname}}/>;return <>{children}</>}
export default function App(){return <Routes><Route path="/login" element={<Login/>}/><Route path="/*" element={<Protected><Layout><Routes>
<Route path="/" element={<Dashboard/>}/><Route path="/quotes" element={<Quotes/>}/><Route path="/quotes/bucket" element={<QuoteBucketPage/>}/><Route path="/quotes/:quoteRef" element={<QuoteDetailPage/>}/>
<Route path="/shipments" element={<Shipments/>}/><Route path="/shipments/new" element={<CreateShipmentPage/>}/><Route path="/shipments/:shipmentId" element={<ShipmentDetailPage/>}/>
<Route path="/customers" element={<CustomersPage/>}/><Route path="/customers/:customerId" element={<CustomerDetailPage/>}/>
<Route path="/carriers" element={<CarrierNetworkPage/>}/><Route path="/carriers/:carrierId" element={<CarrierDetailPage/>}/>
<Route path="/capacity" element={<CapacityPage/>}/><Route path="/visibility" element={<VisibilityPage/>}/><Route path="/automation" element={<AutomationCenterPage/>}/><Route path="/pricing" element={<PricingPage/>}/>
<Route path="/finance" element={<FinancePage/>}/><Route path="/billing" element={<Navigate to="/finance" replace/>}/><Route path="/claims" element={<ClaimsPage/>}/>
<Route path="/intelligence" element={<IntelligencePage/>}/><Route path="/analytics" element={<AnalyticsPage/>}/><Route path="/prospects" element={<Prospects/>}/>
<Route path="/integrations" element={<IntegrationHubPage/>}/><Route path="/portal-admin" element={<PortalAdminPage/>}/>
</Routes></Layout></Protected>}/></Routes>}
