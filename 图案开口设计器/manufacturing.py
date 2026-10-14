"""Create a complete, current-only manufacturing package in memory."""
import copy
import csv
from html import escape
import io
import json
from zipfile import ZipFile, ZIP_DEFLATED


def preview(spec, m):
    foil, frame, _ = m.build_evaporation(spec, spec.get('arc_segments_per_90',24))
    x0,y0,x1,y1=m.shape_bbox(frame.outline)
    pad=max(x1-x0,y1-y0)*.05
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0-pad} {-y1-pad} {x1-x0+2*pad} {y1-y0+2*pad}">',
           f'<title>{escape(spec["name"])} 装配预览</title><g transform="scale(1 -1)">']
    def shape(s,fill,stroke,width=.15,dash=None):
        extra=f' stroke-dasharray="{dash}"' if dash else ''
        if s[0]=='circle':
            parts.append(f'<circle cx="{s[1]}" cy="{s[2]}" r="{s[3]}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"{extra}/>')
        else:
            d='M'+'L'.join(f'{x},{y}' for x,y in s[1])+'Z'
            parts.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"{extra}/>')
    shape(foil.outline,'#fff2af','#d4c77b')
    shape(frame.outline,'#add8e6','#6b97a7')
    for w in frame.window_cuts:shape(w,'#fff2af','#6b97a7')
    for h in foil.holes:shape(h,'#197366','#13594f',.04)
    for h in frame.tooling+foil.tooling:shape(h,'white','#6b97a7')
    for r in foil.ito_effective or []:shape(r,'none','#aa42a0',.12,'.5 .3')
    seen=set()
    for part in (foil,frame):
        for item in part.marking:
            key=json.dumps(item['contours'])
            if key in seen:continue
            seen.add(key)
            d=''.join('M'+'L'.join(f'{x},{y}' for x,y in s[1])+'Z' for s in item['contours'])
            parts.append(f'<path d="{d}" fill="#d77a28" fill-rule="evenodd"/>')
    parts.append('</g></svg>')
    return ''.join(parts)


def statistics_csv(statistics):
    out=io.StringIO(newline='');writer=csv.writer(out)
    writer.writerow(['计算方法','解析灵敏度的一阶公式传播，单Pixel，不加和'])
    for key,value in statistics['settings'].items():writer.writerow([key,value])
    writer.writerow(['pixel','有效面积_mm2','有效面积_cm2','u_mm2','U_k2_mm2','相对u_%','公式','说明','状态'])
    for row in statistics['pixels']:
        writer.writerow([row['pixel'],row['area_mm2'],row['area_cm2'],row['u_mm2'],row['U_mm2'],row['relative_u_percent'],row['formula'],row['warning'],row['status']])
    for note in statistics['notes']:writer.writerow(['说明',note])
    return '\ufeff'+out.getvalue()


def package(spec,m,area_stats):
    name=spec['name'];spec=copy.deepcopy(spec)
    spec['outputs']={'assembly':f'{name}_装配参考.dxf','foil':f'{name}_掩模片_含ITO参考.dxf','skeleton':f'{name}_骨架_含ITO参考.dxf'}
    foil,frame,ref=m.build_evaporation(spec,spec.get('arc_segments_per_90',24))
    m.validate_parts([foil,frame],spec)
    report=m.analyze(spec,[foil,frame],m._extra_info(spec,'evaporation'))
    if foil.validation_errors or frame.validation_errors:
        return report,{},spec
    files={spec['outputs']['assembly']:m.render([foil,frame,ref],True),
           spec['outputs']['foil']:m.render([foil],False),spec['outputs']['skeleton']:m.render([frame],False)}
    for part,suffix in [(foil,'掩模片'),(frame,'骨架')]:
        if part.marking:files[f'{name}_{suffix}_激光打标.dxf']=m.render_marking(part)
        cut=copy.deepcopy(part);cut.ito_effective=None;cut.reference=[];cut.marking=[];cut.marking_enabled=False
        files[f'{name}_{suffix}_切割.dxf']=m.render([cut],False)
    files['几何校验报告.txt']=report
    files['完整设计参数.json']=json.dumps(spec,ensure_ascii=False,indent=2)+'\n'
    files['装配预览.svg']=preview(spec,m)
    files['加工说明.txt']=f'''{name}
单位mm，比例1:1，DXF R12，设计名义尺寸，割缝补偿由加工方设置。
切割使用“掩模片_切割.dxf”和“骨架_切割.dxf”；激光打标使用独立打标DXF。
ITO_EFFECTIVE、SUB_REFERENCE和装配图用于复核，不作为切割轮廓。
LASER_MARK文字轮廓用于打标，不得切穿。取片缺口已并入定位开口，不另计孔。
图纸不标材料或厚度，下单时选择。请查看几何校验报告中的错误和警告。
'''
    if spec.get('ito_effective',{}).get('features'):
        try:files['有效面积不确定度.csv']=statistics_csv(area_stats.calculate(spec,m,spec.get('uncertainty_settings')))
        except ValueError as exc:files['面积计算说明.txt']=str(exc)
    archive=io.BytesIO()
    with ZipFile(archive,'w',ZIP_DEFLATED) as z:
        for filename,text in files.items():z.writestr(filename,text.encode('utf-8'))
    files[f'{name}_加工文件包.zip']=archive.getvalue()
    return report,files,spec
