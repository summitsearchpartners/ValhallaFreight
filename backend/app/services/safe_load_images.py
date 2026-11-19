"""Local image normalization, barcode decoding and conservative OCR. No remote ID upload."""
import io,re,subprocess,time,os,shutil,logging
from datetime import datetime
from PIL import Image,ImageOps,ImageStat

def normalize(raw,limit=2400,allow_blank=False):
    try:
        image=Image.open(io.BytesIO(raw))
        if image.format not in {'JPEG','PNG','WEBP'} or image.width*image.height>16000000:raise ValueError()
        image=ImageOps.exif_transpose(image)
        if image.mode in {'RGBA','LA'} or 'transparency' in image.info:
            rgba=image.convert('RGBA');background=Image.new('RGBA',rgba.size,'white');background.alpha_composite(rgba);image=background.convert('RGB')
        else:image=image.convert('RGB')
        image.thumbnail((limit,limit))
        stats=ImageStat.Stat(image.convert('L'))
        if stats.mean[0]<3 and not allow_blank:raise ValueError('blank')
        output=io.BytesIO();image.save(output,'JPEG',quality=92)
        return output.getvalue()
    except Exception:raise ValueError('Photo is blank, unsupported or too large. Retake a well-lit JPEG/PNG/WebP photo, maximum 16 megapixels.')

def _tesseract_executable():
    """Find the offline OCR binary on Windows/Linux without requiring PATH edits."""
    choices = [os.environ.get('SAFE_LOAD_TESSERACT_PATH'), os.environ.get('TESSERACT_CMD'), shutil.which('tesseract')]
    if os.name == 'nt':
        for root in (os.environ.get('ProgramFiles'), os.environ.get('ProgramFiles(x86)'), os.environ.get('LOCALAPPDATA')):
            if root:
                choices.append(os.path.join(root, 'Tesseract-OCR', 'tesseract.exe'))
    # Common winget/Chocolatey/Scoop installations on Windows.
    if os.name == 'nt':
        home = os.path.expanduser('~')
        choices.extend([
            os.path.join(home, 'scoop', 'apps', 'tesseract', 'current', 'tesseract.exe'),
            os.path.join(os.environ.get('ChocolateyInstall', r'C:\\ProgramData\\chocolatey'), 'bin', 'tesseract.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', home), 'Programs', 'Tesseract-OCR', 'tesseract.exe'),
        ])
    choices.extend(['/usr/bin/tesseract', '/usr/local/bin/tesseract'])
    return next((p for p in choices if p and os.path.isfile(p)), None)


def text(raw,psm=6,timeout=12):
    executable = _tesseract_executable()
    if not executable:
        raise ValueError('Local Tesseract OCR is not installed or discoverable. Install Tesseract OCR with English language data or set SAFE_LOAD_TESSERACT_PATH. Freight remains held for broker review.')
    try:
        result=subprocess.run([executable,'stdin','stdout','-l','eng','--psm',str(psm)],input=raw,capture_output=True,timeout=timeout,check=True)
        return result.stdout.decode('utf-8',errors='replace').upper()
    except (OSError,subprocess.SubprocessError) as exc:
        logging.getLogger(__name__).warning('Local Tesseract OCR failed: %s',exc)
        raise ValueError('Local photo reader unavailable or timed out. Verify Tesseract English language data. Freight remains blocked; contact the broker.') from exc

def barcodes(raw,license_only=False):
    import zxingcpp
    image=ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert('L')
    enhanced=ImageOps.expand(ImageOps.autocontrast(image),border=24,fill=255)
    variants=[image,enhanced]
    if max(image.size)<1800:
        variants.append(enhanced.resize((enhanced.width*2,enhanced.height*2),Image.Resampling.LANCZOS))
    variants.append(ImageOps.invert(enhanced))
    found=set()
    for variant in variants:
        for mode in [zxingcpp.Binarizer.LocalAverage,zxingcpp.Binarizer.GlobalHistogram]:
            options={'formats':zxingcpp.BarcodeFormat.PDF417} if license_only else {}
            for result in zxingcpp.read_barcodes(variant,binarizer=mode,try_rotate=True,try_downscale=True,**options):
                if result.valid:
                    payload=result.bytes
                    try:value=payload.decode('utf-8')
                    except UnicodeDecodeError:value=payload.decode('latin-1')
                    found.add(value)
        if found:break
    return sorted(found)

