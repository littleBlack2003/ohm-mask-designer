# Build an offline browser application. No Qt/desktop window dependency.
from pathlib import Path
root=Path(SPECPATH)
repo=root.parent
datas=[(str(root/'index.html'),'Ohm Mask Designer'),
       (str(root/'project-ui.js'),'Ohm Mask Designer'),
       (str(root/'canvas-controls.js'),'Ohm Mask Designer'),
       (str(root/'static-api.js'),'Ohm Mask Designer'),
       (str(root/'pyodide.js'),'Ohm Mask Designer'),
       (str(root/'i18n.js'),'Ohm Mask Designer'),
       (str(root/'default_project.json'),'Ohm Mask Designer'),
       (str(repo/'ohm-mask-skill/scripts/make_mask.py'),'ohm-mask-skill/scripts')]
a=Analysis([str(root/'browser_app.py')],pathex=[str(root)],datas=datas,
           hiddenimports=['matplotlib.font_manager','matplotlib.textpath'],
           hookspath=[],hooksconfig={'matplotlib':{'backends':['Agg']}},
           excludes=['PySide6','PyQt5','PyQt6','tkinter','IPython','pytest'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='欧姆掩模设计器',
        debug=False,strip=False,upx=False,console=False)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='欧姆掩模设计器')
