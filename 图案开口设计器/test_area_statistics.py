"""Check area intersections and uncertainty against analytic cases."""
import importlib.util
import math
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent
loader=importlib.util.spec_from_file_location('editor',ROOT/'server.py')
s=importlib.util.module_from_spec(loader);loader.loader.exec_module(s)
a=s.area_stats

def rect(w,h,x=0,y=0,angle=0):
    return dict(type='rect_array',width=w,height=h,nx=1,ny=1,pitch_x=0,pitch_y=0,origin=[x,y],angle=angle)

def spec(holes,ito):
    q=s.initial();q['foil']['cell']=holes;q['ito_effective']={'features':ito};q['laser_marking']=[]
    return q

class AreaTests(unittest.TestCase):
    def test_counts_and_current_intersections(self):
        holes=[rect(3,11,x,y) for y in [-7,7] for x in [-5,0,5]]+[rect(4,10,x) for x in [-10.5,10.5]]
        r=a.nominal(spec(holes,[rect(25,10)]),s.m)
        self.assertEqual(r['counts']['cell_openings'],8)
        self.assertEqual(r['counts']['foil_pattern_openings'],288)
        self.assertEqual(r['counts']['frame_positioning_openings'],36)
        self.assertEqual([p['area_mm2'] for p in r['pixels']],[10.5]*6+[40]*2)
        self.assertNotIn('cell_effective_mm2',r)
        self.assertNotIn('array_effective_mm2',r)

    def test_rectangle_uniform_matches_propagation_formula(self):
        w,h,e=3,4,.01
        r=a.calculate(spec([rect(w,h)],[rect(20,20)]),s.m,dict(aperture_mm=e))
        u=e/math.sqrt(3)
        expected=math.sqrt((h*u)**2+(w*u)**2)
        self.assertAlmostEqual(r['pixels'][0]['u_mm2'],expected,places=12)
        self.assertEqual(r['pixels'][0]['U_mm2'],2*r['pixels'][0]['u_mm2'])

    def test_normal_inputs_are_standard_uncertainties(self):
        r=a.calculate(spec([rect(3,4)],[rect(20,20)]),s.m,dict(distribution='normal',aperture_mm=.01))
        expected=math.sqrt((4*.01)**2+(3*.01)**2)
        self.assertAlmostEqual(r['pixels'][0]['u_mm2'],expected,places=12)

    def test_each_pixel_registration_uncertainty(self):
        r=a.calculate(spec([rect(2,2,-3,1),rect(2,2,3,1)],[rect(10,2)]),s.m,
                      dict(aperture_mm=0,registration_y_mm=.01))
        single=r['pixels'][0]['u_mm2']
        self.assertAlmostEqual(single,2*.01/math.sqrt(3),delta=.0004)
        self.assertAlmostEqual(r['pixels'][1]['u_mm2'],single,places=10)
        self.assertNotIn('cell_uncertainty',r)

    def test_clipping_boundary_has_conservative_one_sided_formula(self):
        r=a.calculate(spec([rect(2,2,0,2)],[rect(10,2)]),s.m,
                      dict(aperture_mm=0,registration_y_mm=.01))
        p=r['pixels'][0]
        self.assertEqual(p['area_mm2'],0)
        self.assertGreater(p['u_mm2'],0)
        self.assertEqual(p['status'],'conservative')
        self.assertAlmostEqual(p['u_mm2'],2*.01/math.sqrt(3),places=12)
        self.assertIsNone(p['relative_u_percent'])

    def test_ito_union_avoids_double_area_and_zero_errors(self):
        r=a.calculate(spec([rect(3,4)],[rect(20,20),rect(20,20)]),s.m,dict(aperture_mm=0))
        self.assertEqual(r['pixels'][0]['area_mm2'],12)
        self.assertEqual(r['pixels'][0]['u_mm2'],0)

    def test_rotated_circle_slot_and_polygon_areas(self):
        holes=[rect(2,3,-6,angle=32),dict(type='circle',diameter=2,center=[0,0]),
               dict(type='slot',length=4,width=1,center=[5,0],angle=40),
               dict(type='polygon',points=[[-1,5],[1,5],[0,7]])]
        r=a.calculate(spec(holes,[rect(25,25)]),s.m,dict(aperture_mm=0))
        for p,expected in zip(r['pixels'],[6,math.pi,3+math.pi/4,2]):
            self.assertAlmostEqual(p['area_mm2'],expected,delta=.00003)
            self.assertEqual(p['u_mm2'],0)

    def test_missing_ito_overlap_and_unsupported_model(self):
        with self.assertRaisesRegex(ValueError,'ITO'):a.calculate(spec([rect(2,2)],[]),s.m)
        r=a.nominal(spec([rect(2,2),rect(2,2)],[rect(20,20)]),s.m)
        self.assertEqual(r['counts']['cell_connected_openings'],1)
        with self.assertRaisesRegex(ValueError,'重叠'):a.calculate(spec([rect(2,2),rect(2,2)],[rect(20,20)]),s.m)
        r=a.calculate(spec([dict(type='polygon',points=[[0,0],[1,0],[0,1]])],[rect(20,20)]),s.m)
        self.assertEqual(r['pixels'][0]['status'],'unsupported')
        self.assertIsNone(r['pixels'][0]['u_mm2'])

    def test_current_pixel_analytic_sensitivities(self):
        r=a.calculate(spec([rect(3,11,0,7),rect(4,10,10.5)],[rect(25,10)]),s.m)
        self.assertAlmostEqual(r['pixels'][0]['u_mm2'],.01/math.sqrt(3)*math.sqrt(3.5**2+1.5**2),places=12)
        self.assertEqual(r['pixels'][0]['status'],'ok')
        self.assertAlmostEqual(r['pixels'][1]['u_mm2'],.01/math.sqrt(3)*math.sqrt(10**2+4**2),places=12)
        self.assertEqual(r['pixels'][1]['status'],'conservative')
        self.assertNotIn('mean_mm2',r['pixels'][0])
        self.assertNotIn('samples',r['settings'])

    def test_circle_and_slot_closed_form_derivatives(self):
        for p,derivatives in [(dict(type='circle',diameter=2),[math.pi]),
                             (dict(type='slot',length=4,width=1),[1,4+math.pi/2-2])]:
            r=a.calculate(spec([p],[rect(20,20)]),s.m)
            self.assertAlmostEqual(r['pixels'][0]['u_mm2'],.01/math.sqrt(3)*math.sqrt(sum(v*v for v in derivatives)),places=12)

    def test_tolerance_crosses_clip_branch_is_explicit(self):
        r=a.calculate(spec([rect(2,2,0,2.005)],[rect(10,2)]),s.m,dict(aperture_mm=0,registration_y_mm=.01))
        self.assertEqual(r['pixels'][0]['status'],'unsupported')
        self.assertIsNone(r['pixels'][0]['u_mm2'])

    def test_absolute_pattern_uses_ito_in_actual_array_positions(self):
        q=spec([dict(type='circle',diameter=2,center=[-75,-75])],[rect(25,10)])
        q['foil']['per_window']=False
        r=a.calculate(q,s.m)
        self.assertEqual(r['counts']['foil_pattern_openings'],1)
        self.assertAlmostEqual(r['pixels'][0]['area_mm2'],math.pi,places=12)
        self.assertAlmostEqual(r['pixels'][0]['u_mm2'],math.pi*.01/math.sqrt(3),places=12)

    def test_invalid_options_and_dimensions(self):
        for options in [dict(aperture_mm=-1),dict(ito_mm=float('nan')),dict(distribution='bad')]:
            with self.assertRaises(ValueError):a.settings(options)
        with self.assertRaisesRegex(ValueError,'尺寸误差'):a.calculate(spec([rect(.01,2)],[rect(20,20)]),s.m)

if __name__=='__main__':unittest.main()
