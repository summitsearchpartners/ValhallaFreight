import {useState, type FormEvent} from 'react';
import {Link, useSearchParams} from 'react-router-dom';
import {LockKeyhole, ShieldCheck} from 'lucide-react';
import MusePoweredBy from '../components/MusePoweredBy';
import {api} from '../services/api';

export default function ResetPassword(){
  const [params]=useSearchParams();
  const token=params.get('token')||'';
  const [password,setPassword]=useState('');
  const [confirm,setConfirm]=useState('');
  const [error,setError]=useState('');
  const [success,setSuccess]=useState(false);
  const [busy,setBusy]=useState(false);
  async function submit(e:FormEvent){
    e.preventDefault();setError('');
    if(password!==confirm){setError('Passwords do not match.');return}
    if(new TextEncoder().encode(password).length>72){setError('Password must not exceed 72 bytes.');return}
    setBusy(true);
    try{await api('/auth/reset-password',{method:'POST',body:JSON.stringify({token,password})});setSuccess(true);setPassword('');setConfirm('')}
    catch(err:any){setError(err.message||'Unable to reset password.')}
    finally{setBusy(false)}
  }
  return <div className="loginPage resetPage"><section className="loginFormSide" style={{gridColumn:'1 / -1'}}>
    <form className="loginCard" onSubmit={submit}>
      <div className="loginCardTop"><div className="loginLock"><LockKeyhole/></div><div><h2>Set a new password</h2><p>Valhalla Freight secure account recovery</p></div></div>
      {success?<><div className="loginSuccess" role="status">Password updated successfully.</div><Link className="resetBack" to="/login">Return to sign in</Link></>:<>
        {!token&&<div className="loginError">Reset link missing. Request a new link from the sign-in page.</div>}
        <label>New password<div className="loginInput"><LockKeyhole/><input type="password" autoComplete="new-password" minLength={12} maxLength={128} required value={password} onChange={e=>setPassword(e.target.value)}/></div></label>
        <label>Confirm new password<div className="loginInput"><LockKeyhole/><input type="password" autoComplete="new-password" minLength={12} maxLength={128} required value={confirm} onChange={e=>setConfirm(e.target.value)}/></div></label>
        {error&&<div className="loginError">{error}</div>}
        <button className="loginSubmit" disabled={!token||busy}>{busy?'Updating…':'Update password'}</button>
        <Link className="resetBack" to="/login">Back to sign in</Link>
      </>}
      <div className="secureLine"><ShieldCheck/> Secure access to Valhalla Freight systems</div>
    </form><MusePoweredBy/></section></div>
}
