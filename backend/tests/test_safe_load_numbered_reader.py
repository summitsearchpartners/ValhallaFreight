"""Synthetic documents only: no customer identity data."""
from app.services.safe_load_images import parse_license_text

def test_numbered_inline_fields_distinguish_birth_issue_and_expiry():
    fields=parse_license_text('OKLAHOMA\n4d. TEST1234 3. 01/01/1990\n4a ISS 05/11/2026 4b EXP 03/31/2035\n1. DOE\n2. JOHN ALAN, JR\n')
    assert fields=={'DAQ':'TEST1234','DAC':'JOHN ALAN, JR','DCS':'DOE','DBA':'03312035','DAJ':'OK'}

def test_separate_labels_and_ambiguous_numbers_stay_conservative():
    fields=parse_license_text('ISSUING STATE: KS\nDL NUMBER\nTEST1234\nLAST NAME\nDOE\nFIRST NAME\nJOHN\nEXPIRATION DATE\n01/01/2035')
    assert fields['DAQ']=='TEST1234' and fields['DAC']=='JOHN' and fields['DBA']=='01012035'
    ambiguous=parse_license_text('DL NUMBER TEST1234\nDL NUMBER TEST9876\n')
    assert not ambiguous['DAQ']

def test_issue_date_is_never_used_as_expiration():
    fields=parse_license_text('OKLAHOMA\n4a ISS 05/11/2026\n3. 01/01/1990\n1. DOE\n2. JOHN')
    assert fields['DBA']==''

def test_numbered_card_real_ocr_rotated():
    import io
    from PIL import Image,ImageDraw,ImageFont
    from app.services.safe_load_images import license_evidence
    im=Image.new('RGB',(1400,850),'white');draw=ImageDraw.Draw(im)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',36)
    for i,line in enumerate(['OKLAHOMA','4d. TEST1234 3. 01/01/1990','4a ISS 05/11/2026 4b EXP 03/31/2035','1. DOE','2. JOHN ALAN, JR']):draw.text((80,80+i*110),line,font=font,fill='black')
    data=io.BytesIO();im.rotate(90,expand=True).save(data,'JPEG',quality=95)
    result=license_evidence(data.getvalue())
    assert not result['errors'],result['errors']
    assert result['fields']['DAQ']=='TEST1234' and result['fields']['DBA']=='03312035'

def test_uncertainty_is_not_reported_as_identity_mismatch():
    from types import SimpleNamespace
    from datetime import datetime
    from app.services.safe_load_assessment import assess
    from app.services.safe_load import license_key
    row=SimpleNamespace(license_digest=license_key('TEST1234','KS'),driver_name='John Doe Jr',license_expires=datetime(2030,1,1),vin='1HGCM82633A004352')
    reasons,summary=assess(row,{'fields':{'DAJ':'KS','DCS':'DOE'},'errors':['Unreadable first name and number'],'source':'local_ocr'},'', ['VIN unreadable'])
    assert reasons and summary['evidence_quality']=='unreadable_or_incomplete'
    assert summary['check_outcomes']['name']=='incomplete'
    fields={'DAQ':'TEST1234','DAJ':'KS','DAC':'JOHN ALAN','DCS':'DOE','DBA':'01012035'}
    reasons,summary=assess(row,{'fields':fields,'errors':[],'source':'pdf417'},row.vin,[])
    assert not reasons and summary['renewal_accepted']
    fields['DAQ']='DIFFERENT1234'
    reasons,summary=assess(row,{'fields':fields,'errors':[],'source':'pdf417'},row.vin,[])
    assert reasons and summary['evidence_quality']=='data_mismatch'
