/* Project geometry and browser project management. */
function substrateSize(){const s=project.substrate;return s.type==='circle'?[s.diameter,s.diameter]:[s.width,s.height]}
function cellExtent(){return Math.max(...substrateSize())*.66}
function rawBounds(s){if(s[0]==='circle')return [s[1]-s[3],s[2]-s[3],s[1]+s[3],s[2]+s[3]];return [Math.min(...s[1].map(p=>p[0])),Math.min(...s[1].map(p=>p[1])),Math.max(...s[1].map(p=>p[0])),Math.max(...s[1].map(p=>p[1]))]}
function assemblyViewBox(){const b=rawBounds(frame.outline),pad=Math.max(b[2]-b[0],b[3]-b[1])*.055;return `${b[0]-pad} ${-b[3]-pad} ${b[2]-b[0]+2*pad} ${b[3]-b[1]+2*pad}`}
function defaultMarkCenter(){const h=project.skeleton.handle,b=rawBounds(frame.outline);if(h&&!Array.isArray(h)&&h.edge==='top')return [h.offset||0,b[3]-h.height/2];return [(b[0]+b[2])/2,b[3]-4]}
function layoutSettings(){let s={};for(const key of ['kind','name','substrate','skeleton','test_mask','clearance_mm','min_web_mm','arc_segments_per_90','curve_tolerance_mm'])if(key in project)s[key]=clone(project[key]);s.foil={};for(const key of ['per_window','outline','frame_holes'])if(key in project.foil)s.foil[key]=clone(project.foil[key]);return s}
function shapeSizeText(shape){if(!shape)return'—';if(shape.type==='circle')return`Ø${shape.diameter}`;if(shape.type==='rect')return`${shape.width}×${shape.height}`;return'自定义外形'}
function bboxSizeText(shape){let b=rawBounds(shape);return`${round(b[2]-b[0])}×${round(b[3]-b[1])}`}
function layoutSummary(multiline=true){let sk=project.skeleton,sub=project.substrate,w=sk.windows||{},picks=sk.pick_hole?(Array.isArray(sk.pick_hole)?sk.pick_hole:[sk.pick_hole]):[],handle=sk.handle?(Array.isArray(sk.handle)?sk.handle:[sk.handle]):[],foilCustom=project.foil.outline,tm=project.test_mask||{};let parts=[`基板 ${shapeSizeText(sub)}`,`掩模片 ${frame.foil_outline?bboxSizeText(frame.foil_outline):shapeSizeText(foilCustom||sk.outline)}${foilCustom?'（独立外形）':'（跟随骨架）'}`,`骨架 ${shapeSizeText(sk.outline)}${handle.length&&frame.outline?'，总外形 '+bboxSizeText(frame.outline):''}`,w.type==='array'?`阵列 ${w.nx}×${w.ny}，中心距 ${w.pitch_x}×${w.pitch_y??w.pitch_x}`:`定位开口 ${frame.centers.length} 个`];if(handle.length)parts.push(`把手 ${handle.map(h=>h.width+'×'+h.height).join('、')}`);parts.push(`取片缺口 ${picks.length?picks.length+' 个，R'+picks.map(p=>p.diameter/2).join('、'):'无'}`);parts.push(`安装孔 ${sk.frame_holes||project.foil.frame_holes?'已设置':'无'}`);parts.push(`测试 mask ${tm.enabled===false?'关闭':`${(tm.aperture_scale??.8)*100}% 边长，${tm.size_snap_mm??.1} mm 吸附`}`);return parts.join(multiline?'\n':'；')}
function updateProjectSummary(){$('project-name').textContent=project.name;$('project-name').title=projectDirectory||project.name;$('project-summary').textContent=layoutSummary();$('project-summary').style.whiteSpace='pre-line'}
function scheduleAutoSave(){clearTimeout(autoSaveTimer);autoSaveTimer=setTimeout(async()=>{let rev=checkSequence;try{await api('save',designPayload());if(rev===checkSequence)$('save-state').textContent='已自动保存'}catch(e){if(rev===checkSequence)$('save-state').textContent='待保存：'+e.message}},1200)}

