"""Regression coverage for v0.19.40 numbered name and expiration OCR."""
from app.services.safe_load_images import _numbered_name_pair, _expiry_label_date, _supplement_front

def test_numbered_name_fields():
    result = _supplement_front({}, 'DOB 03/30/1984\n1. MONTERVILLE\n2. THOM ALLEN, JR\n8. 1722 DENIM LN\n4b EXP 03/31/2030')
    assert result['DCS'] == 'MONTERVILLE'
    assert result['DAC'] == 'THOM ALLEN, JR'
    assert result['DBA'] == '03312030'

def test_ocr_misread_numbered_given_name():
    result = _numbered_name_pair('1 MONTERVILLE\n7. THOM ALLEN, JR\n8. 1722 DENIM LN')
    assert result['DCS'] == 'MONTERVILLE'
    assert result['DAC'] == 'THOM ALLEN, JR'

def test_no_unanchored_identity_guess():
    assert _numbered_name_pair('MOODY\nCOBY DEVEN\n123 MAIN ST')['DCS'] == ''

def test_expiration_not_issue_or_dob():
    assert _expiry_label_date('DOB 03/30/1984 ISS 05/11/2026') == ''
    assert _expiry_label_date('4b EXP 03/31/2030') == '03312030'
