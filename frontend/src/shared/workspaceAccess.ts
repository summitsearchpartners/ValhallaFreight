export const roleLabels: Record<string,string> = {
  admin: 'Valhalla Freight Admin',
  muse_admin:'Muse Freight Admin',
  manufacturer_admin: 'Manufacturer Admin',
  manufacturer: 'Manufacturer',
  broker_admin: 'Broker Admin',
  broker: 'Broker',
  customer: 'Customer',
};

export const isManufacturer = (role?: string) => role === 'manufacturer' || role === 'manufacturer_admin';
export const isBroker = (role?: string) => role === 'broker' || role === 'broker_admin';
export const canAdministerCompany = (role?: string) => role === 'admin' || role === 'manufacturer_admin' || role === 'broker_admin';
export const pricingUsesVisibility = (role?: string) => isManufacturer(role) || role === 'broker';
export const canManageCarriers = (role?: string) => role === 'admin' || role === 'broker_admin';

export const canAccessMuse = (role?:string, partnerAccess=false) => role==='admin'||(partnerAccess&&(role==='broker_admin'||role==='muse_admin'));

export function canOpenWorkspacePage(path: string, role?: string, showPricing = false, partnerAccess = false) {
  if (path==='/truckload')return role==='admin'||isBroker(role);
  if (path==='/muse')return canAccessMuse(role,partnerAccess);
  if (path.startsWith('/admin/')) return role === 'admin';
  if (path === '/portal-admin')return role==='admin';
  if (path === '/integrations') return canAdministerCompany(role);
  if (path === '/pricing') return !pricingUsesVisibility(role) || showPricing;
  if (isManufacturer(role)) return !['/prospects','/automation','/capacity','/carriers'].some(section => path === section || path.startsWith(section + '/'));
  return true;
}
