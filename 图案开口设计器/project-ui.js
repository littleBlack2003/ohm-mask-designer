/* Project geometry and browser project management. */
function substrateSize(){const s=project.substrate;return s.type==='circle'?[s.diameter,s.diameter]:[s.width,s.height]}
function cellExtent(){return Math.max(...substrateSize())*.66}
function rawBounds(s){if(s[0]==='circle')return [s[1]-s[3],s[2]-s[3],s[1]+s[3],s[2]+s[3]];return [Math.min(...s[1].map(p=>p[0])),Math.min(...s[1].map(p=>p[1])),Math.max(...s[1].map(p=>p[0])),Math.max(...s[1].map(p=>p[1]))]}
function assemblyViewBox(){const b=rawBounds(frame.outline),pad=Math.max(b[2]-b[0],b[3]-b[1])*.055;return `${b[0]-pad} ${-b[3]-pad} ${b[2]-b[0]+2*pad} ${b[3]-b[1]+2*pad}`}
function defaultMarkCenter(){const h=project.skeleton.handle,b=rawBounds(frame.outline);if(h&&!Array.isArray(h)&&h.edge==='top')return [h.offset||0,b[3]-h.height/2];return [(b[0]+b[2])/2,b[3]-4]}
function layoutSettings(){let s={};for(const key of ['kind','name','substrate','skeleton','test_mask','clearance_mm','min_web_mm','arc_segments_per_90','curve_tolerance_mm'])if(key in project)s[key]=clone(project[key]);s.foil={};for(const key of ['per_window','outline','frame_holes'])if(key in project.foil)s.foil[key]=clone(project.foil[key]);return s}
function shapeSizeText(shape){if(!shape)return'—';if(shape.type==='circle')return`Ø${shape.diameter}`;if(shape.type==='rect')return`${shape.width}×${shape.height}`;return T('自定义外形')}
function bboxSizeText(shape){let b=rawBounds(shape);return`${round(b[2]-b[0])}×${round(b[3]-b[1])}`}
function layoutSummary(multiline=true){let sk=project.skeleton,sub=project.substrate,w=sk.windows||{},picks=sk.pick_hole?(Array.isArray(sk.pick_hole)?sk.pick_hole:[sk.pick_hole]):[],handle=sk.handle?(Array.isArray(sk.handle)?sk.handle:[sk.handle]):[],foilCustom=project.foil.outline,tm=project.test_mask||{};let parts=[T('基板 ')+shapeSizeText(sub),T('掩模片 ')+(frame.foil_outline?bboxSizeText(frame.foil_outline):shapeSizeText(foilCustom||sk.outline))+(foilCustom?T('（独立外形）'):T('（跟随骨架）')),T('骨架 ')+shapeSizeText(sk.outline)+(handle.length&&frame.outline?T('，总外形 ')+bboxSizeText(frame.outline):''),w.type==='array'?TF('阵列 {a}×{b}，中心距 {c}×{d}',{a:w.nx,b:w.ny,c:w.pitch_x,d:w.pitch_y??w.pitch_x}):TF('定位开口 {n} 个',{n:frame.centers.length})];if(handle.length)parts.push(TF('把手 {list}',{list:handle.map(h=>h.width+'×'+h.height).join('、')}));parts.push(TF('取片缺口 {v}',{v:picks.length?TF('{n} 个，R{list}',{n:picks.length,list:picks.map(p=>p.diameter/2).join('、')}):T('无')}));parts.push(TF('安装孔 {v}',{v:(sk.frame_holes||project.foil.frame_holes)?T('已设置'):T('无')}));parts.push(TF('测试 mask {v}',{v:tm.enabled===false?T('已关闭'):TF('{p}% 边长，{s} mm 吸附',{p:(tm.aperture_scale??.8)*100,s:tm.size_snap_mm??.1})}));return parts.join(multiline?'\n':T('；'))}
function updateProjectSummary(){$('project-name').textContent=project.name;$('project-name').title=projectDirectory||project.name;$('project-summary').textContent=layoutSummary();$('project-summary').style.whiteSpace='pre-line'}
function scheduleAutoSave(){clearTimeout(autoSaveTimer);autoSaveTimer=setTimeout(async()=>{let rev=checkSequence;try{await api('save',designPayload());if(rev===checkSequence)$('save-state').textContent='已自动保存'}catch(e){if(rev===checkSequence)$('save-state').textContent='待保存：'+e.message}},1200)}

