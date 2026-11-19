"""Regression tests for AAMVA front-of-license name layouts and expiration."""
from app.services.safe_load_images import _front_name_components,_expiration_anchored,_supplement_front

def test_name_surname_given_middle_suffix():
    source='DOB 03/30/1984\n1. MONTERVILLE\n2. THOM ALLEN, JR\n8. 1722 DENIM LN\nENID OK'
    got=_front_name_components(source)
    assert got['DCS']=='MONTERVILLE'
    assert got['DAC']=='THOM ALLEN, JR'

def test_separate_middle_name():
    source='DOB 03/30/1984\n1. SMITH\n2. JANE\n3. MARIE\n8. 123 MAIN ST'
    got=_front_name_components(source)
    assert got=={'DCS':'SMITH','DAC':'JANE','DAD':'MARIE'}

def test_unanchored_names_not_assumed():
    assert _front_name_components('SMITH\nJANE\nMARIE')=={'DCS':'','DAC':'','DAD':''}

def test_expiration_not_confused_with_dob_or_issue():
    source='DOB 03/30/1984 4a ISS 05/11/2026 4b EXP 03/31/2030'
    assert _expiration_anchored(source)=='03312030'

def test_expiration_missing_no_guess():
    assert _expiration_anchored('DOB 03/30/1984 ISS 05/11/2026')==''

def test_merge_all_name_parts():
    source='DOB 03/30/1984\n1. SMITH\n2. JANE\n3. MARIE\n8. 123 MAIN ST\n4b EXP 03/31/2030'
    result=_supplement_front({},source)
    assert result['DCS']=='SMITH' and result['DAC']=='JANE' and result['DAD']=='MARIE'
    assert result['DBA']=='03312030'
