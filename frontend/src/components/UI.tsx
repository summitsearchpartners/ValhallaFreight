import type {ReactNode} from 'react';
export function PageHead({eyebrow='Valhalla Freight',title,sub,actions}:{eyebrow?:string,title:string,sub:string,actions?:ReactNode}){return <div className="pagehead"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{sub}</p></div>{actions&&<div className="actions">{actions}</div>}</div>}
export function Card({children,className=''}:{children:ReactNode,className?:string}){return <div className={`card ${className}`}>{children}</div>}
export function Pill({children,tone='neutral'}:{children:ReactNode,tone?:string}){return <span className={`pill ${tone}`}>{children}</span>}
export function Stat({label,value,delta,icon}:{label:string,value:string,delta?:string,icon?:ReactNode}){return <Card className="stat"><div className="statrow"><span>{label}</span><div className="staticon">{icon}</div></div><strong>{value}</strong>{delta&&<small>{delta}</small>}</Card>}
