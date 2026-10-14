"""Pyodide bridge for the static GitHub Pages edition."""
import base64
import copy
import json
import math
import re

import area_statistics as area_stats
import make_mask as m
import manufacturing


APP_VERSION = "0.7.1 Web"
CURRENT_SPEC = {}


def set_current_spec(text):
    global CURRENT_SPEC
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("项目数据须为JSON对象")
    CURRENT_SPEC = value


def validate_project(spec):
    if spec.get("kind") != "evaporation":
        raise ValueError("本版本支持蒸镀掩模总成项目")
    name = spec.get("name", "")
    if (
        not isinstance(name, str)
        or not name.strip()
        or len(name) > 100
        or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
        or name.endswith((".", " "))
        or name in (".", "..")
    ):
        raise ValueError("项目名称须为1～100个字符，不能包含文件名保留字符")
    if name.upper().split(".")[0] in {
        "CON", "PRN", "AUX", "NUL",
        *[f"COM{i}" for i in range(1, 10)],
        *[f"LPT{i}" for i in range(1, 10)],
    }:
        raise ValueError("项目名称不能使用系统保留名称")
    m.validate_spec(spec)
    windows = spec["skeleton"].get("windows", {})
    if windows.get("type") == "array" and int(windows.get("nx", 1)) * int(windows.get("ny", 1)) > 400:
        raise ValueError("最多400个定位开口")
    if windows.get("type") == "list" and len(windows.get("positions", [])) > 400:
        raise ValueError("最多400个定位开口")
    layout = frame_geometry(spec)
    if len(layout["centers"]) > 400:
        raise ValueError("最多400个定位开口")
    outside = sum(not m.shape_inside(window, layout["foil_outline"]) for window in layout["windows"])
    if outside:
        raise ValueError(f"掩模片外形未覆盖全部定位开口：有{outside}个定位开口超出掩模片")
    frame = m.Part("FRAME", "骨架")
    frame.outline = layout["outline"]
    frame.window_cuts = layout["windows"]
    frame.tooling = layout["tooling"]
    foil = m.Part("FOIL", "掩模片")
    foil.outline = layout["foil_outline"]
    foil.tooling = layout["foil_tooling"]
    m.validate_parts([foil, frame], spec)
    errors = foil.validation_errors + frame.validation_errors
    if errors:
        raise ValueError("；".join(errors))


def frame_geometry(spec):
    skeleton = spec["skeleton"]
    segments = spec.get("arc_segments_per_90", 24)
    base = m.expand_outline(spec["substrate"], spec.get("clearance_mm", 0.2) / 2, segments)
    centers = m.window_centers(skeleton.get("windows"))
    windows = [m.transform_shape(base, *center) for center in centers]
    picks = m.build_pick_holes(skeleton.get("pick_hole"), base, centers)
    body = m.build_outline(skeleton["outline"], segments)
    outline = m.merged_outline(body, m.build_handle(skeleton.get("handle"), body), segments, 0.001)
    foil_spec = spec.get("foil", {})
    foil_custom = foil_spec.get("outline")
    foil_outline = m.build_outline(foil_custom, segments) if foil_custom else outline
    foil_tooling_base = foil_outline if foil_custom else body
    return {
        "outline": outline,
        "foil_outline": foil_outline,
        "windows": m.merge_window_cuts(windows, picks, segments, 0.001),
        "centers": centers,
        "tooling": m.build_frame_holes(skeleton["frame_holes"], body, "skeleton.frame_holes")
        if skeleton.get("frame_holes") else [],
        "foil_tooling": m.build_frame_holes(foil_spec["frame_holes"], foil_tooling_base, "foil.frame_holes")
        if foil_spec.get("frame_holes") else [],
        "test_mask": test_mask_geometry(spec),
    }


def test_mask_geometry(spec):
    config = spec.get("test_mask") if isinstance(spec.get("test_mask"), dict) else {}
    outline_spec = (config or {}).get("outline") or spec["substrate"]
    result = {
        "enabled": (config or {}).get("enabled", True) is not False,
        "outline": m.build_outline(outline_spec, spec.get("arc_segments_per_90", 24)),
        "holes": [],
        "error": None,
    }
    try:
        part, _ = manufacturing.build_test_mask(spec, m, area_stats)
        if part:
            result.update(outline=part.outline, holes=part.holes)
    except (ValueError, m.SpecError) as exc:
        result["error"] = str(exc)
    return result


