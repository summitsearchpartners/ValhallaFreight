export type DisplayPreferences={theme:'light'|'dark'|'system';time_format:'12h'|'24h';timezone:string;date_format:'MM/DD/YYYY'|'DD/MM/YYYY'|'YYYY-MM-DD';density:'comfortable'|'compact';show_seconds:boolean;show_clock:boolean};
export const defaultPreferences:DisplayPreferences={theme:'light',time_format:'12h',timezone:'local',date_format:'MM/DD/YYYY',density:'comfortable',show_seconds:false,show_clock:true};
let active:DisplayPreferences={...defaultPreferences};
export function configureDisplay(p:DisplayPreferences){active={...p}}
function dateValue(value:Date|string|number){
 if(value instanceof Date)return value;
 // Retain the existing local interpretation of offset-free appointment values.
 // Offset-bearing timestamps retain their explicit timezone; calendar dates stay dates.
 return new Date(value);
}
const zone=(p:DisplayPreferences):Intl.DateTimeFormatOptions=>p.timezone==='local'?{}:{timeZone:p.timezone};
export function formatDate(value:Date|string|number|null|undefined,p=active):string{
 if(value===null||value===undefined||value==='')return '—';
 const calendar=typeof value==='string'&&/^\d{4}-\d\d-\d\d$/.test(value);
 const d=calendar?new Date(value+'T12:00:00'):dateValue(value);if(Number.isNaN(d.getTime()))return '—';
 const parts=new Intl.DateTimeFormat('en-US',{year:'numeric',month:'2-digit',day:'2-digit',...(calendar?{}:zone(p))}).formatToParts(d);
 const get=(type:string)=>parts.find(x=>x.type===type)?.value||'';
 return p.date_format==='YYYY-MM-DD'?`${get('year')}-${get('month')}-${get('day')}`:p.date_format==='DD/MM/YYYY'?`${get('day')}/${get('month')}/${get('year')}`:`${get('month')}/${get('day')}/${get('year')}`;
}
export function formatTime(value:Date|string|number|null|undefined,p=active):string{
 if(value===null||value===undefined||value==='')return '—';const d=dateValue(value);if(Number.isNaN(d.getTime()))return '—';
 return new Intl.DateTimeFormat('en-US',{hour:'2-digit',minute:'2-digit',...(p.show_seconds?{second:'2-digit'}:{}),hourCycle:p.time_format==='24h'?'h23':'h12',...zone(p)}).format(d);
}
export function formatDateTime(value:Date|string|number|null|undefined,p=active):string{
 if(value===null||value===undefined||value==='')return '—';const date=formatDate(value,p),time=formatTime(value,p);return date==='—'||time==='—'?'—':`${date} · ${time}`;
}

// Database-generated timestamps are UTC; appointment values remain local wall times.
export function formatTimestamp(value:string|null|undefined,p=active){if(!value)return '—';return formatDateTime(/^\d{4}-\d\d-\d\dT/.test(value)&&!/(Z|[+-]\d\d:\d\d)$/.test(value)?value+'Z':value,p)}
export function calendarDate(value=new Date(),p=active){return formatDate(value,{...p,date_format:'YYYY-MM-DD'})}
export function greeting(value=new Date(),p=active){const hour=Number(new Intl.DateTimeFormat('en-US',{hour:'2-digit',hourCycle:'h23',...zone(p)}).format(value));return hour>=5&&hour<12?'Good Morning':hour>=12&&hour<18?'Good Afternoon':'Good Evening'}
