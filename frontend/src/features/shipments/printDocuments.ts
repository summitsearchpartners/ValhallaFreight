import type {ShipmentDetail} from './types';
import {accessorialLabel} from '../../shared/freight/AccessorialSelector';

const esc=(v:any)=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]||m));
const money=(v:any)=>Number(v||0).toLocaleString(undefined,{style:'currency',currency:'USD'});
const dateOnly=(v?:string|null)=>v?new Date(v).toLocaleDateString():'—';
const dateTime=(v?:string|null)=>v?new Date(v).toLocaleString():'—';
const addressLines=(a:any)=>[
  a?.name,
  a?.address1,
  a?.address2,
  a?.city&&a?.state?`${a.city}, ${a.state} ${a.postal_code||''}`:a?.postal_code,
  a?.country&&a.country!=='USA'&&a.country!=='US'?a.country:null,
].filter(Boolean).map(esc).join('<br/>');
const contactLine=(a:any)=>[a?.contact_name,a?.phone].filter(Boolean).map(esc).join(' · ');

function barcodeBars(text:string){
  let bits='101011';
  for(const ch of text){
    const n=ch.charCodeAt(0);
    bits+='10';
    for(let i=0;i<7;i++) bits+=((n>>i)&1)?'11':'0';
    bits+='0';
  }
  bits+='110101';
  return bits.split('').map((b,i)=>`<i style="width:${b==='1'?(i%5===0?3:2):1}px;background:${b==='1'?'#111':'transparent'}"></i>`).join('');
}

