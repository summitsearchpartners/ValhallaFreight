const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');const ts=require('typescript');
const root=path.resolve(__dirname,'..');
function load(file,imports={},globals={}){const module={exports:{}};vm.runInNewContext(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{module,exports:module.exports,require:n=>{assert.ok(n in imports,n);return imports[n]},Blob,Uint8Array,TextEncoder,...globals});return module.exports}
const expo=path.dirname(require.resolve('expo/package.json'));const {installFormDataPatch}=load(path.join(expo,'src/winter/FormData.ts'));class NativeFormData{constructor(){this._parts=[]}}const FormData=installFormDataPatch(NativeFormData);const {convertFormDataAsync}=load(path.join(expo,'src/winter/fetch/convertFormData.ts'),{'../../utils/blobUtils':{blobToArrayBufferAsync:b=>b.arrayBuffer()}});
class CameraFile{constructor(uri){this.uri=uri;this.name='camera.jpg';this.type='image/jpeg';this.exists=!uri.includes('missing');this.size=3}async bytes(){return new Uint8Array([255,216,1])}}
const context={server:'http://test:8000',token:'test-token',shipmentId:4,revision:2};
function api(fetch){return load(path.join(root,'cameraApi.ts'),{'expo-file-system':{File:CameraFile},'expo/fetch':{fetch}},{FormData})}
test('live PDF417 sends barcode without URI placeholders and requires complete fields',async()=>{
 const scan='@\nANSI\nDAQTEST1234';let seen;
 const client=api(async(url,options)=>{seen={url,options};return {ok:true,json:async()=>({complete:true,first_name:'JOHN'})}});
 const result=await client.decodeLiveBarcode(context,'license',scan);assert.equal(result.barcode,scan);assert.ok(seen.url.endsWith('/4/license-barcode/preview'));assert.equal(JSON.parse(seen.options.body).revision,2);
 await assert.rejects(api(async()=>({ok:true,json:async()=>({complete:false})})).decodeLiveBarcode(context,'license',scan),/entire PDF417/);
});
test('VIN results use canonical server data including AIM-prefixed input',async()=>{
 const result=await api(async(url,options)=>{assert.ok(url.endsWith('/vin-barcode/preview'));assert.equal(JSON.parse(options.body).barcode,']C01HGCM82633A004352');return {ok:true,json:async()=>({vin:'1HGCM82633A004352'})}}).decodeLiveBarcode(context,'vin',']C01HGCM82633A004352');assert.equal(result.barcode,'1HGCM82633A004352');
});
test('fallback frame uses actual Expo multipart File bytes, scoped auth and endpoint',async()=>{
 await api(async(url,options)=>{assert.ok(url.endsWith('/4/barcode-frame'));assert.equal(options.headers.Authorization,'Bearer test-token');assert.equal(options.headers['Content-Type'],undefined);const encoded=await convertFormDataAsync(options.body,'CameraBoundary');const fields=await new Response(encoded.body,{headers:{'Content-Type':'multipart/form-data; boundary='+encoded.boundary}}).formData();assert.equal(fields.get('revision'),'2');assert.equal(fields.get('kind'),'license');assert.deepEqual(Buffer.from(await fields.get('frame').arrayBuffer()),Buffer.from([255,216,1]));return {ok:true,json:async()=>({barcode:'test'})}}).inspectCameraFrame(context,'file:///camera.jpg','license');
});
test('no-code and stale errors preserve actionable status for retry or cancellation',async()=>{
 for(const [status,message]of [[422,'No readable PDF417 ID barcode'],[409,'Assignment changed']])await assert.rejects(api(async()=>({ok:false,status,json:async()=>({detail:message})})).decodeLiveBarcode(context,'license','scan'),e=>e.status===status&&e.message===message);
});
test('readiness does not request decode or accept missing local camera file',async()=>{
 let called=0;const client=api(async(url)=>{called++;assert.ok(url.endsWith('/capture-readiness'));return {ok:true,json:async()=>({ready:false})}});
 assert.equal((await client.inspectCameraFrame(context,'file:///camera.jpg','idPhoto')).ready,false);
 await assert.rejects(client.inspectCameraFrame(context,'file:///missing.jpg','idPhoto'),/unavailable/);assert.equal(called,1);
});
const policy=load(path.join(root,'capturePolicy.ts'));
test('auto-capture requires consecutive ready stationary frames, resets for motion or blur',()=>{
 let state={box:null,count:0};state=policy.captureStability(state,true,[.5,.5,.7,.4]);assert.equal(state.count,1);state=policy.captureStability(state,true,[.51,.5,.7,.4]);assert.equal(state.count,2);state=policy.captureStability(state,true,[.7,.5,.7,.4]);assert.equal(state.count,1);state=policy.captureStability(state,false,[.7,.5,.7,.4]);assert.equal(state.count,0);assert.equal(policy.captureStability(state,true,[NaN,0,0,0]).count,0);
});
test('capture size keeps detailed supported pictures within backend limits',()=>{
 assert.equal(policy.choosePictureSize(['8000x6000','4000x3000','2400x1800','1920x1080','640x480','bad']),'2400x1800');assert.equal(policy.choosePictureSize(['bad','8000x6000']),undefined);
});
