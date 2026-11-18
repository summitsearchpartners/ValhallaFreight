export const portalKey=(company:string)=>`vf_portal_support_${company}`;
export function portalSession(company:string){try{return JSON.parse(sessionStorage.getItem(portalKey(company))||'null')}catch{return null}}
export function savePortalSession(company:string,value:{portal_token:string;expires_at:string}){sessionStorage.setItem(portalKey(company),JSON.stringify(value))}
export function clearPortalSession(company:string){sessionStorage.removeItem(portalKey(company))}