function openDoc(title:string,body:string){
  const w=window.open('','_blank','width=1180,height=900');
  if(!w)return;
  w.document.write(`<!doctype html><html><head><title>${esc(title)}</title><meta charset="utf-8"/><style>
  @page{size:Letter portrait;margin:.22in}
  *{box-sizing:border-box}html,body{margin:0;padding:0}body{font-family:Arial,Helvetica,sans-serif;color:#111;background:#eef2f4;font-size:10px}
  .toolbar{position:sticky;top:0;display:flex;gap:8px;justify-content:flex-end;padding:10px 16px;background:#17212b;z-index:5}.toolbar button{border:0;border-radius:6px;padding:8px 14px;font-weight:700;cursor:pointer}.toolbar .primary{background:#f26722;color:white}.toolbar .secondary{background:white;color:#17212b}
  .sheet{width:8.06in;min-height:10.55in;margin:14px auto;background:white;box-shadow:0 10px 35px rgba(0,0,0,.2);padding:.03in}
  .bol{border:1.5px solid #151515}.top{display:grid;grid-template-columns:2.15fr 3.4fr 1.8fr;align-items:center;min-height:.72in;border-bottom:1.5px solid #151515}.brand{padding:6px 10px;display:flex;align-items:center;gap:8px}.brand img{width:52px;height:52px;object-fit:contain}.brand strong{display:block;font-size:19px;letter-spacing:.2px}.brand small{font-size:7px;text-transform:uppercase;letter-spacing:1.4px;color:#5d6872}.title{text-align:center;font-size:12px;font-weight:800;letter-spacing:.8px}.topmeta{display:grid;grid-template-columns:1fr 1fr;height:100%;border-left:1px solid #111}.topmeta div{padding:5px 7px;border-bottom:1px solid #111}.topmeta div:nth-last-child(-n+2){border-bottom:0}.lbl{display:block;font-size:6.6px;text-transform:uppercase;letter-spacing:.7px;color:#56616a;margin-bottom:2px}.val{font-size:9.5px;font-weight:700}.sectionbar{background:#17212b;color:#fff;text-align:center;text-transform:uppercase;font-weight:800;letter-spacing:.8px;padding:4px 6px}.addresses{display:grid;grid-template-columns:1fr 1fr}.party{min-height:1.25in;padding:7px 9px;border-right:1px solid #111}.party:last-child{border-right:0}.party .company{font-size:11px;font-weight:800;margin-bottom:3px}.party .addr{line-height:1.35}.party .contact{margin-top:5px;font-size:8px}.party .instruction{margin-top:5px;padding-top:4px;border-top:1px dashed #c8cdd0;font-size:7.5px;line-height:1.35}.refgrid{display:grid;grid-template-columns:1.15fr 1fr}.billto{border-top:1px solid #111;border-right:1px solid #111;min-height:.74in;padding:6px 8px}.refs{border-top:1px solid #111;display:grid;grid-template-columns:1fr 1fr}.refs>div{padding:5px 7px;border-right:1px solid #111;border-bottom:1px solid #111}.refs>div:nth-child(2n){border-right:0}.refs>div:nth-last-child(-n+2){border-bottom:0}.servicegrid{display:grid;grid-template-columns:4.4fr 1.5fr;border-top:1px solid #111}.services{padding:6px 8px;border-right:1px solid #111;min-height:.65in}.terms{padding:6px 8px}.checks{display:flex;gap:10px;margin-top:5px}.check{display:flex;align-items:center;gap:4px}.boxcheck{width:11px;height:11px;border:1px solid #111;display:inline-flex;align-items:center;justify-content:center;font-size:9px;font-weight:900}.boxcheck.on:after{content:'✓'}.pohead,.commodityhead{display:grid;background:#17212b;color:#fff;text-align:center;font-weight:800}.pohead{grid-template-columns:2fr .55fr .85fr .7fr 2.8fr}.commodityhead{grid-template-columns:.45fr .72fr .45fr .72fr .55fr .72fr .38fr 3.35fr 1.12fr 1fr}.pohead div,.commodityhead div{padding:4px 3px;border-right:1px solid #fff3}.rows .r{display:grid;min-height:24px;border-bottom:1px solid #777}.rows.po .r{grid-template-columns:2fr .55fr .85fr .7fr 2.8fr}.rows.commodity .r{grid-template-columns:.45fr .72fr .45fr .72fr .55fr .72fr .38fr 3.35fr 1.12fr 1fr}.rows .r>div{padding:4px 4px;border-right:1px solid #777;display:flex;align-items:center}.rows .r>div:last-child{border-right:0}.totals{display:grid;grid-template-columns:1.15fr 2fr 1.15fr;background:#f2f4f5;border-bottom:1px solid #111;font-weight:800}.totals div{padding:5px 7px;border-right:1px solid #111}.totals div:last-child{border-right:0}.lower{display:grid;grid-template-columns:2.05fr 1fr;min-height:1.35in}.barcodearea{padding:7px 10px;border-right:1px solid #111;display:flex;flex-direction:column;justify-content:center;align-items:center}.barcodeTitle{font-size:8px;color:#56616a;text-transform:uppercase;letter-spacing:.7px}.barcode{height:42px;display:flex;align-items:stretch;gap:0;margin:5px 0 3px;max-width:310px;overflow:hidden}.barcode i{display:block}.barcodeText{font:700 11px monospace;letter-spacing:1.5px}.sticker{font-size:18px;font-weight:900;color:#c5c8ca;text-align:center;line-height:1.1}.declared{padding:7px 8px;font-size:7.4px;line-height:1.35}.legal{border-top:1px solid #111;padding:6px 8px;font-size:6.8px;line-height:1.32}.signatures{display:grid;grid-template-columns:1.5fr 1.5fr .55fr;border-top:1px solid #111}.sig{padding:5px 7px;min-height:.5in;border-right:1px solid #111}.sig:last-child{border-right:0}.sigline{margin-top:13px;border-top:1px solid #111;padding-top:2px;font-size:6.8px;color:#56616a}.footer{text-align:center;font-size:6.8px;padding:4px 5px;border-top:1px solid #111;color:#58636d}.orange{color:#f26722}.nowrap{white-space:nowrap}
  @media print{body{background:white}.toolbar{display:none}.sheet{margin:0;box-shadow:none;width:auto;min-height:auto}.bol{break-inside:avoid}}
  </style></head><body><div class="toolbar"><button class="secondary" onclick="window.close()">Close</button><button class="primary" onclick="window.print()">Print / Save PDF</button></div><div class="sheet">${body}</div></body></html>`);
  w.document.close();
}

function commodityRows(s:ShipmentDetail){
  const units=(s.handling_units||[]);
  const source=units.length?units:[{}];
  const rows=source.map((u:any,index:number)=>{
    const haz=(s.accessorials||[]).includes('hazmat')?'X':'';
    const dims=[u.length_in,u.width_in,u.height_in].every(Boolean)?`${u.length_in} × ${u.width_in} × ${u.height_in}`:'';
    const pkgQty=index===0?(s.package_count??''):'';
    const pkgType=index===0?(s.package_type||''):'';
    const nmfc=index===0?(s.nmfc_number||u.nmfc||''):(u.nmfc||'');
    const description=index===0?(s.commodity_description||u.description||'General freight'):(u.description||'General freight');
    return `<div class="r"><div>${esc(u.quantity||'')}</div><div>${esc(u.type||'Pallet')}</div><div>${esc(pkgQty)}</div><div>${esc(pkgType)}</div><div>${esc(u.freight_class||'')}</div><div>${esc(nmfc)}</div><div>${haz}</div><div>${esc(description)}</div><div>${esc(dims)}</div><div>${esc(u.weight_lbs||'')}</div></div>`;
  });
  while(rows.length<7) rows.push('<div class="r"><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div></div>');
  return rows.join('');
}


