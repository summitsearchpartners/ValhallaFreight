"""Conservative local document orientation; no identity/expected values are used."""
import hashlib,io,re,subprocess,threading,time
from collections import OrderedDict
from PIL import Image,ImageOps

_cache=OrderedDict();_lock=threading.Lock()

def correction(raw):
    key=hashlib.sha256(raw).hexdigest()
    with _lock:
        if key in _cache:return _cache[key]
    image=ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert('L')
    image.thumbnail((1600,1600));image=ImageOps.autocontrast(image)
    output=io.BytesIO();image.save(output,'PNG')
    angle=None
    try:
        from app.services.safe_load_vin_neural import document_angle
        angle=document_angle(image)
    except Exception:pass
    if angle is not None:
        with _lock:
            _cache[key]=angle
            while len(_cache)>256:_cache.popitem(last=False)
        return angle
    angle=0
    try:
        result=subprocess.run(['tesseract','stdin','stdout','--psm','0','--dpi','150'],input=output.getvalue(),capture_output=True,timeout=2,check=True)
        report=result.stdout.decode('utf-8',errors='replace')
        rotate=re.search(r'Rotate:\s*(0|90|180|270)\b',report);confidence=re.search(r'Orientation confidence:\s*([0-9.]+)',report)
        if rotate and confidence and float(confidence.group(1))>=8:angle=int(rotate.group(1))
        else:angle=_text_angle(image)
    except (OSError,subprocess.SubprocessError):angle=_text_angle(image)
    with _lock:
        _cache[key]=angle
        while len(_cache)>256:_cache.popitem(last=False)
    return angle

def _text_angle(image):
    from app.services.safe_load_images import parse_license_text
    candidates=[];deadline=time.monotonic()+7
    for clockwise in [0,90,180,270]:
        if time.monotonic()>deadline:return 0
        output=io.BytesIO();image.rotate(-clockwise,expand=True).save(output,'PNG')
        try:
            result=subprocess.run(['tesseract','stdin','stdout','-l','eng','--psm','11','--dpi','150'],input=output.getvalue(),capture_output=True,timeout=2,check=True)
        except (OSError,subprocess.SubprocessError):return 0
        source=result.stdout.decode('utf-8',errors='replace').upper()
        fields=parse_license_text(source)
        complete=sum(bool(fields.get(k)) for k in ['DAQ','DAC','DCS','DBA','DAJ'])
        words=set(re.findall(r'[A-Z]+',source))&{'DRIVER','LICENSE','FIRST','LAST','NAME','EXPIRATION','ISSUING','STATE','RESTRICTIONS','ENDORSEMENTS'}
        candidates.append((complete*4+len(words),complete,clockwise))
    ranked=sorted(candidates,reverse=True)
    # No forced rotation on photos with too little or conflicting readable text.
    return ranked[0][2] if ranked[0][1]>=2 and ranked[0][0]-ranked[1][0]>=4 else 0

def upright(raw):
    """Derived display or new-upload normalization; never rewrites stored files."""
    angle=correction(raw)
    if not angle:return raw
    image=Image.open(io.BytesIO(raw)).rotate(-angle,expand=True)
    output=io.BytesIO();image.save(output,'JPEG',quality=92)
    result=output.getvalue()
    with _lock:_cache[hashlib.sha256(result).hexdigest()]=0
    return result

def normalize_license(raw,allow_blank=False):
    from app.services.safe_load_images import normalize
    return upright(normalize(raw,allow_blank=allow_blank))
