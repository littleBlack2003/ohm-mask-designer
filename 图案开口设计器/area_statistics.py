"""Geometric counts and formula-based uncertainty of aperture/ITO intersections.

Tolerance inputs are full dimension tolerances, not per-edge offsets. ITO size
errors and relative translation are shared by all pixels in one cell; aperture
dimension errors are independent. No inter-cell uncertainty model is implied.
"""
import math
from shapely import affinity
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union

DEFAULTS = dict(distribution='uniform', aperture_mm=.01, ito_mm=0.,
                registration_x_mm=0., registration_y_mm=0.)


def settings(value=None):
    if value is not None and not isinstance(value, dict):
        raise ValueError('不确定度设置必须为对象')
    result = DEFAULTS | (value or {})
    if result['distribution'] not in ('uniform', 'normal'):
        raise ValueError('请选择矩形分布公差或正态分布标准不确定度')
    for key in ('aperture_mm', 'ito_mm', 'registration_x_mm', 'registration_y_mm'):
        v = result[key]
        if isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or not 0 <= v <= 10:
            raise ValueError('误差输入须为0～10 mm的有限数值')
        result[key] = float(v)
    return {key: result[key] for key in DEFAULTS}


def expand(features, m):
    """Expand arrays into individual dimensioned primitives, preserving order."""
    result = []
    for source, f in enumerate(features):
        if f['type'] in ('rect_array', 'circle_array'):
            def primitive(x, y):
                q = dict(f, type='rect' if f['type']=='rect_array' else 'circle', center=[x,y])
                q['source'] = source
                return q
            result.extend(m.expand_array(f, primitive))
        else:
            result.append(dict(f, source=source))
    return result



def scoped_regions(spec,regions,m):
    if spec['foil'].get('per_window',True):return regions
    result=[]
    for x,y,angle in m.window_centers(spec['skeleton']['windows']):
        for p in regions:
            q=dict(p)
            if p['type']=='polygon':q['points']=[(x+rx,y+ry) for rx,ry in (m.rot(a,b,angle) for a,b in p['points'])]
            else:
                rx,ry=m.rot(*p.get('center',[0,0]),angle);q['center']=[x+rx,y+ry];q['angle']=p.get('angle',0)+angle
            result.append(q)
    return result

def geometry(p):
    kind = p['type']
    if kind == 'polygon':
        return Polygon(p['points'])
    if kind == 'circle':
        # Dense approximation keeps curved intersection error small relative
        # to normal machining tolerances (whole-disc relative area < 7e-6).
        return Point(p.get('center', [0,0])).buffer(p['diameter']/2, quad_segs=256)
    if kind == 'rect':
        w, h = p['width']/2, p['height']/2
        g = box(-w, -h, w, h)
    elif kind == 'slot':
        r, half = p['width']/2, (p['length']-p['width'])/2
        g = (LineString([(-half,0),(half,0)]).buffer(r, quad_segs=256)
             if half > 0 else Point(0,0).buffer(r, quad_segs=256))
    else:
        raise ValueError('不支持的面积图案类型')
    g = affinity.rotate(g, p.get('angle', 0), origin=(0,0))
    x, y = p.get('center', [0,0])
    return affinity.translate(g, x, y)


def components(g):
    if g.is_empty: return 0
    if g.geom_type == 'Polygon': return 1
    return sum(components(item) for item in g.geoms)


def nominal(spec, m):
    apertures = expand(spec['foil'].get('cell') or [], m)
    regions = scoped_regions(spec,expand((spec.get('ito_effective') or {}).get('features') or [], m),m)
    holes = [geometry(p) for p in apertures]
    ito = unary_union([geometry(p) for p in regions])
    hole_union = unary_union(holes)
    centers = m.window_centers(spec['skeleton']['windows'])
    repeats = len(centers) if spec['foil'].get('per_window', True) else 1
    sk = spec['skeleton']
    base = m.expand_outline(spec['substrate'], spec.get('clearance_mm',.2)/2, 24)
    windows = [m.transform_shape(base,*c) for c in centers]
    cuts = m.merge_window_cuts(windows, m.build_pick_holes(sk.get('pick_hole'),base,centers),24,.001)
    body = m.build_outline(sk['outline'],24)
    frame_tooling = len(m.build_frame_holes(sk['frame_holes'],body,'skeleton.frame_holes')) if sk.get('frame_holes') else 0
    foil_tooling = len(m.build_frame_holes(spec['foil']['frame_holes'],body,'foil.frame_holes')) if spec['foil'].get('frame_holes') else 0
    overlap = any(g.intersects(other) for i,g in enumerate(holes) for other in holes[i+1:])
    rows = []
    for i, (p,g) in enumerate(zip(apertures,holes)):
        area = (full_area(p) if ito.covers(g) else g.intersection(ito).area) if regions else None
        rows.append(dict(pixel=i+1, source=p['source'], shape=p['type'],
                         opening_mm2=full_area(p), area_mm2=area,
                         area_cm2=None if area is None else area/100))
    return dict(counts=dict(cells=len(centers), cell_openings=len(holes),
                cell_connected_openings=components(hole_union),
                foil_pattern_openings=len(holes)*repeats, foil_mounting_holes=foil_tooling,
                foil_total_openings=len(holes)*repeats+foil_tooling,
                frame_positioning_openings=len(cuts), frame_mounting_holes=frame_tooling,
                frame_total_openings=len(cuts)+frame_tooling), pixels=rows,
                ito_defined=bool(regions), overlapping=overlap)



