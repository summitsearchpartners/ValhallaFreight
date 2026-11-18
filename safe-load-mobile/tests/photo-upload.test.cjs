const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ts=require('typescript');
const root=path.resolve(__dirname,'..');
function load(file,imports={},globals={}){
 const module={exports:{}};
 vm.runInNewContext(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{module,exports:module.exports,require:n=>{assert.ok(n in imports,'Unexpected dependency '+n);return imports[n]},Blob,Uint8Array,TextEncoder,...globals},{filename:file});return module.exports;
}
const expo=path.dirname(require.resolve('expo/package.json'));
const {installFormDataPatch}=load(path.join(expo,'src/winter/FormData.ts'));
class NativeFormData {constructor(){this._parts=[]}}
const FormData=installFormDataPatch(NativeFormData);
const {convertFormDataAsync}=load(path.join(expo,'src/winter/fetch/convertFormData.ts'),{'../../utils/blobUtils':{blobToArrayBufferAsync:b=>b.arrayBuffer()}});
// Stand-in for the native File bridge: exercise its actual bytes()/name/type contract
// through the installed Expo serializer, without pretending a physical device was used.
class CameraFile {
 constructor(uri){this.uri=uri;this.name=path.basename(uri);this.type='image/jpeg';this.exists=!uri.includes('missing');this.size=uri.includes('large')?9*1024*1024:3}
 async bytes(){return Uint8Array.from(this.uri.includes('vin')?[255,216,2]:[255,216,1])}
}
const input={server:'http://test:8000/',token:'fixture-token',shipmentId:12,revision:3,idUri:'file:///camera/id.jpg',vinUri:'file:///camera/vin.jpg',idCapturedAt:'2026-11-14T01:00:00Z',vinCapturedAt:'2026-11-14T01:00:01Z'};
function uploader(fetchImpl){return load(path.join(root,'photoUpload.ts'),{'expo-file-system':{File:CameraFile},'expo/fetch':{fetch:fetchImpl}},{FormData}).uploadArrivalPhotos}
test('reproduces SDK58 failure for the previous URI-only upload part',async()=>{
 const data=new FormData();data.append('license_photo',{uri:input.idUri,name:'id.jpg',type:'image/jpeg'});
 await assert.rejects(convertFormDataAsync(data),/Unsupported FormDataPart implementation/);
});
test('new upload serializes both camera File byte streams and required metadata',async()=>{
 const result=await uploader(async(url,options)=>{
  assert.equal(url,'http://test:8000/api/v1/safe-load/shipments/12/photo-review');
  assert.equal(options.headers.Authorization,'Bearer fixture-token');assert.equal(options.headers['Content-Type'],undefined);
  const encoded=await convertFormDataAsync(options.body,'TestBoundary');const bytes=Buffer.from(encoded.body);const text=bytes.toString('latin1');
  for(const field of ['revision','capture_source','license_captured_at','vin_captured_at','license_photo','vin_photo'])assert.ok(text.includes(`name="${field}"`));
  assert.ok(text.includes('filename="id.jpg"')&&text.includes('filename="vin.jpg"'));
  assert.ok(text.includes('Content-Type: image/jpeg')||text.includes('content-type: image/jpeg'));
  assert.ok(bytes.includes(Buffer.from([255,216,1]))&&bytes.includes(Buffer.from([255,216,2])));
  assert.ok(!text.includes('file:///'));return {ok:true,status:200,json:async()=>({status:'released'})};
 })(input);assert.equal(result.status,'released');
});
test('transport failure explains retry and leaves camera files untouched',async()=>{
 await assert.rejects(uploader(async()=>{throw Error('offline')})(input),/photos are retained/);
});
test('server validation and unreadable responses give actionable errors',async()=>{
 await assert.rejects(uploader(async()=>({ok:false,status:422,json:async()=>({detail:[{loc:['body','revision'],msg:'Invalid revision'}]})}))(input),/revision: Invalid revision/);
 await assert.rejects(uploader(async()=>({ok:false,status:502,json:async()=>{throw Error('not JSON')}}))(input),/HTTP 502/);
});
test('missing and oversized camera files fail before upload',async()=>{
 let called=false;const send=uploader(async()=>{called=true});
 await assert.rejects(send({...input,idUri:'file:///missing.jpg'}),/driver ID.*Retake/);
 await assert.rejects(send({...input,vinUri:'file:///large.jpg'}),/truck VIN.*8 MB/);
 assert.equal(called,false);
});
test('real fixture JPEGs and metadata survive the installed Expo multipart encoder',async()=>{
 const fixtures=path.resolve(root,'../docs/safe-load-test-photos');
 class DiskCameraFile extends CameraFile{
  constructor(uri){super(uri);this.path=path.join(fixtures,uri.includes('vin')?'vin.jpg':'id.jpg');this.size=fs.statSync(this.path).size;this.exists=true}
  async bytes(){return new Uint8Array(fs.readFileSync(this.path))}
 }
 const send=load(path.join(root,'photoUpload.ts'),{'expo-file-system':{File:DiskCameraFile},'expo/fetch':{fetch:async(url,options)=>{
  const {body,boundary}=await convertFormDataAsync(options.body,'SafeLoadCameraFixture');
  const decoded=await new Response(body,{headers:{'Content-Type':'multipart/form-data; boundary='+boundary}}).formData();
  for(const [key,name] of [['license_photo','id.jpg'],['vin_photo','vin.jpg']]){
   const file=decoded.get(key);assert.equal(file.type,'image/jpeg');assert.deepEqual(Buffer.from(await file.arrayBuffer()),fs.readFileSync(path.join(fixtures,name)));
  }
  assert.equal(decoded.get('revision'),'3');assert.equal(decoded.get('capture_source'),'native_camera');
  if(process.env.SAFE_LOAD_MULTIPART_OUTPUT)fs.writeFileSync(process.env.SAFE_LOAD_MULTIPART_OUTPUT,body);
  return {ok:true,status:200,json:async()=>({status:'released'})};
 }}},{FormData}).uploadArrivalPhotos;
 await send(input);
});
test('PDF417 newlines, VIN and progress job survive multipart serialization',async()=>{
 const barcode='@\nANSI 636000100002DL\nDAQTEST1234\nDAJKS\nDCSDOE\nDACJOHN\nDBA01012030\n';
 await uploader(async(url,options)=>{
  const {body,boundary}=await convertFormDataAsync(options.body,'ScannedMetadata');
  const decoded=await new Response(body,{headers:{'Content-Type':'multipart/form-data; boundary='+boundary}}).formData();
  assert.equal(decoded.get('license_barcode'),barcode);
  assert.equal(decoded.get('vin_barcode'),'1HGCM82633A004352');
  assert.equal(decoded.get('upload_id'),'a'.repeat(32));
  return {ok:true,status:200,json:async()=>({status:'released',confirmation_number:'SL-TEST'})};
 })({...input,licenseBarcode:barcode,vinBarcode:'1HGCM82633A004352',uploadId:'a'.repeat(32)});
});
test('ID back uploads as a third File part only after backend capability is confirmed',async()=>{
 let requests=0;
 const result=await uploader(async(url,options)=>{
  requests++;
  if(url.endsWith('/capture-features'))return {ok:true,json:async()=>({id_back_photo:true})};
  const encoded=await convertFormDataAsync(options.body,'BackPhoto');const parts=await new Response(encoded.body,{headers:{'Content-Type':'multipart/form-data; boundary='+encoded.boundary}}).formData();
  assert.ok(parts.get('license_photo'));assert.ok(parts.get('vin_photo'));assert.ok(parts.get('license_back_photo'));return {ok:true,status:200,json:async()=>({status:'rejected'})};
 })({...input,backUri:'file:///camera/back.jpg'});assert.equal(requests,2);assert.equal(result.status,'rejected');
});
test('older backend cannot silently ignore back evidence; photos remain for retry',async()=>{
 let requests=0;await assert.rejects(uploader(async()=>{requests++;return {ok:false,status:404,json:async()=>({detail:'Not Found'})}})({...input,backUri:'file:///camera/back.jpg'}),/backend must be updated/);assert.equal(requests,1);
});
