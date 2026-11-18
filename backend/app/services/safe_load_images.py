"""Local image normalization, barcode decoding and conservative OCR. No remote ID upload."""
import io,re,subprocess,time
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

def text(raw,psm=6):
    try:
        result=subprocess.run(['tesseract','stdin','stdout','-l','eng','--psm',str(psm)],input=raw,capture_output=True,timeout=8,check=True)
        return result.stdout.decode('utf-8',errors='replace').upper()
    except (OSError,subprocess.SubprocessError):raise ValueError('Local photo reader unavailable or timed out. Freight remains blocked; contact the broker.')

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
    # Numbered AAMVA front-card labels can be inline, on their own line, or in columns.
    source=source.upper().replace('’',"'")
    fields={}
    fields['DAQ']=optional(r'(?:^|\n|\s)(?:4D|DLN?\s*(?:NO\.?|NUMBER|#)|LICEN[CS]E\s*(?:NO\.?|NUMBER|#)|5)[.:# -]*[ \t]*(?:\n[ \t]*)?([A-Z0-9][A-Z0-9-]{3,29})(?=[ \t]*(?:\n|$)|[ \t]+(?:3|4[A-C])\b)',source)
    def name(label):
        value=optional(r'(?:^|\n)[ \t]*(?:'+label+r')[.: -]*[ \t]*(?:\n[ \t]*)?([A-Z][A-Z .,\'-]{0,65})[ \t]*(?=\n|$)',source)
        # Do not turn address/endorsement text into a name when labels were missed.
        if any(word in value.split() for word in ['RESTRICTIONS','ENDORSEMENTS','LICENSE','DRIVER','ISS','EXP','NONE']):return ''
        return value.strip(' .,')
    fields['DAC']=name(r'FIRST[ \t]*NAME|FN|2')
    fields['DCS']=name(r'LAST[ \t]*NAME|LN|1')
    expiry=optional(r'(?:EXP(?:IRATION|IRES)?(?:[ \t]*DATE)?|4B(?:[ \t]*EXP)?)[ \t.:#-]*(?:\n[ \t]*)?(\d{2}[/.-]\d{2}[/.-]\d{4}|\d{4}-\d{2}-\d{2})',source)
    try:
        cleaned=expiry.replace('.','/').replace('-','/')
        fields['DBA']=datetime.strptime(cleaned,'%Y/%m/%d' if len(cleaned.split('/')[0])==4 else '%m/%d/%Y').strftime('%m%d%Y')
    except ValueError:fields['DBA']=''
    fields['DAJ']=optional(r'ISSUING\s*STATE[ :.-]+([A-Z]{2})\b',source)
    if not fields['DAJ']:
        from app.api.routes.truckload import STATES
        candidates={code for code,name in STATES.items() if re.search(r'\b'+re.escape(name.upper())+r'\b',source)}
        if len(candidates)==1:fields['DAJ']=candidates.pop()
    return fields

def rotated(raw,angle):
    if angle==0:return raw
    output=io.BytesIO();Image.open(io.BytesIO(raw)).rotate(angle,expand=True).save(output,'PNG');return output.getvalue()

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
        best={};source='local_ocr';deadline=time.monotonic()+36
        for angle,psm in [(a,p) for p in [11,6] for a in [0,90,270,180]]:
            if time.monotonic()>deadline:break
            try:
                oriented=rotated(raw,angle)
                image=ImageOps.autocontrast(Image.open(io.BytesIO(oriented)).convert('L'))
                if image.width<1400:
                    scale=min(3,1800/image.width);image=image.resize((round(image.width*scale),round(image.height*scale)),Image.Resampling.LANCZOS)
                buf=io.BytesIO();image.save(buf,'PNG')
                candidate=parse_license_text(text(buf.getvalue(),psm))
            except ValueError:continue
            if sum(bool(v) for v in candidate.values())>sum(bool(v) for v in best.values()):best=candidate
            if all(best.get(k) for k in ['DAQ','DAJ','DAC','DCS','DBA']):break
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
