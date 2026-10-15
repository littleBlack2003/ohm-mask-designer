"""Package the approved GUI design and verify serialized manufacturing contours."""
import copy
import importlib.util
import json
from pathlib import Path
from collections import Counter
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'加工图纸'
loader=importlib.util.spec_from_file_location('mask',ROOT.parent/'ohm-mask-skill/scripts/make_mask.py')
m=importlib.util.module_from_spec(loader);loader.loader.exec_module(m)
spec=json.loads((ROOT/'图案开口设计草稿.json').read_text(encoding='utf-8'))
spec['_stage']='加工图纸'
m.validate_spec(spec)
foil,frame,reference=m.build_evaporation(spec,spec.get('arc_segments_per_90',24))
m.validate_parts([foil,frame],spec)
report=m.analyze(spec,[foil,frame],m._extra_info(spec,'evaporation'))
if foil.validation_errors or frame.validation_errors:raise RuntimeError(report)

def parse_contours(text):
    lines=text.splitlines()
    if len(lines)%2:raise ValueError('DXF group code/value pairing failed')
    records=[];current=None;in_entities=False;section=False
    for code,value in zip(lines[::2],lines[1::2]):
        if code=='0' and value=='SECTION':section=True;continue
        if section and code=='2':in_entities=value=='ENTITIES';section=False;continue
        if not in_entities:continue
        if code=='0':
            if current:records.append(current)
            current=[value,[]]
            if value=='ENDSEC':in_entities=False
        elif current:current[1].append((code,value))
    contours=[]
    for i,(kind,fields) in enumerate(records):
        if kind not in ('POLYLINE','CIRCLE'):continue
        data=dict(fields)
        if kind=='POLYLINE':
            if data.get('70')!='1':raise ValueError('Unclosed cutting polyline')
            points=[];j=i+1
            while records[j][0]=='VERTEX':
                p=dict(records[j][1]);points.append((float(p['10']),float(p['20'])));j+=1
            if records[j][0]!='SEQEND':raise ValueError('Missing SEQEND')
            shape=('poly',points)
        else:shape=('circle',float(data['10']),float(data['20']),float(data['40']))
        m.shape_geometry(shape)
        contours.append((data['8'],shape))
    return contours

name=spec['name']
OUT.mkdir(exist_ok=True)
cut_foil=copy.deepcopy(foil);cut_frame=copy.deepcopy(frame)
cut_foil.ito_effective=cut_frame.ito_effective=None
cut_foil.reference=[];cut_frame.reference=[]
cut_foil.marking=[];cut_frame.marking=[]
cut_foil.marking_enabled=cut_frame.marking_enabled=False
texts={
    f'{name}_掩模片_切割.dxf':m.render([cut_foil],False),
    f'{name}_骨架_切割.dxf':m.render([cut_frame],False),
    f'{name}_装配参考.dxf':m.render([foil,frame,reference],True),
    f'{name}_掩模片_含ITO参考.dxf':m.render([foil],False),
    f'{name}_骨架_含ITO参考.dxf':m.render([frame],False),
}
for part,suffix in [(foil,'掩模片'),(frame,'骨架')]:
    if part.marking:
        texts[f'{name}_{suffix}_激光打标.dxf']=m.render_marking(part)
checks=[]
for filename,text in texts.items():
    contours=parse_contours(text)
    counts=Counter(layer for layer,_ in contours)
    if '_切割.dxf' in filename:
        expected=({'OUTLINE':1,'HOLES':len(foil.holes)} if '掩模片' in filename
                  else {'OUTLINE':1,'WINDOW':len(frame.window_cuts)})
        if dict(counts)!=expected:raise ValueError(f'{filename}: unexpected machining layers {counts}')
        rounded=m.Part('ROUND','serialized DXF')
        rounded.outline=next(s for layer,s in contours if layer=='OUTLINE')
        rounded.holes=[s for layer,s in contours if layer!='OUTLINE']
        m.validate_parts([rounded],spec)
        if rounded.validation_errors:raise ValueError(rounded.validation_errors)
    if '含ITO参考' in filename or '装配参考' in filename:
        if counts['ITO_EFFECTIVE']!=len(foil.ito_effective or []):raise ValueError('ITO region count mismatch')
    (OUT/filename).write_text(text,encoding='utf-8',newline='\n')
    checks.append(f'{filename}\n  闭合轮廓检查通过；图层实体数量：{dict(counts)}')

(OUT/'完整设计参数.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'几何校验报告.txt').write_text(report+'\n',encoding='utf-8')
(OUT/'DXF轮廓检查.txt').write_text('\n\n'.join(checks)+'\n',encoding='utf-8')
instructions=f'''{name}
加工图纸包 · 2026-10-12

加工文件：
  {name}_掩模片_切割.dxf
  {name}_骨架_切割.dxf
切割版只包含OUTLINE、HOLES或WINDOW加工轮廓。

复核文件：装配参考、掩模片含ITO参考、骨架含ITO参考。
ITO_EFFECTIVE与SUB_REFERENCE均为参考图层，在CAM中须排除。
LASER_MARK为激光打标字形矢量轮廓，按打标加工；独立激光打标DXF只含该图层，切割版不含打标文字。
装配参考图用于叠加核对两片与基片位置。

单位mm，比例1:1，DXF R12(AC1009)。名义尺寸，不含割缝补偿；由加工方在CAM设置补偿与引线。
主体190×190；顶边居中把手沿边60、向外40；总体190×230。
25×25基片；定位开口25.2×25.2，直角（R0）；图案阵列6×6、中心距30×30。
每格右上角取片缺口R2.5，共36个；无安装孔。
每格6个3×11开口（中心X=-5/0/5，Y=-7/+7），2个4×10开口（中心X=-10.5/+10.5，Y=0）。
掩模片共288个图案开口。ITO有效区域每格25×10，居中，仅作参考。
厚度与材料不在图纸标注，下单时选择。
已检查真实边界、加工轮廓相交/重叠及DXF闭合标志；详见两份检查报告。
'''
(OUT/'加工说明.txt').write_text(instructions,encoding='utf-8')
archive=ROOT/f'{name}_加工图纸包_直角定位开口.zip'
with ZipFile(archive,'w',ZIP_DEFLATED) as z:
    for file in sorted(OUT.iterdir()):
        if file.is_file():z.write(file,file.name)
print(report)
print('\n'.join(checks))
print(archive)
