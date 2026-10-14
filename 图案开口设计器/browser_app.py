"""Portable application launcher: bundled local engine, existing browser UI."""
import argparse
import json
import os
from pathlib import Path
import sys
from urllib.request import urlopen
import webbrowser

# Windowless executables have no stderr; HTTP logging needs a writable stream.
if getattr(sys,'frozen',False) or sys.stderr is None:
    log_dir=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'OhmMaskDesigner'
    log_dir.mkdir(parents=True,exist_ok=True)
    sys.stderr=open(log_dir/'service.log','a',encoding='utf-8')
    sys.stdout=sys.stderr
import server as editor


def check(report):
    spec=json.loads((editor.ROOT/'default_project.json').read_text(encoding='utf-8-sig'))
    editor.validate_project(spec)
    statistics=editor.area_stats.calculate(spec,editor.m,spec.get('uncertainty_settings'))
    geometry,files,_=editor.manufacturing.package(spec,editor.m,editor.area_stats)
    custom=json.loads(json.dumps(spec));custom['foil']['outline']={'type':'rect','width':200,'height':190,'corner_radius':3}
    editor.validate_project(custom);custom_foil,_,_=editor.m.build_evaporation(custom,custom.get('arc_segments_per_90',24))
    custom_bbox=editor.m.shape_bbox(custom_foil.outline)
    assert files and len(statistics['pixels'])==8
    assert any('激光打标' in name for name in files)
    assert statistics['pixels'][0]['u_mm2']>0
    assert custom_bbox==(-100.0,-95.0,100.0,95.0)
    data={'ok':True,'version':editor.APP_VERSION,'counts':statistics['counts'],
          'pixel_u_mm2':[p['u_mm2'] for p in statistics['pixels']],
          'custom_foil_bbox':custom_bbox,'package_files':list(files),'resource_root':str(editor.ROOT)}
    Path(report).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--no-browser',action='store_true');parser.add_argument('--check-only',type=Path)
    parser.add_argument('--data-dir',type=Path)
    args=parser.parse_args()
    if args.check_only:check(args.check_only);return
    url=f'http://127.0.0.1:{args.port}/'
    try:
        with urlopen(url+'api/project',timeout=1) as response:data=json.load(response)
        if data.get('version')==editor.APP_VERSION:
            if not args.no_browser:webbrowser.open(url)
            return
        raise RuntimeError('8765端口有旧版工作台，请先关闭旧版本再启动')
    except OSError:pass
    if args.data_dir:data_dir=args.data_dir.resolve()
    elif getattr(sys,'frozen',False):data_dir=Path.home()/'Documents'/'欧姆掩模设计器'
    else:data_dir=editor.ROOT.parent
    editor.LIBRARY=data_dir/'掩模项目'
    if getattr(sys,'frozen',False) or args.data_dir:
        seed=json.loads((editor.ROOT/'default_project.json').read_text(encoding='utf-8-sig'))
        target=editor.LIBRARY/seed['name']/'项目.json'
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(json.dumps(seed,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        editor.configure_project(target);editor.DEFAULT_SOURCE=target
    editor.restore_project()
    http=editor.ThreadingHTTPServer(('127.0.0.1',args.port),editor.Handler)
    editor.STOP_SERVER=http.shutdown
    if not args.no_browser:webbrowser.open(url)
    try:http.serve_forever()
    finally:http.server_close()


if __name__=='__main__':
    try:main()
    except Exception as exc:
        if '--check-only' in sys.argv:
            idx=sys.argv.index('--check-only')
            Path(sys.argv[idx+1]).write_text(json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False),encoding='utf-8')
        elif '--no-browser' not in sys.argv:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,str(exc),'欧姆掩模设计器启动失败',0x10)
        print(str(exc),file=sys.stderr)
        sys.exit(1)