function drawPartCanvas(kind,g){
 if(kind==='skeleton'){
  rawShape(frame.outline,g,'#add8e6','#6b97a7',.25);
  for(const shape of frame.windows)rawShape(shape,g,'white','#6b97a7',.16);
  for(const shape of frame.tooling||[])rawShape(shape,g,'white','#6b97a7',.16);
  if(assemblyGridVisible){drawEngineeringGrid(g);drawCoordinateAxes(g,rawBounds(frame.outline),true)}
  $('canvas-label').textContent=T('骨架外框');
  $('canvas-subtitle').textContent=TF('主体 {a}，{b} 个定位开口',{a:shapeSizeText(project.skeleton.outline),b:frame.windows.length});
  return;
 }
 if(kind==='foil'){
  const foilOutline=frame.foil_outline||frame.outline;rawShape(foilOutline,g,'#fff2af','#d4c77b',.25);
  const apertures=shapes.filter(s=>s.type!=='text'&&(s.layer||'aperture')==='aperture');
  if(project.foil.per_window!==false){for(const [x,y,angle]of frame.centers){let cell=node('g',{transform:`translate(${x} ${y}) rotate(${angle})`},g);for(const shape of apertures)renderShape(shape,cell)}}
  else for(const shape of apertures)renderShape(shape,g);
  for(const shape of frame.foil_tooling||[])rawShape(shape,g,'white','#a99a55',.16);
  if(assemblyGridVisible){drawEngineeringGrid(g);drawCoordinateAxes(g,rawBounds(foilOutline),true)}
  $('canvas-label').textContent=T('掩模片外框');
  $('canvas-subtitle').textContent=project.foil.outline?TF('独立外形 {a}',{a:shapeSizeText(project.foil.outline)}):T('外形跟随骨架（含把手）');
  return;
 }
 const tm=frame.test_mask||{};
 const config=project.test_mask||{};
 const gridOutline=tm.outline||frame.foil_outline||frame.outline;
 if(config.mode==='manual'){
  if(tm.outline)rawShape(tm.outline,g,'#fff2af','#d4c77b',.08);
  for(const s of shapes.filter(x=>x.layer==='mask_outline'))renderShape(s,g,true);
  for(const s of shapes.filter(x=>x.layer==='mask'))renderShape(s,g,true);
  if(assemblyGridVisible){drawEngineeringGrid(g);drawCoordinateAxes(g,rawBounds(gridOutline),true)}
  $('canvas-label').textContent=T('测试 mask')+' · '+T('自主绘制');
  $('canvas-subtitle').textContent=TF('外形与通光孔自主绘制（{n} 个孔）',{n:shapes.filter(x=>x.layer==='mask').length});
  return;
 }
 if(tm.outline)rawShape(tm.outline,g,'#fff2af','#d4c77b',.08);
 for(const shape of tm.holes||[])rawShape(shape,g,'white','#197366',.06);
  if(assemblyGridVisible){drawEngineeringGrid(g);drawCoordinateAxes(g,rawBounds(gridOutline),true)}
 $('canvas-label').textContent=T('测试 mask');
  $('canvas-subtitle').textContent=!tm.enabled?T('自动生成已关闭'):tm.error?TF('暂不能生成：{e}',{e:tm.error}):TF('{n} 个通光孔，{p}% 边长，{s} mm 吸附',{n:(tm.holes||[]).length,p:(config.aperture_scale??.8)*100,s:config.size_snap_mm??.1});
}

async function applyPartConfiguration(update,button){
 button.disabled=true;
 try{
  let settings=layoutSettings();update(settings);
  let result=await api('layout',{...designPayload(),project_settings:settings});
  project=result.spec;frame=result.frame;cameras={};updateProjectSummary();localSave();updateWorkspaceTools();draw();properties();
  await api('save',designPayload());await validate();$('save-state').textContent='已保存外框设置';toast('外框设置已应用并保存');
 }catch(error){toast(error.message)}finally{button.disabled=false}
}