export function printBOL(s:ShipmentDetail){
  const totalQty=(s.handling_units||[]).reduce((a:number,u:any)=>a+Number(u.quantity||0),0);
  const totalWeight=(s.handling_units||[]).reduce((a:number,u:any)=>a+Number(u.weight_lbs||0),0);
  const accessorials=(s.accessorials||[]).map(accessorialLabel).join(' • ')||'None';
  const originName=s.origin?.name||s.customer_name||'Shipper';
  const destinationName=s.destination?.name||'Consignee';
  const pro=s.pro_number||'';
  const barcode=pro?`<div class="barcodeTitle">Carrier PRO</div><div class="barcode">${barcodeBars(pro)}</div><div class="barcodeText">${esc(pro)}</div>`:`<div class="sticker">PLACE CARRIER PRO<br/>STICKER HERE</div>`;
  const logo=`${window.location.origin}/valhalla-freight-logo.png`;
  openDoc(`BOL ${s.bol_number||s.shipment_number}`,`
  <div class="bol">
    <div class="top">
      <div class="brand"><img src="${logo}"/><div><strong>Valhalla Freight</strong><small>Transportation Management System</small></div></div>
      <div class="title">STRAIGHT BILL OF LADING ORIGINAL - NOT NEGOTIABLE</div>
      <div class="topmeta"><div><span class="lbl">BOL #</span><span class="val">${esc(s.bol_number||'Pending')}</span></div><div><span class="lbl">Page</span><span class="val">1 of 1</span></div><div><span class="lbl">Date</span><span class="val">${dateOnly(s.created_at)}</span></div><div><span class="lbl">Shipment #</span><span class="val">${esc(s.shipment_number)}</span></div></div>
    </div>

    <div class="addresses">
      <div><div class="sectionbar">Ship From</div><div class="party"><span class="lbl">Shipper</span><div class="company">${esc(originName)}</div><div class="addr">${addressLines({...s.origin,name:undefined})}</div>${contactLine(s.origin)?`<div class="contact"><b>Shipper contact:</b> ${contactLine(s.origin)}</div>`:''}${s.origin?.email?`<div class="contact"><b>Email:</b> ${esc(s.origin.email)}</div>`:''}${s.origin?.instructions?`<div class="instruction"><b>Pickup instructions:</b> ${esc(s.origin.instructions)}</div>`:''}</div></div>
      <div><div class="sectionbar">Ship To</div><div class="party"><span class="lbl">Consignee</span><div class="company">${esc(destinationName)}</div><div class="addr">${addressLines({...s.destination,name:undefined})}</div>${contactLine(s.destination)?`<div class="contact"><b>Consignee contact:</b> ${contactLine(s.destination)}</div>`:''}${s.destination?.email?`<div class="contact"><b>Email:</b> ${esc(s.destination.email)}</div>`:''}${s.destination?.instructions?`<div class="instruction"><b>Delivery instructions:</b> ${esc(s.destination.instructions)}</div>`:''}</div></div>
    </div>

    <div class="refgrid">
      <div class="billto"><div class="sectionbar" style="margin:-6px -8px 5px">Third-Party Freight Charges Bill To</div><div class="company"><b>Valhalla Freight</b></div><div>Brokered shipment - billing per carrier and customer agreement.</div></div>
      <div class="refs"><div><span class="lbl">Carrier</span><span class="val">${esc(s.carrier_name||'Pending')}</span></div><div><span class="lbl">SCAC</span><span class="val">${esc(s.carrier_scac||'—')}</span></div><div><span class="lbl">PRO #</span><span class="val">${esc(s.pro_number||'Pending')}</span></div><div><span class="lbl">Customer Account</span><span class="val">${esc(s.customer_name||'—')}</span></div></div>
    </div>

    <div class="servicegrid"><div class="services"><span class="lbl">Comments / Special Services</span><b>${esc(accessorials)}</b></div><div class="terms"><span class="lbl">Freight Charges</span><div class="checks"><span class="check"><i class="boxcheck"></i>Prepaid</span><span class="check"><i class="boxcheck"></i>Collect</span><span class="check"><i class="boxcheck on"></i>Third Party</span></div></div></div>

    <div class="pohead"><div>Purchase Order / Customer Reference</div><div># Pkgs</div><div>Weight</div><div>Pallet Y/N</div><div>Additional Shipper Information</div></div>
    <div class="rows po"><div class="r"><div>${esc([s.po_number,s.customer_reference].filter(Boolean).join(' / ')||'—')}</div><div>${esc(s.package_count??totalQty)}</div><div>${esc(totalWeight)} lb</div><div>Y</div><div>${s.package_type?`Package type: ${esc(s.package_type)} · `:''}Required delivery: ${dateTime(s.requested_delivery_at)}${s.scheduled_pickup_at?` · Scheduled pickup: ${dateTime(s.scheduled_pickup_at)}`:''}</div></div></div>

    <div class="commodityhead"><div>H/U Qty</div><div>H/U Type</div><div>Pkg Qty</div><div>Pkg Type</div><div>Class</div><div>NMFC #</div><div>Haz</div><div>Commodity Description</div><div>Dimensions (in)</div><div>Weight (lb)</div></div>
    <div class="rows commodity">${commodityRows(s)}</div>
    <div class="totals"><div>Total Quantity: ${esc(totalQty)}</div><div>Grand Total Weight: ${esc(totalWeight)} lb</div><div>Total Packages: ${esc(s.package_count??totalQty)}</div></div>

    <div class="lower"><div class="barcodearea">${barcode}</div><div class="declared"><b>Declared Value / Special Liability</b><br/>${s.declared_value!=null?`<span class="val">${money(s.declared_value)}</span>`:'Not declared'}<br/><br/>If a rate depends on declared value, the shipper must state that value in writing according to the applicable carrier tariff and governing rules.${(s.hazmat_emergency_contact||s.hazmat_emergency_phone)?`<br/><br/><b>Hazmat Emergency Contact</b><br/>${esc(s.hazmat_emergency_contact||'')} ${esc(s.hazmat_emergency_phone||'')}`:''}<br/><br/><b>Customer Required Delivery</b><br/>${dateTime(s.requested_delivery_at)}</div></div>

    <div class="legal"><b>SHIPPER CERTIFICATION:</b> The shipper certifies that the materials described on this Bill of Lading are properly classified, described, packaged, marked and labeled for transportation. Transportation is subject to applicable carrier tariffs, classifications, NMFC rules, governing transportation terms and lawful charges. The carrier's acceptance of the freight confirms receipt in apparent good order except as otherwise noted.</div>
    <div class="signatures"><div class="sig"><b>Shipper</b><div class="sigline">Authorized signature / printed name</div></div><div class="sig"><b>Carrier: ${esc(s.carrier_name||'')}</b><div class="sigline">Driver / carrier signature</div></div><div class="sig"><b>Date</b><div class="sigline">Date / time</div></div></div>
    <div class="footer">Generated by Valhalla Freight · ${esc(s.shipment_number)} · ${esc(s.bol_number||'')}</div>
  </div>`);
}

