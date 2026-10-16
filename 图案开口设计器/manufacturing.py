"""Create a complete, current-only manufacturing package in memory."""
import copy
import csv
from html import escape
import io
import json
import math
from zipfile import ZipFile, ZIP_DEFLATED
from shapely import affinity
from shapely.ops import unary_union


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
    writer.writerow(['计算对象','仅活性区域；公共电极和未标记开口不计算'])
    writer.writerow(['计算方法','解析灵敏度的一阶公式传播，单活性区域，不加和'])
    for key,value in statistics['settings'].items():writer.writerow([key,value])
    writer.writerow(['活性区域','原开口序号','region_role','有效面积_mm2','有效面积_cm2','u_mm2','U_k2_mm2','相对u_%','公式','说明','状态'])
    for row in statistics['pixels']:
        writer.writerow([row['pixel'],row['opening'],row['region_role'],row['area_mm2'],row['area_cm2'],row['u_mm2'],row['U_mm2'],row['relative_u_percent'],row['formula'],row['warning'],row['status']])
    for note in statistics['notes']:writer.writerow(['说明',note])
    return '\ufeff'+out.getvalue()


def _polygon_cuts(geometry):
    """Convert an active/ITO intersection into closed DXF cutting contours."""
    if geometry.is_empty:
        return []
    if geometry.geom_type == 'Polygon':
        if geometry.interiors:
            raise ValueError('活性区域与ITO交集产生带岛孔的复杂轮廓，暂不能自动生成测试遮光掩模')
        points=[(float(x),float(y)) for x,y in list(geometry.exterior.coords)[:-1]]
        return [('poly',points)] if len(points)>=3 and geometry.area>1e-9 else []
    if geometry.geom_type in ('MultiPolygon','GeometryCollection'):
        return [shape for item in geometry.geoms for shape in _polygon_cuts(item)]
    raise ValueError(f'活性区域与ITO交集产生{geometry.geom_type}，无法形成闭合测试通光孔')


def _snap_length(value, step, upper):
    """将目标边长吸附到 step，同时保证严格小于活性有效区域。"""
    snapped=int(value/step+.5)*step
    if snapped>=upper-1e-9:
        snapped=int((upper-1e-9)/step)*step
    if snapped<=1e-9:
        raise ValueError(f'活性有效区域边长 {upper:.4f} mm 过小，无法生成吸附到 {step:g} mm 的更小通光孔')
    return snapped


def _scaled_snapped_components(geometry, scale, snap):
    """Scale each effective-area component about its oriented centre and snap its two spans."""
    if geometry.is_empty:
        return []
    if geometry.geom_type in ('MultiPolygon','GeometryCollection'):
        return [item for child in geometry.geoms
                for item in _scaled_snapped_components(child,scale,snap)]
    if geometry.geom_type!='Polygon':
        raise ValueError(f'活性有效区域产生{geometry.geom_type}，无法形成闭合测试通光孔')
    if geometry.interiors:
        raise ValueError('活性有效区域产生带岛孔的复杂轮廓，暂不能自动生成测试遮光掩模')
    rectangle=geometry.minimum_rotated_rectangle
    points=list(rectangle.exterior.coords)
    edges=[(points[i+1][0]-points[i][0],points[i+1][1]-points[i][1]) for i in range(4)]
    dx,dy=max(edges,key=lambda edge:edge[0]**2+edge[1]**2)
    angle=math.degrees(math.atan2(dy,dx))
    origin=(rectangle.centroid.x,rectangle.centroid.y)
    aligned=affinity.rotate(geometry,-angle,origin=origin)
    x0,y0,x1,y1=aligned.bounds
    width,height=x1-x0,y1-y0
    target_w=_snap_length(width*scale,snap,width)
    target_h=_snap_length(height*scale,snap,height)
    centre=((x0+x1)/2,(y0+y1)/2)
    result=affinity.scale(aligned,target_w/width,target_h/height,origin=centre)
    result=affinity.rotate(result,angle,origin=origin)
    if not geometry.contains(result) or geometry.boundary.distance(result)<=1e-7:
        raise ValueError('通光孔缩放后未能严格位于活性有效区域内；请降低边长比例或简化区域轮廓')
    return [result]


