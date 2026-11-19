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


def text(raw,psm=6):
    executable = _tesseract_executable()
    if not executable:
        raise ValueError('Local Tesseract OCR is not installed or discoverable. Install Tesseract OCR with English language data or set SAFE_LOAD_TESSERACT_PATH. Freight remains held for broker review.')
    try:
        result=subprocess.run([executable,'stdin','stdout','-l','eng','--psm',str(psm)],input=raw,capture_output=True,timeout=12,check=True)
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
    from app.api.routes.truckload import STATES
    if not found['DAJ']:
        state_names={code for code,name in STATES.items() if re.search(r'\b'+re.escape(name.upper())+r'\b',source)}
        if len(state_names)==1:found['DAJ']=state_names
    for key,values in found.items():
        if len(values)==1:fields[key]=next(iter(values))
    return fields

def rotated(raw,angle):
    if angle==0:return raw
    output=io.BytesIO();Image.open(io.BytesIO(raw)).rotate(angle,expand=True).save(output,'PNG');return output.getvalue()

def _license_ocr_variants(raw):
    """Try orientation and contrast, retaining the original evidence unchanged."""
    original=ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert('L')
    for angle in (0,90,270,180):
        oriented=original.rotate(angle,expand=True)
        scale=min(3,max(1,2000/max(oriented.width,1)))
        if scale>1:
            oriented=oriented.resize((round(oriented.width*scale),round(oriented.height*scale)),Image.Resampling.LANCZOS)
        contrast=ImageOps.autocontrast(oriented)
        for variant in (contrast,ImageOps.autocontrast(contrast,cutoff=2)):
            output=io.BytesIO();variant.save(output,'PNG')
            yield angle,output.getvalue()


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
        source='local_ocr';best={};deadline=time.monotonic()+55
        # OCR is mandatory for a front-only ID. Never fabricate identity fields,
        # and never turn an unreadable document into an automatic release.
        if not _tesseract_executable():
            return {'fields':{},'source':source,'errors':['Local Tesseract OCR is missing. Install the offline OCR engine and English language data; freight remains held for broker review.']}
        observed={key:set() for key in ('DAQ','DAJ','DAC','DCS','DBA')}
        for angle,prepared in _license_ocr_variants(raw):
            if time.monotonic()>deadline:break
            for psm in (11,6,3):
                if time.monotonic()>deadline:break
                try:candidate=parse_license_text(text(prepared,psm))
                except ValueError:continue
                for key,value in candidate.items():
                    if value:observed[key].add(value)
                # Do not stop on the first complete-looking OCR result: a truncated
                # DAQ such as TEST must not suppress a later TEST1234 reading.
            if time.monotonic()>deadline:break
        # A strict prefix may be a truncated read of the same printed value.
        # Only prefer a longer reading when the short read is its exact prefix;
        # unrelated conflicting license numbers remain ambiguous and blocked.
        numbers=observed['DAQ']
        if len(numbers)>1:
            longest=sorted(numbers,key=len,reverse=True)[0]
            if all(longest.startswith(item) for item in numbers):
                observed['DAQ']={longest}
        best={key:next(iter(values)) if len(values)==1 else '' for key,values in observed.items()}
    labels={'DAQ':'License number','DAJ':'Issuing state','DAC':'First name','DCS':'Last name','DBA':'Expiration date'}
    errors=[name+' could not be read unambiguously from the onsite ID photo' for k,name in labels.items() if not best.get(k)]
    return {'fields':best,'source':source,'errors':errors}

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
