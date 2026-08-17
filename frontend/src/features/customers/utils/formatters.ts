export function formatUsPhone(value:string){
  let digits=(value||'').replace(/\D/g,'');
  if(digits.length===11&&digits.startsWith('1')) digits=digits.slice(1);
  digits=digits.slice(0,10);
  if(digits.length<=3) return digits;
  if(digits.length<=6) return `(${digits.slice(0,3)}) ${digits.slice(3)}`;
  return `(${digits.slice(0,3)}) ${digits.slice(3,6)}-${digits.slice(6)}`;
}
export function telHref(value:string){
  const digits=(value||'').replace(/\D/g,'');
  return digits?`tel:+${digits.length===10?'1':''}${digits}`:'#';
}
export function websiteHref(value:string){
  if(!value) return '#';
  return /^https?:\/\//i.test(value)?value:`https://${value}`;
}