def dimensions(p):
    return {'rect':('width','height'), 'circle':('diameter',),
            'slot':('length','width'), 'polygon':()}[p['type']]


def full_area(p):
    if p['type']=='rect':return p['width']*p['height']
    if p['type']=='circle':return math.pi*p['diameter']**2/4
    if p['type']=='slot':return p['width']*(p['length']-p['width'])+math.pi*p['width']**2/4
    return geometry(p).area


def interval_overlap(a,b,A,B,da,db,dA,dB,side):
    """Closed piecewise derivatives of max(0,min(b,B)-max(a,A))."""
    tol=1e-9
    length=min(b,B)-max(a,A)
    if b<B-tol:upper=db
    elif b>B+tol:upper=dB
    else:upper=min(db,dB) if side>0 else max(db,dB)
    if a>A+tol:lower=da
    elif a<A-tol:lower=dA
    else:lower=max(da,dA) if side>0 else min(da,dA)
    slope=upper-lower
    if length<-tol:slope=0.
    elif abs(length)<=tol:slope=max(0.,slope) if side>0 else min(0.,slope)
    return max(0.,length),slope


def rectangular_formula(p,r,opts):
    theta=math.radians(r.get('angle',0));cs,sn=math.cos(theta),math.sin(theta)
    delta=(p.get('angle',0)-r.get('angle',0))%180
    if min(abs(delta),abs(delta-90),abs(delta-180))>1e-8:return None
    swap=abs(delta-90)<1e-8
    w,h=(p['height'],p['width']) if swap else (p['width'],p['height'])
    px,py=p.get('center',[0,0]);rx,ry=r.get('center',[0,0])
    dx,dy=px-rx,py-ry;x,y=cs*dx+sn*dy,-sn*dx+cs*dy
    ax,bx,ay,by=x-w/2,x+w/2,y-h/2,y+h/2
    Ax,Bx,Ay,By=-r['width']/2,r['width']/2,-r['height']/2,r['height']/2
    # Slopes of left/right aperture and ITO edges in the ITO coordinate system.
    w_edges=(-.5,.5,0,0,0,0,0,0)
    h_edges=(0,0,-.5,.5,0,0,0,0)
    parameters=[('w',opts['aperture_mm'],h_edges if swap else w_edges),
                ('h',opts['aperture_mm'],w_edges if swap else h_edges),
                ('W',opts['ito_mm'],(0,0,0,0,-.5,.5,0,0)),
                ('H',opts['ito_mm'],(0,0,0,0,0,0,-.5,.5)),
                ('X',opts['registration_x_mm'],(0,0,0,0,cs,cs,-sn,-sn)),
                ('Y',opts['registration_y_mm'],(0,0,0,0,sn,sn,cs,cs))]
    terms=[];warnings=[]
    for name,error,edge_slopes in parameters:
        if not error:continue
        slopes=[]
        for side in (-1,1):
            da,db,dc,dd,dA,dB,dC,dD=edge_slopes
            lx,sx=interval_overlap(ax,bx,Ax,Bx,da,db,dA,dB,side)
            ly,sy=interval_overlap(ay,by,Ay,By,dc,dd,dC,dD,side)
            slopes.append(ly*sx+lx*sy)
        coefficient=max(slopes,key=abs)
        if abs(slopes[0]-slopes[1])>1e-8:
            warnings.append('边界重合，取较大单侧灵敏度作保守线性估计')
        terms.append((name,coefficient,error))
    # If a tolerance can change the active min/max branch, local linear
    # propagation is no longer representative over the entire input range.
    span=1 if opts['distribution']=='uniform' else 3
    gaps=[abs(ax-Ax),abs(bx-Bx),abs(ay-Ay),abs(by-By),
          abs(ax-Bx),abs(bx-Ax),abs(ay-By),abs(by-Ay)]
    reach=span*(opts['aperture_mm']/2+opts['ito_mm']/2+
                abs(cs)*opts['registration_x_mm']+abs(sn)*opts['registration_y_mm'])
    reach=max(reach,span*(opts['aperture_mm']/2+opts['ito_mm']/2+
              abs(sn)*opts['registration_x_mm']+abs(cs)*opts['registration_y_mm']))
    if any(1e-9<gap<=reach for gap in gaps):
        return dict(unsupported='误差范围可能改变边界裁切关系，局部一阶公式不适用；请缩小误差或调整边界')
    return dict(terms=terms,area_formula='A=Lx×Ly',warning='；'.join(dict.fromkeys(warnings)))


