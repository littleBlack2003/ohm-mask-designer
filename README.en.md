# Ohm Mask Designer

**English** | [简体中文](README.md) | [繁體中文](README.zh-Hant.md)

<p align="center">
  <img src="assets/ohm-logo.svg" alt="Wuhan Ohm Technology Co., Ltd. Logo" width="520">
</p>

Ohm Mask Designer is a local browser application for evaporation-mask assembly design, pattern-aperture editing, ITO effective-area analysis, geometry validation, and manufacturing-file export, starting from the substrate, mask-foil, and frame dimensions.

Pure web edition: [https://littleblack2003.github.io/ohm-mask-designer/](https://littleblack2003.github.io/ohm-mask-designer/)

Windows portable build: [download the latest release](https://github.com/littleBlack2003/ohm-mask-designer/releases/latest). Unzip it and double-click “欧姆掩模设计器.exe”; no Python or AutoCAD is required.

The web edition runs the same Python/Shapely geometry algorithms as the desktop app inside the browser via Pyodide. Projects are stored in the current browser’s local storage; export the project JSON regularly as a backup. Generated DXF, SVG, CSV, and ZIP files download directly to your machine. The first launch requires an internet connection to load the browser compute runtime and a Chinese vector font.

## Features

- Set rectangular or circular substrate, mask-foil, and frame dimensions separately.
- The mask foil can follow the frame outline, or use an independent rectangular or circular outline.
- Workspaces are arranged as “Frame, Single-cell pattern, Mask foil, Marking, Assembly preview, mask”; each page shows only the tools needed for the current task.
- The single-cell pattern shows an adjustable internal grid of the substrate; other workspaces can toggle an on-top 10 mm engineering grid, center axes, and coordinate numbers via the button at the bottom-right of the canvas (off by default).
- The Frame page sets the outer outline, handle, total clearance, and substrate positioning-opening array directly; the canvas shows the actual manufacturing contour.
- Size settings are edited as tabs: Basic info, Substrate, Frame, Positioning openings & pattern array, Mask foil, Test mask, and Advanced.
- Configure the pattern array, positioning openings, handle, pick notches, and optional mounting holes.
- Draw rectangular, circular, slot, and polygon pattern apertures, with move, array, and center operations.
- Tag pattern apertures as active region, common electrode region, or untagged; count and export by role.
- Edit the ITO effective area and laser-marking text layers independently.
- Count openings; compute effective area and analytical area uncertainty only for active regions.
- Determine the active effective area as “active-region opening ∩ ITO effective area” and auto-generate a test light-blocking mask drawing; through-holes are shrunk to 80% of the edge length and snapped to 0.1 mm, strictly inside the active effective area.
- Validate outline boundaries, overlaps, minimum web width, and mask-foil coverage of positioning openings.
- Export mask-foil and frame cutting DXF, laser-marking DXF, assembly reference, SVG preview, CSV, JSON, and a manufacturing package.

## Run from source

Requires Python 3.10 or later.

```powershell
python -m pip install -r requirements.txt
python -X utf8 -B "图案开口设计器/launch.py"
```

Windows users can also double-click `图案开口设计器/启动设计器.cmd`. The designer starts a local service and opens `http://127.0.0.1:8765/`; AutoCAD is not required.

## Tests

```powershell
python -X utf8 -B -m unittest discover -s "图案开口设计器" -p "test_*.py"
python -X utf8 -B -m unittest discover -s "ohm-mask-skill/tests" -p "test_*.py"
```

## Layout

- `图案开口设计器/`: browser GUI, project management, statistics, validation, and manufacturing export.
- `ohm-mask-skill/`: Codex Skill, geometry-generation scripts, format specification, and examples.
- `默认25mm基底/`: reproducible example project configuration.

See [`图案开口设计器/使用说明.md`](图案开口设计器/使用说明.md) for detailed usage.

## License & Contact

This project is initiated and maintained by **Wuhan Ohm Technology Co., Ltd.** and released under the [Apache License 2.0](LICENSE) with no additional restrictions. Use, modification, distribution, and contributions are welcome. Please read the [contributing guide](CONTRIBUTING.md) before submitting code.

- GitHub: <https://github.com/littleBlack2003/ohm-mask-designer>
- Email: <dasohm@163.com>

Wuhan Ohm Technology Co., Ltd. provides mask fabrication services; customers who bring complete manufacturing drawings can get discounted quotes. See the [mask fabrication service](SERVICE.md) for details.