export function printShippingLabel(s:ShipmentDetail){openDoc(`Shipping Label ${s.shipment_number}`,`<div class="bol" style="padding:18px"><div class="brand"><img src="${window.location.origin}/valhalla-freight-logo.png"/><div><strong>Valhalla Freight</strong><small>Shipping Label</small></div></div><div class="sectionbar">LTL SHIPPING LABEL</div><div style="padding:16px"><div class="barcode">${barcodeBars(s.pro_number||s.shipment_number)}</div><div class="barcodeText" style="text-align:center">${esc(s.pro_number||s.shipment_number)}</div><div class="addresses" style="margin-top:16px"><div class="party"><span class="lbl">FROM</span><div class="company">${esc(s.origin?.name||s.customer_name||'Shipper')}</div>${addressLines({...s.origin,name:undefined})}</div><div class="party"><span class="lbl">TO</span><div class="company" style="font-size:17px">${esc(s.destination?.name||'Consignee')}</div><div style="font-size:14px;line-height:1.45">${addressLines({...s.destination,name:undefined})}</div></div></div><div class="refs" style="border:1px solid #111;margin-top:12px"><div><span class="lbl">Carrier</span><span class="val">${esc(s.carrier_name||'')}</span></div><div><span class="lbl">SCAC</span><span class="val">${esc(s.carrier_scac||'')}</span></div><div><span class="lbl">BOL</span><span class="val">${esc(s.bol_number||'')}</span></div><div><span class="lbl">PRO</span><span class="val">${esc(s.pro_number||'Pending')}</span></div></div></div></div>`)}