def unique(pattern,source,label):
    found={re.sub(r'\s+',' ',v).strip() for v in re.findall(pattern,source,re.M|re.I)}
    if len(found)!=1:raise ValueError(f'{label} could not be read unambiguously. Retake the photo with all printed fields in focus.')
    return found.pop()

def optional(pattern,source):
    try:return unique(pattern,source,'Field')
    except ValueError:return ''

def parse_license_text(source):
    """Parse independent, explicitly labelled AAMVA front-card fields.

    A line may contain multiple numbered fields, and OCR can introduce spacing
    around labels. Never infer an ID from unrelated numbers or resolve conflicts
    by choosing whichever value happens to match the dispatcher assignment.
    """
    source = source.upper().replace('’', "'").replace('\r', '')
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in source.splitlines()]
    fields = {'DAQ':'', 'DAC':'', 'DCS':'', 'DBA':'', 'DAJ':''}
    patterns = {
        'DAQ': r'(?:\bDL\s*(?:NUMBER|NO\.?|#)|\bLICEN[CS]E\s*(?:NUMBER|NO\.?|#)|(?<![A-Z0-9])4\s*D\.?|(?<![A-Z0-9])DLN\b)',
        'DAC': r'(?:\bFIRST\s*NAME\b|(?<![A-Z0-9])2\s*\.|\bFN\s*:)',
        'DCS': r'(?:\bLAST\s*NAME\b|(?<![A-Z0-9])1\s*\.|\bLN\s*:)',
        'DBA': r'(?:\bEXP(?:IRATION|IRES)?(?:\s*DATE)?\b|(?<![A-Z0-9])4\s*B\b(?:\s*EXP)?)',
        'DAJ': r'\bISSUING\s*STATE\b',
    }
    combined = re.compile('|'.join('(?P<'+key+'>'+pattern+')' for key,pattern in patterns.items()))
    found = {key:set() for key in fields}
    for index,line in enumerate(lines):
        matches=list(combined.finditer(line))
        for position,match in enumerate(matches):
            key=match.lastgroup
            end=matches[position+1].start() if position+1<len(matches) else len(line)
            fragment=line[match.end():end].strip(' .:#-')
            if not fragment and index+1<len(lines):fragment=lines[index+1]
            if key=='DAQ':
                # Numbered cards often put the DOB immediately after the license:
                # '4d. TEST1234 3. 01/01/1990'.  The '3.' is a separate
                # printed field, not part of the license number.  Do not strip
                # arbitrary digits: only explicit numbered-field boundaries.
                fragment=re.split(r'\s+(?:(?:[1-9]|4[A-C])\s*[.:]\s*|4[A-C]\s+(?:ISS|EXP)\b)',fragment,maxsplit=1,flags=re.I)[0].strip()
                # Tesseract sometimes separates a license's letter prefix and digits
                # (TEST 1234). Join only within the explicitly labelled field, and
                # never across another labelled field or a date-like token.
                tokens=re.findall(r'[A-Z0-9]+',fragment)
                if tokens and re.match(r'^[A-Z0-9-]{4,30}$',tokens[0]):
                    value=tokens[0]
                    if (len(tokens)>1 and len(tokens)==2 and
                        re.fullmatch(r'[A-Z]+',tokens[0]) and
                        re.fullmatch(r'[0-9]{2,12}',tokens[1]) and
                        len(tokens[0])+len(tokens[1])<=30):
                        value=tokens[0]+tokens[1]
                    # Do not accept trailing prose as an identity value.
                    if len(tokens)==1 or value!=tokens[0]:
                        found[key].add(value)
            elif key in ('DAC','DCS'):
                candidate=re.match(r"^([A-Z][A-Z . ,\'-]{0,65}?)(?=\s{2,}|$|\s+\d|\s+(?:ISS|EXP|DL|4[A-D])\b)",fragment)
                if not candidate:
                    candidate=re.match(r"^([A-Z][A-Z . ,\'-]{0,65})$",fragment)
                if candidate:
                    value=candidate.group(1).strip(' .,')
                    if value and not any(word in value.split() for word in ('RESTRICTIONS','ENDORSEMENTS','LICENSE','DRIVER','ISS','EXP','NONE')):
                        found[key].add(value)
            elif key=='DBA':
                candidate=re.search(r'(?<!\d)(\d{2}[/.-]\d{2}[/.-]\d{4}|\d{4}-\d{2}-\d{2})(?!\d)',fragment)
                if candidate:
                    date=candidate.group(1).replace('.','/').replace('-','/')
                    try:found[key].add(datetime.strptime(date,'%Y/%m/%d' if len(date.split('/')[0])==4 else '%m/%d/%Y').strftime('%m%d%Y'))
                    except ValueError:pass
            elif key=='DAJ':
                candidate=re.match(r'^([A-Z]{2})\b',fragment)
                if candidate:found[key].add(candidate.group(1))
    try:
        from app.api.routes.truckload import STATES
    except ImportError:
        STATES={'OK':'Oklahoma','KS':'Kansas','MO':'Missouri','TX':'Texas','CA':'California'}
    if not found['DAJ']:
        state_names={code for code,name in STATES.items() if re.search(r'\b'+re.escape(name.upper())+r'\b',source)}
        if len(state_names)==1:found['DAJ']=state_names
    for key,values in found.items():
        if len(values)==1:fields[key]=next(iter(values))
    return fields

