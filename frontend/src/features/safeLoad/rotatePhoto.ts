/** Rotate actual pixels; a CSS transform alone would leave the uploaded file sideways. */
export async function rotatePhoto(file:File,clockwise=90):Promise<File>{
 const url=URL.createObjectURL(file);
 try{
  const image=new Image();image.src=url;await image.decode();
  const angle=((clockwise%360)+360)%360;
  if(![0,90,180,270].includes(angle))throw Error('Use a quarter-turn rotation.');
  const canvas=document.createElement('canvas');canvas.width=angle%180?image.naturalHeight:image.naturalWidth;canvas.height=angle%180?image.naturalWidth:image.naturalHeight;
  const context=canvas.getContext('2d');if(!context)throw Error('Photo rotation is unavailable in this browser.');
  context.translate(canvas.width/2,canvas.height/2);context.rotate(angle*Math.PI/180);context.drawImage(image,-image.naturalWidth/2,-image.naturalHeight/2);
  const blob=await new Promise<Blob>((resolve,reject)=>canvas.toBlob(value=>value?resolve(value):reject(Error('Photo could not be rotated.')),'image/jpeg',.95));
  if(blob.size>8*1024*1024)throw Error('Rotated photo exceeds 8 MB. Choose a smaller clear image.');
  return new File([blob],file.name.replace(/\.[^.]*$/,'')+'-rotated.jpg',{type:'image/jpeg'});
 }finally{URL.revokeObjectURL(url)}
}