def prepare(body):
    features = body.get("features")
    if not isinstance(features, list) or len(features) > 80:
        raise m.SpecError("单格图案须为数组，最多80个图案对象")
    valid_region_roles = {"unassigned", "active", "common"}
    for feature in features:
        if not isinstance(feature, dict):
            raise m.SpecError("图案对象须为JSON对象")
        if feature.get("region_role", "unassigned") not in valid_region_roles:
            raise m.SpecError("图案开口区域用途须为 unassigned、active 或 common")
    spec = copy.deepcopy(CURRENT_SPEC)
    project_settings = body.get("project_settings")
    if project_settings is not None:
        if not isinstance(project_settings, dict):
            raise ValueError("项目设置须为对象")
        for key in (
            "name", "substrate", "skeleton", "test_mask", "clearance_mm", "min_web_mm",
            "arc_segments_per_90", "curve_tolerance_mm",
        ):
            if key in project_settings:
                spec[key] = copy.deepcopy(project_settings[key])
        if "foil" in project_settings:
            for key in ("per_window", "outline", "frame_holes"):
                spec["foil"].pop(key, None)
                if key in project_settings["foil"]:
                    spec["foil"][key] = copy.deepcopy(project_settings["foil"][key])
    validate_project(spec)
    uncertainty = body.get("uncertainty_settings")
    spec["uncertainty_settings"] = area_stats.settings(
        uncertainty if uncertainty is not None else spec.get("uncertainty_settings")
    )
    if "markings" in body:
        spec["laser_marking"] = body["markings"]
    if "ito_features" in body:
        ito_features = body["ito_features"]
        if not isinstance(ito_features, list) or len(ito_features) > 40:
            raise m.SpecError("ITO参考图案须为数组，最多40个区域对象")
        spec["ito_effective"] = {"features": ito_features}
    spec["foil"]["cell"] = features
    spec["foil"].pop("features", None)
    spec.pop("outputs", None)
    spec.pop("_base_dir", None)
    spec["_stage"] = "GUI图案设计" if features else "骨架已确定；单格图案待绘制"
    m.validate_spec(spec)
    expanded = sum(
        int(feature.get("nx", 1)) * int(feature.get("ny", 1))
        if feature.get("type") in ("rect_array", "circle_array") else 1
        for feature in features
    )
    repeats = len(m.window_centers(spec["skeleton"]["windows"])) if spec["foil"].get("per_window", True) else 1
    if expanded * repeats > 1600:
        raise m.SpecError("图案开口过多：总成最多1600个开口")
    shapes = m.build_features(features, "foil") if features else []
    if len(shapes) * repeats > 1600:
        raise m.SpecError("图案开口过多：总成最多1600个开口，请减少单格复制数量")
    for shape in shapes:
        m.shape_geometry(shape)
    m.build_ito_effective(spec, 24, [(0, 0, 0)])
    m.marking_preview(spec)
    return spec, shapes


def inspect_cell(spec, shapes):
    geometry = frame_geometry(spec)
    if shapes:
        foil, frame, _ = m.build_evaporation(spec, spec.get("arc_segments_per_90", 24))
        if spec["foil"].get("per_window", True):
            boundary = m.expand_outline(spec["substrate"], spec.get("clearance_mm", 0.2) / 2, 24)
            bad = sum(not m.shape_inside(shape, boundary) for shape in shapes)
            if bad:
                foil.validation_errors.append(f"{bad}个单格图案开口超出该格定位开口")
    else:
        frame = m.Part("FRAME", "骨架")
        frame.outline = geometry["outline"]
        frame.window_cuts = geometry["windows"]
        frame.tooling = geometry["tooling"]
        foil = m.Part("FOIL", "掩模片")
        foil.outline = geometry["foil_outline"]
        foil.tooling = geometry["foil_tooling"]
        m.attach_marking(spec, [foil, frame])
    m.validate_parts([foil, frame], spec)
    report = m.analyze(spec, [foil, frame], m._extra_info(spec, "evaporation"))
    if not shapes:
        report += "\n尚未绘制图案开口。"
    if "ito_effective" in spec:
        report += "\nITO有效区域为参考图层，不参与切割。"
    return report, not foil.validation_errors and not frame.validation_errors


def _encoded_files(files):
    result = []
    for name, content in files.items():
        raw = content if isinstance(content, bytes) else content.encode("utf-8")
        result.append({"name": name, "base64": base64.b64encode(raw).decode("ascii")})
    return result


def _run(action, body):
    if action == "project":
        validate_project(CURRENT_SPEC)
        return {
            "spec": CURRENT_SPEC,
            "frame": frame_geometry(CURRENT_SPEC),
            "project_dir": "浏览器本地存储",
            "desktop": False,
            "version": APP_VERSION,
            "can_shutdown": False,
            "project_file": "浏览器本地存储",
        }
    spec, shapes = prepare(body)
    if action == "statistics":
        return {"ok": True, "statistics": area_stats.calculate(spec, m, spec["uncertainty_settings"])}
    if action == "layout":
        return {"ok": True, "spec": spec, "frame": frame_geometry(spec)}
    report, valid = inspect_cell(spec, shapes)
    if action == "validate":
        return {
            "ok": valid,
            "report": report,
            "shapes": shapes,
            "mark_paths": m.marking_preview(spec),
            "statistics": area_stats.nominal(spec, m),
            "frame": frame_geometry(spec),
        }
    if action == "save":
        return {"ok": True, "valid": valid, "report": report, "path": "浏览器本地存储", "_spec": spec}
    if action == "generate":
        if not shapes:
            raise m.SpecError("请先绘制单格图案开口")
        if not valid:
            return {"_status": 422, "error": "几何校验未通过，未生成DXF", "report": report}
        report, files, result_spec = manufacturing.package(spec, m, area_stats)
        if not files:
            return {"_status": 422, "error": "几何校验未通过，未生成DXF", "report": report}
        return {
            "ok": True,
            "report": report,
            "files": list(files),
            "_blobs": _encoded_files(files),
            "_spec": result_spec,
            "path": "浏览器下载",
        }
    raise ValueError("操作不存在")


def call(action, body_text="{}"):
    try:
        body = json.loads(body_text or "{}")
        if not isinstance(body, dict):
            raise ValueError("请求须为JSON对象")
        result = _run(action, body)
        status = int(result.pop("_status", 200))
        return json.dumps({"status": status, "body": result}, ensure_ascii=False)
    except (m.SpecError, ValueError, TypeError, KeyError, OverflowError, OSError) as exc:
        return json.dumps({"status": 422, "body": {"error": str(exc)}}, ensure_ascii=False)