def _front_card_fallback(source):
    """Read common AAMVA front layouts when OCR drops tiny numeric field labels.

    Only take values in anchored card regions; never guess missing identity values
    from arbitrary numbers or use a dispatcher-provided identity as a hint.
    """
    lines=[re.sub(r'\s+',' ',v).strip(' .:;|') for v in source.upper().splitlines()]
    lines=[v for v in lines if v]
    result={'DAQ':'','DAC':'','DCS':'','DBA':''}
    # Number directly below the printed DRIVER LICENSE header or next to LIC NO.
    for i,line in enumerate(lines):
        if re.search(r'\b(?:DRIVER\s+LICEN[CS]E|LICEN[CS]E\s+(?:NO|NUMBER)|DL\s*(?:NO|NUMBER))\b',line):
            nearby=lines[i:i+3]
            candidates=[]
            for v in nearby:
                v=re.sub(r'^.*?(?:LICEN[CS]E\s*(?:NO|NUMBER)|DL\s*(?:NO|NUMBER))\s*[:#.]?','',v)
                # Date-like strings are never license numbers.
                for token in re.findall(r'(?<![A-Z0-9])[A-Z0-9]{7,15}(?![A-Z0-9])',v):
                    if re.search(r'\d',token) and not re.fullmatch(r'(?:19|20)\d{6}',token) and token not in ('LICENSE','DRIVER'):
                        candidates.append(token)
            if len(set(candidates))==1:result['DAQ']=candidates[0]
            break
    # Names printed immediately after DOB, before street address. OCR often
    # drops the small "1" and "2" labels on high-security license stock.
    dob_index=next((i for i,line in enumerate(lines) if re.search(r'\b(?:DOB|BIRTH)\b',line)),None)
    if dob_index is not None:
        region=lines[dob_index+1:dob_index+5]
        names=[]
        for line in region:
            candidate=re.sub(r'^(?:1|2)\s*[.:]\s*','',line)
            if (re.fullmatch(r"[A-Z][A-Z ,.'-]{1,45}",candidate) and
                not any(word in candidate.split() for word in ('NONE','RESTR','CLASS','ISS','EXP','DRIVER','LICENSE','OKLAHOMA','ADDRESS','ENID'))):
                names.append(candidate.strip(' ,'))
            elif re.search(r'\d{2,}',candidate):break
        if len(names)>=2:
            result['DCS']=names[0]
            result['DAC']=names[1]
    # Expiration must have an explicit EXP label; never borrow issue or DOB.
    for line in lines:
        match=re.search(r'\bEXP(?:IRATION|IRES)?\b[^0-9]{0,12}(\d{2}[/.-]\d{2}[/.-]\d{4})',line)
        if match:
            try:result['DBA']=datetime.strptime(match.group(1).replace('.','/').replace('-','/'),'%m/%d/%Y').strftime('%m%d%Y')
            except ValueError:pass
    return result


