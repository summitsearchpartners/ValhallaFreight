import {Plus,StickyNote,UserRound,Clock3} from 'lucide-react';
import {Card} from '../../../components/UI';

export default function CustomerNotes({data,add}:{data:any,add:()=>void}){
 const notes=data.activities.filter((a:any)=>a.activity_type==='note');
 return <Card className="notesWorkspace">
  <div className="notesHead"><div><div className="notesTitle"><StickyNote size={18}/><h3>Customer notes</h3></div><p>Dedicated account notes for sales, operations, billing and customer relationship context.</p></div><button className="btn primary" onClick={add}><Plus size={14}/>Add note</button></div>
  <div className="notesSummary"><strong>{notes.length}</strong><span>{notes.length===1?'account note':'account notes'}</span></div>
  {notes.length?<div className="notesList">{notes.map((a:any)=><article className="noteCard" key={a.id}><header><div><StickyNote size={16}/><b>{a.subject}</b></div><span><Clock3 size={12}/>{new Date(a.created_at).toLocaleString()}</span></header>{a.body&&<p>{a.body}</p>}<footer><UserRound size={12}/>{a.created_by||'Valhalla Freight'}</footer></article>)}</div>:<div className="notesEmpty"><StickyNote size={26}/><b>No customer notes yet</b><span>Add the first note to keep important customer context in one visible place.</span><button className="btn primary" onClick={add}><Plus size={14}/>Add first note</button></div>}
 </Card>
}
