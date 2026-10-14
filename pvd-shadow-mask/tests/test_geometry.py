"""Regression tests for manufacturing contours and real boundary checks."""
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from shapely.geometry import LineString, Point

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.util.spec_from_file_location('make_mask', ROOT / 'scripts/make_mask.py')
m = importlib.util.module_from_spec(loader)
loader.loader.exec_module(m)


def evaporation():
    return {
        'kind': 'evaporation', 'name': 'test',
        'substrate': {'type': 'rect', 'width': 10, 'height': 10},
        'skeleton': {
            'outline': {'type': 'rect', 'width': 40, 'height': 40},
            'handle': {'width': 8, 'height': 5, 'edge': 'top'},
            'pick_hole': {'diameter': 2, 'edge': 'top'},
            'frame_holes': {'diameter': 2, 'inset': 3},
        },
        'foil': {'cell': [{'type': 'circle', 'diameter': 1}],
                 'frame_holes': {'diameter': 2, 'inset': 3}},
    }


def single(outline=None, features=None):
    return {'name': 'test', 'outline': outline or {'type': 'rect', 'width': 20, 'height': 20},
            'features': features or [{'type': 'circle', 'diameter': 1}]}


class GeometryTests(unittest.TestCase):
    def generate(self, spec):
        return m.generate(spec, Path('unused-test-output'), None)

    def assert_blocked(self, spec):
        report, files = self.generate(spec)
        self.assertEqual(len(files),0)
        self.assertIn('[错误]', report)

    def test_examples_still_generate(self):
        for path in (ROOT / 'examples').glob('*.json'):
            with self.subTest(path=path.name):
                report, files = self.generate(json.loads(path.read_text(encoding='utf-8-sig')))
                self.assertTrue(files)
                self.assertNotIn('[错误]', report)

    def test_square_window_remains_square_with_clearance(self):
        window=m.expand_outline({'type':'rect','width':25,'height':25},.1,24)
        self.assertEqual(len(window[1]),4)
        self.assertEqual(set(window[1]),{(-12.6,-12.6),(12.6,-12.6),(12.6,12.6),(-12.6,12.6)})
        self.assertAlmostEqual(m.shape_area(window),25.2**2)
        spec=evaporation()
        spec['substrate']={'type':'rect','width':25,'height':25,'corner_radius':0}
        spec['skeleton']['pick_hole']={'diameter':5,'corner':'top_right'}
        _,frame,_=m.build_evaporation(spec,24)
        points={(round(x,6),round(y,6)) for x,y in frame.window_cuts[0][1]}
        self.assertTrue({(-12.6,-12.6),(-12.6,12.6),(12.6,-12.6)}.issubset(points))
        self.assertNotIn((12.6,12.6),points)  # 此角按要求开了R2.5取片缺口

    def test_explicit_rounded_substrate_keeps_offset_radius(self):
        window=m.expand_outline({'type':'rect','width':25,'height':25,'corner_radius':1},.1,24)
        self.assertGreater(len(window[1]),4)
        self.assertAlmostEqual(window[1][0][0],12.6)
        self.assertAlmostEqual(window[1][0][1],11.5)

    def test_handle_union_four_edges_and_shared_foil(self):
        for edge in ['top', 'bottom', 'left', 'right']:
            with self.subTest(edge=edge):
                spec = evaporation()
                spec['skeleton']['handle']['edge'] = edge
                foil, frame, _ = m.build_evaporation(spec, 16)
                self.assertEqual(foil.outline, frame.outline)
                self.assertEqual(foil.tooling, frame.tooling)
                self.assertFalse(frame.outline_extra)
                geom = m.shape_geometry(frame.outline)
                self.assertAlmostEqual(geom.area, 1600 + 8 * 5)
                seam = {'top': [(-4,20),(4,20)], 'bottom': [(-4,-20),(4,-20)],
                        'left': [(-20,-4),(-20,4)], 'right': [(20,-4),(20,4)]}[edge]
                self.assertAlmostEqual(geom.boundary.intersection(LineString(seam)).length, 0)
                bbox = m.shape_bbox(frame.outline)
                self.assertEqual((bbox[2]-bbox[0],bbox[3]-bbox[1]),
                                 (40,45) if edge in ['top','bottom'] else (45,40))

    def test_several_handles_form_one_outline(self):
        spec = evaporation()
        spec['skeleton']['handle'] = [{'width':8,'height':5,'edge':edge} for edge in ['top','left']]
        _, frame, _ = m.build_evaporation(spec,16)
        self.assertEqual(frame.handle_count,2)
        self.assertAlmostEqual(m.shape_area(frame.outline),1680)

    def test_custom_foil_outline_does_not_gain_handle(self):
        spec = evaporation()
        spec['foil']['outline'] = {'type':'rect','width':40,'height':40}
        foil, frame, _ = m.build_evaporation(spec,16)
        self.assertEqual(foil.handle_count,0)
        self.assertEqual(m.shape_area(foil.outline),1600)
        self.assertEqual(m.shape_area(frame.outline),1640)

    def test_detached_or_point_connected_handle_rejected(self):
        for offset in [100,24]:
            spec = evaporation()
            spec['skeleton']['handle']['offset'] = offset
            with self.assertRaises(m.SpecError): self.generate(spec)

    def test_pick_union_has_no_internal_cut_or_complete_circle(self):
        spec = evaporation()
        _, frame, _ = m.build_evaporation(spec,24)
        self.assertEqual(len(frame.window_cuts),1)
        geom = m.shape_geometry(frame.window_cuts[0])
        self.assertAlmostEqual(geom.area, m.shape_area(frame.window[0]) + math.pi/2, delta=.005)
        self.assertAlmostEqual(geom.boundary.intersection(LineString([(-1,5.1),(1,5.1)])).length,0)
        output = m.render([frame],False)
        self.assertNotIn('\nPICK\n',output)
        self.assertEqual(output.count('\nPOLYLINE\n'),2)  # one outline + one window

    def test_multiple_rotated_pick_notches(self):
        spec = evaporation()
        spec['skeleton']['windows'] = {'type':'list','positions':[[0,0]],'angle':37}
        spec['skeleton']['pick_hole'] = [{'diameter':2,'edge':edge} for edge in ['top','left']]
        _, frame, _ = m.build_evaporation(spec,24)
        self.assertEqual(len(frame.window_cuts),1)
        self.assertTrue(m.shape_geometry(frame.window_cuts[0]).is_valid)
        self.assertTrue(self.generate(spec)[1])

    def test_invalid_pick_location_rejected(self):
        for fields in [{'offset':100},{'inset':3}]:
            spec = evaporation()
            spec['skeleton']['pick_hole'].update(fields)
            with self.assertRaises(m.SpecError): self.generate(spec)

    def test_four_corner_notches(self):
        for corner, (sx, sy) in {'top_left':(-1,1),'top_right':(1,1),
                                'bottom_left':(-1,-1),'bottom_right':(1,-1)}.items():
            with self.subTest(corner=corner):
                spec = evaporation()
                spec['skeleton']['pick_hole'] = {'diameter':2,'corner':corner}
                _, frame, _ = m.build_evaporation(spec,24)
                self.assertAlmostEqual(frame.pick[0][1],sx*5.1)
                self.assertAlmostEqual(frame.pick[0][2],sy*5.1)
                self.assertEqual(len(frame.window_cuts),1)
                geom = m.shape_geometry(frame.window_cuts[0])
                self.assertTrue(geom.contains(Point(sx*5.7,sy*5.7)))
                self.assertGreater(geom.area,m.shape_area(frame.window[0]))
                self.assertTrue(self.generate(spec)[1])

    def test_corner_inset_and_rotation(self):
        spec = evaporation()
        spec['skeleton']['windows'] = {'type':'list','positions':[[2,3]],'angle':90}
        spec['skeleton']['pick_hole'] = {'diameter':2,'corner':'top_right','inset':.2}
        spec['foil']['per_window'] = True
        _, frame, _ = m.build_evaporation(spec,24)
        self.assertAlmostEqual(frame.pick[0][1],2-4.9)
        self.assertAlmostEqual(frame.pick[0][2],3+4.9)
        self.assertTrue(self.generate(spec)[1])

    def test_mixed_edge_and_corner_notches(self):
        spec = evaporation()
        spec['skeleton']['pick_hole'] = [{'diameter':2,'edge':'left'},
                                        {'diameter':2,'corner':'top_right'}]
        _, frame, _ = m.build_evaporation(spec,24)
        self.assertEqual(len(frame.pick),2)
        self.assertEqual(len(frame.window_cuts),1)
        self.assertTrue(self.generate(spec)[1])

    def test_corner_input_errors(self):
        for pick in [{'diameter':2,'corner':'wrong'},
                     {'diameter':2,'corner':'top_right','edge':'top'},
                     {'diameter':2,'corner':'top_right','offset':1}]:
            spec = evaporation()
            spec['skeleton']['pick_hole'] = pick
            with self.assertRaises(m.SpecError): self.generate(spec)
        spec = evaporation()
        spec['substrate'] = {'type':'circle','diameter':10}
        spec['skeleton']['pick_hole'] = {'diameter':2,'corner':'top_right'}
        with self.assertRaises(m.SpecError): self.generate(spec)

    def test_no_installation_holes_is_valid(self):
        spec = evaporation()
        spec['skeleton'].pop('frame_holes')
        spec['foil'].pop('frame_holes')
        report, files = self.generate(spec)
        self.assertEqual(len(files),3)
        self.assertNotIn('[错误]',report)
        for _, content in files:
            self.assertNotIn('\nTOOLING\n',content)
            self.assertNotIn('\nFOIL_TOOLING\n',content)
            self.assertNotIn('\nFRAME_TOOLING\n',content)

    def test_ito_reference_layer_not_cut_and_no_duplicate_assembly_entities(self):
        spec=evaporation()
        spec['ito_effective']={'features':[{'type':'rect_array','width':8,'height':8,
            'nx':1,'ny':1,'pitch_x':0,'origin':[0,0]}]}
        foil,frame,ref=m.build_evaporation(spec,24)
        self.assertEqual(len(foil.ito_effective),1)
        self.assertNotIn(foil.ito_effective[0],m.cut_shapes(foil))
        before=m.render([foil,frame,ref],True)
        # layer table + POLYLINE + 4 VERTEX + SEQEND
        self.assertEqual(before.count('\nITO_EFFECTIVE\n'),7)
        self.assertEqual(m.color_for('ITO_EFFECTIVE'),6)
        original=evaporation()
        original_report,_=self.generate(original)
        report,files=self.generate(spec)
        self.assertEqual(report,original_report)
        self.assertEqual(len(files),3)
        spec['ito_effective']={'features':[]}
        self.assertIn('\nITO_EFFECTIVE\n',self.generate(spec)[1][0][1])

    def test_ito_reference_boundary_checked(self):
        spec=evaporation()
        spec['ito_effective']={'features':[{'type':'circle','diameter':2,'center':[10,0]}]}
        with self.assertRaises(m.SpecError):self.generate(spec)

    def test_laser_marking_chinese_is_vector_and_target_specific(self):
        spec=evaporation()
        spec['laser_marking']=[{'text':'A中','height':1.5,'center':[0,22.5],'angle':0,'target':'skeleton'}]
        foil,frame,ref=m.build_evaporation(spec,24)
        self.assertFalse(foil.marking)
        self.assertEqual(len(frame.marking),1)
        self.assertFalse(frame.validation_errors)
        all_points=[p for s in frame.marking[0]['contours'] for p in s[1]]
        self.assertAlmostEqual(max(p[1] for p in all_points)-min(p[1] for p in all_points),1.5)
        marking=m.render_marking(frame)
        self.assertIn('\nLASER_MARK\n',marking)
        self.assertNotIn('\nTEXT\n',marking)
        self.assertNotIn('\nOUTLINE\n',marking)
        self.assertNotIn('\nHOLES\n',marking)
        self.assertIn('\nPOLYLINE\n',marking)
        self.assertEqual(len(m.cut_shapes(frame)),len(m.cut_shapes(m.build_evaporation(evaporation(),24)[1])))

    def test_marking_on_opening_or_outside_body_blocks_generation(self):
        for center in [[0,0],[100,100]]:
            spec=evaporation()
            spec['laser_marking']=[{'text':'TEST','height':2,'center':center,'target':'skeleton'}]
            self.assert_blocked(spec)

    def test_marking_rotation_and_both_parts(self):
        spec=evaporation()
        spec['laser_marking']=[{'text':'O','height':2,'center':[0,22.5],'angle':90,'target':'both'}]
        foil,frame,_=m.build_evaporation(spec,24)
        self.assertEqual(len(foil.marking),1);self.assertEqual(len(frame.marking),1)
        self.assertTrue(self.generate(spec)[1])
        self.assertGreaterEqual(len(frame.marking[0]['contours']),2)  # 字母O保留内外环

    def test_invalid_marking_text_height_and_target(self):
        for item in [{'text':''},{'text':'two\nlines'},{'text':'x','height':0},
                     {'text':'x','target':'wrong'},{'text':'x','center':[float('nan'),0]}]:
            spec=evaporation();spec['laser_marking']=[item]
            with self.assertRaises((m.SpecError,ValueError)):self.generate(spec)

    def test_analytic_circle_in_circle(self):
        self.assertFalse(m.shape_inside(('circle',3,3,1),('circle',0,0,5)))
        self.assertTrue(m.shape_inside(('circle',3,0,2),('circle',0,0,5)))

    def test_round_light_block_rejects_corner_hole(self):
        self.assert_blocked({'kind':'light_block','name':'round',
            'substrate':{'type':'circle','diameter':10},
            'features':[{'type':'circle','center':[4,4],'diameter':1}]})

    def test_circle_and_concave_polygon_margins(self):
        circle = m._inset_boundary(('circle',0,0,5),.3)
        self.assertFalse(m.shape_inside(('circle',4.4,0,.5),circle))
        self.assertTrue(m.shape_inside(('circle',4.2,0,.5),circle))
        boundary = ('poly',[(0,0),(6,0),(6,6),(4,6),(4,2),(2,2),(2,6),(0,6)])
        # All vertices lie inside, but the upper edge bridges a concave notch.
        crossing = ('poly',[(1,1),(5,1),(5,5),(1,5)])
        self.assertFalse(m.shape_inside(crossing,boundary))
        self.assertFalse(m.shape_inside(('circle',3,4,.2),boundary))
        self.assertFalse(m.shape_inside(('circle',1.8,1.3,.3),m._inset_boundary(boundary,.6)))

    def test_rounded_corner_boundary(self):
        outline = m.build_outline({'type':'rect','width':10,'height':10,'corner_radius':2},24)
        self.assertFalse(m.shape_inside(('circle',4.5,4.5,.2),outline))

    def test_rotated_rectangle_boundary(self):
        boundary = m.transform_shape(m._rect(0,0,4,4,0),0,0,45)
        self.assertFalse(m.shape_inside(('circle',2,2,.2),boundary))

    def test_frame_window_tooling_and_foil_outline_are_checked(self):
        outside_window = evaporation()
        outside_window['skeleton']['windows'] = {'type':'list','positions':[[100,100]]}
        outside_window['foil']['per_window'] = True
        self.assert_blocked(outside_window)
        tooling = evaporation()
        tooling['skeleton']['frame_holes'] = {'diameter':2,'positions':[[100,100]]}
        self.assert_blocked(tooling)
        foil = evaporation()
        foil['foil'].update(outline={'type':'rect','width':.5,'height':.5})
        self.assert_blocked(foil)
        pick = evaporation()
        pick['skeleton']['outline'] = {'type':'rect','width':10.4,'height':10.4}
        pick['skeleton'].pop('frame_holes')
        pick['skeleton'].pop('handle')
        pick['foil'].pop('frame_holes')
        self.assert_blocked(pick)

    def test_overlapping_and_duplicate_cut_paths_blocked(self):
        self.assert_blocked(single(features=[{'type':'circle','diameter':2},
                                             {'type':'circle','diameter':2}]))
        spec = evaporation()
        spec['skeleton']['windows'] = {'type':'array','nx':2,'ny':1,'pitch_x':8,'origin':[-4,0]}
        spec['skeleton'].pop('pick_hole')
        self.assert_blocked(spec)

    def test_invalid_numeric_input_and_self_intersection(self):
        for d in [-1,0,float('nan')]:
            with self.assertRaises(m.SpecError): self.generate(single(features=[{'type':'circle','diameter':d}]))
        for count in [0,-1,1.5,True]:
            with self.assertRaises(m.SpecError): self.generate(single(features=[
                {'type':'circle_array','diameter':1,'pitch_x':2,'nx':count,'ny':1}]))
        with self.assertRaises(m.SpecError): self.generate(single(outline={
            'type':'polygon','points':[[0,0],[4,4],[0,4],[4,0]]}))

    def test_nested_csv_uses_spec_directory(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td)/'holes.csv').write_text('2,0,1\n',encoding='utf-8')
            spec = evaporation()
            spec['_base_dir'] = td
            spec['foil']['holes_csv'] = 'holes.csv'
            self.assertTrue(self.generate(spec)[1])

    def test_frame_ratio_includes_windows_and_web_check_includes_rects(self):
        report, _ = self.generate(evaporation())
        frame_report = report.split('[FRAME]')[1]
        self.assertNotIn('开孔占比 : 0.00',frame_report)
        self.assertIn('最小筋宽',frame_report)
        spec = single(features=[{'type':'rect_array','width':2,'height':2,
            'pitch_x':2.1,'nx':2,'ny':1,'origin':[-1.05,0]}])
        self.assertIn('[警告] 最小筋宽',self.generate(spec)[0])

    def test_cli_does_not_write_invalid_dxf(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spec = single(features=[{'type':'circle','diameter':1,'center':[100,100]}])
            path = root/'spec.json'
            path.write_text(json.dumps(spec),encoding='utf-8')
            result = subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'scripts/make_mask.py'),
                str(path),'--outdir',str(root/'out')],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,2)
            self.assertFalse(list(root.rglob('*.dxf')))
            self.assertTrue((root/'out/test_report.txt').exists())


if __name__ == '__main__':
    unittest.main()
