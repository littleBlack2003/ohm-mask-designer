"""Check the browser-only bridge keeps aperture role metadata."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT.parent / 'pvd-shadow-mask' / 'scripts'
sys.path.insert(0, str(ROOT))
loader = importlib.util.spec_from_file_location('make_mask', SCRIPTS / 'make_mask.py')
make_mask = importlib.util.module_from_spec(loader)
sys.modules['make_mask'] = make_mask
loader.loader.exec_module(make_mask)
bridge_loader = importlib.util.spec_from_file_location('web_bridge', ROOT / 'web_bridge.py')
bridge = importlib.util.module_from_spec(bridge_loader)
bridge_loader.loader.exec_module(bridge)


class WebBridgeTests(unittest.TestCase):
    def setUp(self):
        bridge.set_current_spec((ROOT.parent / '默认25mm基底' / '项目设置.json').read_text(encoding='utf-8'))

    def test_region_role_is_preserved(self):
        feature={'type':'circle','diameter':2,'center':[0,0],'region_role':'common'}
        spec, shapes = bridge.prepare({'features':[feature]})
        self.assertEqual(spec['foil']['cell'],[feature])
        self.assertEqual(len(shapes),1)

    def test_invalid_region_role_is_rejected(self):
        body={'features':[{'type':'circle','diameter':2,'region_role':'electrode'}]}
        result=json.loads(bridge.call('save',json.dumps(body)))
        self.assertEqual(result['status'],422)
        self.assertIn('区域用途',result['body']['error'])

    def test_web_package_contains_derived_test_mask(self):
        body={'features':[{'type':'rect_array','width':2,'height':4,'nx':1,'ny':1,
                           'pitch_x':0,'pitch_y':0,'origin':[0,1],'region_role':'active'}],
              'ito_features':[{'type':'rect_array','width':10,'height':2,'nx':1,'ny':1,
                               'pitch_x':0,'pitch_y':0,'origin':[0,0]}]}
        result=json.loads(bridge.call('generate',json.dumps(body)))
        self.assertEqual(result['status'],200)
        self.assertIn('默认25mm基底_测试遮光掩模_切割.dxf',result['body']['files'])

    def test_web_validate_returns_test_mask_canvas_geometry(self):
        body={'features':[{'type':'rect_array','width':2,'height':4,'nx':1,'ny':1,
                           'pitch_x':0,'pitch_y':0,'origin':[0,1],'region_role':'active'}],
              'ito_features':[{'type':'rect_array','width':10,'height':2,'nx':1,'ny':1,
                               'pitch_x':0,'pitch_y':0,'origin':[0,0]}]}
        result=json.loads(bridge.call('validate',json.dumps(body)))
        self.assertEqual(result['status'],200)
        preview=result['body']['frame']['test_mask']
        self.assertEqual(len(preview['holes']),1)
        self.assertIsNone(preview['error'])


if __name__ == '__main__':
    unittest.main()