def _name_region_fallback(source):
    """Read numbered AAMVA name lines even when small labels are split/missed.

    Only accept adjacent labelled surname/given-name lines. Never infer a
    person's identity from a dispatcher record or an unlabelled OCR guess.
    """
    lines=[re.sub(r'\s+',' ',v.upper()).strip() for v in source.splitlines()]
    lines=[v for v in lines if v]
    found={'DCS':set(),'DAC':set()}
    for i,line in enumerate(lines):
        for key,number in (('DCS','1'),('DAC','2')):
            match=re.search(r'(?<![A-Z0-9])'+number+r'\s*[.:]?\s+([A-Z][A-Z ,\'-]{1,48})$',line)
            if not match and re.fullmatch(number+r'\s*[.:]?',line) and i+1<len(lines):
                match=re.match(r'^([A-Z][A-Z ,\'-]{1,48})$',lines[i+1])
            if match:
                candidate=match.group(1).strip(' ,.-')
                if not any(v in candidate.split() for v in ('NONE','LICENSE','CLASS','EXP','ISS','RESTR','ADDRESS')):
                    found[key].add(candidate)
    return {key:next(iter(values)) if len(values)==1 else '' for key,values in found.items()}


def _address_anchored_name_fallback(source):
    """Recover a two-line name immediately above a labelled street address.

    The layout anchor prevents mistaking random uppercase card text for a name.
    This is deliberately conservative: no guess if multiple name pairs qualify.
    """
    lines=[re.sub(r'\s+',' ',v.upper()).strip(' .:;|') for v in source.splitlines()]
    lines=[v for v in lines if v]
    choices=set()
    excluded={'NONE','CLASS','RESTR','ENDOR','DRIVER','LICENSE','OKLAHOMA','EXP','ISS','DOB','SEX','EYES','HAZ','HEIGHT','WEIGHT','USA'}
    def clean_name(value):
        value=re.sub(r'^(?:[12]\s*[.:]?\s*)','',value).strip(' ,.-')
        if not re.fullmatch(r"[A-Z][A-Z ,.'-]{1,45}",value):return ''
        if any(token in excluded for token in value.replace(',',' ').split()):return ''
        return value
    for i,line in enumerate(lines):
        # The next line must be the printed street address (8/8a is AAMVA address).
        if not re.match(r'^(?:8\s*[A-Z]?\s*[.:]?\s*)?\d{1,6}\s+[A-Z]',line):continue
        if i<2:continue
        last=clean_name(lines[i-2]);first=clean_name(lines[i-1])
        if last and first and len(last.split())<=3 and len(first.split())<=4:
            choices.add((last,first))
    if len(choices)!=1:return {'DCS':'','DAC':''}
    last,first=choices.pop()
    return {'DCS':last,'DAC':first}


def _targeted_front_regions(raw):
    """Focused reads of name and date regions, avoiding a full OCR sweep.

    Regions are layout hints, not an identity assertion; the existing anchored
    parsers must still validate the OCR output. Only used for upright cards.
    """
    im=ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert('L')
    w,h=im.size
    if w<400 or h<220 or w<h:return []
    # Common horizontal US ID: name/address middle-left, DL/expiry top-right.
    regions=[(int(.30*w),int(.34*h),int(.91*w),int(.79*h)),
             (int(.37*w),int(.08*h),int(.97*w),int(.40*h))]
    prepared=[]
    for bounds in regions:
        crop=ImageOps.autocontrast(im.crop(bounds),cutoff=1)
        if crop.width<1400:
            factor=min(2.0,1400/max(crop.width,1))
            crop=crop.resize((int(crop.width*factor),int(crop.height*factor)),Image.Resampling.LANCZOS)
        out=io.BytesIO();crop.save(out,'PNG');prepared.append(out.getvalue())
    return prepared


def _merge_license_observations(first,second):
    """Only supplement missing fields when observations do not conflict."""
    return {key:(first.get(key) or second.get(key) or '') for key in ('DAQ','DAJ','DAC','DCS','DBA')}


def _merge_front_fields(primary,secondary):
    """Conservative fill: never replace an already-read conflicting value."""
    return {key:(primary.get(key) or secondary.get(key,'') or '') for key in ('DAQ','DAJ','DAC','DCS','DBA')}

def rotated(raw,angle):
    if angle==0:return raw
    output=io.BytesIO();Image.open(io.BytesIO(raw)).rotate(angle,expand=True).save(output,'PNG');return output.getvalue()

def _license_ocr_variants(raw):
    """One inexpensive OCR image per orientation; no repeated contrast/PSM sweep."""
    original=ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert('L')
    for angle in (0,90,270,180):
        oriented=original.rotate(angle,expand=True)
        # Avoid huge images and expensive upscaling; 1600px is enough for most cards.
        oriented.thumbnail((1800,1800))
        prepared=ImageOps.autocontrast(oriented,cutoff=1)
        output=io.BytesIO();prepared.save(output,'PNG')
        yield angle,output.getvalue()


