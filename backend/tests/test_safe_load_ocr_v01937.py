from app.services.safe_load_images import _name_region_fallback, parse_license_text


def test_numbered_license_names_without_punctuation():
    result = _name_region_fallback('OKLAHOMA\n1 MONTERVILLE\n2 THOM ALLEN, JR\n8 1722 DENIM LN')
    assert result == {'DCS': 'MONTERVILLE', 'DAC': 'THOM ALLEN, JR'}


def test_numbered_license_names_with_punctuation():
    result = _name_region_fallback('1. MONTERVILLE\n2. THOM ALLEN, JR')
    assert result == {'DCS': 'MONTERVILLE', 'DAC': 'THOM ALLEN, JR'}


def test_license_number_and_expiry_are_label_anchored():
    result = parse_license_text('OKLAHOMA\n4d DLN C083936230 4b EXP 03/31/2030\n1. MONTERVILLE\n2. THOM ALLEN, JR')
    assert result['DAQ'] == 'C083936230'
    assert result['DBA'] == '03312030'
