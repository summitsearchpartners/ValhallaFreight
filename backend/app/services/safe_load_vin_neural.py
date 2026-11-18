"""Local CPU VIN text recognition. No external OCR service receives images.

RapidOCR's pinned distribution includes the ONNX models; no runtime download.
OCR scores are text-recognition scores, never identity/release confidence.
"""
import threading,time,logging
from PIL import Image,ImageOps

_engine=None
_lock=threading.Lock()
logger=logging.getLogger(__name__)

def _local_engine():
    global _engine
    if _engine is None:
        import onnxruntime
        onnxruntime.disable_telemetry_events()
        from rapidocr_onnxruntime import RapidOCR
        _engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1,use_cuda=False,use_dml=False)
    return _engine

def document_angle(image):
    """Use agreement of readable text-line directions, never faces/identity."""
    import numpy as np,re
    votes={0:0,90:0,180:0,270:0};counts={a:0 for a in votes}
    with _lock:
        engine=_local_engine();image=ImageOps.exif_transpose(image).convert('RGB');image.thumbnail((1600,1600));array=np.asarray(image)[:,:,::-1].copy()
        boxes,_=engine.text_det(array)
        if boxes is None or len(boxes)<3:return None
        crops=engine.get_crop_img_list(array,boxes)
        corrected,angles,_=engine.text_cls(crops)
        texts,_=engine.text_rec(corrected)
        for box,angle,text in zip(boxes,angles,texts):
            recognized=re.sub('[^A-Z0-9]','',text[0].upper())
            if float(angle[1])<.98 or float(text[1])<.8 or len(recognized)<5:continue
            width=max(np.linalg.norm(box[0]-box[1]),np.linalg.norm(box[2]-box[3]));height=max(np.linalg.norm(box[0]-box[3]),np.linalg.norm(box[1]-box[2]))
            turn=(270 if height/max(width,1)>=1.5 else 0)+(180 if angle[0]=='180' else 0);turn%=360
            votes[turn]+=min(40,len(recognized));counts[turn]+=1
    best=max(votes,key=votes.get);total=sum(votes.values())
    return best if total and counts[best]>=3 and votes[best]/total>=.8 else None

def candidates(image):
    """Return complete high-score VINs, without access to dispatcher data."""
    import cv2,numpy as np
    from app.services.safe_load_images import vin_candidates
    global _engine
    found=set()
    with _lock:
        _local_engine()
        original=ImageOps.exif_transpose(image).convert('RGB')
        original.thumbnail((1600,1600))
        gray=np.asarray(ImageOps.grayscale(original))
        enhanced=Image.fromarray(cv2.createCLAHE(clipLimit=2,tileGridSize=(8,8)).apply(gray)).convert('RGB')
        # Each pass detects/straightens text lines before recognizing them.
        # A complete pass is examined, so two readable VINs cannot be ignored.
        deadline=time.monotonic()+12
        for variant in [original,enhanced,original.rotate(90,expand=True),original.rotate(270,expand=True),original.rotate(180,expand=True)]:
            result,_=_engine(np.asarray(variant)[:,:,::-1].copy())
            for item in result or []:
                if float(item[2])>=.95:found.update(vin_candidates(item[1]))
            if found or time.monotonic()>deadline:break
    return found