def _ocr_license_candidates(raw):
    """Time-bounded OCR: one normal pass plus one layout pass if incomplete."""
    deadline=time.monotonic()+16
    best={};best_angle=0;best_score=-1
    for angle,prepared in _license_ocr_variants(raw):
        remaining=deadline-time.monotonic()
        if remaining<1:break
        try:recognized=text(prepared,11,timeout=min(5,max(1,int(remaining))))
        except ValueError:continue
        parsed=parse_license_text(recognized)
        candidate=_merge_front_fields(parsed,_front_card_fallback(recognized))
        candidate=_merge_license_observations(candidate,_name_region_fallback(recognized))
        candidate=_merge_license_observations(candidate,_address_anchored_name_fallback(recognized))
        # PSM 11 can fragment numbered names. A single PSM 6 pass is a
        # bounded fallback, not a full multi-enhancement OCR sweep.
        if (not candidate.get('DAC') or not candidate.get('DCS') or not candidate.get('DBA')) and angle==0:
            remaining=deadline-time.monotonic()
            if remaining>=2:
                try:
                    alternate=text(prepared,6,timeout=min(4,max(1,int(remaining))))
                    other=_merge_front_fields(parse_license_text(alternate),_front_card_fallback(alternate))
                    other=_merge_license_observations(other,_name_region_fallback(alternate))
                    other=_merge_license_observations(other,_address_anchored_name_fallback(alternate))
                    candidate=_merge_license_observations(candidate,other)
                except ValueError:pass
        # One targeted region pass on upright, incomplete front-card reads.
        # Stay inside the existing global deadline; no remote OCR service.
        if angle==0 and (not candidate.get('DAC') or not candidate.get('DCS') or not candidate.get('DBA')):
            for region in _targeted_front_regions(raw):
                remaining=deadline-time.monotonic()
                if remaining<2:break
                try:region_text=text(region,6,timeout=min(3,max(1,int(remaining))))
                except ValueError:continue
                supplemental=_merge_front_fields(parse_license_text(region_text),_front_card_fallback(region_text))
                supplemental=_merge_license_observations(supplemental,_name_region_fallback(region_text))
                supplemental=_merge_license_observations(supplemental,_address_anchored_name_fallback(region_text))
                candidate=_merge_license_observations(candidate,supplemental)
                if candidate.get('DAC') and candidate.get('DCS') and candidate.get('DBA'):break
        score=sum(2 if candidate.get(k) else 0 for k in ('DAQ','DAC','DCS','DBA'))+int(bool(candidate.get('DAJ')))
        if score>best_score:best,best_angle,best_score=candidate,angle,score
        if all(candidate.get(k) for k in ('DAQ','DAC','DCS','DBA','DAJ')):break
    return best,best_angle

def license_evidence(raw):
    from app.services.safe_load import decode_license
    codes=[]
    for value in barcodes(raw,license_only=True):
        try:codes.append(decode_license(value))
        except ValueError:pass
    if codes:
        if any(c!=codes[0] for c in codes):return {'fields':{},'source':'pdf417','errors':['Multiple different licenses found in the photo']}
        best=codes[0];source='pdf417'
    else:
        source='local_ocr';best={};angle=0
        if not _tesseract_executable():
            return {'fields':{},'source':source,'errors':['Local Tesseract OCR is missing. Install the offline OCR engine and English language data; freight remains held for broker review.']}
        best,angle=_ocr_license_candidates(raw)
    labels={'DAQ':'License number','DAJ':'Issuing state','DAC':'First name','DCS':'Last name','DBA':'Expiration date'}
    errors=[name+' could not be read unambiguously from the onsite ID photo' for k,name in labels.items() if not best.get(k)]
    return {'fields':best,'source':source,'errors':errors,'rotation_degrees':(360-angle)%360 if source=='local_ocr' else 0}

def license_data(raw):
    result=license_evidence(raw)
    if result['errors']:raise ValueError('; '.join(result['errors']))
    return result['fields']

