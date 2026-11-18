"""Automatic field comparison. Changed identity documents are routed to broker review."""
import re,unicodedata,hmac
from datetime import datetime
from app.services.safe_load import license_key
SUFFIXES={'JR','SR','II','III','IV','V'}
def tokens(value):
    clean=unicodedata.normalize('NFKD',value or '').encode('ascii','ignore').decode().upper()
    return re.findall('[A-Z]+',clean)
def strip_suffix(parts):
    while parts and parts[-1] in SUFFIXES:parts=parts[:-1]
    return parts

def name_matches(expected,first,last):
    given=strip_suffix(tokens(first));surname=strip_suffix(tokens(last));full=strip_suffix(tokens(expected))
    if ',' in expected:
        family,given_name=expected.split(',',1)
        if set(tokens(given_name))-SUFFIXES:full=strip_suffix(tokens(given_name))+strip_suffix(tokens(family))
    return bool(given and surname and full and full[0]==given[0] and full[-len(surname):]==surname)

def expiry(fields):
    value=fields.get('DBA','')
    try:return datetime.strptime(value,'%Y%m%d' if value.startswith(('19','20')) else '%m%d%Y').date()
    except ValueError:return None

def assess(row,evidence,vehicle,vin_errors):
    fields=evidence['fields'];reasons=list(evidence['errors'])+list(vin_errors);flags=[]
    same_id=bool(fields.get('DAQ') and fields.get('DAJ') and hmac.compare_digest(license_key(fields['DAQ'],fields['DAJ']),row.license_digest or ''))
    same_name=name_matches(row.driver_name or '',fields.get('DAC',''),fields.get('DCS',''))
    if fields.get('DAQ') and fields.get('DAJ') and not same_id:
        reasons.append('Onsite license number or issuing state differs from the dispatcher record. Possible reissued/replacement license: broker review required.')
        flags.append('license_identity_changed')
    if fields.get('DAC') and fields.get('DCS') and not same_name:reasons.append('Extracted driver name does not match the dispatcher assignment')
    observed=expiry(fields);expected=row.license_expires.date() if row.license_expires else None
    if fields.get('DBA') and observed is None:reasons.append('Extracted license expiration is invalid')
    if observed and observed<datetime.utcnow().date():reasons.append('Onsite license is expired')
    if observed and expected and observed!=expected:
        if observed>=datetime.utcnow().date() and observed>expected and same_id and same_name:flags.append('valid_renewal_expiration')
        else:
            reasons.append('License expiration differs from the dispatcher record and needs broker review')
            flags.append('license_expiration_changed')
    if not expected:reasons.append('Dispatcher license expiration is missing')
    if vehicle and vehicle!=row.vin:reasons.append('Truck VIN does not match the dispatcher assignment')
    summary={'driver_name':' '.join([fields.get('DAC',''),fields.get('DCS','')]).strip(),'license_last4':re.sub('[^A-Z0-9]','',fields.get('DAQ','').upper())[-4:],'issuing_state':fields.get('DAJ',''),'expires_at':observed.isoformat() if observed else None,'vin':vehicle,'reader':evidence['source'],'flags':flags,'renewal_accepted':bool('valid_renewal_expiration' in flags),'requires_license_review':bool(set(flags)&{'license_identity_changed','license_expiration_changed'}),'name_matched':same_name,'license_identity_matched':same_id,'vin_matched':bool(vehicle and vehicle==row.vin),'decision':'broker_review' if reasons else 'matched'}
    missing=[k for k in ['DAQ','DAJ','DAC','DCS','DBA'] if not fields.get(k)]
    mismatch=bool((fields.get('DAQ') and fields.get('DAJ') and not same_id) or (fields.get('DAC') and fields.get('DCS') and not same_name) or (vehicle and vehicle!=row.vin))
    summary['evidence_quality']='data_mismatch' if mismatch else 'unreadable_or_incomplete' if missing or vin_errors or evidence['errors'] else 'fields_read'
    summary['check_outcomes']={'license':'unreadable' if not fields.get('DAQ') or not fields.get('DAJ') else 'matched' if same_id else 'mismatch','name':'incomplete' if not fields.get('DAC') or not fields.get('DCS') else 'matched' if same_name else 'mismatch','expiration':'unreadable' if not observed else 'expired' if observed<datetime.utcnow().date() else 'renewal' if summary['renewal_accepted'] else 'read','vin':'unreadable' if not vehicle else 'matched' if vehicle==row.vin else 'mismatch'}
    return reasons,summary
