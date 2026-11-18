/** A photo cannot be adopted until the operator explicitly accepts it. */
export class PhotoReviewFlow{
 phase:'camera'|'checking'|'review'|'saving'|'closed'='camera';
 uri='';private generation=0;private autoAttempted=false;
 constructor(private discard:(uri:string)=>void){}
 claimAuto(){if(this.autoAttempted||this.phase!=='camera')return false;this.autoAttempted=true;return true}
 begin(){if(this.phase!=='camera')return null;this.autoAttempted=true;this.phase='checking';return ++this.generation}
 present(uri:string,round:number){if(round!==this.generation||this.phase==='closed'){this.discard(uri);return false}this.uri=uri;this.phase='review';return true}
 replace(uri:string,expected:string){
  if(this.phase!=='review'||this.uri!==expected){this.discard(uri);return false}
  if(uri!==this.uri)this.discard(this.uri);this.uri=uri;return true;
 }
 failed(round:number){if(round===this.generation&&this.phase==='checking')this.phase='camera'}
 retake(){if(this.phase==='saving'||this.phase==='closed')return false;if(this.uri)this.discard(this.uri);this.uri='';this.generation++;this.autoAttempted=false;this.phase='camera';return true}
 async accept(save:(uri:string)=>Promise<void>){
  if(this.phase!=='review'||!this.uri)return false;
  const round=this.generation,uri=this.uri;this.phase='saving';
  try{await save(uri);this.uri='';this.phase='closed';return true}
  catch(e){if(round!==this.generation){this.discard(uri);this.uri=''}else this.phase='review';throw e}
 }
 cancel(){this.generation++;if(this.phase!=='saving'){if(this.uri)this.discard(this.uri);this.uri=''}this.phase='closed'}
}
