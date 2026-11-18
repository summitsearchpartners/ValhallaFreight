"""Transient document readiness. This is not identity approval or face recognition."""
def document_readiness(raw):
    import cv2,numpy as np
    data=cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),cv2.IMREAD_COLOR)
    if data is None:raise ValueError('Camera frame could not be read')
    h,w=data.shape[:2]
    if max(h,w)>1200:
        scale=1200/max(h,w);data=cv2.resize(data,(round(w*scale),round(h*scale)));h,w=data.shape[:2]
    gray=cv2.cvtColor(data,cv2.COLOR_BGR2GRAY)
    edges=cv2.Canny(cv2.GaussianBlur(gray,(5,5),0),40,120)
    contours,_=cv2.findContours(edges,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
    best=None
    for contour in contours:
        area=cv2.contourArea(contour)
        if area<w*h*.10:continue
        quad=cv2.approxPolyDP(contour,.025*cv2.arcLength(contour,True),True)
        if len(quad)!=4 or not cv2.isContourConvex(quad):continue
        (_, _),(a,b),_=cv2.minAreaRect(quad)
        if min(a,b)<=0 or not 1.3<=max(a,b)/min(a,b)<=1.95:continue
        if best is None or area>best[0]:best=(area,quad)
    if best is None:return {'ready':False,'hint':'Place all four ID edges inside the outline against a contrasting background','box':None}
    x,y,bw,bh=cv2.boundingRect(best[1]);roi=gray[y:y+bh,x:x+bw]
    focus=float(cv2.Laplacian(roi,cv2.CV_64F).var());light=float(roi.mean());clipped=float((roi>=252).mean())
    box=[(x+bw/2)/w,(y+bh/2)/h,bw/w,bh/h]
    centered=abs(box[0]-.5)<.16 and abs(box[1]-.5)<.18
    sharp=focus>=75;exposed=45<=light<=235 and clipped<.85
    large=bw>=450 and bh>=230 and best[0]/(w*h)>=.12
    ready=bool(centered and sharp and exposed and large)
    hint='Clear ID detected — hold still' if ready else 'Center the ID inside the outline' if not centered else 'Move closer so the ID fills the outline' if not large else 'Improve lighting and remove glare' if not exposed else 'Hold steady and let the camera focus'
    return {'ready':ready,'hint':hint,'box':box,'sharpness':round(focus,1)}