function partProperties(parent,kind){
 const controls={};
 function heading(text){let h=document.createElement('h3');h.className='selection-title';h.textContent=T(text);parent.append(h)}
 function subheading(text){let h=document.createElement('h4');h.className='part-subheading';h.textContent=T(text);parent.append(h)}
 function fields(defs){let row=document.createElement('div');row.className='row';for(const def of defs){let [key,label,value,options]=def,wrap=document.createElement('div');wrap.className='field';if(options?.span)wrap.classList.add('span');let l=document.createElement('label');l.htmlFor='part-'+key;l.textContent=T(label);let input;if(options?.choices){input=document.createElement('select');for(const [v,text]of Object.entries(options.choices)){let o=document.createElement('option');o.value=v;o.textContent=T(text);input.append(o)}input.value=value}else{input=document.createElement('input');input.type=options?.type||'number';if(input.type==='checkbox'){input.checked=!!value;input.style.width='auto'}else{input.value=value;input.step=options?.step??'.001';if(options?.min!==undefined)input.min=options.min;if(options?.max!==undefined)input.max=options.max}}input.id='part-'+key;input.setAttribute('aria-label',T(label));controls[key]=input;wrap.append(l,input);row.append(wrap)}parent.append(row)}
  function number(key,label){let input=controls[key],value=Number(input.value);if(!input.reportValidity()||input.value===''||!Number.isFinite(value))throw Error(TF('请检查{label}',{label}));return value}
 function advanced(){let b=document.createElement('button');b.className='small';b.style.width='100%';b.textContent=T('完整设置');b.onclick=()=>$('project-settings').click();parent.append(b)}
 function apply(text,update){let b=document.createElement('button');b.className='primary';b.style.width='100%';b.textContent=T(text);b.onclick=()=>applyPartConfiguration(update,b);parent.append(b)}
 if(kind==='skeleton'){
  heading('骨架');let outline=project.skeleton.outline,handles=project.skeleton.handle?(Array.isArray(project.skeleton.handle)?project.skeleton.handle:[project.skeleton.handle]):[],picks=project.skeleton.pick_hole?(Array.isArray(project.skeleton.pick_hole)?project.skeleton.pick_hole:[project.skeleton.pick_hole]):[],windowsConfig=project.skeleton.windows||{};
  if(outline.type!=='rect'||handles.length>1||picks.length>1||(windowsConfig.type&&windowsConfig.type!=='array')||windowsConfig.stagger||windowsConfig.skip?.length){parent.insertAdjacentHTML('beforeend','<p class="hint">当前骨架使用高级轮廓、多个把手或自定义定位开口，请在完整设置的高级 JSON 中编辑。</p>');advanced();return}
  let handle=handles[0]||{},nx=windowsConfig.nx||1,ny=windowsConfig.ny||1,px=windowsConfig.pitch_x||30,py=windowsConfig.pitch_y??px,angle=windowsConfig.angle||0,origin=windowsConfig.origin||[0,0],a=angle*Math.PI/180,cx=-(nx-1)*px/2,cy=-(ny-1)*py/2,centered=Math.abs(origin[0]-(cx*Math.cos(a)-cy*Math.sin(a)))<1e-6&&Math.abs(origin[1]-(cx*Math.sin(a)+cy*Math.cos(a)))<1e-6;
  subheading('外框');
  fields([['width','主体宽度 / mm',outline.width,{min:.01}],['height','主体高度 / mm',outline.height,{min:.01}],['radius','外框圆角 R / mm',outline.corner_radius||0,{min:0}]]);
  fields([['handle','把手位置',handle.edge||'none',{span:true,choices:{none:'不设置',top:'顶边',bottom:'底边',left:'左边',right:'右边'}}],['handlewidth','把手沿边宽度 / mm',handle.width||60,{min:.01}],['handleheight','把手凸出长度 / mm',handle.height||40,{min:.01}],['handleoffset','把手沿边偏移 / mm',handle.offset||0,{}]]);
  let toggle=()=>{let off=controls.handle.value==='none';for(const key of ['handlewidth','handleheight','handleoffset'])controls[key].disabled=off};controls.handle.onchange=toggle;toggle();
  subheading('基板定位开口');
  let note=document.createElement('p');note.className='hint';note.textContent=TF('开口按基板 {a} 加总旷量生成。',{a:shapeSizeText(project.substrate)});parent.append(note);
  fields([['clearance','总旷量 / mm',project.clearance_mm??.2,{min:0}],['nx','列数',nx,{min:1,max:20,step:1}],['ny','行数',ny,{min:1,max:20,step:1}],['pitchx','X 中心距 / mm',px,{min:.01}],['pitchy','Y 中心距 / mm',py,{min:.01}],['centered','阵列自动居中',centered,{type:'checkbox',span:true}],['originx','阵列起点 X / mm',origin[0],{}],['originy','阵列起点 Y / mm',origin[1],{}],['arrayangle','阵列旋转角 / °',angle,{}]]);
  let position=()=>{let locked=controls.centered.checked;controls.originx.disabled=locked;controls.originy.disabled=locked;if(!locked)return;let cols=Number(controls.nx.value)||1,rows=Number(controls.ny.value)||1,pitchX=Number(controls.pitchx.value)||0,pitchY=Number(controls.pitchy.value)||0,radians=(Number(controls.arrayangle.value)||0)*Math.PI/180,x=-(cols-1)*pitchX/2,y=-(rows-1)*pitchY/2;controls.originx.value=round(x*Math.cos(radians)-y*Math.sin(radians));controls.originy.value=round(x*Math.sin(radians)+y*Math.cos(radians))};controls.centered.onchange=position;for(const key of ['nx','ny','pitchx','pitchy','arrayangle'])controls[key].oninput=position;position();
  subheading('取片缺口');
  let pick=picks[0],pickPos=pick?(pick.corner||pick.edge||'top'):'none';
  fields([['pickpos','取片缺口位置',pickPos,{span:true,choices:{none:'不设置',top_right:'右上角',top_left:'左上角',bottom_right:'右下角',bottom_left:'左下角',top:'顶边',bottom:'底边',left:'左边',right:'右边'}}],['pickr','取片缺口 R / mm',(pick?.diameter||5)/2,{min:.01}],['pickinset','取片缺口内缩 / mm',pick?.inset||0,{}],['pickoffset','边上缺口偏移 / mm',pick?.offset||0,{}]]);
  let pickToggle=()=>{let p=controls.pickpos.value,off=p==='none',edge=!off&&['top','bottom','left','right'].includes(p);controls.pickr.disabled=off;controls.pickinset.disabled=off;controls.pickoffset.disabled=!edge};controls.pickpos.onchange=pickToggle;pickToggle();
  apply('应用骨架设置',s=>{s.skeleton.outline={type:'rect',width:number('width','骨架宽度'),height:number('height','骨架高度'),corner_radius:number('radius','骨架圆角')};if(controls.handle.value==='none')delete s.skeleton.handle;else s.skeleton.handle={edge:controls.handle.value,width:number('handlewidth','把手宽度'),height:number('handleheight','把手长度'),offset:number('handleoffset','把手偏移')};position();s.clearance_mm=number('clearance','总旷量');s.skeleton.windows={type:'array',nx:number('nx','列数'),ny:number('ny','行数'),pitch_x:number('pitchx','X 中心距'),pitch_y:number('pitchy','Y 中心距'),origin:[number('originx','阵列起点 X'),number('originy','阵列起点 Y')],angle:number('arrayangle','阵列旋转角')};let pos=controls.pickpos.value;if(pos==='none')delete s.skeleton.pick_hole;else{s.skeleton.pick_hole=[{diameter:2*number('pickr','取片缺口 R'),inset:number('pickinset','取片缺口内缩')}];if(['top','bottom','left','right'].includes(pos)){s.skeleton.pick_hole[0].edge=pos;s.skeleton.pick_hole[0].offset=number('pickoffset','边上缺口偏移')}else s.skeleton.pick_hole[0].corner=pos}});advanced();return;
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
 let manual=config.mode==='manual';
 if(manual){
  parent.insertAdjacentHTML('beforeend','<p class="hint">自主绘制：切换到“mask”页，用绘图工具画出 mask 外形（一个）与通光孔（多个），再点下面应用。</p>');
  fields([['margin','外框边缘余量 / mm',config.edge_margin_mm??project.min_web_mm??.3,{min:0}]]);
  apply('应用',s=>{let tm={...(s.test_mask||{}),mode:'manual',edge_margin_mm:number('margin','边缘余量')};s.test_mask=tm});
  let expBtn=document.createElement('button');expBtn.className='small';expBtn.style.width='100%';expBtn.textContent='单独导出 mask 切割 DXF';expBtn.onclick=()=>exportMaskOnly(expBtn);parent.append(expBtn);
  advanced();return;
 }
 if(outline&&!['rect','circle'].includes(outline.type)){parent.insertAdjacentHTML('beforeend','<p class="hint">当前测试 mask 使用高级自定义轮廓，请在完整板件设置的高级 JSON 中编辑。</p>');advanced();return}
 let mode=outline?.type||'substrate',base=outline||project.substrate;
 fields([['enabled','自动生成测试 mask',config.enabled!==false,{type:'checkbox',span:true}],['scale','通光孔边长比例 / %',(config.aperture_scale??.8)*100,{min:.1,max:99.9}],['snap','尺寸吸附 / mm',config.size_snap_mm??.1,{min:.001}],['margin','外框边缘余量 / mm',config.edge_margin_mm??project.min_web_mm??.3,{min:0}]]);
 fields([['mode','mask 外形',mode,{span:true,choices:{substrate:'跟随基板',rect:'独立矩形',circle:'独立圆形'}}],['width','矩形宽度 / mm',base.width||25,{min:.01}],['height','矩形高度 / mm',base.height||25,{min:.01}],['radius','矩形圆角 R / mm',base.corner_radius||0,{min:0}],['diameter','圆形直径 / mm',base.diameter||25,{min:.01}]]);
 let toggle=()=>{let mode=controls.mode.value;for(const key of ['width','height','radius'])controls[key].disabled=mode!=='rect';controls.diameter.disabled=mode!=='circle'};controls.mode.onchange=toggle;toggle();
 apply('应用',s=>{let tm={...(s.test_mask||{}),mode:'auto',enabled:controls.enabled.checked,aperture_scale:number('scale','边长比例')/100,size_snap_mm:number('snap','吸附步长'),edge_margin_mm:number('margin','边缘余量')};if(controls.mode.value==='substrate')delete tm.outline;else if(controls.mode.value==='circle')tm.outline={type:'circle',diameter:number('diameter','测试 mask 直径')};else tm.outline={type:'rect',width:number('width','测试 mask 宽度'),height:number('height','测试 mask 高度'),corner_radius:number('radius','测试 mask 圆角')};s.test_mask=tm});advanced();
}
const layoutPages=[['project','基本信息'],['substrate','基板'],['skeleton','骨架'],['array','定位开口与图案阵列'],['foil','掩模片'],['testmask','测试 mask'],['advanced','高级设置']];
const layoutFieldDefinitions=[
 ['name','项目名称','text','project'],
 ['subtype','基板形状',{rect:'矩形',circle:'圆形'},'substrate'],['subw','基板宽度 / mm',25,'substrate'],['subh','基板高度 / mm',25,'substrate'],['subd','基板直径 / mm',25,'substrate'],['subr','基板圆角 R / mm',0,'substrate'],
 ['bodyw','骨架主体宽度 / mm',190,'skeleton'],['bodyh','骨架主体高度 / mm',190,'skeleton'],['bodyr','骨架外框圆角 R / mm',0,'skeleton'],
 ['handleedge','把手位置',{none:'不设置',top:'顶边',bottom:'底边',left:'左边',right:'右边'},'skeleton'],['handlew','把手沿边宽度 / mm',60,'skeleton'],['handleh','把手凸出长度 / mm',40,'skeleton'],['handleoffset','把手沿边偏移 / mm',0,'skeleton'],
 ['pickpos','取片缺口位置',{none:'不设置',top_right:'右上角',top_left:'左上角',bottom_right:'右下角',bottom_left:'左下角',top:'顶边',bottom:'底边',left:'左边',right:'右边'},'skeleton'],['pickr','取片缺口 R / mm',2.5,'skeleton'],['pickinset','取片缺口内缩 / mm',0,'skeleton'],['pickoffset','边上缺口偏移 / mm',0,'skeleton'],
 ['mounttarget','安装孔（可选）',{none:'不设置',both:'两片',frame:'骨架',foil:'掩模片'},'skeleton'],['mountd','安装孔直径 / mm',3,'skeleton'],['mountinset','四角安装孔内缩 / mm',5,'skeleton'],
 ['clearance','总旷量 / mm',.2,'array'],['minweb','最小筋宽要求 / mm',.3,'array'],['nx','图案阵列列数',6,'array'],['ny','图案阵列行数',6,'array'],['px','X 中心距 / mm',30,'array'],['py','Y 中心距 / mm',30,'array'],['centered','阵列自动居中','checkbox','array'],['ox','阵列起点 X / mm',-75,'array'],['oy','阵列起点 Y / mm',-75,'array'],['arrayangle','阵列旋转角 / °',0,'array'],
 ['foiltype','掩模片外形模式',{follow:'跟随骨架外形（含把手）',rect:'独立矩形',circle:'独立圆形'},'foil'],['foilw','掩模片宽度 / mm',190,'foil'],['foilh','掩模片高度 / mm',190,'foil'],['foild','掩模片直径 / mm',190,'foil'],['foilr','掩模片圆角 R / mm',0,'foil'],['perwindow','每格复制图案','checkbox','foil'],
 ['testmaskenabled','自动生成测试 mask','checkbox','testmask'],['testmaskscale','通光孔边长比例 / %',80,'testmask'],['testmasksnap','通光孔尺寸吸附 / mm',.1,'testmask'],['testmaskmargin','外框边缘余量 / mm',.3,'testmask']
];
let activeLayoutPage='substrate';
function setLayoutPage(page){activeLayoutPage=page;const advanced=page==='advanced';$('layout-fields').hidden=advanced;$('layout-advanced').hidden=!advanced;document.querySelectorAll('.layout-page[data-layout-page]').forEach(p=>p.hidden=p.dataset.layoutPage!==page);document.querySelectorAll('#layout-tabs button').forEach(b=>{const selected=b.dataset.layoutPage===page;b.classList.toggle('active',selected);b.setAttribute('aria-selected',String(selected))})}
function makeLayoutFields(){let tabs=$('layout-tabs'),grid=$('layout-grid'),pages={};for(const [key,label]of layoutPages){let button=document.createElement('button');button.type='button';button.textContent=T(label);button.dataset.layoutPage=key;button.setAttribute('role','tab');button.onclick=()=>setLayoutPage(key);tabs.append(button);if(key==='advanced')continue;let page=document.createElement('section');page.className='layout-page stats-inputs';page.dataset.layoutPage=key;page.hidden=true;let title=document.createElement('h3');title.className='layout-page-title';title.textContent=T(label);page.append(title);grid.append(page);pages[key]=page}for(const [key,label,kind,page]of layoutFieldDefinitions){let field=document.createElement('div');field.className='field';if(key==='name'||key==='foiltype')field.classList.add('span');let l=document.createElement('label');l.htmlFor='layout-'+key;l.textContent=T(label);let input;if(typeof kind==='object'){input=document.createElement('select');for(const [v,t]of Object.entries(kind)){let option=document.createElement('option');option.value=v;option.textContent=T(t);input.append(option)}}else{input=document.createElement('input');input.type=kind==='checkbox'?'checkbox':kind==='text'?'text':'number';if(input.type==='number'){input.step=['nx','ny'].includes(key)?'1':'.001';input.min=['nx','ny'].includes(key)?'1':'0';if(['nx','ny'].includes(key))input.max=20;if(key==='testmaskscale'){input.min='.1';input.max='99.9'}if(key==='testmasksnap')input.min='.001'}if(input.type==='checkbox')input.style.width='auto'}input.id='layout-'+key;input.setAttribute('aria-label',T(label));field.append(l,input);pages[page].append(field)}for(const key of ['subtype','foiltype','centered','nx','ny','px','py'])$('layout-'+key).onchange=layoutConstraints;setLayoutPage(activeLayoutPage)}
function layoutConstraints(){const circle=$('layout-subtype').value==='circle';for(const key of ['subw','subh','subr'])$('layout-'+key).disabled=circle;$('layout-subd').disabled=!circle;const foiltype=$('layout-foiltype').value,foilFollow=foiltype==='follow',foilCircle=foiltype==='circle';for(const key of ['foilw','foilh','foilr'])$('layout-'+key).disabled=foilFollow||foilCircle;$('layout-foild').disabled=foilFollow||!foilCircle;let centered=$('layout-centered').checked;for(const key of ['ox','oy'])$('layout-'+key).disabled=centered;if(centered){const x=(+$('layout-nx').value-1)*+$('layout-px').value/2,y=(+$('layout-ny').value-1)*+$('layout-py').value/2,a=+$('layout-arrayangle').value*Math.PI/180;$('layout-ox').value=-x*Math.cos(a)+y*Math.sin(a);$('layout-oy').value=-x*Math.sin(a)-y*Math.cos(a)}}
function fillLayout(){const s=layoutSettings(),sk=s.skeleton,w=sk.windows||{},h=Array.isArray(sk.handle)?sk.handle[0]:sk.handle,p=Array.isArray(sk.pick_hole)?sk.pick_hole[0]:sk.pick_hole,fh=sk.frame_holes,ff=s.foil.frame_holes,mount=fh||ff,fo=s.foil.outline,tm=s.test_mask||{};let v={name:s.name,subtype:s.substrate.type,subw:s.substrate.width||25,subh:s.substrate.height||25,subd:s.substrate.diameter||25,subr:s.substrate.corner_radius||0,foiltype:fo?.type||'follow',foilw:fo?.width||sk.outline.width||190,foilh:fo?.height||sk.outline.height||190,foild:fo?.diameter||190,foilr:fo?.corner_radius||0,bodyw:sk.outline.width||190,bodyh:sk.outline.height||190,bodyr:sk.outline.corner_radius||0,clearance:s.clearance_mm??.2,minweb:s.min_web_mm??.3,nx:w.nx||1,ny:w.ny||1,px:w.pitch_x||30,py:w.pitch_y??w.pitch_x??30,ox:w.origin?.[0]||0,oy:w.origin?.[1]||0,arrayangle:w.angle||0,perwindow:s.foil.per_window!==false,testmaskenabled:tm.enabled!==false,testmaskscale:(tm.aperture_scale??.8)*100,testmasksnap:tm.size_snap_mm??.1,testmaskmargin:tm.edge_margin_mm??s.min_web_mm??.3,handleedge:h?(h.edge||'top'):'none',handlew:h?.width||60,handleh:h?.height||40,handleoffset:h?.offset||0,pickpos:p?(p.corner||p.edge||'top'):'none',pickr:(p?.diameter||5)/2,pickinset:p?.inset||0,pickoffset:p?.offset||0,mounttarget:fh&&ff?'both':fh?'frame':ff?'foil':'none',mountd:mount?.diameter||3,mountinset:mount?.inset??5};
 let a=(w.angle||0)*Math.PI/180,cx=-(v.nx-1)*v.px/2,cy=-(v.ny-1)*v.py/2;v.centered=Math.abs(v.ox-(cx*Math.cos(a)-cy*Math.sin(a)))<1e-6&&Math.abs(v.oy-(cx*Math.sin(a)+cy*Math.cos(a)))<1e-6;
 for(const [key,,kind]of layoutFieldDefinitions){let input=$('layout-'+key);if(kind==='checkbox')input.checked=!!v[key];else input.value=v[key]}
 let complex=(sk.outline.type&&sk.outline.type!=='rect')||(fo&& !['rect','circle'].includes(fo.type))||(w.type&&w.type!=='array')||w.stagger||w.skip?.length||(Array.isArray(sk.handle)&&sk.handle.length>1)||(Array.isArray(sk.pick_hole)&&sk.pick_hole.length>1)||mount?.positions||mount?.skip_corners?.length||(fh&&ff&&JSON.stringify(fh)!==JSON.stringify(ff));
 $('layout-json').value=JSON.stringify(s,null,2);$('layout-error').textContent=complex?'当前项目使用复杂几何配置，请在高级设置中编辑。':'';if(complex)setLayoutPage('advanced');else setLayoutPage(activeLayoutPage);layoutConstraints();
}
function formLayout(){const n=k=>{let value=Number($('layout-'+k).value);if($('layout-'+k).value===''||!Number.isFinite(value))throw Error('请输入有效数值');return value};let s=layoutSettings();s.name=$('layout-name').value.trim();s.substrate=$('layout-subtype').value==='circle'?{type:'circle',diameter:n('subd')}:{type:'rect',width:n('subw'),height:n('subh'),corner_radius:n('subr')};s.clearance_mm=n('clearance');s.min_web_mm=n('minweb');s.skeleton.outline={type:'rect',width:n('bodyw'),height:n('bodyh'),corner_radius:n('bodyr')};let foiltype=$('layout-foiltype').value;if(foiltype==='follow')delete s.foil.outline;else if(foiltype==='circle')s.foil.outline={type:'circle',diameter:n('foild')};else s.foil.outline={type:'rect',width:n('foilw'),height:n('foilh'),corner_radius:n('foilr')};layoutConstraints();s.skeleton.windows={type:'array',nx:n('nx'),ny:n('ny'),pitch_x:n('px'),pitch_y:n('py'),origin:[n('ox'),n('oy')],angle:n('arrayangle')};s.foil.per_window=$('layout-perwindow').checked;s.test_mask={...(s.test_mask||{}),enabled:$('layout-testmaskenabled').checked,aperture_scale:n('testmaskscale')/100,size_snap_mm:n('testmasksnap'),edge_margin_mm:n('testmaskmargin')};let edge=$('layout-handleedge').value;if(edge==='none')delete s.skeleton.handle;else s.skeleton.handle={edge,width:n('handlew'),height:n('handleh'),offset:n('handleoffset')};let pos=$('layout-pickpos').value;if(pos==='none')delete s.skeleton.pick_hole;else{s.skeleton.pick_hole=[{diameter:2*n('pickr'),inset:n('pickinset')}];if(pos.includes('_'))s.skeleton.pick_hole[0].corner=pos;else{s.skeleton.pick_hole[0].edge=pos;s.skeleton.pick_hole[0].offset=n('pickoffset')}}let target=$('layout-mounttarget').value;delete s.skeleton.frame_holes;delete s.foil.frame_holes;if(target!=='none'){let f={diameter:n('mountd'),inset:n('mountinset')};if(['both','frame'].includes(target))s.skeleton.frame_holes=clone(f);if(['both','foil'].includes(target))s.foil.frame_holes=clone(f)}return s}
$('project-settings').onclick=()=>{fillLayout();$('layout-dialog').showModal()};$('close-layout').onclick=()=>$('layout-dialog').close();$('reset-layout').onclick=fillLayout;
$('apply-layout').onclick=async()=>{let b=$('apply-layout');b.disabled=true;try{let settings=activeLayoutPage==='advanced'?JSON.parse($('layout-json').value):formLayout(),r=await api('layout',{...designPayload(),project_settings:settings});project=r.spec;frame=r.frame;extent=cellExtent();cameras={};updateProjectSummary();$('layout-dialog').close();history=[];future=[];selected.clear();changed();await api('save',designPayload());$('save-state').textContent='已保存项目设置';toast('项目设置已应用并保存')}catch(e){$('layout-error').textContent=e.message}finally{b.disabled=false}};

let importedProject=null;
async function saveCurrent(){clearTimeout(autoSaveTimer);let r=await api('save',designPayload());$('save-state').textContent='已保存';return r}
async function listProjects(){let response=await fetch('/api/projects'),r=await response.json();if(!response.ok)throw Error(r.error);$('library-path').textContent=TF('保存位置：{d}',{d:r.library_dir});let list=$('project-library');list.replaceChildren();for(const p of r.projects){let card=document.createElement('div');card.className='project-card';let title=document.createElement('strong');title.textContent=p.name+(p.current?T('（当前）'):'');let info=document.createElement('div');info.className='hint';info.textContent=TF('{n} 个定位开口',{n:p.cells});let path=document.createElement('div');path.className='hint';path.style.overflowWrap='anywhere';path.textContent=p.path;let open=document.createElement('button');open.className='small';open.textContent=p.current?T('已打开'):T('打开');open.disabled=p.current;open.onclick=async()=>{open.disabled=true;try{await saveCurrent();await api('project-open',{id:p.id,project_key:projectKey});location.reload()}catch(e){toast(e.message);open.disabled=false}};card.append(title,info,path,open);list.append(card)}}
$('manage-projects').onclick=async()=>{try{await listProjects();$('projects-dialog').showModal()}catch(e){toast(e.message)}};$('close-projects').onclick=()=>$('projects-dialog').close();
function showNew(mode){importedProject=null;$('new-project-mode').value=mode;$('new-project-name').value=mode==='copy'?TF('{name} 副本',{name:project.name}):T('新建掩模项目');$('new-project-error').textContent='';$('new-project-dialog').showModal()}
$('new-project').onclick=()=>showNew('empty');$('copy-project').onclick=()=>showNew('copy');$('new-in-library').onclick=()=>{$('projects-dialog').close();showNew('empty')};document.addEventListener('click',e=>{let menu=$('project-actions-menu');if(menu.open&&!menu.contains(e.target))menu.open=false});for(const id of ['new-project','manage-projects','copy-project'])$(id).addEventListener('click',()=>$('project-actions-menu').removeAttribute('open'));
$('create-project').onclick=async()=>{let b=$('create-project');b.disabled=true;try{let name=$('new-project-name').value.trim();if(!name)throw Error('请输入项目名称');await saveCurrent();let route=importedProject?'project-import':$('new-project-mode').value==='copy'?'project-copy':'project-new';await api(route,{name,spec:importedProject,project_key:projectKey});if(route==='project-new')sessionStorage.setItem('open-layout-after-reload','1');location.reload()}catch(e){$('new-project-error').textContent=e.message}finally{b.disabled=false}};$('cancel-new-project').onclick=()=>$('new-project-dialog').close();
$('import-project').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;const obj=JSON.parse((await file.text()).replace(/^\uFEFF/,''));if(!obj.skeleton||!obj.substrate||!obj.foil)throw Error('请选择完整蒸镀总成项目JSON');$('projects-dialog').close();showNew('copy');importedProject=obj;$('new-project-name').value=obj.name||file.name.replace(/\.json$/i,'');$('new-project-mode').disabled=true}catch(e){toast(e.message)}finally{e.target.value=''}};
$('new-project-dialog').addEventListener('close',()=>{$('new-project-mode').disabled=false});
$('quit-service').onclick=async()=>{try{await saveCurrent();await api('shutdown',{});$('projects-dialog').close();toast('本地工作台已结束，可以关闭此页面。');document.querySelectorAll('button').forEach(b=>b.disabled=true)}catch(e){toast(e.message)}};
makeLayoutFields();$('layout-arrayangle').onchange=layoutConstraints;
init().then(()=>{if(sessionStorage.getItem('open-layout-after-reload')==='1'){sessionStorage.removeItem('open-layout-after-reload');$('project-settings').click()}});