function drawPartCanvas(kind,g){
 if(kind==='skeleton'){
  rawShape(frame.outline,g,'#add8e6','#6b97a7',.25);
  for(const shape of frame.windows)rawShape(shape,g,'white','#6b97a7',.16);
  for(const shape of frame.tooling||[])rawShape(shape,g,'white','#6b97a7',.16);
  $('canvas-label').textContent='骨架外框';
  $('canvas-subtitle').textContent=`主体 ${shapeSizeText(project.skeleton.outline)}，${frame.windows.length} 个定位开口`;
  return;
 }
 if(kind==='foil'){
  rawShape(frame.foil_outline||frame.outline,g,'#fff2af','#d4c77b',.25);
  const apertures=shapes.filter(s=>s.type!=='text'&&(s.layer||'aperture')==='aperture');
  if(project.foil.per_window!==false){for(const [x,y,angle]of frame.centers){let cell=node('g',{transform:`translate(${x} ${y}) rotate(${angle})`},g);for(const shape of apertures)renderShape(shape,cell)}}
  else for(const shape of apertures)renderShape(shape,g);
  for(const shape of frame.foil_tooling||[])rawShape(shape,g,'white','#a99a55',.16);
  $('canvas-label').textContent='掩模片外框';
  $('canvas-subtitle').textContent=project.foil.outline?`独立外形 ${shapeSizeText(project.foil.outline)}`:'外形跟随骨架（含把手）';
  return;
 }
 const tm=frame.test_mask||{};
 if(tm.outline)rawShape(tm.outline,g,'#fff2af','#d4c77b',.08);
 for(const shape of tm.holes||[])rawShape(shape,g,'white','#197366',.06);
 $('canvas-label').textContent='测试 mask';
 const config=project.test_mask||{};
 $('canvas-subtitle').textContent=!tm.enabled?'自动生成已关闭':tm.error?`暂不能生成：${tm.error}`:`${(tm.holes||[]).length} 个通光孔，${(config.aperture_scale??.8)*100}% 边长，${config.size_snap_mm??.1} mm 吸附`;
}

async function applyPartConfiguration(update,button){
 button.disabled=true;
 try{
  let settings=layoutSettings();update(settings);
  let result=await api('layout',{...designPayload(),project_settings:settings});
  project=result.spec;frame=result.frame;cameras={};updateProjectSummary();localSave();draw();properties();
  await api('save',designPayload());await validate();$('save-state').textContent='已保存外框设置';toast('外框设置已应用并保存');
 }catch(error){toast(error.message)}finally{button.disabled=false}
}

