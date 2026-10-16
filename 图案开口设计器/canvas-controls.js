/* View operations never enter the design payload or geometry undo history. */
function selectionBounds(){
 const bb=shapes.filter(s=>selected.has(s.id)).map(bounds);
 return bb.length?[Math.min(...bb.map(b=>b[0])),Math.min(...bb.map(b=>b[1])),Math.max(...bb.map(b=>b[2])),Math.max(...bb.map(b=>b[3]))]:null;
}
function fittedCamera(){
 let b;
 if(view==='cell'){
  const [w,h]=substrateSize(),bb=[[-w/2,-h/2,w/2,h/2],...shapes.filter(s=>s.type!=='text').map(bounds)];
  b=[Math.min(...bb.map(b=>b[0])),Math.min(...bb.map(b=>b[1])),Math.max(...bb.map(b=>b[2])),Math.max(...bb.map(b=>b[3]))];
 }else if(view==='skeleton')b=rawBounds(frame.outline);
 else if(view==='foil')b=rawBounds(frame.foil_outline||frame.outline);
 else if(view==='testmask_manual')b=[-25,-25,25,25];
 else if(view==='testmask')b=rawBounds(frame.test_mask?.outline||frame.foil_outline||frame.outline);
 else{const all=[rawBounds(frame.outline),rawBounds(frame.foil_outline||frame.outline)];b=[Math.min(...all.map(q=>q[0])),Math.min(...all.map(q=>q[1])),Math.max(...all.map(q=>q[2])),Math.max(...all.map(q=>q[3]))]}
 const pad=Math.max(b[2]-b[0],b[3]-b[1])*(view==='cell'?.16:['skeleton','foil','testmask'].includes(view)?.11:.075);
 return {x:(b[0]+b[2])/2,y:(b[1]+b[3])/2,w:Math.max(.1,b[2]-b[0]+2*pad),h:Math.max(.1,b[3]-b[1]+2*pad)};
}
function camera(){return cameras[view]||(cameras[view]=fittedCamera())}
function applyCamera(){const c=camera();$('canvas').setAttribute('viewBox',`${c.x-c.w/2} ${-c.y-c.h/2} ${c.w} ${c.h}`)}
function fitView(){if(!project)return;cameras[view]=fittedCamera();draw()}
function zoomCamera(factor,event){
 if(!project)return;const c=camera(),base=fittedCamera(),ratio=c.w/base.w;
 factor=Math.max(.04,Math.min(20,ratio*factor))/ratio;
 const anchor=event?pAt(event,true):{x:c.x,y:c.y};
 c.x=anchor.x+(c.x-anchor.x)*factor;c.y=anchor.y+(c.y-anchor.y)*factor;c.w*=factor;c.h*=factor;applyCamera();
}
function endPan(){if(!panDrag)return;const id=panDrag.pointer;panDrag=null;if($('canvas').hasPointerCapture(id))$('canvas').releasePointerCapture(id);$('canvas').style.cursor=tool==='pan'?'grab':'default'}
function translateSelection(dx,dy){
 if(!Number.isFinite(dx)||!Number.isFinite(dy))return;
 const ss=shapes.filter(s=>selected.has(s.id));if(!ss.length){toast('先选择要移动的对象');return}if(!dx&&!dy)return;
 checkpoint();ss.forEach(s=>move(s,dx,dy));changed();
}
function positionControls(parent){
 const b=selectionBounds(),cx=round((b[0]+b[2])/2),cy=round((b[1]+b[3])/2);
 const hint=document.createElement('p');hint.className='hint';hint.textContent='整体移动当前选中对象，保持相互间距。中心按外包框计算；会改变加工坐标，可撤销。';parent.append(hint);
 function fields(defs){const row=document.createElement('div');row.className='row';const inputs={};for(const [id,label,value]of defs){const f=document.createElement('div');f.className='field';const l=document.createElement('label');l.htmlFor=id;l.textContent=label;const input=document.createElement('input');input.id=id;input.type='number';input.step='.1';input.value=value;input.required=true;f.append(l,input);row.append(f);inputs[id]=input}parent.append(row);return inputs}
 function action(text,id,inputs,fn){const button=document.createElement('button');button.className='small';button.style.width='100%';button.id=id;button.textContent=text;button.onclick=()=>{if(Object.values(inputs).every(i=>i.reportValidity()))fn()};parent.append(button)}
 const center=fields([['selection-x','选中整体中心 X / mm',cx],['selection-y','选中整体中心 Y / mm',cy]]);
 action('设置整体中心','set-selection-center',center,()=>{const current=selectionBounds();translateSelection(+center['selection-x'].value-(current[0]+current[2])/2,+center['selection-y'].value-(current[1]+current[3])/2)});
 const offset=fields([['selection-dx','整体平移 ΔX / mm',0],['selection-dy','整体平移 ΔY / mm',0]]);
 action('应用整体平移','translate-selection',offset,()=>translateSelection(+offset['selection-dx'].value,+offset['selection-dy'].value));
}
