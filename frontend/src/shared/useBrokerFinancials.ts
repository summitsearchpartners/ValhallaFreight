import {useAuth} from '../context/AuthContext';

export default function useBrokerFinancials(){
 const {user}=useAuth();
 return !!user&&['admin','broker','broker_admin','muse_admin'].includes(user.role);
}