function partProperties(parent,kind){
 const controls={};
 function heading(text){let h=document.createElement('h3');h.className='selection-title';h.textContent=text;parent.append(h)}
 function fields(defs){let row=document.createElement('div');row.className='row';for(const def of defs){let [key,label,value,options]=def,wrap=document.createElement('div');wrap.className='field';if(options?.span)wrap.classList.add('span');let l=document.createElement('label');l.htmlFor='part-'+key;l.textContent=label;let input;if(options?.choices){input=document.createElement('select');for(const [v,text]of Object.entries(options.choices)){let o=document.createElement('option');o.value=v;o.textContent=text;input.append(o)}input.value=value}else{input=document.createElement('input');input.type=options?.type||'number';if(input.type==='checkbox'){input.checked=!!value;input.style.width='auto'}else{input.value=value;input.step=options?.step??'.01';if(options?.min!==undefined)input.min=options.min;if(options?.max!==undefined)input.max=options.max}}input.id='part-'+key;controls[key]=input;wrap.append(l,input);row.append(wrap)}parent.append(row)}
 function number(key,label){let input=controls[key],value=Number(input.value);if(!input.reportValidity()||input.value===''||!Number.isFinite(value))throw Error(`请检查${label}`);return value}
 function advanced(){let b=document.createElement('button');b.className='small';b.style.width='100%';b.textContent='完整设置';b.onclick=()=>$('project-settings').click();parent.append(b)}
 function apply(text,update){let b=document.createElement('button');b.className='primary';b.style.width='100%';b.textContent=text;b.onclick=()=>applyPartConfiguration(update,b);parent.append(b)}
 if(kind==='skeleton'){
  heading('骨架外框');let outline=project.skeleton.outline,handles=project.skeleton.handle?(Array.isArray(project.skeleton.handle)?project.skeleton.handle:[project.skeleton.handle]):[];
  if(outline.type!=='rect'||handles.length>1){parent.insertAdjacentHTML('beforeend','<p class="hint">当前骨架使用高级轮廓或多个把手，请在完整板件设置的高级 JSON 中编辑。</p>');advanced();return}
  let handle=handles[0]||{};
  fields([['width','主体宽度 / mm',outline.width,{min:.01}],['height','主体高度 / mm',outline.height,{min:.01}],['radius','外框圆角 R / mm',outline.corner_radius||0,{min:0}]]);
  fields([['handle','把手位置',handle.edge||'none',{span:true,choices:{none:'不设置',top:'顶边',bottom:'底边',left:'左边',right:'右边'}}],['handlewidth','把手沿边宽度 / mm',handle.width||60,{min:.01}],['handleheight','把手凸出长度 / mm',handle.height||40,{min:.01}],['handleoffset','把手沿边偏移 / mm',handle.offset||0,{}]]);
  let toggle=()=>{let off=controls.handle.value==='none';for(const key of ['handlewidth','handleheight','handleoffset'])controls[key].disabled=off};controls.handle.onchange=toggle;toggle();
  apply('应用',s=>{s.skeleton.outline={type:'rect',width:number('width','骨架宽度'),height:number('height','骨架高度'),corner_radius:number('radius','骨架圆角')};if(controls.handle.value==='none')delete s.skeleton.handle;else s.skeleton.handle={edge:controls.handle.value,width:number('handlewidth','把手宽度'),height:number('handleheight','把手长度'),offset:number('handleoffset','把手偏移')}});advanced();return;
 }
 if(kind==='foil'){
  heading('掩模片外框');let outline=project.foil.outline;
  if(outline&&!['rect','circle'].includes(outline.type)){parent.insertAdjacentHTML('beforeend','<p class="hint">当前掩模片使用高级自定义轮廓，请在完整板件设置的高级 JSON 中编辑。</p>');advanced();return}
  let mode=outline?.type||'follow',base=outline||project.skeleton.outline;
  fields([['mode','外形模式',mode,{span:true,choices:{follow:'跟随骨架外形（含把手）',rect:'独立矩形',circle:'独立圆形'}}]]);
  fields([['width','矩形宽度 / mm',base.width||190,{min:.01}],['height','矩形高度 / mm',base.height||190,{min:.01}],['radius','矩形圆角 R / mm',base.corner_radius||0,{min:0}],['diameter','圆形直径 / mm',base.diameter||190,{min:.01}]]);
  let toggle=()=>{let mode=controls.mode.value;for(const key of ['width','height','radius'])controls[key].disabled=mode!=='rect';controls.diameter.disabled=mode!=='circle'};controls.mode.onchange=toggle;toggle();
  apply('应用',s=>{if(controls.mode.value==='follow')delete s.foil.outline;else if(controls.mode.value==='circle')s.foil.outline={type:'circle',diameter:number('diameter','掩模片直径')};else s.foil.outline={type:'rect',width:number('width','掩模片宽度'),height:number('height','掩模片高度'),corner_radius:number('radius','掩模片圆角')}});advanced();return;
 }
 heading('测试 mask');let config=project.test_mask||{},outline=config.outline;
 if(outline&&!['rect','circle'].includes(outline.type)){parent.insertAdjacentHTML('beforeend','<p class="hint">当前测试 mask 使用高级自定义轮廓，请在完整板件设置的高级 JSON 中编辑。</p>');advanced();return}
 let mode=outline?.type||'substrate',base=outline||project.substrate;
 fields([['enabled','自动生成测试 mask',config.enabled!==false,{type:'checkbox',span:true}],['scale','通光孔边长比例 / %',(config.aperture_scale??.8)*100,{min:.1,max:99.9}],['snap','尺寸吸附 / mm',config.size_snap_mm??.1,{min:.001}],['margin','外框边缘余量 / mm',config.edge_margin_mm??project.min_web_mm??.3,{min:0}]]);
 fields([['mode','mask 外形',mode,{span:true,choices:{substrate:'跟随基板',rect:'独立矩形',circle:'独立圆形'}}],['width','矩形宽度 / mm',base.width||25,{min:.01}],['height','矩形高度 / mm',base.height||25,{min:.01}],['radius','矩形圆角 R / mm',base.corner_radius||0,{min:0}],['diameter','圆形直径 / mm',base.diameter||25,{min:.01}]]);
 let toggle=()=>{let mode=controls.mode.value;for(const key of ['width','height','radius'])controls[key].disabled=mode!=='rect';controls.diameter.disabled=mode!=='circle'};controls.mode.onchange=toggle;toggle();
 apply('应用',s=>{let tm={...(s.test_mask||{}),enabled:controls.enabled.checked,aperture_scale:number('scale','边长比例')/100,size_snap_mm:number('snap','吸附步长'),edge_margin_mm:number('margin','边缘余量')};if(controls.mode.value==='substrate')delete tm.outline;else if(controls.mode.value==='circle')tm.outline={type:'circle',diameter:number('diameter','测试 mask 直径')};else tm.outline={type:'rect',width:number('width','测试 mask 宽度'),height:number('height','测试 mask 高度'),corner_radius:number('radius','测试 mask 圆角')};s.test_mask=tm});advanced();
}
const layoutFieldDefinitions=[
 ['project-section','基本信息','section'],['name','项目名称','text'],
 ['substrate-section','基板尺寸（样品）','section'],['subtype','基板形状',{rect:'矩形',circle:'圆形'}],
 ['subw','基板宽度 / mm',25],['subh','基板高度 / mm',25],['subd','基板直径 / mm',25],['subr','基板圆角 R / mm',0],
 ['foil-section','掩模片外形','section'],['foiltype','掩模片外形模式',{follow:'跟随骨架外形（含把手）',rect:'独立矩形',circle:'独立圆形'}],
 ['foilw','掩模片宽度 / mm',190],['foilh','掩模片高度 / mm',190],['foild','掩模片直径 / mm',190],['foilr','掩模片圆角 R / mm',0],
 ['skeleton-section','骨架外形','section'],
 ['bodyw','骨架主体宽度 / mm',190],['bodyh','骨架主体高度 / mm',190],['bodyr','骨架外框圆角 R / mm',0],
 ['array-section','定位开口与图案阵列','section'],
 ['clearance','总旷量 / mm',.2],['minweb','最小筋宽要求 / mm',.3],
 ['nx','图案阵列列数',6],['ny','图案阵列行数',6],['px','X 中心距 / mm',30],['py','Y 中心距 / mm',30],
 ['centered','阵列自动居中','checkbox'],['ox','阵列起点 X / mm',-75],['oy','阵列起点 Y / mm',-75],['arrayangle','阵列旋转角 / °',0],
 ['testmask-section','测试遮光 mask','section'],['testmaskenabled','自动生成测试 mask','checkbox'],
 ['testmaskscale','通光孔边长比例 / %',80],['testmasksnap','通光孔尺寸吸附 / mm',.1],['testmaskmargin','外框边缘余量 / mm',.3],
 ['details-section','把手、缺口与安装孔','section'],['perwindow','每格复制图案','checkbox'],['handleedge','把手位置',{none:'不设置',top:'顶边',bottom:'底边',left:'左边',right:'右边'}],
 ['handlew','把手沿边宽度 / mm',60],['handleh','把手凸出长度 / mm',40],['handleoffset','把手沿边偏移 / mm',0],
 ['pickpos','取片缺口位置',{none:'不设置',top_right:'右上角',top_left:'左上角',bottom_right:'右下角',bottom_left:'左下角',top:'顶边',bottom:'底边',left:'左边',right:'右边'}],
 ['pickr','取片缺口 R / mm',2.5],['pickinset','取片缺口内缩 / mm',0],['pickoffset','边上缺口偏移 / mm',0],
 ['mounttarget','安装孔（可选）',{none:'不设置',both:'两片',frame:'骨架',foil:'掩模片'}],['mountd','安装孔直径 / mm',3],['mountinset','四角安装孔内缩 / mm',5]
];
function makeLayoutFields(){let grid=$('layout-grid');for(const [key,label,kind]of layoutFieldDefinitions){if(kind==='section'){let section=document.createElement('h3');section.className='layout-section';section.textContent=label;grid.append(section);continue}let field=document.createElement('div');field.className='field';if(key==='name'||key==='foiltype')field.classList.add('span');let l=document.createElement('label');l.htmlFor='layout-'+key;l.textContent=label;let input;if(typeof kind==='object'){input=document.createElement('select');for(const [v,t]of Object.entries(kind)){let option=document.createElement('option');option.value=v;option.textContent=t;input.append(option)}}else{input=document.createElement('input');input.type=kind==='checkbox'?'checkbox':kind==='text'?'text':'number';if(input.type==='number'){input.step=['nx','ny'].includes(key)?'1':'.1';input.min=['nx','ny'].includes(key)?'1':'0';if(['nx','ny'].includes(key))input.max=20;if(key==='testmaskscale'){input.min='.1';input.max='99.9'}if(key==='testmasksnap')input.min='.001'}if(input.type==='checkbox')input.style.width='auto'}input.id='layout-'+key;input.setAttribute('aria-label',label);field.append(l,input);grid.append(field)}for(const key of ['subtype','foiltype','centered','nx','ny','px','py'])$('layout-'+key).onchange=layoutConstraints}
function layoutConstraints(){const circle=$('layout-subtype').value==='circle';for(const key of ['subw','subh','subr'])$('layout-'+key).disabled=circle;$('layout-subd').disabled=!circle;const foiltype=$('layout-foiltype').value,foilFollow=foiltype==='follow',foilCircle=foiltype==='circle';for(const key of ['foilw','foilh','foilr'])$('layout-'+key).disabled=foilFollow||foilCircle;$('layout-foild').disabled=foilFollow||!foilCircle;let centered=$('layout-centered').checked;for(const key of ['ox','oy'])$('layout-'+key).disabled=centered;if(centered){const x=(+$('layout-nx').value-1)*+$('layout-px').value/2,y=(+$('layout-ny').value-1)*+$('layout-py').value/2,a=+$('layout-arrayangle').value*Math.PI/180;$('layout-ox').value=-x*Math.cos(a)+y*Math.sin(a);$('layout-oy').value=-x*Math.sin(a)-y*Math.cos(a)}}
function fillLayout(){const s=layoutSettings(),sk=s.skeleton,w=sk.windows||{},h=Array.isArray(sk.handle)?sk.handle[0]:sk.handle,p=Array.isArray(sk.pick_hole)?sk.pick_hole[0]:sk.pick_hole,fh=sk.frame_holes,ff=s.foil.frame_holes,mount=fh||ff,fo=s.foil.outline,tm=s.test_mask||{};let v={name:s.name,subtype:s.substrate.type,subw:s.substrate.width||25,subh:s.substrate.height||25,subd:s.substrate.diameter||25,subr:s.substrate.corner_radius||0,foiltype:fo?.type||'follow',foilw:fo?.width||sk.outline.width||190,foilh:fo?.height||sk.outline.height||190,foild:fo?.diameter||190,foilr:fo?.corner_radius||0,bodyw:sk.outline.width||190,bodyh:sk.outline.height||190,bodyr:sk.outline.corner_radius||0,clearance:s.clearance_mm??.2,minweb:s.min_web_mm??.3,nx:w.nx||1,ny:w.ny||1,px:w.pitch_x||30,py:w.pitch_y??w.pitch_x??30,ox:w.origin?.[0]||0,oy:w.origin?.[1]||0,arrayangle:w.angle||0,perwindow:s.foil.per_window!==false,testmaskenabled:tm.enabled!==false,testmaskscale:(tm.aperture_scale??.8)*100,testmasksnap:tm.size_snap_mm??.1,testmaskmargin:tm.edge_margin_mm??s.min_web_mm??.3,handleedge:h?(h.edge||'top'):'none',handlew:h?.width||60,handleh:h?.height||40,handleoffset:h?.offset||0,pickpos:p?(p.corner||p.edge||'top'):'none',pickr:(p?.diameter||5)/2,pickinset:p?.inset||0,pickoffset:p?.offset||0,mounttarget:fh&&ff?'both':fh?'frame':ff?'foil':'none',mountd:mount?.diameter||3,mountinset:mount?.inset??5};
 let a=(w.angle||0)*Math.PI/180,cx=-(v.nx-1)*v.px/2,cy=-(v.ny-1)*v.py/2;v.centered=Math.abs(v.ox-(cx*Math.cos(a)-cy*Math.sin(a)))<1e-6&&Math.abs(v.oy-(cx*Math.sin(a)+cy*Math.cos(a)))<1e-6;
 for(const [key,,kind]of layoutFieldDefinitions){if(kind==='section')continue;let input=$('layout-'+key);if(kind==='checkbox')input.checked=!!v[key];else input.value=v[key]}
 let complex=(sk.outline.type&&sk.outline.type!=='rect')||(fo&& !['rect','circle'].includes(fo.type))||(w.type&&w.type!=='array')||w.stagger||w.skip?.length||(Array.isArray(sk.handle)&&sk.handle.length>1)||(Array.isArray(sk.pick_hole)&&sk.pick_hole.length>1)||mount?.positions||mount?.skip_corners?.length||(fh&&ff&&JSON.stringify(fh)!==JSON.stringify(ff));
 $('layout-mode').value=complex?'json':'form';$('layout-json').value=JSON.stringify(s,null,2);$('layout-error').textContent=complex?'当前项目使用高级几何配置，可在JSON中完整保留和修改。':'';toggleLayoutMode();layoutConstraints();
}
function toggleLayoutMode(){let advanced=$('layout-mode').value==='json';$('layout-fields').hidden=advanced;$('layout-advanced').hidden=!advanced}
function formLayout(){const n=k=>{let value=Number($('layout-'+k).value);if($('layout-'+k).value===''||!Number.isFinite(value))throw Error('请输入有效数值');return value};let s=layoutSettings();s.name=$('layout-name').value.trim();s.substrate=$('layout-subtype').value==='circle'?{type:'circle',diameter:n('subd')}:{type:'rect',width:n('subw'),height:n('subh'),corner_radius:n('subr')};s.clearance_mm=n('clearance');s.min_web_mm=n('minweb');s.skeleton.outline={type:'rect',width:n('bodyw'),height:n('bodyh'),corner_radius:n('bodyr')};let foiltype=$('layout-foiltype').value;if(foiltype==='follow')delete s.foil.outline;else if(foiltype==='circle')s.foil.outline={type:'circle',diameter:n('foild')};else s.foil.outline={type:'rect',width:n('foilw'),height:n('foilh'),corner_radius:n('foilr')};layoutConstraints();s.skeleton.windows={type:'array',nx:n('nx'),ny:n('ny'),pitch_x:n('px'),pitch_y:n('py'),origin:[n('ox'),n('oy')],angle:n('arrayangle')};s.foil.per_window=$('layout-perwindow').checked;s.test_mask={...(s.test_mask||{}),enabled:$('layout-testmaskenabled').checked,aperture_scale:n('testmaskscale')/100,size_snap_mm:n('testmasksnap'),edge_margin_mm:n('testmaskmargin')};let edge=$('layout-handleedge').value;if(edge==='none')delete s.skeleton.handle;else s.skeleton.handle={edge,width:n('handlew'),height:n('handleh'),offset:n('handleoffset')};let pos=$('layout-pickpos').value;if(pos==='none')delete s.skeleton.pick_hole;else{s.skeleton.pick_hole=[{diameter:2*n('pickr'),inset:n('pickinset')}];if(pos.includes('_'))s.skeleton.pick_hole[0].corner=pos;else{s.skeleton.pick_hole[0].edge=pos;s.skeleton.pick_hole[0].offset=n('pickoffset')}}let target=$('layout-mounttarget').value;delete s.skeleton.frame_holes;delete s.foil.frame_holes;if(target!=='none'){let f={diameter:n('mountd'),inset:n('mountinset')};if(['both','frame'].includes(target))s.skeleton.frame_holes=clone(f);if(['both','foil'].includes(target))s.foil.frame_holes=clone(f)}return s}
$('layout-mode').onchange=toggleLayoutMode;$('layout-arrayangle')?.addEventListener('change',layoutConstraints);
$('project-settings').onclick=()=>{fillLayout();$('layout-dialog').showModal()};$('close-layout').onclick=()=>$('layout-dialog').close();$('reset-layout').onclick=fillLayout;
$('apply-layout').onclick=async()=>{let b=$('apply-layout');b.disabled=true;try{let settings=$('layout-mode').value==='json'?JSON.parse($('layout-json').value):formLayout(),r=await api('layout',{...designPayload(),project_settings:settings});project=r.spec;frame=r.frame;extent=cellExtent();cameras={};updateProjectSummary();$('layout-dialog').close();history=[];future=[];selected.clear();changed();await api('save',designPayload());$('save-state').textContent='已保存项目设置';toast('项目设置已应用并保存')}catch(e){$('layout-error').textContent=e.message}finally{b.disabled=false}};

