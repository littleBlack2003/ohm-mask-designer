"""Double-click launcher: start a hidden local server, then open the editor."""
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen
import webbrowser

ROOT=Path(__file__).resolve().parent
URL='http://127.0.0.1:8765'

def ready():
    try:
        with urlopen(URL+'/api/project',timeout=1) as response:
            return 'frame' in json.load(response)
    except (OSError,ValueError):return False

if not ready():
    with (ROOT/'server.log').open('ab') as log:
        process=subprocess.Popen([sys.executable,'-X','utf8','-B',str(ROOT/'server.py')],
            cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
    for attempt in range(30):
        if ready():break
        if process.poll() is not None:raise RuntimeError('启动失败，请查看 server.log（可能端口8765已被占用）')
        time.sleep(.2)
    else:raise RuntimeError('启动超时，请查看 server.log')
webbrowser.open(URL)
