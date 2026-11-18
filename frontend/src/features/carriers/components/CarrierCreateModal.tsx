import RecordModal,{type Field} from './RecordModal';
const fields:Field[]=[
  {key:'name',label:'Carrier name',placeholder:'Example Transport LLC'},
  {key:'scac',label:'SCAC',placeholder:'ABCD'},
  {key:'mode',label:'Primary mode',type:'select',options:['LTL','FTL','Volume LTL','Partial','Expedited','Drayage','Intermodal']},
  {key:'mc_number',label:'MC number',placeholder:'MC123456'},
  {key:'dot_number',label:'DOT number',placeholder:'DOT1234567'},
  {key:'authority_status',label:'Authority status',type:'select',options:['pending','active','inactive','revoked']},
  {key:'preferred',label:'Preferred carrier',type:'checkbox'},
  {key:'api_enabled',label:'API / EDI capable (verify in Integration Hub)',type:'checkbox'},
];
export default function CarrierCreateModal({open,onClose,onSubmit}:{open:boolean;onClose:()=>void;onSubmit:(x:any)=>Promise<void>}){return <RecordModal open={open} title="Add carrier to network" fields={fields} initial={{mode:'LTL',authority_status:'pending',preferred:false,api_enabled:false}} submitLabel="Create carrier" onClose={onClose} onSubmit={onSubmit}/>}
