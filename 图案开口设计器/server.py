"""Local mask pattern editor. Bind only to loopback; geometry uses the skill."""
import argparse
import copy
import importlib.util
import json
import mimetypes
import hashlib
import re
import sys
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import time
from urllib.parse import unquote, urlsplit

ROOT = Path(sys._MEIPASS) / '图案开口设计器' if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
sys.path.insert(0,str(Path(__file__).resolve().parent))
import manufacturing
import area_statistics as area_stats
import loc
def default_output_dir():
    """Exports land in the user's Downloads folder by default."""
    if os.name=='nt':
        try:
            import winreg
            key=winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders')
            value,_=winreg.QueryValueEx(key,'{374DE290-123F-4565-9164-39C4925E467B}')
            winreg.CloseKey(key)
            if value:return Path(value)
        except Exception:pass
    return Path.home()/'Downloads'


PROJECT = ROOT.parent / '默认25mm基底'
SOURCE = PROJECT / '项目设置.json'
DRAFT = PROJECT / '图案开口设计草稿.json'
OUTPUT = default_output_dir()
loader = importlib.util.spec_from_file_location('mask', ROOT.parent / 'ohm-mask-skill/scripts/make_mask.py')
m = importlib.util.module_from_spec(loader)
loader.loader.exec_module(m)
LOCK = threading.RLock()
DEFAULT_SOURCE = SOURCE
LIBRARY = ROOT.parent / '掩模项目'
APP_VERSION = '0.9.6'
STOP_SERVER = None
LAST_PING = [0.0]
WATCHDOG = [None]


def _shutdown_watchdog(stop, idle=45.0):
    """Exit the local service if the browser page stops sending heartbeats."""
    while True:
        time.sleep(5)
        if LAST_PING[0] and time.time() - LAST_PING[0] > idle:
            try:
                stop()
            except Exception:
                pass
            return

def initial():
    with LOCK:
        file = DRAFT if DRAFT.exists() else SOURCE
        return json.loads(file.read_text(encoding='utf-8-sig'))



def save_document(spec,path=None):
    path=Path(path or DRAFT)
    pending=path.with_name(path.name+'.tmp')
    pending.write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(pending,path)

def project_key():
    return hashlib.sha256(str(SOURCE.resolve()).encode('utf-8')).hexdigest()[:24]


def configure_project(path):
    global PROJECT, SOURCE, DRAFT, OUTPUT
    path=Path(path).resolve()
    spec=json.loads(path.read_text(encoding='utf-8-sig'))
    validate_project(spec)
    with LOCK:
        PROJECT=path.parent;SOURCE=path
        legacy=path.name=='项目设置.json'
        DRAFT=PROJECT/'图案开口设计草稿.json' if legacy else path
        OUTPUT=default_output_dir()
    return spec


