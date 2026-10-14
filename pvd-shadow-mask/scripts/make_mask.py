#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""镀膜/测试掩模板参数化 DXF 生成器.

支持三种 kind:
  - single       : 单件掩模板(兼容旧版规格)
  - evaporation  : 蒸镀掩模板 = 0.1mm 掩模片 + 2mm 骨架, 一次出 3 个 DXF
                   (装配图 / 掩模片 / 骨架), 骨架定位开口 = 基片 + 旷量
  - light_block  : 测试遮光 mask, 外形同基片, 通光孔比镀银区小一圈

使用 Shapely 做轮廓合并与几何校验, 不依赖 ezdxf/AutoCAD, 输出 DXF R12 (AC1009)。

厚度/材料不在图纸标注, 而是下单时选择; 本工具不把厚度写进 DXF。

用法:
    python make_mask.py spec.json --outdir 输出目录
    python make_mask.py spec.json -o mask.dxf          # single / light_block
    python make_mask.py spec.json --stdout             # 只打印校验报告

规格结构见 references/spec-format.md 与 examples/。
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

try:
    from shapely.geometry import Point, Polygon
    from shapely.ops import unary_union
except ImportError:
    Point = Polygon = unary_union = None

EPS = 1e-8

# --------------------------------------------------------------------------
# 几何基础
# --------------------------------------------------------------------------


class SpecError(Exception):
    pass


def rot(px: float, py: float, deg: float) -> tuple[float, float]:
    """绕原点旋转, 角度为度, 逆时针为正。"""
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return px * c - py * s, px * s + py * c


def arc_points(cx, cy, radius, a0, a1, segments_per_90=16):
    """用折线逼近圆弧 (角度制, 逆时针, a1 > a0)。"""
    span = a1 - a0
    n = max(2, int(math.ceil(abs(span) / 90.0 * segments_per_90)))
    return [
        (cx + radius * math.cos(math.radians(a0 + span * i / n)),
         cy + radius * math.sin(math.radians(a0 + span * i / n)))
        for i in range(n + 1)
    ]


