"""Fictional VIN fixtures only; exact reading without assignment-driven corrections."""
import io
import pytest
from PIL import Image,ImageDraw,ImageFont
from app.services.safe_load_images import vehicle
VIN='1HGCM82633A004352'

def plate(background=False,angle=0,values=None):
    im=Image.new('RGB',(1300,1100) if background else (1300,220),(35,45,55))
    d=ImageDraw.Draw(im);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',52)
    if background:d.ellipse((100,80,480,460),fill='white')
    for i,value in enumerate(values or [VIN]):d.text((80,570+i*90 if background else 70+i*65),value,font=font,fill='white')
    b=io.BytesIO();im.rotate(angle,expand=True).save(b,'JPEG',quality=94);return b.getvalue()

@pytest.mark.parametrize('background,angle',[(False,0),(True,0),(True,90)])
def test_exact_vin_from_strip_or_rotated_full_photo(background,angle):
    assert vehicle(plate(background,angle))==VIN

def test_two_vins_are_never_treated_as_one():
    with pytest.raises(ValueError,match='Multiple'):vehicle(plate(False,values=[VIN,'1HGCM82633A004353']))

def test_reader_does_not_guess_missing_or_invalid_characters():
    with pytest.raises(ValueError):vehicle(plate(False,values=['1HGCM82633A00435']))

def test_letter_spacing_only_combines_a_complete_standalone_vin_line():
    from app.services.safe_load_images import vin_candidates
    assert vin_candidates('VIN: '+' '.join(VIN))=={VIN}
    assert not vin_candidates('VIN: '+VIN[:-1])
    assert not vin_candidates(VIN.replace('1','I',1))
    assert not vin_candidates('VIN: 1HGC\nM82633A004352')

def test_neural_reader_recovers_dirty_italic_label_locally():
    import random
    from app.services.safe_load_images import vehicle_evidence
    im=Image.new('RGB',(1000,300),(99,112,108));d=ImageDraw.Draw(im);rng=random.Random(42)
    for _ in range(550):
        x,y=rng.randrange(1000),rng.randrange(300);radius=rng.randrange(1,4)
        d.ellipse((x,y,x+radius,y+radius),fill=(160,167,160))
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Oblique.ttf',56)
    d.text((100,110),VIN,font=font,fill=(244,248,242))
    b=io.BytesIO();im.save(b,'JPEG',quality=80)
    result=vehicle_evidence(b.getvalue())
    assert result['vin']==VIN and result['reader']=='local_neural_ocr'

def test_neural_prediction_needs_no_network_and_is_not_given_an_expected_vin(monkeypatch):
    import socket
    from app.services.safe_load_vin_neural import candidates
    def blocked(*args,**kwargs):raise AssertionError('Network must not be used for OCR')
    monkeypatch.setattr(socket.socket,'connect',blocked)
    assert VIN in candidates(Image.open(io.BytesIO(plate())))