def seed_default_project():
    """Create the bundled starter project in the writable project library."""
    seed=json.loads((ROOT/'default_project.json').read_text(encoding='utf-8-sig'))
    target=LIBRARY/seed['name']/'项目.json'
    if not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(seed,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    configure_project(target)
    return target



def project_catalog():
    with LOCK:
        paths=[DEFAULT_SOURCE,SOURCE]+sorted(LIBRARY.glob('*/项目.json'))
        found=[];seen=set()
        for path in paths:
            path=Path(path).resolve()
            if path in seen or not path.is_file():continue
            seen.add(path)
            try:
                draft=path.parent/'图案开口设计草稿.json' if path.name=='项目设置.json' else path
                file=draft if draft.exists() else path
                spec=json.loads(file.read_text(encoding='utf-8-sig'))
                key=hashlib.sha256(str(path).encode('utf-8')).hexdigest()[:24]
                windows=spec.get('skeleton',{}).get('windows',{})
                found.append({'id':key,'name':spec['name'],'file':path,'path':str(path),
                              'current':key==project_key(),'modified':file.stat().st_mtime,
                              'cells':len(m.window_centers(windows))})
            except (OSError,ValueError,KeyError,TypeError):continue
        return found


def remember_project():
    LIBRARY.mkdir(parents=True,exist_ok=True)
    (LIBRARY/'最近项目.json').write_text(json.dumps({'id':project_key()},ensure_ascii=False),encoding='utf-8')


def restore_project():
    try:
        key=json.loads((LIBRARY/'最近项目.json').read_text(encoding='utf-8'))['id']
        for item in project_catalog():
            if item['id']==key:configure_project(item['file']);break
    except (OSError,ValueError,KeyError):pass


def manage_project(route,body):
    if route=='/api/project-open':
        match=next((p for p in project_catalog() if p['id']==body.get('id')),None)
        if not match:raise ValueError('项目不存在，请重新打开项目列表')
        configure_project(match['file'])
    else:
        if route=='/api/project-import':
            incoming=body.get('spec')
            if not isinstance(incoming,dict):raise ValueError('请导入完整项目JSON')
            spec=copy.deepcopy(incoming)
        else:
            spec=initial()
            if route=='/api/project-new':
                spec['foil']['cell']=[];spec.pop('ito_effective',None);spec.pop('laser_marking',None)
        spec['name']=body.get('name',spec.get('name',''))
        # Only document geometry is imported; generated outputs and external CSV
        # references are not consumed by this editor.
        spec.pop('outputs',None);spec.pop('_base_dir',None)
        spec['foil'].pop('holes_csv',None)
        spec['foil']['cell']=spec['foil'].get('cell',spec['foil'].get('features',[]))
        spec['foil'].pop('features',None)
        spec['uncertainty_settings']=area_stats.settings(spec.get('uncertainty_settings'))
        validate_project(spec)
        if len(spec['foil']['cell'])>80:raise ValueError('最多80个单格图案对象')
        if spec['foil']['cell']:
            shapes=m.build_features(spec['foil']['cell'],'foil')
            if len(shapes)*(len(m.window_centers(spec['skeleton']['windows'])) if spec['foil'].get('per_window',True) else 1)>1600:raise ValueError('总成最多1600个图案开口')
            for shape in shapes:m.shape_geometry(shape)
        m.build_ito_effective(spec,24,[(0,0,0)]);m.marking_preview(spec)
        if any(p['name'].casefold()==spec['name'].casefold() for p in project_catalog()):
            raise ValueError('已有同名项目，请修改名称；不会覆盖已有项目')
        target=(LIBRARY/spec['name']).resolve()
        if target.parent!=LIBRARY.resolve():raise ValueError('项目目录无效')
        target.mkdir(parents=True,exist_ok=False)
        path=target/'项目.json'
        path.write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        configure_project(path)
    remember_project()
    return {'ok':True,'project_key':project_key(),'path':str(SOURCE)}


def validate_project(spec):
    if spec.get('kind')!='evaporation':raise ValueError('本版本支持蒸镀掩模总成项目')
    name=spec.get('name','')
    if not isinstance(name,str) or not name.strip() or len(name)>100 or re.search(r'[<>:"/\\|?*\x00-\x1f]',name) or name.endswith(('.', ' ')) or name in ('.','..'):
        raise ValueError('项目名称须为1～100个字符，不能包含文件名保留字符')
    if name.upper().split('.')[0] in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:
        raise ValueError('项目名称不能使用系统保留名称')
    m.validate_spec(spec)
    w=spec['skeleton'].get('windows',{})
    if w.get('type')=='array' and int(w.get('nx',1))*int(w.get('ny',1))>400:
        raise ValueError('最多400个定位开口')
    if w.get('type')=='list' and len(w.get('positions',[]))>400:
        raise ValueError('最多400个定位开口')
    layout=frame_geometry(spec)
    if len(layout['centers'])>400:raise ValueError('最多400个定位开口')
    outside=sum(not m.shape_inside(window,layout['foil_outline']) for window in layout['windows'])
    if outside:raise ValueError(f'掩模片外形未覆盖全部定位开口：有{outside}个定位开口超出掩模片')
    frame=m.Part('FRAME','骨架');frame.outline=layout['outline'];frame.window_cuts=layout['windows'];frame.tooling=layout['tooling']
    foil=m.Part('FOIL','掩模片');foil.outline=layout['foil_outline'];foil.tooling=layout['foil_tooling']
    m.validate_parts([foil,frame],spec)
    errors=foil.validation_errors+frame.validation_errors
    if errors:raise ValueError('；'.join(errors))


def frame_geometry(spec):
    sk = spec['skeleton']; seg = spec.get('arc_segments_per_90',24)
    base = m.expand_outline(spec['substrate'],spec.get('clearance_mm',.2)/2,seg)
    centers = m.window_centers(sk.get('windows'))
    windows = [m.transform_shape(base,*c) for c in centers]
    picks = m.build_pick_holes(sk.get('pick_hole'),base,centers)
    body = m.build_outline(sk['outline'],seg)
    outline = m.merged_outline(body,m.build_handle(sk.get('handle'),body),seg,.001)
    foil_spec=spec.get('foil',{});foil_custom=foil_spec.get('outline')
    foil_outline=m.build_outline(foil_custom,seg) if foil_custom else outline
    foil_tooling_base=foil_outline if foil_custom else body
    return {'outline':outline,'foil_outline':foil_outline,'windows':m.merge_window_cuts(windows,picks,seg,.001),'centers':centers,
            'tooling':m.build_frame_holes(sk['frame_holes'],body,'skeleton.frame_holes') if sk.get('frame_holes') else [],
            'foil_tooling':m.build_frame_holes(foil_spec['frame_holes'],foil_tooling_base,'foil.frame_holes') if foil_spec.get('frame_holes') else [],
            'test_mask':test_mask_geometry(spec)}

def test_mask_geometry(spec):
    config=spec.get('test_mask') if isinstance(spec.get('test_mask'),dict) else {}
    outline_spec=(config or {}).get('outline') or spec['substrate']
    result={'enabled':(config or {}).get('enabled',True) is not False,
            'outline':m.build_outline(outline_spec,spec.get('arc_segments_per_90',24)),
            'holes':[],'error':None}
    try:
        part,_=manufacturing.build_test_mask(spec,m,area_stats)
        if part:
            result.update(outline=part.outline,holes=part.holes)
    except (ValueError,m.SpecError) as exc:
        result['error']=str(exc)
    return result

def prepare(features, ito_features=None, markings=None, uncertainty=None, project_settings=None, mask_mode=None, mask_outline=None, mask_holes=None):
    if not isinstance(features,list) or len(features)>80:
        raise m.SpecError('单格图案须为数组，最多80个图案对象')
    valid_region_roles={'unassigned','active','common'}
    for feature in features:
        if not isinstance(feature,dict):
            raise m.SpecError('图案对象须为JSON对象')
        if feature.get('region_role','unassigned') not in valid_region_roles:
            raise m.SpecError('图案开口区域用途须为 unassigned、active 或 common')
    spec = initial()
    if project_settings is not None:
        if not isinstance(project_settings,dict):raise ValueError('项目设置须为对象')
        for key in ('name','substrate','skeleton','test_mask','clearance_mm','min_web_mm','arc_segments_per_90','curve_tolerance_mm'):
            if key in project_settings:spec[key]=copy.deepcopy(project_settings[key])
        if 'foil' in project_settings:
            for key in ('per_window','outline','frame_holes'):
                spec['foil'].pop(key,None)
                if key in project_settings['foil']:spec['foil'][key]=copy.deepcopy(project_settings['foil'][key])
    if mask_mode=='manual':
        tm=dict(spec.get('test_mask') or {})
        tm['mode']='manual'
        if mask_outline:tm['outline']=copy.deepcopy(mask_outline)
        else:tm.pop('outline',None)
        tm['holes']=copy.deepcopy(mask_holes or [])
        spec['test_mask']=tm
    elif mask_mode=='auto':
        tm=dict(spec.get('test_mask') or {})
        tm.pop('mode',None);tm.pop('holes',None)
        spec['test_mask']=tm
    validate_project(spec)
    spec['uncertainty_settings'] = area_stats.settings(uncertainty if uncertainty is not None else spec.get('uncertainty_settings'))
    if markings is not None:
        spec['laser_marking'] = markings
    if ito_features is not None:
        if not isinstance(ito_features,list) or len(ito_features)>40:
            raise m.SpecError('ITO参考图案须为数组，最多40个区域对象')
        spec['ito_effective'] = {'features':ito_features}
    spec['foil']['cell'] = features
    spec['foil'].pop('features',None)
    spec.pop('outputs',None)
    spec.pop('_base_dir',None)
    spec['_stage'] = 'GUI图案设计' if features else '骨架已确定；单格图案待绘制'
    m.validate_spec(spec)
    expanded=sum(int(f.get('nx',1))*int(f.get('ny',1)) if f.get('type') in ('rect_array','circle_array') else 1 for f in features)
    repeats=len(m.window_centers(spec['skeleton']['windows'])) if spec['foil'].get('per_window',True) else 1
    if expanded*repeats>1600:raise m.SpecError('图案开口过多：总成最多1600个开口')
    shapes = m.build_features(features,'foil') if features else []
    if len(shapes)*(len(m.window_centers(spec['skeleton']['windows'])) if spec['foil'].get('per_window',True) else 1)>1600:
        raise m.SpecError('图案开口过多：总成最多1600个开口，请减少单格复制数量')
    for shape in shapes: m.shape_geometry(shape)
    m.build_ito_effective(spec,24,[(0,0,0)])
    m.marking_preview(spec)
    return spec,shapes

def inspect_cell(spec,shapes):
    geometry=frame_geometry(spec)
    if shapes:
        foil,frame,_=m.build_evaporation(spec,spec.get('arc_segments_per_90',24))
        if spec['foil'].get('per_window',True):
            boundary=m.expand_outline(spec['substrate'],spec.get('clearance_mm',.2)/2,24)
            bad=sum(not m.shape_inside(shape,boundary) for shape in shapes)
            if bad:foil.validation_errors.append(f'{bad}个单格图案开口超出该格定位开口')
    else:
        frame=m.Part('FRAME','骨架');frame.outline=geometry['outline'];frame.window_cuts=geometry['windows']
        frame.tooling=geometry['tooling']
        foil=m.Part('FOIL','掩模片');foil.outline=geometry['foil_outline'];foil.tooling=geometry['foil_tooling']
        m.attach_marking(spec,[foil,frame])
    m.validate_parts([foil,frame],spec)
    report=m.analyze(spec,[foil,frame],m._extra_info(spec,'evaporation'))
    if not shapes:report+='\n尚未绘制图案开口。'
    if 'ito_effective' in spec:report+='\nITO有效区域为参考图层，不参与切割。'
    return report,not foil.validation_errors and not frame.validation_errors


class Handler(BaseHTTPRequestHandler):
    def send(self,status,data,ctype='application/json; charset=utf-8'):
        content=json.dumps(data,ensure_ascii=False).encode('utf-8') if isinstance(data,dict) else data
        self.send_response(status);self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(len(content)));self.send_header('Cache-Control','no-store')
        self.end_headers();self.wfile.write(content)

    def do_GET(self):
        path=unquote(urlsplit(self.path).path)
        if path=='/api/projects':
            self.send(200,{'ok':True,'projects':[{k:v for k,v in p.items() if k!='file'} for p in project_catalog()], 'library_dir':str(LIBRARY)});return
        if path=='/api/project':
            spec=initial();self.send(200,{'spec':spec,'frame':frame_geometry(spec),'project_dir':str(PROJECT),'project_key':project_key(),'desktop':False,'version':APP_VERSION,'can_shutdown':bool(STOP_SERVER),'project_file':str(SOURCE)});return
        if path.startswith('/files/'):
            filename=path[len('/files/'):]
            candidate=(OUTPUT/filename).resolve()
            if candidate.parent!=OUTPUT.resolve() or not candidate.is_file():
                self.send(404,{'error':'文件不存在'});return
            self.send(200,candidate.read_bytes(),mimetypes.guess_type(filename)[0] or 'application/octet-stream');return
        if path in ['/project-ui.js','/canvas-controls.js','/static-api.js','/pyodide.js','/i18n.js']:
            self.send(200,(ROOT/path[1:]).read_bytes(),'text/javascript; charset=utf-8');return
        if path not in ['/','/index.html']:
            self.send(404,{'error':'页面不存在'});return
        self.send(200,(ROOT/'index.html').read_bytes(),'text/html; charset=utf-8')

    def do_POST(self):
        path=urlsplit(self.path).path
        # Browser requests must originate from this local editor.
        origin=self.headers.get('Origin')
        if origin and origin!=f'http://{self.headers.get("Host")}':
            self.send(403,{'error':'请求来源不匹配'});return
        lang='zh-Hans'
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=250000:raise ValueError('请求大小无效')
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict):raise ValueError('请求须为JSON对象')
            if isinstance(body.get('lang'),str) and body['lang'] in loc.SUPPORTED:lang=body['lang']
            with LOCK:
                if body.get('project_key') and body['project_key']!=project_key():raise ValueError('当前项目已经切换，请刷新本页')
                if path in ('/api/project-new','/api/project-copy','/api/project-open','/api/project-import'):
                    self.send(200,manage_project(path,body));return
                if path=='/api/shutdown':
                    if not STOP_SERVER:raise ValueError('当前服务不支持从页面退出')
                    self.send(200,{'ok':True})
                    if STOP_SERVER:threading.Thread(target=STOP_SERVER,daemon=True).start()
                    return
                if path=='/api/ping':
                    LAST_PING[0]=time.time()
                    if WATCHDOG[0] is None and STOP_SERVER is not None:
                        WATCHDOG[0]=threading.Thread(target=_shutdown_watchdog,args=(STOP_SERVER,),daemon=True);WATCHDOG[0].start()
                    self.send(200,{'ok':True});return
                spec,shapes=prepare(body['features'],body.get('ito_features'),body.get('markings'),body.get('uncertainty_settings'),body.get('project_settings'),body.get('mask_mode'),body.get('mask_outline'),body.get('mask_holes'))
                if path=='/api/statistics':
                    self.send(200,{'ok':True,'statistics':area_stats.calculate(spec,m,spec['uncertainty_settings'])});return
                if path=='/api/layout':
                    self.send(200,{'ok':True,'spec':spec,'frame':frame_geometry(spec)});return
                report,valid=inspect_cell(spec,shapes)
                if path=='/api/validate':
                    self.send(200,{'ok':valid,'report':loc.report(report,lang),'shapes':shapes,'mark_paths':m.marking_preview(spec),
                                   'statistics':area_stats.nominal(spec,m),'frame':frame_geometry(spec)});return
                if path=='/api/save':
                    with LOCK: save_document(spec)
                    self.send(200,{'ok':True,'valid':valid,'report':loc.report(report,lang),'path':str(DRAFT)});return
                if path=='/api/mask':
                    part,test_report=manufacturing.build_test_mask(spec,m,area_stats)
                    if not part:
                        self.send(422,{'error':loc.message('未生成测试遮光掩模',lang)});return
                    tfiles={f"{spec['name']}_测试遮光掩模_切割.dxf":m.render([part],False),'测试遮光掩模_校验报告.txt':(test_report or '')}
                    tfiles={loc.filename(k,lang):v for k,v in tfiles.items()}
                    with LOCK:
                        OUTPUT.mkdir(parents=True,exist_ok=True)
                        for filename,content in tfiles.items():
                            file=OUTPUT/filename
                            if isinstance(content,bytes):file.write_bytes(content)
                            else:file.write_text(content,encoding='utf-8',newline='\n')
                        save_document(spec)
                    self.send(200,{'ok':True,'report':loc.report(test_report,lang),'files':list(tfiles),'path':str(OUTPUT)});return
                if path=='/api/generate':
                    if not shapes:raise m.SpecError('请先绘制单格图案开口')
                    if not valid:
                        self.send(422,{'error':loc.message('几何校验未通过，未生成DXF',lang),'report':loc.report(report,lang)});return
                    report,files,spec=manufacturing.package(spec,m,area_stats)
                    if not files:
                        self.send(422,{'error':loc.message('几何校验未通过，未生成DXF',lang),'report':loc.report(report,lang)});return
                    files={loc.filename(k,lang):v for k,v in files.items()}
                    with LOCK:
                        OUTPUT.mkdir(parents=True,exist_ok=True)
                        for filename,content in files.items():
                            file=OUTPUT/filename
                            if isinstance(content,bytes):file.write_bytes(content)
                            else:file.write_text(content,encoding='utf-8',newline='\n')
                        save_document(spec)
                    self.send(200,{'ok':True,'report':loc.report(report,lang),'files':list(files),'path':str(OUTPUT)});return
                self.send(404,{'error':'操作不存在'})
        except (m.SpecError,ValueError,TypeError,KeyError,OverflowError,OSError) as e:
            self.send(422,{'error':loc.message(str(e),lang)})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);parser.add_argument('--library',type=Path);parser.add_argument('--project',type=Path)
    args=parser.parse_args()
    if args.library:LIBRARY=args.library.resolve()
    if args.project:configure_project(args.project);DEFAULT_SOURCE=SOURCE
    else:DEFAULT_SOURCE=seed_default_project()
    restore_project()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    STOP_SERVER=server.shutdown
    print(f'图案开口设计器：http://127.0.0.1:{args.port}',flush=True)
    server.serve_forever()