def rounded_rect_outline(width, height, radius, segments_per_90=16):
    """返回以 (0,0) 为中心的圆角矩形闭合折线顶点。"""
    hw, hh = width / 2.0, height / 2.0
    r = max(0.0, min(radius, hw, hh))
    if r <= 0:
        return [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
    c = [(hw - r, hh - r, 0, 90), (-hw + r, hh - r, 90, 180),
         (-hw + r, -hh + r, 180, 270), (hw - r, -hh + r, 270, 360)]
    pts = []
    for cx, cy, a0, a1 in c:
        pts.extend(arc_points(cx, cy, r, a0, a1, segments_per_90))
    return pts


# Shape = ("circle", cx, cy, r) | ("poly", [(x, y), ...])


def shape_bbox(shape):
    if shape[0] == "circle":
        _, cx, cy, r = shape
        return cx - r, cy - r, cx + r, cy + r
    pts = shape[1]
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


def polyline_area(pts):
    a = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def shape_area(shape):
    return math.pi * shape[3] ** 2 if shape[0] == "circle" else polyline_area(shape[1])


def _extremes(shape):
    if shape[0] == "circle":
        _, cx, cy, r = shape
        return [(cx + r, cy), (cx - r, cy), (cx, cy + r), (cx, cy - r)]
    return shape[1]


def shape_geometry(shape, seg=16, tolerance=0.001):
    """布尔运算用几何; 圆弧弦高误差不超过 tolerance mm。"""
    if Point is None:
        raise SpecError("缺少 Shapely: 请运行 python -m pip install -r requirements.txt")
    if shape[0] == "circle":
        _, x, y, r = shape
        if not all(math.isfinite(v) for v in (x, y, r)) or r <= 0:
            raise SpecError("圆孔/圆外形的坐标必须有限, 半径必须 > 0")
        angle = math.acos(1 - min(tolerance / r, 1.0))
        n = max(seg, int(math.ceil(math.pi / (4 * angle))))
        return Point(x, y).buffer(r, quad_segs=n)
    pts = shape[1]
    if not all(len(p) == 2 and all(math.isfinite(v) for v in p) for p in pts):
        raise SpecError("多边形必须提供有限的二维坐标")
    geom = Polygon(pts)
    if geom.is_empty or not geom.is_valid or geom.area <= EPS:
        raise SpecError("多边形自交、退化或为空, 不能作为切割轮廓")
    return geom


def geometry_shapes(geom, ctx):
    """仅接受无内部岛的闭合多边形, 不悄悄删除岛或分离部件。"""
    polygons = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    if any(g.geom_type != "Polygon" or g.interiors for g in polygons):
        raise SpecError(f"{ctx}: 合并结果含内部岛或非面几何, 请调整轮廓")
    return [("poly", list(g.exterior.coords)[:-1]) for g in polygons]


def merged_outline(outline, handles, seg, tolerance):
    if not handles:
        return outline
    geom = unary_union([shape_geometry(s, seg, tolerance) for s in [outline] + handles])
    contours = geometry_shapes(geom, "把手与外框")
    if len(contours) != 1:
        raise SpecError("把手必须与主体沿一段边连接; 当前把手脱离主体或仅点接触")
    return contours[0]


def merge_window_cuts(windows, picks, seg, tolerance):
    if not picks:
        return list(windows)
    wg = [shape_geometry(w, seg, tolerance) for w in windows]
    groups = [[] for _ in windows]
    for pick in picks:
        pg = shape_geometry(pick, seg, tolerance)
        touched = [i for i, g in enumerate(wg) if g.intersection(pg).area > EPS]
        if len(touched) != 1:
            raise SpecError("取片缺口必须与一个定位开口相交, 不能脱离定位开口或跨接多个定位开口")
        if wg[touched[0]].covers(pg):
            raise SpecError("取片缺口完全位于定位开口内, 无法形成取片缺口")
        groups[touched[0]].append(pg)
    result = []
    for w, g, additions in zip(windows, wg, groups):
        result.extend(geometry_shapes(unary_union([g] + additions), "定位开口与取片缺口") if additions else [w])
    return result


def shape_inside(shape, boundary, margin=0.0):
    """真实轮廓包含检查; 圆孔与圆边界使用解析半径, 不用四点或包围盒近似。"""
    if boundary[0] == "inset":
        margin += boundary[2]
        boundary = boundary[1]
    if boundary[0] == "circle":
        _, bx, by, br = boundary
        if shape[0] == "circle":
            return math.hypot(shape[1] - bx, shape[2] - by) + shape[3] + margin <= br + EPS
        return all(math.hypot(x - bx, y - by) + margin <= br + EPS for x, y in shape[1])
    bg = shape_geometry(boundary)
    if shape[0] == "circle":
        center = Point(shape[1], shape[2])
        return bg.covers(center) and bg.boundary.distance(center) + EPS >= shape[3] + margin
    sg = shape_geometry(shape)
    return bg.buffer(EPS).covers(sg) and bg.boundary.distance(sg) + EPS >= margin


def shape_distance(a, b, ga=None, gb=None):
    """圆形保留解析距离, 其余距离按实际输出折线计算。"""
    if a[0] == b[0] == "circle":
        return max(0.0, math.hypot(a[1] - b[1], a[2] - b[2]) - a[3] - b[3])
    if a[0] == "circle":
        return max(0.0, Point(a[1], a[2]).distance(gb if gb is not None else shape_geometry(b)) - a[3])
    if b[0] == "circle":
        return shape_distance(b, a, gb, ga)
    return (ga if ga is not None else shape_geometry(a)).distance(gb if gb is not None else shape_geometry(b))


def validate_spec(value, ctx="spec"):
    """提前拒绝无效尺寸/阵列计数, 避免 int() 截断或负半径进入 DXF。"""
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{ctx}.{key}"
            if key in ("nx", "ny", "arc_segments_per_90"):
                if isinstance(item, bool) or not isinstance(item, int) or item <= 0:
                    raise SpecError(f"{path} 必须为正整数")
            if key in ("width", "height", "diameter", "length", "curve_tolerance_mm"):
                if isinstance(item, bool) or not isinstance(item, (int, float)) or item <= 0:
                    raise SpecError(f"{path} 必须 > 0")
            if key in ("corner_radius", "clearance_mm", "min_web_mm", "edge_margin_mm", "aperture_inset_mm"):
                if isinstance(item, bool) or not isinstance(item, (int, float)) or item < 0:
                    raise SpecError(f"{path} 必须 ≥ 0")
            validate_spec(item, path)
        if value.get("type") in ("array", "circle_array", "rect_array"):
            for axis in ("x", "y"):
                pitch = value.get(f"pitch_{axis}", value.get("pitch_x"))
                if value.get(f"n{axis}", 1) > 1 and (not isinstance(pitch, (int, float)) or pitch <= 0):
                    raise SpecError(f"{ctx}.pitch_{axis} 在该方向重复阵列时必须 > 0")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            validate_spec(item, f"{ctx}[{i}]")
    elif isinstance(value, (int, float)) and not math.isfinite(value):
        raise SpecError(f"{ctx} 必须为有限数值")


def need(d, key, ctx):
    if key not in d or d[key] is None:
        raise SpecError(f"{ctx}: 缺少必填字段 {key}")
    return d[key]


def build_outline(o, seg):
    t = o.get("type", "rect")
    if t == "rect":
        return ("poly", rounded_rect_outline(float(need(o, "width", "outline")),
                                             float(need(o, "height", "outline")),
                                             float(o.get("corner_radius", 0.0)), seg))
    if t == "circle":
        return ("circle", 0.0, 0.0, float(need(o, "diameter", "outline")) / 2.0)
    if t == "polygon":
        pts = [tuple(map(float, p)) for p in need(o, "points", "outline")]
        if len(pts) < 3:
            raise SpecError("outline.polygon 至少需要 3 个点")
        return ("poly", pts)
    raise SpecError(f"未知 outline type: {t}")


def expand_outline(o, per_side, seg):
    """基片外形按每边 per_side 外扩 -> 骨架定位开口。"""
    t = o.get("type", "rect")
    if t == "rect":
        radius = float(o.get("corner_radius", 0.0))
        # 配合余量增大边长; 直角方片的定位开口保持直角, 不自动添加圆角。
        window_radius = max(0.0, radius + per_side) if radius > 0 else 0.0
        return ("poly", rounded_rect_outline(float(o["width"]) + 2 * per_side,
                                             float(o["height"]) + 2 * per_side,
                                             window_radius, seg))
    if t == "circle":
        return ("circle", 0.0, 0.0, float(o["diameter"]) / 2.0 + per_side)
    raise SpecError("骨架定位开口只支持 rect / circle 基片外形")


def outline_size(o):
    t = o.get("type", "rect")
    if t == "rect":
        return float(o["width"]), float(o["height"])
    if t == "circle":
        return float(o["diameter"]), float(o["diameter"])
    raise SpecError("该处仅支持 rect / circle 外形")


# --------------------------------------------------------------------------
# DXF R12 写出器
# --------------------------------------------------------------------------

SUFFIX_COLORS = {"OUTLINE": 1, "HOLES": 3, "WINDOW": 5, "TOOLING": 4, "REFERENCE": 6, "NOTES": 8, "PICK": 2, "ITO_EFFECTIVE": 6, "LASER_MARK": 30}


def color_for(layer: str) -> int:
    for suffix, color in SUFFIX_COLORS.items():
        if layer == suffix or layer.endswith("_" + suffix):
            return color
    return 7


def encode_text(s: str) -> str:
    """非 ASCII 用 AutoCAD 的 \\U+XXXX 转义, 否则 R12 乱码。"""
    return "".join(ch if ord(ch) < 128 else "\\U+%04X" % ord(ch) for ch in str(s))


class Dxf:
    def __init__(self):
        self._ent = []
        self._layers = {}

    def _pair(self, code, value):
        self._ent.append(f"{code}\n{value}")

    def _use(self, layer):
        self._layers.setdefault(layer, color_for(layer))
        self._pair(8, layer)

    def add_layer(self, layer):
        self._layers.setdefault(layer, color_for(layer))

    def circle(self, layer, cx, cy, r):
        self._pair(0, "CIRCLE")
        self._use(layer)
        self._pair(10, f"{cx:.6f}")
        self._pair(20, f"{cy:.6f}")
        self._pair(30, "0.0")
        self._pair(40, f"{r:.6f}")

    def polyline(self, layer, pts, closed=True):
        self._pair(0, "POLYLINE")
        self._use(layer)
        self._pair(66, "1")
        self._pair(70, "1" if closed else "0")
        self._pair(10, "0.0")
        self._pair(20, "0.0")
        self._pair(30, "0.0")
        for x, y in pts:
            self._pair(0, "VERTEX")
            self._use(layer)
            self._pair(10, f"{x:.6f}")
            self._pair(20, f"{y:.6f}")
            self._pair(30, "0.0")
        self._pair(0, "SEQEND")
        self._use(layer)

    def shape(self, layer, shape):
        if shape[0] == "circle":
            self.circle(layer, shape[1], shape[2], shape[3])
        else:
            self.polyline(layer, shape[1], True)

    def text(self, layer, x, y, height, s):
        self._pair(0, "TEXT")
        self._use(layer)
        self._pair(10, f"{x:.6f}")
        self._pair(20, f"{y:.6f}")
        self._pair(30, "0.0")
        self._pair(40, f"{height:.6f}")
        self._pair(1, encode_text(s))

    def dumps(self):
        out = []

        def w(code, value):
            out.append(f"{code}\n{value}")

        w(0, "SECTION"); w(2, "HEADER")
        w(9, "$ACADVER"); w(1, "AC1009")
        w(9, "$MEASUREMENT"); w(70, "1")
        w(9, "$INSUNITS"); w(70, "4")
        w(0, "ENDSEC")
        w(0, "SECTION"); w(2, "TABLES"); w(0, "TABLE"); w(2, "LAYER")
        w(70, str(len(self._layers)))
        for name, color in self._layers.items():
            w(0, "LAYER"); w(2, name); w(70, "0"); w(62, str(color)); w(6, "CONTINUOUS")
        w(0, "ENDTAB"); w(0, "ENDSEC")
        w(0, "SECTION"); w(2, "ENTITIES")
        out.extend(self._ent)
        w(0, "ENDSEC"); w(0, "EOF")
        return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# features -> 孔
# --------------------------------------------------------------------------


def expand_array(a, hole_builder):
    """origin 是第 0 个孔的中心。"""
    ox, oy = a.get("origin", [0.0, 0.0])
    px = float(need(a, "pitch_x", "array"))
    py = float(a.get("pitch_y", px))
    nx = int(need(a, "nx", "array"))
    ny = int(need(a, "ny", "array"))
    angle = float(a.get("angle", 0.0))
    stagger = bool(a.get("stagger", False))
    skip = {(int(s[0]), int(s[1])) for s in a.get("skip", [])}
    holes = []
    for j in range(ny):
        for i in range(nx):
            if (i, j) in skip:
                continue
            lx = i * px + (px / 2.0 if stagger and (j % 2) else 0.0)
            rx, ry = rot(lx, j * py, angle)
            holes.append(hole_builder(ox + rx, oy + ry))
    return holes


def _circle(cx, cy, d):
    return ("circle", cx, cy, d / 2.0)


def _rect(cx, cy, w, h, angle):
    hw, hh = w / 2.0, h / 2.0
    return ("poly", [(cx + rx, cy + ry) for rx, ry in
                     (rot(x, y, angle) for x, y in
                      [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)])])


