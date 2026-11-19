"""Regression tests for conservative front-card name recovery."""
from app.services.safe_load_images import _address_anchored_name_fallback, _targeted_front_regions
from PIL import Image
import io


def test_name_anchored_to_address():
    source='OKLAHOMA\nMONTERVILLE\nTHOM ALLEN, JR\n8 1722 DENIM LN\nENID OK'
    assert _address_anchored_name_fallback(source)=={'DCS':'MONTERVILLE','DAC':'THOM ALLEN, JR'}


def test_no_unanchored_name_guess():
    assert _address_anchored_name_fallback('MONTERVILLE\nTHOM ALLEN JR\nEXP 03/31/2030')=={'DCS':'','DAC':''}


def test_no_multiple_conflicting_pairs():
    text='SMITH\nJANE\n8 123 MAIN ST\nOTHER\nPERSON\n8 456 OTHER ST'
    assert _address_anchored_name_fallback(text)=={'DCS':'','DAC':''}


def test_regions_only_for_horizontal_card():
    output=io.BytesIO();Image.new('RGB',(1000,600),'white').save(output,'PNG')
    assert len(_targeted_front_regions(output.getvalue()))==2
    output=io.BytesIO();Image.new('RGB',(600,1000),'white').save(output,'PNG')
    assert _targeted_front_regions(output.getvalue())==[]