let importedProject=null;
async function saveCurrent(){clearTimeout(autoSaveTimer);let r=await api('save',designPayload());$('save-state').textContent='已保存';return r}
async function listProjects(){let response=await fetch('/api/projects'),r=await response.json();if(!response.ok)throw Error(r.error);$('library-path').textContent='保存位置：'+r.library_dir;let list=$('project-library');list.replaceChildren();for(const p of r.projects){let card=document.createElement('div');card.className='project-card';let title=document.createElement('strong');title.textContent=p.name+(p.current?'（当前）':'');let info=document.createElement('div');info.className='hint';info.textContent=`${p.cells} 个定位开口`;let path=document.createElement('div');path.className='hint';path.style.overflowWrap='anywhere';path.textContent=p.path;let open=document.createElement('button');open.className='small';open.textContent=p.current?'已打开':'打开';open.disabled=p.current;open.onclick=async()=>{open.disabled=true;try{await saveCurrent();await api('project-open',{id:p.id,project_key:projectKey});location.reload()}catch(e){toast(e.message);open.disabled=false}};card.append(title,info,path,open);list.append(card)}}
$('manage-projects').onclick=async()=>{try{await listProjects();$('projects-dialog').showModal()}catch(e){toast(e.message)}};$('close-projects').onclick=()=>$('projects-dialog').close();
function showNew(mode){importedProject=null;$('new-project-mode').value=mode;$('new-project-name').value=mode==='copy'?project.name+' 副本':'新建掩模项目';$('new-project-error').textContent='';$('new-project-dialog').showModal()}
$('new-project').onclick=()=>showNew('empty');$('copy-project').onclick=()=>showNew('copy');$('new-in-library').onclick=()=>{$('projects-dialog').close();showNew('empty')};document.addEventListener('click',e=>{let menu=$('project-actions-menu');if(menu.open&&!menu.contains(e.target))menu.open=false});for(const id of ['new-project','manage-projects','copy-project'])$(id).addEventListener('click',()=>$('project-actions-menu').removeAttribute('open'));
$('create-project').onclick=async()=>{let b=$('create-project');b.disabled=true;try{let name=$('new-project-name').value.trim();if(!name)throw Error('请输入项目名称');await saveCurrent();let route=importedProject?'project-import':$('new-project-mode').value==='copy'?'project-copy':'project-new';await api(route,{name,spec:importedProject,project_key:projectKey});if(route==='project-new')sessionStorage.setItem('open-layout-after-reload','1');location.reload()}catch(e){$('new-project-error').textContent=e.message}finally{b.disabled=false}};$('cancel-new-project').onclick=()=>$('new-project-dialog').close();
$('import-project').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;const obj=JSON.parse((await file.text()).replace(/^\uFEFF/,''));if(!obj.skeleton||!obj.substrate||!obj.foil)throw Error('请选择完整蒸镀总成项目JSON');$('projects-dialog').close();showNew('copy');importedProject=obj;$('new-project-name').value=obj.name||file.name.replace(/\.json$/i,'');$('new-project-mode').disabled=true}catch(e){toast(e.message)}finally{e.target.value=''}};
$('new-project-dialog').addEventListener('close',()=>{$('new-project-mode').disabled=false});
$('quit-service').onclick=async()=>{try{await saveCurrent();await api('shutdown',{});$('projects-dialog').close();toast('本地工作台已结束，可以关闭此页面。');document.querySelectorAll('button').forEach(b=>b.disabled=true)}catch(e){toast(e.message)}};
makeLayoutFields();$('layout-arrayangle').onchange=layoutConstraints;
init().then(()=>{if(sessionStorage.getItem('open-layout-after-reload')==='1'){sessionStorage.removeItem('open-layout-after-reload');$('project-settings').click()}});