def build_features(feats, ctx):
    """返回功能孔列表(圆孔 + 异形轮廓), 全部落在 HOLES 层。"""
    if not isinstance(feats, list) or not feats:
        raise SpecError(f"{ctx}: features 必须是非空数组")
    holes = []
    for idx, f in enumerate(feats):
        t = f.get("type")
        k = f"{ctx}.features[{idx}]"
        if t == "circle_array":
            d = float(need(f, "diameter", k))
            holes += expand_array(f, lambda x, y, d=d: _circle(x, y, d))
        elif t == "rect_array":
            wd, ht = float(need(f, "width", k)), float(need(f, "height", k))
            ang = float(f.get("angle", 0.0))
            holes += expand_array(f, lambda x, y, w=wd, h=ht, a=ang: _rect(x, y, w, h, a))
        elif t == "circle":
            cx, cy = f.get("center", [0.0, 0.0])
            holes.append(_circle(cx, cy, float(need(f, "diameter", k))))
        elif t == "polygon":
            pts = [tuple(map(float, p)) for p in need(f, "points", k)]
            if len(pts) < 3:
                raise SpecError(f"{k}: polygon 至少 3 点")
            holes.append(("poly", pts))
        elif t == "slot":
            cx, cy = f.get("center", [0.0, 0.0])
            length, wd = float(need(f, "length", k)), float(need(f, "width", k))
            if wd > length:
                raise SpecError(f"{k}: slot width > length")
            ang = float(f.get("angle", 0.0))
            r, half = wd / 2.0, length / 2.0 - wd / 2.0
            pts = arc_points(-half, 0, r, 90, 270, 8) + arc_points(half, 0, r, -90, 90, 8)
            holes.append(("poly", [(cx + x, cy + y) for x, y in (rot(a, b, ang) for a, b in pts)]))
        else:
            raise SpecError(f"{k}: 未知 type '{t}'")
    return holes


