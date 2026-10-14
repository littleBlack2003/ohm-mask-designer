"""Exercise GUI save/generate routes in an isolated temporary project."""
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from zipfile import ZipFile
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parent
loader=importlib.util.spec_from_file_location('editor',ROOT/'server.py')
s=importlib.util.module_from_spec(loader);loader.loader.exec_module(s)

class EditorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='mask-editor-test-')
        root=Path(self.temp.name)
        self.old=(s.SOURCE,s.DRAFT,s.OUTPUT,s.LIBRARY,s.DEFAULT_SOURCE)
        s.SOURCE=root/'项目设置.json';s.DRAFT=root/'图案开口设计草稿.json';s.OUTPUT=root/'output'
        s.LIBRARY=root/'projects';s.DEFAULT_SOURCE=s.SOURCE
        s.SOURCE.write_text(self.old[0].read_text(encoding='utf-8'),encoding='utf-8')
        self.server=s.ThreadingHTTPServer(('127.0.0.1',0),s.Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
        s.SOURCE,s.DRAFT,s.OUTPUT,s.LIBRARY,s.DEFAULT_SOURCE=self.old
        self.temp.cleanup()

    def post(self,route,features,ito_features=None,markings=None,uncertainty=None,extra=None):
        payload={'features':features}
        if ito_features is not None:payload['ito_features']=ito_features
        if markings is not None:payload['markings']=markings
        if uncertainty is not None:payload['uncertainty_settings']=uncertainty
        if extra:payload.update(extra)
        req=Request(self.url+'/api/'+route,data=json.dumps(payload).encode(),
                    headers={'Content-Type':'application/json'},method='POST')
        try:
            with urlopen(req) as response:return response.status,json.load(response)
        except HTTPError as e:
            with e:return e.code,json.load(e)

    def test_valid_pattern_and_generation(self):
        shapes=[{'type':'rect_array','width':2,'height':14,'nx':2,'ny':1,
                 'pitch_x':6.5,'pitch_y':0,'origin':[-3.25,0]}]
        status,data=self.post('generate',shapes)
        self.assertEqual(status,200);self.assertIn('装配预览.svg',data['files'])
        self.assertTrue(any(f.endswith('.zip') for f in data['files']))
        self.assertEqual(len(list(s.OUTPUT.glob('*.dxf'))),5)
        self.assertEqual(json.loads(s.DRAFT.read_text(encoding='utf-8'))['foil']['cell'],shapes)
        self.assertNotIn('[错误]',data['report'])

    def test_region_role_is_saved_and_invalid_values_are_rejected(self):
        shapes=[{'type':'circle','diameter':2,'center':[0,0],'region_role':'active'},
                {'type':'circle','diameter':2,'center':[4,0],'region_role':'common'},
                {'type':'circle','diameter':2,'center':[-4,0]}]
        status,data=self.post('generate',shapes)
        self.assertEqual(status,200)
        saved=json.loads(s.DRAFT.read_text(encoding='utf-8'))
        self.assertEqual(saved['foil']['cell'],shapes)
        status,data=self.post('validate',shapes)
        self.assertEqual(status,200)
        self.assertEqual(data['statistics']['counts']['cell_active_openings'],1)
        self.assertEqual(data['statistics']['counts']['cell_common_openings'],1)
        self.assertEqual(data['statistics']['counts']['cell_unassigned_openings'],1)
        invalid=[{'type':'circle','diameter':2,'region_role':'electrode'}]
        status,data=self.post('save',invalid)
        self.assertEqual(status,422)
        self.assertIn('区域用途',data['error'])

    def test_invalid_pattern_stops_dxf(self):
        status,data=self.post('generate',[{'type':'circle','diameter':2,'center':[20,0]}])
        self.assertEqual(status,422);self.assertIn('[错误]',data['report'])
        self.assertFalse(s.OUTPUT.exists())

    def test_overlap_report(self):
        status,data=self.post('validate',[{'type':'circle','diameter':2},{'type':'circle','diameter':2}])
        self.assertEqual(status,200);self.assertFalse(data['ok']);self.assertIn('重叠',data['report'])

    def test_empty_draft_and_empty_generation(self):
        self.assertEqual(self.post('save',[])[0],200)
        self.assertEqual(json.loads(s.DRAFT.read_text(encoding='utf-8'))['foil']['cell'],[])
        self.assertEqual(self.post('generate',[])[0],422)

    def test_shape_modes(self):
        shapes=[{'type':'circle','diameter':2,'center':[-8,0]},
                {'type':'slot','length':6,'width':1,'center':[0,0],'angle':30},
                {'type':'polygon','points':[[6,-1],[8,-1],[7,1]]}]
        status,data=self.post('validate',shapes)
        self.assertEqual(status,200);self.assertTrue(data['ok'])

    def test_nonfinite_and_path_escape(self):
        self.assertEqual(self.post('save',[{'type':'circle','diameter':float('nan')}])[0],422)
        try:
            urlopen(self.url+'/files/../source.json')
            self.fail('path escape was allowed')
        except HTTPError as e:
            self.assertEqual(e.code,404)
            e.close()

    def test_ito_saved_exported_and_separate_from_apertures(self):
        apertures=[{'type':'circle','diameter':2}]
        ito=[{'type':'rect_array','width':20,'height':20,'nx':1,'ny':1,
             'pitch_x':0,'pitch_y':0,'origin':[0,0]}]
        status,data=self.post('generate',apertures,ito)
        self.assertEqual(status,200)
        saved=json.loads(s.DRAFT.read_text(encoding='utf-8'))
        self.assertEqual(saved['foil']['cell'],apertures)
        self.assertEqual(saved['ito_effective']['features'],ito)
        for path in s.OUTPUT.glob('*.dxf'):
            content=path.read_text(encoding='utf-8')
            if '_切割.dxf' in path.name:self.assertNotIn('\nITO_EFFECTIVE\n',content)
            else:self.assertIn('\nITO_EFFECTIVE\n',content)

    def test_invalid_ito_stops_generation(self):
        status,data=self.post('generate',[{'type':'circle','diameter':2}],
                              [{'type':'circle','diameter':30}])
        self.assertEqual(status,422)
        self.assertIn('ITO',data['error'])
        self.assertFalse(s.OUTPUT.exists())

    def test_marking_saved_and_separate_cut_and_mark_files(self):
        marks=[{'text':'默认25mm','center':[0,115],'height':3,'angle':0,'target':'skeleton'}]
        status,data=self.post('generate',[{'type':'circle','diameter':2}],markings=marks)
        self.assertEqual(status,200)
        self.assertTrue(any(f.endswith('.zip') for f in data['files']))
        saved=json.loads(s.DRAFT.read_text(encoding='utf-8'))
        self.assertEqual(saved['laser_marking'],marks)
        marker=[p for p in s.OUTPUT.glob('*.dxf') if '激光打标' in p.name]
        self.assertEqual(len(marker),1)
        self.assertIn('LASER_MARK',marker[0].read_text(encoding='utf-8'))
        for p in s.OUTPUT.glob('*切割.dxf'):
            self.assertNotIn('LASER_MARK',p.read_text(encoding='utf-8'))
        status,data=self.post('validate',[{'type':'circle','diameter':2}],markings=marks)
        self.assertTrue(data['mark_paths'][0]['contours'])

    def test_marking_collision_report(self):
        marks=[{'text':'test','center':[-75,-75],'height':3,'target':'skeleton'}]
        status,data=self.post('generate',[{'type':'circle','diameter':2}],markings=marks)
        self.assertEqual(status,422);self.assertIn('打标文字',data['report'])

    def test_text_only_draft_before_pattern(self):
        marks=[{'text':'TEST','center':[0,115],'height':3,'target':'skeleton'}]
        self.assertEqual(self.post('save',[],markings=marks)[0],200)

    def test_statistics_route_and_saved_settings(self):
        holes=[{'type':'circle','diameter':2,'region_role':'active'}]
        ito=[{'type':'circle','diameter':20}]
        opts={'aperture_mm':.01}
        status,data=self.post('statistics',holes,ito,markings=[],uncertainty=opts)
        self.assertEqual(status,200)
        self.assertEqual(data['statistics']['counts']['foil_pattern_openings'],36)
        self.assertGreater(data['statistics']['pixels'][0]['u_mm2'],0)
        self.assertFalse(s.OUTPUT.exists())
        self.assertEqual(self.post('save',holes,ito,uncertainty=opts)[0],200)
        saved=json.loads(s.DRAFT.read_text(encoding='utf-8'))
        self.assertEqual(saved['uncertainty_settings']['aperture_mm'],.01)
        self.assertNotIn('samples',s.initial()['uncertainty_settings'])
        status,data=self.post('validate',holes,ito,markings=[])
        self.assertEqual(status,200)
        self.assertIn('statistics',data)

    def test_active_effective_area_generates_substrate_sized_test_mask(self):
        holes=[{'type':'rect_array','width':2,'height':4,'nx':1,'ny':1,
                'pitch_x':0,'pitch_y':0,'origin':[-3,1],'region_role':'active'},
               {'type':'rect_array','width':5,'height':5,'nx':1,'ny':1,
                'pitch_x':0,'pitch_y':0,'origin':[3,0],'region_role':'common'}]
        ito=[{'type':'rect_array','width':10,'height':2,'nx':1,'ny':1,
              'pitch_x':0,'pitch_y':0,'origin':[0,0]}]
        prepared,_=s.prepare(holes,ito)
        part,report=s.manufacturing.build_test_mask(prepared,s.m,s.area_stats)
        self.assertEqual(s.m.shape_bbox(part.outline),(-12.5,-12.5,12.5,12.5))
        self.assertEqual(len(part.holes),1)
        self.assertAlmostEqual(s.m.shape_area(part.holes[0]),2.56,places=6)
        for actual,expected in zip(s.m.shape_bbox(part.holes[0]),(-3.8,-.8,-2.2,.8)):
            self.assertAlmostEqual(actual,expected,places=9)
        self.assertIn('基片/外形  : 25.000 x 25.000 mm',report)
        self.assertIn('活性有效区域边长的 80.0%',report)
        self.assertIn('0.100 mm 吸附',report)
        status,data=self.post('generate',holes,ito)
        self.assertEqual(status,200)
        self.assertIn('默认25mm基底_测试遮光掩模_切割.dxf',data['files'])
        archive=next(s.OUTPUT.glob('*.zip'))
        with ZipFile(archive) as package:
            self.assertIn('默认25mm基底_测试遮光掩模_切割.dxf',package.namelist())
            self.assertIn('测试遮光掩模_校验报告.txt',package.namelist())
        saved=json.loads(s.DRAFT.read_text(encoding='utf-8'))
        self.assertEqual(saved['outputs']['test_mask'],'默认25mm基底_测试遮光掩模_切割.dxf')

    def test_test_mask_uses_nearest_size_snap_and_stays_inside_active_area(self):
        holes=[{'type':'rect_array','width':3.17,'height':2.93,'nx':1,'ny':1,
                'pitch_x':0,'pitch_y':0,'origin':[0,0],'region_role':'active'}]
        ito=[{'type':'rect_array','width':10,'height':10,'nx':1,'ny':1,
              'pitch_x':0,'pitch_y':0,'origin':[0,0]}]
        prepared,_=s.prepare(holes,ito)
        part,_=s.manufacturing.build_test_mask(prepared,s.m,s.area_stats)
        for actual,expected in zip(s.m.shape_bbox(part.holes[0]),(-1.25,-1.15,1.25,1.15)):
            self.assertAlmostEqual(actual,expected,places=9)
        source=s.area_stats.geometry(s.area_stats.active_apertures(prepared,s.m)[0])
        result=s.m.shape_geometry(part.holes[0])
        self.assertTrue(source.contains(result))
        self.assertGreater(source.boundary.distance(result),0)

    def test_test_mask_scale_and_snap_are_configurable_and_must_shrink(self):
        holes=[{'type':'rect_array','width':3.17,'height':2.93,'nx':1,'ny':1,
                'pitch_x':0,'pitch_y':0,'origin':[0,0],'region_role':'active'}]
        ito=[{'type':'rect_array','width':10,'height':10,'nx':1,'ny':1,
              'pitch_x':0,'pitch_y':0,'origin':[0,0]}]
        settings=s.initial();settings['test_mask']={'aperture_scale':.7,'size_snap_mm':.2}
        prepared,_=s.prepare(holes,ito,project_settings=settings)
        part,_=s.manufacturing.build_test_mask(prepared,s.m,s.area_stats)
        for actual,expected in zip(s.m.shape_bbox(part.holes[0]),(-1.1,-1,1.1,1)):
            self.assertAlmostEqual(actual,expected,places=9)
        settings['test_mask']['aperture_scale']=1
        with self.assertRaisesRegex(s.m.SpecError,'小于1'):
            s.prepare(holes,ito,project_settings=settings)

    def test_statistics_missing_ito_is_explicit(self):
        status,data=self.post('statistics',[{'type':'circle','diameter':2}],[],markings=[])
        self.assertEqual(status,422)
        self.assertIn('ITO',data['error'])

    def test_project_new_copy_open_and_stale_request(self):
        original_key=s.project_key();original=s.SOURCE.read_bytes()
        self.assertEqual(self.post('project-new',[],extra={'name':'空白案例'})[0],200)
        empty_key=s.project_key()
        self.assertEqual(s.initial()['foil']['cell'],[])
        self.assertNotEqual(original_key,empty_key)
        self.assertEqual(self.post('save',[{'type':'circle','diameter':2}],extra={'project_key':original_key})[0],422)
        self.assertEqual(self.post('project-copy',[],extra={'name':'复制案例'})[0],200)
        self.assertEqual(self.post('project-copy',[],extra={'name':'复制案例'})[0],422)
        self.assertEqual(self.post('project-open',[],extra={'id':original_key})[0],200)
        self.assertEqual(s.SOURCE.read_bytes(),original)
        self.assertEqual(s.project_key(),original_key)

    def test_saved_layout_survives_reload(self):
        settings=s.initial();settings['name']='布局修改'
        settings['skeleton']['windows']={'type':'array','nx':2,'ny':3,'pitch_x':30,'pitch_y':30,'origin':[-15,-30]}
        settings['foil']['outline']={'type':'rect','width':120,'height':150,'corner_radius':2}
        status,data=self.post('layout',[{'type':'circle','diameter':2}],[],[],extra={'project_settings':settings})
        self.assertEqual(status,200);self.assertEqual(len(data['frame']['centers']),6)
        self.assertEqual(s.m.shape_bbox(data['frame']['foil_outline']),(-60,-75,60,75))
        self.assertEqual(self.post('save',[{'type':'circle','diameter':2}],[],[],extra={'project_settings':settings})[0],200)
        self.assertEqual(s.initial()['skeleton']['windows']['ny'],3)
        self.assertEqual(s.initial()['foil']['outline']['corner_radius'],2)
        self.assertEqual(s.initial()['name'],'布局修改')

    def test_mask_outline_must_cover_positioning_openings(self):
        settings=s.initial();settings['foil']['outline']={'type':'rect','width':20,'height':20}
        status,data=self.post('layout',[],[],[],extra={'project_settings':settings})
        self.assertEqual(status,422);self.assertIn('掩模片外形未覆盖全部定位开口',data['error'])

    def test_project_names_and_import_are_validated(self):
        for name in ('../outside','CON','bad/name',''):
            self.assertEqual(self.post('project-new',[],extra={'name':name})[0],422)
        self.assertFalse(s.LIBRARY.exists())
        self.assertEqual(self.post('project-import',[],extra={'name':'导入案例','spec':s.initial()})[0],200)
        self.assertEqual(s.initial()['name'],'导入案例')

    def test_manufacturing_zip_excludes_stale_files(self):
        s.OUTPUT.mkdir();(s.OUTPUT/'oldcase.dxf').write_text('old')
        status,data=self.post('generate',[{'type':'circle','diameter':2}],[],[])
        self.assertEqual(status,200)
        archive=next(s.OUTPUT.glob('*.zip'))
        with ZipFile(archive) as z:
            self.assertIsNone(z.testzip());self.assertNotIn('oldcase.dxf',z.namelist())
            self.assertIn('装配预览.svg',z.namelist())
            self.assertNotIn('LASER_MARK',z.read(s.initial()['name']+'_骨架_切割.dxf').decode())

    def test_validate_reports_actual_plate_web_not_virtual_cell_border(self):
        shapes=[{'type':'rect_array','width':4,'height':10,'nx':1,'ny':1,'pitch_x':0,'pitch_y':0,'origin':[10.5,0]}]
        status,data=self.post('validate',shapes,[],[])
        self.assertEqual(status,200)
        self.assertNotIn('最小筋宽 0.098',data['report'])
        self.assertNotIn('[警告]',data['report'])

if __name__=='__main__':unittest.main()
