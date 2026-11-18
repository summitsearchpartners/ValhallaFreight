export type Rect={x:number;y:number;width:number;height:number};
/** Map the actual guide rectangle through a center-cover camera preview to image pixels. */
export function guideCrop(image:{width:number;height:number},preview:{width:number;height:number},guide:Rect){
 if([image.width,image.height,preview.width,preview.height,guide.width,guide.height].some(v=>!Number.isFinite(v)||v<=0)||![guide.x,guide.y].every(Number.isFinite))throw Error('Camera framing is not ready. Reopen the camera.');
 const scale=Math.max(preview.width/image.width,preview.height/image.height);
 const offsetX=(image.width*scale-preview.width)/2,offsetY=(image.height*scale-preview.height)/2;
 const x=Math.max(0,Math.min(image.width-1,Math.round((guide.x+offsetX)/scale))),y=Math.max(0,Math.min(image.height-1,Math.round((guide.y+offsetY)/scale)));
 const right=Math.min(image.width,Math.round((guide.x+guide.width+offsetX)/scale)),bottom=Math.min(image.height,Math.round((guide.y+guide.height+offsetY)/scale));
 if(right<=x||bottom<=y)throw Error('The ID guide is outside the image. Reopen the camera.');
 return {originX:x,originY:y,width:right-x,height:bottom-y};
}