def read_holes_csv(spec):
    path = spec.get("holes_csv")
    if not path:
        return []
    p = Path(path)
    if not p.is_absolute():
        p = Path(spec.get("_base_dir", ".")) / p
    if not p.exists():
        raise SpecError(f"holes_csv 不存在: {p}")
    out = []
    for ln, raw in enumerate(p.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            vals = [float(x) for x in (s.strip() for s in line.split(","))]
        except ValueError:
            raise SpecError(f"holes_csv 第 {ln} 行无法解析: {raw}")
        if len(vals) == 3:
            out.append(_circle(vals[0], vals[1], vals[2]))
        elif len(vals) == 4:
            out.append(_rect(vals[0], vals[1], vals[2], vals[3], 0.0))
        else:
            raise SpecError(f"holes_csv 第 {ln} 行需要 3 或 4 列: {raw}")
    return out


def build_frame_holes(fh, outline, ctx):
    d = float(need(fh, "diameter", ctx))
    if fh.get("positions"):
        return [_circle(float(x), float(y), d) for x, y in fh["positions"]]
    inset = float(need(fh, "inset", ctx))
    x0, y0, x1, y1 = shape_bbox(outline)
    skip = {(round(float(p[0]), 3), round(float(p[1]), 3)) for p in fh.get("skip_corners", [])}
    out = []
    for sx in (x0 + inset, x1 - inset):
        for sy in (y0 + inset, y1 - inset):
            if (round(sx, 3), round(sy, 3)) not in skip:
                out.append(_circle(sx, sy, d))
    return out


# --------------------------------------------------------------------------
# Part
# --------------------------------------------------------------------------


class Part:
    def __init__(self, pid, caption):
        self.id = pid
        self.caption = caption
        self.outline = None
        self.outline_extra = []
        self.holes = []
        self.window = []
        self.pick = []
        self.tooling = []
        self.reference = []
        self.ito_effective = None  # None 未启用; [] 表示已启用的空参考图层
        self.notes = []
        self.marking = []
        self.marking_enabled = False
        self.bounds = None  # 允许边界列表(校验用)
        self.window_cuts = None  # 合并缺口后的加工轮廓; window/pick 保留为设计参数
        self.handle_count = 0
        self.validation_errors = []

    def layers(self, prefix=""):
        return {
            "outline": prefix + "OUTLINE",
            "holes": prefix + "HOLES",
            "window": prefix + "WINDOW",
            "pick": prefix + "PICK",
            "tooling": prefix + "TOOLING",
            "reference": prefix + "REFERENCE",
            "notes": "NOTES",
        }


def build_single(spec, seg):
    p = Part("PART", spec.get("label") or spec.get("name", "MASK"))
    p.outline = build_outline(need(spec, "outline", "spec"), seg)
    p.holes = build_features(need(spec, "features", "spec"), "spec") + read_holes_csv(spec)
    if spec.get("frame_holes"):
        p.tooling = build_frame_holes(spec["frame_holes"], p.outline, "frame_holes")
    p.bounds = [_inset_boundary(p.outline, float(spec.get("edge_margin_mm", 0.0)))]
    p.ito_effective = build_ito_effective(spec, seg, [(0, 0, 0)])
    attach_marking(spec, [p])
    return [p]


def build_evaporation(spec, seg):
    sub = need(spec, "substrate", "spec")
    clr = float(spec.get("clearance_mm", 0.2))
    base_window = expand_outline(sub, clr / 2.0, seg)

    sk = need(spec, "skeleton", "spec")
    sk_outline = build_outline(need(sk, "outline", "skeleton"), seg)
    handles = build_handle(sk.get("handle"), sk_outline)
    tolerance = float(spec.get("curve_tolerance_mm", 0.001))
    final_outline = merged_outline(sk_outline, handles, seg, tolerance)
    centers = window_centers(sk.get("windows"))
    windows = [transform_shape(base_window, cx, cy, ang) for cx, cy, ang in centers]

    foil_spec = spec.get("foil", {})
    foil_uses_default = not foil_spec.get("outline")
    foil_outline = final_outline if foil_uses_default else build_outline(foil_spec["outline"], seg)
    per_window = bool(foil_spec.get("per_window", len(centers) > 1))
    local_holes = build_features(_cell_features(foil_spec), "foil") + read_holes_csv(
        dict(foil_spec, _base_dir=spec.get("_base_dir", ".")))

    foil = Part("FOIL", "0.1mm 掩模片")
    foil.outline = foil_outline
    foil.handle_count = len(handles) if foil_uses_default else 0
    foil.holes = []
    for cx, cy, ang in centers if per_window else [(0.0, 0.0, 0.0)]:
        foil.holes += [transform_shape(h, cx, cy, ang) for h in local_holes]
    foil.bounds = windows
    if foil_spec.get("frame_holes"):
        # inset 的基准仍是主体, 不因合并把手后的包围盒变化而移动安装孔。
        tooling_outline = sk_outline if foil_uses_default else foil_outline
        foil.tooling = build_frame_holes(foil_spec["frame_holes"], tooling_outline, "foil.frame_holes")

    frame = Part("FRAME", "2mm 骨架")
    frame.outline = final_outline
    frame.handle_count = len(handles)
    frame.window = windows
    frame.pick = build_pick_holes(sk.get("pick_hole"), base_window, centers)
    frame.window_cuts = merge_window_cuts(windows, frame.pick, seg, tolerance)
    if sk.get("frame_holes"):
        frame.tooling = build_frame_holes(sk["frame_holes"], sk_outline, "skeleton.frame_holes")

    ref = Part("SUB", "基片(参考)")
    sub_shape = build_outline(sub, seg)
    ref.reference = [transform_shape(sub_shape, cx, cy, ang) for cx, cy, ang in centers]
    ito = build_ito_effective(spec, seg, centers)
    foil.ito_effective = frame.ito_effective = ito
    attach_marking(spec, [foil, frame])
    return [foil, frame, ref]


def build_light_block(spec, seg):
    sub = need(spec, "substrate", "spec")
    p = Part("PART", spec.get("label") or spec.get("name", "MASK"))
    p.outline = build_outline(sub, seg)
    silver = spec.get("silvered")
    if silver:
        p.reference = [build_outline(silver, seg)]
    p.holes = build_features(need(spec, "features", "spec"), "spec") + read_holes_csv(spec)
    if spec.get("frame_holes"):
        p.tooling = build_frame_holes(spec["frame_holes"], p.outline, "frame_holes")
    p.bounds = [_inset_boundary(p.reference[0] if silver else p.outline,
                                float(spec.get("aperture_inset_mm", 0.3)))]
    p.ito_effective = build_ito_effective(spec, seg, [(0, 0, 0)])
    attach_marking(spec, [p])
    return [p]


def build_ito_effective(spec, seg, centers):
    """ITO 参考区域相对基片中心, 复制到每格; 不作为切割轮廓。"""
    if 'ito_effective' not in spec:
        return None
    config = spec['ito_effective']
    if not isinstance(config, dict):
        raise SpecError('ito_effective 必须是包含 features 的对象')
    features = config.get('features', [])
    shapes = build_features(features, 'ito_effective') if features else []
    boundary = build_outline(spec.get('substrate', spec.get('outline')), seg)
    for shape in shapes:
        shape_geometry(shape)
        if not shape_inside(shape, boundary):
            raise SpecError('ITO有效区域超出基片真实边界')
    return [transform_shape(s, x, y, angle) for x, y, angle in centers for s in shapes]


def marking_preview(spec):
    """文字转矢量闭合轮廓; center 为文字外包框中心, height 为实际字形总高。"""
    items = spec.get('laser_marking', [])
    if not isinstance(items, list) or len(items) > 40:
        raise SpecError('laser_marking 必须是数组, 最多40段文字')
    if not items:
        return []
    try:
        from matplotlib.font_manager import FontProperties, findfont
        from matplotlib.textpath import TextPath
    except ImportError:
        raise SpecError('文字打标需要 Matplotlib: python -m pip install -r requirements.txt')
    font = findfont(FontProperties(family='Microsoft YaHei'), fallback_to_default=False)
    preview = []
    for item in items:
        text = item.get('text', '')
        if not isinstance(text, str) or not text.strip() or len(text) > 120 or any(ord(c) < 32 for c in text):
            raise SpecError('打标文字须为1至120个字符的单行文字')
        target = item.get('target', 'skeleton')
        if target not in ('skeleton', 'foil', 'both'):
            raise SpecError('打标对象须为 skeleton/foil/both')
        height = float(item.get('height', 3))
        angle = float(item.get('angle', 0))
        center = item.get('center', [0, 0])
        if len(center) != 2 or not all(math.isfinite(float(v)) for v in center) or not math.isfinite(angle) or not math.isfinite(height) or height <= 0:
            raise SpecError('文字字高须 > 0, 坐标和角度须为有限数值')
        path = TextPath((0, 0), text, size=height, prop=FontProperties(fname=font))
        bbox = path.get_extents()
        if not math.isfinite(bbox.height) or bbox.height <= 0:
            raise SpecError('文字没有可打标的字形轮廓')
        scale = height / bbox.height
        ox, oy = (bbox.x0 + bbox.x1)/2, (bbox.y0 + bbox.y1)/2
        contours = []
        for pts in path.to_polygons():
            if len(pts) < 4:
                continue
            shape = ('poly', [((float(x)-ox)*scale, (float(y)-oy)*scale) for x,y in pts[:-1]])
            if shape_area(shape) <= EPS:
                continue
            contours.append(transform_shape(shape, float(center[0]), float(center[1]), angle))
        if not contours:
            raise SpecError('文字没有可打标的字形轮廓')
        preview.append({'text':text, 'target':target, 'height':height, 'center':center,
                        'angle':angle, 'font':'Microsoft YaHei', 'contours':contours})
    return preview


def attach_marking(spec, parts):
    """校验文字落在目标板实体上; 打标轮廓不参与切割/筋宽/开孔统计。"""
    if 'laser_marking' not in spec:
        return
    preview = marking_preview(spec)
    for part in parts:
        part.marking_enabled = True
        material = shape_geometry(part.outline)
        cuts = cut_shapes(part)
        if cuts:
            material = material.difference(unary_union([shape_geometry(s) for s in cuts]))
        for item in preview:
            if part.id == 'FRAME' and item['target'] == 'foil':
                continue
            if part.id == 'FOIL' and item['target'] == 'skeleton':
                continue
            # Text contours can have touching vertices. The polygon buffer repairs only
            # the validation area; exported glyph contours retain original winding/holes.
            outside = any(not material.buffer(EPS).covers(Polygon(s[1]).buffer(0)) for s in item['contours'])
            if outside:
                part.validation_errors.append(f'打标文字“{item["text"]}”超出板实体或压到加工开口')
            part.marking.append(item)


def render_marking(part):
    """独立打标DXF, 仅含LASER_MARK字形轮廓。"""
    mark = Part(part.id, part.caption)
    mark.marking_enabled = True
    mark.marking = part.marking
    return render([mark], False)


def _inset_boundary(shape, inset):
    # 保存原边界与最短距离约束, 避免把圆形/凹多边形内缩成包围盒。
    return ("inset", shape, inset)


def transform_shape(shape, dx, dy, deg):
    """旋转 deg 度后平移 (dx, dy)。"""
    if shape[0] == "circle":
        cx, cy = rot(shape[1], shape[2], deg)
        return ("circle", cx + dx, cy + dy, shape[3])
    return ("poly", [(rx + dx, ry + dy) for rx, ry in (rot(x, y, deg) for x, y in shape[1])])


def window_centers(wspec):
    """返回 [(cx, cy, angle), ...]; 不给则单个居中的定位开口。"""
    if not wspec:
        return [(0.0, 0.0, 0.0)]
    t = wspec.get("type", "array")
    if t == "list":
        ang = float(wspec.get("angle", 0.0))
        positions = need(wspec, "positions", "windows")
        if not positions:
            raise SpecError("windows.positions 不能为空")
        return [(float(x), float(y), ang) for x, y in positions]
    if t == "array":
        ox, oy = wspec.get("origin", [0.0, 0.0])
        px = float(need(wspec, "pitch_x", "windows"))
        py = float(wspec.get("pitch_y", px))
        nx, ny = int(need(wspec, "nx", "windows")), int(need(wspec, "ny", "windows"))
        ang = float(wspec.get("angle", 0.0))
        stagger = bool(wspec.get("stagger", False))
        out = []
        for j in range(ny):
            for i in range(nx):
                lx = i * px + (px / 2.0 if stagger and (j % 2) else 0.0)
                rx, ry = rot(lx, j * py, ang)
                out.append((ox + rx, oy + ry, ang))
        return out
    raise SpecError(f"未知 windows type: {t}")


def _pick_center(cx, cy, ang, window_shape, edge, offset, inset, corner=None):
    """取片缺口圆心: 位于定位开口的边或角, 随定位开口一起旋转。"""
    x0, y0, x1, y1 = shape_bbox(window_shape)
    hx, hy = (x1 - x0) / 2.0, (y1 - y0) / 2.0
    if corner is not None:
        corners = {"top_left": (-1, 1), "top_right": (1, 1),
                   "bottom_left": (-1, -1), "bottom_right": (1, -1)}
        if not isinstance(corner, str) or corner not in corners:
            raise SpecError("pick_hole.corner 只能是 top_left/top_right/bottom_left/bottom_right")
        if window_shape[0] == "circle":
            raise SpecError("圆形定位开口没有角, 请使用 edge 指定边缘位置")
        sx, sy = corners[corner]
        lx, ly = sx * (hx - inset), sy * (hy - inset)
    elif edge == "top":
        lx, ly = offset, hy - inset
    elif edge == "bottom":
        lx, ly = offset, -hy + inset
    elif edge == "left":
        lx, ly = -hx + inset, offset
    elif edge == "right":
        lx, ly = hx - inset, offset
    else:
        raise SpecError(f"pick_hole.edge 只能是 top/bottom/left/right, 收到 '{edge}'")
    rx, ry = rot(lx, ly, ang)
    return cx + rx, cy + ry


def _cell_features(spec_part):
    """单元图案: 接受 features 或 cell(别名)。只描述单个片子上的图案。"""
    feats = spec_part.get("features") or spec_part.get("cell")
    if not feats:
        raise SpecError("缺少单元图案: 请提供 features 或 cell(单个片子上的图案)")
    return feats


def build_handle(hspec, outline):
    """生成把手输入几何, 后续与主体合并; width 沿边, height 为凸出量。"""
    if not hspec:
        return []
    specs = hspec if isinstance(hspec, list) else [hspec]
    x0, y0, x1, y1 = shape_bbox(outline)
    out = []
    for hs in specs:
        w = float(need(hs, "width", "handle"))
        h = float(need(hs, "height", "handle"))
        edge = hs.get("edge", "top")
        off = float(hs.get("offset", 0.0))
        if edge == "top":
            c = (x0 + x1) / 2.0 + off
            pts = [(c - w / 2, y1), (c + w / 2, y1), (c + w / 2, y1 + h), (c - w / 2, y1 + h)]
        elif edge == "bottom":
            c = (x0 + x1) / 2.0 + off
            pts = [(c - w / 2, y0 - h), (c + w / 2, y0 - h), (c + w / 2, y0), (c - w / 2, y0)]
        elif edge == "left":
            c = (y0 + y1) / 2.0 + off
            pts = [(x0 - h, c - w / 2), (x0, c - w / 2), (x0, c + w / 2), (x0 - h, c + w / 2)]
        elif edge == "right":
            c = (y0 + y1) / 2.0 + off
            pts = [(x1, c - w / 2), (x1 + h, c - w / 2), (x1 + h, c + w / 2), (x1, c + w / 2)]
        else:
            raise SpecError(f"handle.edge 只能是 top/bottom/left/right, 收到 '{edge}'")
        out.append(("poly", pts))
    return out


def build_pick_holes(pspec, base_window, centers):
    """取片缺口支持边与角; 原始圆形输入最终与定位开口合并。"""
    if not pspec:
        return []
    specs = pspec if isinstance(pspec, list) else [pspec]
    out = []
    for ps in specs:
        d = float(need(ps, "diameter", "skeleton.pick_hole"))
        edge = ps.get("edge", "top")
        offset = float(ps.get("offset", 0.0))
        inset = float(ps.get("inset", 0.0))
        corner = ps.get("corner")
        if corner is not None and "edge" in ps:
            raise SpecError("取片缺口只能指定 edge 或 corner 其中一种位置")
        if corner is not None and offset != 0:
            raise SpecError("角部取片缺口不使用 offset; inset 可沿 X/Y 两方向向内移动")
        for cx, cy, ang in centers:
            pcx, pcy = _pick_center(cx, cy, ang, base_window, edge, offset, inset, corner)
            out.append(("circle", pcx, pcy, d / 2.0))
    return out


# --------------------------------------------------------------------------
# 渲染 / 校验
# --------------------------------------------------------------------------


def render(parts, prefix_mode):
    dxf = Dxf()
    seen_ito = set()
    seen_mark = set()
    for part in parts:
        L = part.layers(prefix=part.id + "_" if prefix_mode else "")
        if part.outline is not None:
            dxf.shape(L["outline"], part.outline)
        for h in part.outline_extra:
            dxf.shape(L["outline"], h)
        for h in part.holes:
            dxf.shape(L["holes"], h)
        for w in part.window if part.window_cuts is None else part.window_cuts:
            dxf.shape(L["window"], w)
        if part.window_cuts is None:
            for k in part.pick:
                dxf.shape(L["pick"], k)
        for t in part.tooling:
            dxf.shape(L["tooling"], t)
        for r in part.reference:
            dxf.shape(L["reference"], r)
        if part.ito_effective is not None:
            dxf.add_layer('ITO_EFFECTIVE')
            for region in part.ito_effective:
                key = json.dumps(region)
                if key not in seen_ito:
                    dxf.shape('ITO_EFFECTIVE', region)
                    seen_ito.add(key)
        for (x, y, h, s) in part.notes:
            dxf.text("NOTES", x, y, h, s)
        if part.marking_enabled:
            dxf.add_layer('LASER_MARK')
            for item in part.marking:
                for contour in item['contours']:
                    key = json.dumps(contour)
                    if key not in seen_mark:
                        dxf.shape('LASER_MARK', contour)
                        seen_mark.add(key)
    return dxf.dumps()


def cut_shapes(part):
    windows = part.window if part.window_cuts is None else part.window_cuts
    return part.holes + windows + (part.pick if part.window_cuts is None else []) + part.tooling


def validate_parts(parts, spec):
    """校验真正输出的闭合加工轮廓; 错误阻止 DXF 写出。"""
    seg = int(spec.get("arc_segments_per_90", 16))
    tolerance = float(spec.get("curve_tolerance_mm", 0.001))
    for part in parts:
        if part.outline is None:
            continue
        shape_geometry(part.outline, seg, tolerance)
        cuts = cut_shapes(part)
        geoms = [shape_geometry(s, seg, tolerance) for s in cuts]
        bad = sum(not shape_inside(s, part.outline) for s in cuts)
        if bad:
            part.validation_errors.append(f"{bad} 个加工轮廓超出部件真实外形")
        if part.bounds:
            bad = sum(not any(shape_inside(s, b) for b in part.bounds) for s in part.holes)
            if bad:
                part.validation_errors.append(f"{bad} 个功能孔超出定位开口/镀银区内缩区")
        conflicts = 0
        for i, a in enumerate(geoms):
            ax0, ay0, ax1, ay1 = a.bounds
            for j in range(i + 1, len(geoms)):
                b = geoms[j]
                bx0, by0, bx1, by1 = b.bounds
                if ax1 < bx0 - EPS or bx1 < ax0 - EPS or ay1 < by0 - EPS or by1 < ay0 - EPS:
                    continue
                if shape_distance(cuts[i], cuts[j], a, b) <= EPS:
                    conflicts += 1
        if conflicts:
            part.validation_errors.append(f"{conflicts} 对加工轮廓相交、重叠或相切, 请调整位置/中心距")


def analyze_part(part, spec):
    lines = [f"-- {part.caption} [{part.id}] --"]
    if part.outline is not None:
        x0, y0, x1, y1 = shape_bbox(part.outline)
        lines.append(f"   外形     : {x1 - x0:.3f} x {y1 - y0:.3f} mm")
    if part.handle_count:
        lines.append(f"   把手     : {part.handle_count} 个 (已合并外轮廓)")
    n_circ = sum(1 for h in part.holes if h[0] == "circle")
    lines.append(f"   功能孔   : {len(part.holes)} (圆孔 {n_circ} / 异形 {len(part.holes) - n_circ})")
    if part.window:
        wx0, wy0, wx1, wy1 = shape_bbox(part.window[0])
        lines.append(f"   定位开口     : {len(part.window)} 个, 单个 {wx1 - wx0:.3f} x {wy1 - wy0:.3f} mm")
    lines.append(f"   安装孔   : {len(part.tooling)}")
    if part.marking_enabled:
        lines.append(f"   打标文字 : {len(part.marking)} 段 (LASER_MARK独立矢量轮廓)")
    if part.pick:
        lines.append(f"   取片缺口   : {len(part.pick)} 个 (已合并至定位开口缺口)")
    cuts = cut_shapes(part)
    seg = int(spec.get("arc_segments_per_90", 16))
    tolerance = float(spec.get("curve_tolerance_mm", 0.001))
    geoms = [shape_geometry(s, seg, tolerance) for s in cuts]
    if part.outline is not None:
        oa = shape_area(part.outline)
        ha = unary_union(geoms).area if geoms else 0.0
        if oa:
            lines.append(f"   开孔占比 : {ha / oa * 100:.2f} %")

    min_web = float(spec.get("min_web_mm", 0.30))
    # 对曲线离散误差取保守下界, 不高估实际剩余筋宽。
    worst = None
    if geoms and part.outline is not None:
        outline = shape_geometry(part.outline, seg, tolerance)
        boundary = outline.boundary
        distances = []
        for s, g in zip(cuts, geoms):
            if part.outline[0] == "circle":
                _, bx, by, r = part.outline
                furthest = (math.hypot(s[1] - bx, s[2] - by) + s[3] if s[0] == "circle"
                            else max(math.hypot(x - bx, y - by) for x, y in s[1]))
                distances.append(max(0.0, r - furthest))
            elif s[0] == "circle":
                distances.append(max(0.0, Point(s[1], s[2]).distance(boundary) - s[3]))
            else:
                distances.append(g.distance(boundary))
        worst = min(distances)
        for i, a in enumerate(geoms):
            for j in range(i + 1, len(geoms)):
                worst = min(worst, shape_distance(cuts[i], cuts[j], a, geoms[j]))
        worst = max(0.0, worst - 2 * tolerance)
    if worst is not None:
        if worst < min_web:
            lines.append(f"   [警告] 最小筋宽 {worst:.3f} < {min_web} mm, 薄片易变形/断裂。")
        else:
            lines.append(f"   [OK] 最小筋宽 {worst:.3f} mm ≥ {min_web} mm。")

    if part.validation_errors:
        lines.extend(f"   [错误] {message}。" for message in part.validation_errors)
    else:
        lines.append("   [OK] 加工轮廓均在真实边界内, 且无相交/重叠。")
    return lines


def analyze(spec, parts, extra):
    out = ["=" * 64, f"掩模板: {spec.get('name', '(unnamed)')}   (kind={spec.get('kind', 'single')})", "=" * 64]
    out += extra
    for p in parts:
        if p.outline is None and not p.holes and p.window == [] and not p.tooling and not p.pick:
            continue  # 纯参考(如基片)不单独统计
        out += analyze_part(p, spec)
    out.append("-" * 64)
    out.append("注: 厚度/材料不在图纸标注, 下单时选择。单位 mm, DXF R12 (AC1009)。")
    out.append("=" * 64)
    return "\n".join(out)


def _extra_info(spec, kind):
    out = []
    if kind == "evaporation":
        w, h = outline_size(spec["substrate"])
        clr = float(spec.get("clearance_mm", 0.2))
        out.append(f"基片尺寸   : {w:.3f} x {h:.3f} mm")
        out.append(f"旷量       : {clr:.3f} mm (边长差, 单边 {clr / 2:.3f} mm)")
        out.append(f"骨架定位开口   : {w + clr:.3f} x {h + clr:.3f} mm / 个")
        ws = spec.get("skeleton", {}).get("windows")
        if ws and ws.get("type", "array") == "array":
            py = ws.get("pitch_y", ws.get("pitch_x"))
            out.append(f"图案阵列   : {ws.get('nx')} x {ws.get('ny')}, 中心距 {ws.get('pitch_x')} x {py} mm")
        elif ws:
            out.append(f"定位开口数量   : {len(ws['positions'])} 个(指定位置)")
        else:
            out.append("定位开口数量   : 1 个(居中)")
    if kind == "light_block":
        w, h = outline_size(spec["substrate"])
        out.append(f"基片/外形  : {w:.3f} x {h:.3f} mm")
        out.append(f"通光孔内缩 : 相对镀银区单边 {float(spec.get('aperture_inset_mm', 0.3)):.3f} mm")
    return out


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------

DEFAULT_SUFFIX = {
    "evaporation": {"assembly": "_装配图", "foil": "_掩模片", "skeleton": "_骨架"},
    "single": {"main": ""},
    "light_block": {"main": ""},
}


def generate(spec, outdir, single_out):
    if Point is None:
        raise SpecError("缺少 Shapely: 请在 skill 目录运行 python -m pip install -r requirements.txt")
    validate_spec(spec)
    seg = int(spec.get("arc_segments_per_90", 16))
    kind = spec.get("kind", "single")
    base = spec.get("name", "mask")

    if kind == "single":
        parts = build_single(spec, seg)
        files = [("main", render(parts, False))]
    elif kind == "evaporation":
        foil, frame, ref = build_evaporation(spec, seg)
        parts = [foil, frame, ref]
        files = [
            ("assembly", render([foil, frame, ref], True)),
            ("foil", render([foil], False)),
            ("skeleton", render([frame], False)),
        ]
    elif kind == "light_block":
        parts = build_light_block(spec, seg)
        files = [("main", render(parts, False))]
    else:
        raise SpecError(f"未知 kind: {kind}")

    validate_parts(parts, spec)
    overrides = spec.get("outputs", {})
    written = []
    for key, content in files:
        if key == "main" and single_out is not None:
            path = single_out
        else:
            fname = overrides.get(key) or f"{base}{DEFAULT_SUFFIX[kind].get(key, '')}.dxf"
            path = outdir / fname
        written.append((path, content))

    report = analyze(spec, parts, _extra_info(spec, kind))
    return report, [] if any(p.validation_errors for p in parts) else written


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="掩模板 DXF 生成器 (纯标准库)")
    ap.add_argument("spec", help="JSON 规格文件路径")
    ap.add_argument("-o", "--out", help="single/light_block 的输出 DXF 路径")
    ap.add_argument("--outdir", help="多文件输出目录(默认: 规格文件同级 out/)")
    ap.add_argument("--report", help="校验报告输出路径")
    ap.add_argument("--stdout", action="store_true", help="只打印校验报告, 不写 DXF")
    args = ap.parse_args(argv)

    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"找不到规格文件: {spec_path}", file=sys.stderr)
        return 2
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        print(f"规格文件 JSON 解析失败: {e}", file=sys.stderr)
        return 2
    spec["_base_dir"] = str(spec_path.parent)

    outdir = Path(args.outdir) if args.outdir else spec_path.parent / "out"
    single_out = Path(args.out) if args.out else None

    try:
        report, files = generate(spec, outdir, None if args.stdout else single_out)
    except (SpecError, ValueError, TypeError, KeyError, OverflowError) as e:
        print(f"规格错误: {e}", file=sys.stderr)
        return 2

    print(report)
    if not files:
        print("校验失败: 不写出 DXF; 如输出目录有旧图, 请勿把旧图作为本次结果。", file=sys.stderr)
    if not args.stdout:
        for path, content in files:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
            print(f"\n已写出 DXF: {path.resolve()}")

    report_path = Path(args.report) if args.report else (None if args.stdout else outdir / f"{spec.get('name', 'mask')}_report.txt")
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report + "\n", encoding="utf-8")
        print(f"已写出报告: {report_path.resolve()}")
    return 0 if files else 2


if __name__ == "__main__":
    raise SystemExit(main())