def calculate(spec,m,options=None):
    opts=settings(options)
    result=nominal(spec,m);result['settings']=opts;result['method']='formula'
    if not result['ito_defined']:raise ValueError('请先绘制ITO有效区域；未定义ITO时不假定整个基片均有效')
    if result['overlapping']:raise ValueError('图案开口相交或重叠，请处理后再计算每个pixel的不确定度')
    apertures=expand(spec['foil'].get('cell') or [],m)
    regions=scoped_regions(spec,expand(spec['ito_effective']['features'],m),m)
    if not apertures:raise ValueError('请先绘制图案开口')
    span=1 if opts['distribution']=='uniform' else 3
    for ps,error in [(apertures,opts['aperture_mm']),(regions,opts['ito_mm'])]:
        for p in ps:
            if any(p[k]<=span*error for k in dimensions(p)):
                raise ValueError('尺寸误差过大，可能产生非正尺寸；请减小误差')
            if p['type']=='slot' and error and p['length']-p['width']<=2*span*error:
                raise ValueError('长槽尺寸误差可能使总长小于槽宽，请减小误差或使用圆形')
    ito=unary_union([geometry(r) for r in regions])
    divisor=math.sqrt(3) if opts['distribution']=='uniform' else 1.
    for p,row in zip(apertures,result['pixels']):
        model=None;reason=None
        if any(r['type']=='polygon' for r in regions) and opts['ito_mm']:
            reason='多边形ITO未定义尺寸误差模型'
        elif p['type']=='polygon' and opts['aperture_mm']:
            reason='多边形开口未定义尺寸误差模型'
        elif p['type']=='rect':
            reach=span*(opts['aperture_mm']+opts['ito_mm']+math.hypot(opts['registration_x_mm'],opts['registration_y_mm']))
            near=[r for r in regions if geometry(r).distance(geometry(p))<=reach]
            if len(near)==1 and near[0]['type']=='rect':model=rectangular_formula(p,near[0],opts)
            if model and model.get('unsupported'):reason=model['unsupported'];model=None
        if not model and not reason:
            # A well-contained opening has no first-order ITO/translation term.
            hole=geometry(p)
            reach=span*(opts['aperture_mm']+opts['ito_mm']+
                        math.hypot(opts['registration_x_mm'],opts['registration_y_mm']))
            contained=ito.covers(hole.buffer(reach)) if reach else ito.covers(hole)
            if contained:
                if p['type']=='rect':derivatives=[('w',p['height']),('h',p['width'])];formula='A=w×h'
                elif p['type']=='circle':derivatives=[('d',math.pi*p['diameter']/2)];formula='A=πd²/4'
                elif p['type']=='slot':derivatives=[('l',p['width']),('w',p['length']+(math.pi/2-2)*p['width'])];formula='A=w(l−w)+πw²/4'
                else:derivatives=[];formula='A=多边形面积'
                model=dict(terms=[(key,c,opts['aperture_mm']) for key,c in derivatives],area_formula=formula,warning='')
            elif ito.disjoint(hole.buffer(reach)):
                model=dict(terms=[],area_formula='A=0（与ITO保持间隔）',warning='')
            elif not any(opts[k] for k in ('aperture_mm','ito_mm','registration_x_mm','registration_y_mm')):
                model=dict(terms=[],area_formula='A=开口∩ITO',warning='')
            else:
                reason='当前裁切形状暂不支持解析公式（支持同向矩形裁切及完全包含的圆形/长槽）'
        if reason:
            row.update(u_mm2=None,U_mm2=None,relative_u_percent=None,formula='—',warning=reason,status='unsupported')
            continue
        terms=[(name,c,error/divisor) for name,c,error in model['terms'] if error and abs(c)>1e-12]
        u=math.sqrt(sum((c*input_u)**2 for _,c,input_u in terms))
        expr=' + '.join(f'({abs(c):.6g}u_{name})²' for name,c,_ in terms)
        formula=model['area_formula']+'；u=√['+expr+']' if expr else model['area_formula']+'；u=0'
        row.update(u_mm2=u,U_mm2=2*u,relative_u_percent=100*u/row['area_mm2'] if row['area_mm2'] else None,
                   formula=formula,warning=model['warning'],status='conservative' if model['warning'] else 'ok')
    result['notes']=[
        '有效面积=单个图案开口∩ITO区域并集；接触区需自行识别，不加和面积或不确定度。',
        '公式：u(A)=√[Σ(∂A/∂qᵢ·u(qᵢ))²]，输入误差独立；±公差a按u(q)=a/√3换算，直接输入标准不确定度时不换算。',
        '矩形交集：Lx=max(0,min(x右,xITO右)−max(x左,xITO左))，Ly同理；A=Lx×Ly。按当前裁切关系求解析灵敏度。',
        'w/h为开口完整宽高，d为直径，l为槽总长；W/H为ITO完整宽高，X/Y为相对定位平移。旋转角度固定。',
        '边界恰好重合时面积不可微，标记为较大单侧灵敏度的保守线性估计；它不等于完整非线性分布的标准差。',
        'U=2u（k=2），不声明精确95%覆盖；填0表示该误差来源未计入。复杂裁切无解析模型时不提供u。',
    ]
    return result
