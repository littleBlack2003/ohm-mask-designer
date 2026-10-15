"""Portable application launcher: bundled local engine, existing browser UI."""
import argparse
import copy
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
    starter=json.loads((editor.ROOT/'default_project.json').read_text(encoding='utf-8-sig'))
    editor.validate_project(starter)
    assert starter['name']=='欧姆稳定性镀膜案例'
    assert len(starter['foil']['cell'])==8

    # The bundled starter deliberately leaves region roles, ITO and marking for
    # the user to define. Exercise the complete export path with an enriched
    # copy so the portable-build self-check is independent of starter content.
    spec=copy.deepcopy(starter)
    for index,feature in enumerate(spec['foil']['cell']):
        feature['region_role']='active' if index<6 else 'common'
    spec['ito_effective']={'features':[{'type':'rect_array','width':25,'height':10,'angle':0,
        'nx':1,'ny':1,'pitch_x':0,'pitch_y':0,'origin':[0,0]}]}
    spec['laser_marking']=[{'text':'OHM 0.9.6','height':4,'center':[0,126],
        'angle':180,'target':'skeleton'}]
    spec['uncertainty_settings']={'distribution':'uniform','aperture_mm':.01,
        'ito_mm':0.,'registration_x_mm':0.,'registration_y_mm':0.}
    spec['test_mask']={'enabled':True,'aperture_scale':.8,'size_snap_mm':.1,'edge_margin_mm':.3}
    editor.validate_project(spec)
    statistics=editor.area_stats.calculate(spec,editor.m,spec['uncertainty_settings'])
    _,files,_=editor.manufacturing.package(spec,editor.m,editor.area_stats)
    custom=copy.deepcopy(starter);custom['foil']['outline']={'type':'rect','width':200,'height':190,'corner_radius':3}
    editor.validate_project(custom);custom_foil,_,_=editor.m.build_evaporation(custom,custom.get('arc_segments_per_90',24))
    custom_bbox=editor.m.shape_bbox(custom_foil.outline)
    assert files and statistics['counts']['cell_openings']==8
    assert len(statistics['pixels'])==statistics['counts']['cell_active_openings']==6
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
    editor.DEFAULT_SOURCE=editor.seed_default_project()
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