def build_test_mask(spec,m,area_stats):
    """Build one substrate-sized light-blocking test mask from active effective areas."""
    config=spec.get('test_mask') or {}
    if not isinstance(config,dict):
        raise ValueError('test_mask 必须是对象')
    if config.get('mode')=='manual':
        return _build_manual_test_mask(spec,m,config)
    if config.get('enabled',True) is False:
        return None,None
    scale=float(config.get('aperture_scale',.8))
    snap=float(config.get('size_snap_mm',.1))
    if not 0<scale<1:
        raise ValueError('test_mask.aperture_scale 必须大于0且小于1，才能使通光孔小于活性有效区域')
    if snap<=0:
        raise ValueError('test_mask.size_snap_mm 必须 > 0')
    if spec.get('foil',{}).get('per_window',True) is False:
        raise ValueError('当前图案使用全板绝对坐标，无法自动派生单片测试遮光掩模；请改为每格复制图案')
    active=area_stats.active_apertures(spec,m)
    if not active:
        return None,None
    regions=area_stats.expand((spec.get('ito_effective') or {}).get('features') or [],m)
    if not regions:
        raise ValueError('已有活性区域，但未定义ITO有效区域，无法确定测试遮光掩模的通光孔')
    ito=unary_union([area_stats.geometry(region) for region in regions])
    holes=[]
    for aperture in active:
        effective=area_stats.geometry(aperture).intersection(ito)
        for reduced in _scaled_snapped_components(effective,scale,snap):
            holes.extend(_polygon_cuts(reduced))
    if not holes:
        raise ValueError('活性区域与ITO有效区域没有交集，未生成测试遮光掩模')
    part=m.Part('TEST_MASK','测试遮光掩模')
    outline_spec=config.get('outline') or spec['substrate']
    part.outline=m.build_outline(outline_spec,spec.get('arc_segments_per_90',24))
    part.holes=holes
    edge_margin=float(config.get('edge_margin_mm',spec.get('min_web_mm',.3)))
    part.bounds=[m._inset_boundary(part.outline,edge_margin)]
    test_spec={'kind':'light_block','name':spec['name']+' 测试遮光掩模','substrate':outline_spec,
               'aperture_inset_mm':0,'min_web_mm':spec.get('min_web_mm',.3),
               'arc_segments_per_90':spec.get('arc_segments_per_90',24),
               'curve_tolerance_mm':spec.get('curve_tolerance_mm',.001)}
    m.validate_parts([part],test_spec)
    extra=m._extra_info(test_spec,'light_block')
    extra[1]=f'通光孔尺寸 : 活性有效区域边长的 {scale*100:.1f}%, 以 {snap:.3f} mm 吸附'
    extra.append(f'外框边缘余量 : 至少 {edge_margin:.3f} mm')
    report=m.analyze(test_spec,[part],extra)
    if part.validation_errors:
        raise ValueError('测试遮光掩模几何校验未通过：'+'；'.join(part.validation_errors))
    return part,report


def _build_manual_test_mask(spec,m,config):
    """Manual mode: the test mask's outline and through-holes are drawn by the user."""
    feature_list=config.get('holes') or []
    if not feature_list:
        return None,None
    outline_spec=config.get('outline') or spec['substrate']
    holes=m.build_features(feature_list,'test_mask')
    part=m.Part('TEST_MASK','测试遮光掩模')
    part.outline=m.build_outline(outline_spec,spec.get('arc_segments_per_90',24))
    part.holes=holes
    edge_margin=float(config.get('edge_margin_mm',spec.get('min_web_mm',.3)))
    part.bounds=[m._inset_boundary(part.outline,edge_margin)]
    test_spec={'kind':'light_block','name':spec['name']+' 测试遮光掩模','substrate':outline_spec,
               'aperture_inset_mm':0,'min_web_mm':spec.get('min_web_mm',.3),
               'arc_segments_per_90':spec.get('arc_segments_per_90',24),
               'curve_tolerance_mm':spec.get('curve_tolerance_mm',.001)}
    m.validate_parts([part],test_spec)
    extra=m._extra_info(test_spec,'light_block')
    extra[1]=f'通光孔尺寸 : 自主绘制，{len(holes)} 个'
    extra.append(f'外框边缘余量 : 至少 {edge_margin:.3f} mm')
    report=m.analyze(test_spec,[part],extra)
    if part.validation_errors:
        raise ValueError('测试遮光掩模几何校验未通过：'+'；'.join(part.validation_errors))
    return part,report


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
    files['装配预览.svg']=preview(spec,m)
    files['加工说明.txt']=f'''{name}
单位mm，比例1:1，DXF R12，设计名义尺寸，割缝补偿由加工方设置。
切割使用“掩模片_切割.dxf”和“骨架_切割.dxf”；激光打标使用独立打标DXF。
ITO_EFFECTIVE、SUB_REFERENCE和装配图用于复核，不作为切割轮廓。
LASER_MARK文字轮廓用于打标，不得切穿。取片缺口已并入定位开口，不另计孔。
若存在活性区域和ITO有效区域，自动输出测试遮光掩模：外形默认同基板，通光孔以活性区域开口与ITO的交集为母轮廓，默认按80% 边长缩小并以0.1 mm吸附；公共电极不进入测试掩模。
图纸不标材料或厚度，下单时选择。请查看几何校验报告中的错误和警告。
'''
    try:
        test_mask,test_report=build_test_mask(spec,m,area_stats)
        if test_mask:
            filename=f'{name}_测试遮光掩模_切割.dxf'
            files[filename]=m.render([test_mask],False)
            files['测试遮光掩模_校验报告.txt']=test_report
            spec['outputs']['test_mask']=filename
    except ValueError as exc:
        files['测试遮光掩模_生成说明.txt']=str(exc)
    if spec.get('ito_effective',{}).get('features'):
        try:files['有效面积不确定度.csv']=statistics_csv(area_stats.calculate(spec,m,spec.get('uncertainty_settings')))
        except ValueError as exc:files['面积计算说明.txt']=str(exc)
    files['完整设计参数.json']=json.dumps(spec,ensure_ascii=False,indent=2)+'\n'
    archive=io.BytesIO()
    with ZipFile(archive,'w',ZIP_DEFLATED) as z:
        for filename,text in files.items():z.writestr(filename,text.encode('utf-8'))
    files[f'{name}_加工文件包.zip']=archive.getvalue()
    return report,files,spec
