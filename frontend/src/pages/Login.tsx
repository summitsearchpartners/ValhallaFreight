import {useState, type FormEvent} from 'react';
import {Navigate, useLocation, useNavigate} from 'react-router-dom';
import {ArrowRight, Eye, EyeOff, LockKeyhole, Mail, ShieldCheck, CircleCheck, Route, BarChart3, Truck} from 'lucide-react';
import {useAuth} from '../context/AuthContext';

export default function Login(){
  const {user,login}=useAuth();
  const navigate=useNavigate();
  const location=useLocation();
  const [email,setEmail]=useState('');
  const [password,setPassword]=useState('');
  const [showPassword,setShowPassword]=useState(false);
  const [error,setError]=useState('');
  const [submitting,setSubmitting]=useState(false);
  if(user) return <Navigate to="/" replace/>;
  async function submit(e:FormEvent){
    e.preventDefault();setError('');setSubmitting(true);
    try{await login(email,password);navigate((location.state as any)?.from || '/',{replace:true});}
    catch(err:any){setError(err.message || 'Unable to sign in.');}
    finally{setSubmitting(false);}
  }
  return <div className="loginPage">
    <section className="loginHero">
      <div className="loginGlow glowOne"/><div className="loginGlow glowTwo"/>
      <div className="loginHeroInner">
        <div className="loginBrand"><img src="/valhalla-freight-logo.png" alt="Valhalla Freight logo"/><div><strong>Valhalla Freight</strong><span>TRANSPORTATION MANAGEMENT SYSTEM</span></div></div>
        <div className="heroCopy">
          <div className="loginBadge"><Truck size={13}/> LTL TRANSPORTATION OPERATING SYSTEM</div>
          <h1>Move freight smarter.<br/>Command every <em>shipment.</em></h1>
          <p>Quote, book, track, audit, invoice, and analyze freight from one intelligent operating system built for modern LTL brokerage.</p>
        </div>
        <div className="loginBenefits">
          <div><CircleCheck/><span><b>One freight command center</b><small>Quotes, shipments, customers, carriers, billing, and exceptions in one workspace.</small></span></div>
          <div><BarChart3/><span><b>Pricing & margin intelligence</b><small>Protect gross profit with customer, carrier, lane, class, and accessorial pricing rules.</small></span></div>
          <div><Route/><span><b>Built for the long haul</b><small>Structured freight data designed for integrations, automation, and scale.</small></span></div>
        </div>
        <div className="heroFooter"><ShieldCheck/> Built for Valhalla Freight · Driven by Honor.</div>
      </div>
    </section>
    <section className="loginFormSide">
      <form className="loginCard" onSubmit={submit}>
        <div className="loginCardTop"><div className="loginLock"><LockKeyhole/></div><div><h2>Welcome back</h2><p>Sign in to continue to your freight workspace.</p></div></div>
        <label>Email address<div className="loginInput"><Mail/><input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="name@company.com" autoComplete="email" required/></div></label>
        <label>Password <button type="button" className="forgot" onClick={()=>alert('Password recovery will be connected in the next authentication phase.')}>Forgot password?</button><div className="loginInput"><LockKeyhole/><input type={showPassword?'text':'password'} value={password} onChange={e=>setPassword(e.target.value)} placeholder="Enter your password" autoComplete="current-password" required/><button type="button" className="showPass" onClick={()=>setShowPassword(x=>!x)} aria-label="Toggle password visibility">{showPassword?<EyeOff/>:<Eye/>}</button></div></label>
        {error&&<div className="loginError">{error}</div>}
        <button className="loginSubmit" disabled={submitting}>{submitting?'Signing in…':'Sign in to Valhalla Freight'}<ArrowRight/></button>
        <div className="secureLine"><ShieldCheck/> Secure access to Valhalla Freight systems</div>
      </form>
      <div className="loginMeta">VALHALLA FREIGHT <i/> TRANSPORTATION MANAGEMENT SYSTEM <i/> BUILT FOR THE LONG HAUL</div>
    </section>
  </div>
}