def vin_regions(image):
    """Find text-line regions without using the assigned VIN as a hint."""
    import cv2,numpy as np
    gray=np.asarray(image.convert('L'))
    # Both dark print on a light label and bright etched text on dark glass.
    candidates=[]
    for operation in [cv2.MORPH_BLACKHAT,cv2.MORPH_TOPHAT]:
        detail=cv2.morphologyEx(gray,operation,cv2.getStructuringElement(cv2.MORPH_RECT,(25,7)))
        _,mask=cv2.threshold(detail,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        joined=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_RECT,(23,3)))
        contours,_=cv2.findContours(joined,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            x,y,w,h=cv2.boundingRect(contour)
            if w>=max(60,image.width*.22) and 5<=h<=image.height*.3 and w/h>=3:
                pad=max(4,round(h*.4))
                box=(max(0,x-pad),max(0,y-pad),min(image.width,x+w+pad),min(image.height,y+h+pad))
                if box not in candidates:candidates.append(box)
    return [image.crop(box) for box in sorted(candidates,key=lambda b:b[2]-b[0],reverse=True)[:4]]

def vin_ocr_image(image):
    image=ImageOps.autocontrast(image.convert('L'))
    scale=max(1,min(4,1800/image.width))
    if scale>1:image=image.resize((round(image.width*scale),round(image.height*scale)),Image.Resampling.LANCZOS)
    image=ImageOps.expand(image,border=20,fill=255)
    output=io.BytesIO();image.save(output,'PNG');return output.getvalue()

def vin_candidates(source):
    pattern=r'(?<![A-Z0-9])[A-HJ-NPR-Z0-9]{17}(?![A-Z0-9])'
    values=set(re.findall(pattern,source.upper()))
    # Etched/letter-spaced VINs may be emitted with spaces. Only join a whole
    # standalone line, never arbitrary nearby text or look-alike characters.
    for line in source.upper().splitlines():
        line=re.sub(r'^VIN[ :#]*','',line.strip())
        if re.fullmatch(r'[A-HJ-NPR-Z0-9](?:[ \t]*[A-HJ-NPR-Z0-9]){16}',line):values.add(re.sub(r'[ \t]','',line))
    return values

def _legacy_vehicle(raw):
    from app.services.safe_load import vin
    values=set()
    for candidate in barcodes(raw):
        try:values.add(vin(candidate))
        except ValueError:pass
    if len(values)>1:raise ValueError('Multiple different VINs were read. Photograph only the arriving truck VIN label.')
    if values:return values.pop()
    deadline=time.monotonic()+24
    image=ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert('L')
    # A framed VIN is a single line. Full photos also need text localization to
    # exclude the windshield/glare/background before single-line recognition.
    for angle in [0,90,270,180]:
        oriented=image.rotate(angle,expand=True)
        regions=vin_regions(oriented)
        # Prefer localized text. Whole-frame passes are fallbacks, not competing
        # guesses when the localized VIN has already been read.
        for jobs in [[(region,7) for region in regions],[(oriented,11),(oriented,6)]]:
            for region,psm in jobs:
                if time.monotonic()>deadline:break
                try:source=text(vin_ocr_image(region),psm)
                except ValueError:continue
                values.update(vin_candidates(source))
            if values or time.monotonic()>deadline:break
        if values or time.monotonic()>deadline:break
    if len(values)>1:raise ValueError('Multiple different VINs were read. Retake a straight-on photo of only the full VIN label.')
    if not values:raise ValueError('A single 17-character VIN could not be read. Fill the VIN outline with all 17 characters, check the cropped preview and retake without glare. Freight remains held for broker review.')
    return values.pop()


def vehicle_evidence(raw):
    from app.services.safe_load import vin
    values=set()
    for candidate in barcodes(raw):
        try:values.add(vin(candidate))
        except ValueError:pass
    if len(values)>1:raise ValueError('Multiple different VINs were read. Photograph only the arriving truck VIN label.')
    if values:return {'vin':values.pop(),'reader':'local_barcode'}
    try:
        from app.services.safe_load_vin_neural import candidates
        values=candidates(Image.open(io.BytesIO(raw)))
    except Exception:
        # Preserve offline legacy reading if the local model runtime is unavailable.
        import logging
        logging.getLogger(__name__).warning('Local neural VIN reader unavailable; using conservative legacy OCR')
        values=set()
    if len(values)>1:raise ValueError('Multiple different VINs were read. Retake a photo showing only the arriving truck VIN label.')
    if values:return {'vin':values.pop(),'reader':'local_neural_ocr'}
    return {'vin':_legacy_vehicle(raw),'reader':'local_tesseract'}


def vehicle(raw):
    return vehicle_evidence(raw)['vin']
