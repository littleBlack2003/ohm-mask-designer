/* Browser-only API adapter for the GitHub Pages edition. */
(() => {
  const staticMode = location.protocol === 'file:' ||
    location.hostname.endsWith('github.io') ||
    new URLSearchParams(location.search).has('static');
  if (!staticMode) return;

  window.OHM_STATIC_MODE = true;
  const nativeFetch = window.fetch.bind(window);
  const assetBase = new URL('.', location.href);
  const storeKey = 'ohm-mask-designer-web-projects-v2';
  const pyodideBase = 'https://cdn.jsdelivr.net/pyodide/v0.28.3/full/';
  const fontUrl = 'https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/Variable/TTF/Subset/NotoSansSC-VF.ttf';
  let enginePromise;
  let storePromise;
  let generatedUrls = [];

  const jsonResponse = (body, status = 200) => new Response(JSON.stringify(body), {
    status,
    headers: {'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store'}
  });
  const clone = value => JSON.parse(JSON.stringify(value));
  const uuid = () => crypto.randomUUID ? crypto.randomUUID() :
    'web-' + Date.now().toString(36) + Math.random().toString(36).slice(2);

  function setLoading(text) {
    const apply = () => {
      const mode = document.getElementById('app-mode');
      const name = document.getElementById('project-name');
      if (mode) mode.textContent = '纯网页版';
      if (name) name.textContent = text;
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', apply, {once: true});
    else apply();
  }

  async function loadScript(src) {
    await new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = src;
      script.onload = resolve;
      script.onerror = () => reject(new Error('无法加载浏览器计算运行时，请检查网络连接'));
      document.head.appendChild(script);
    });
  }

  async function textAsset(name) {
    const response = await nativeFetch(new URL(name, assetBase), {cache: 'no-cache'});
    if (!response.ok) throw new Error(`无法加载 ${name}`);
    return response.text();
  }

  async function ensureEngine() {
    if (enginePromise) return enginePromise;
    enginePromise = (async () => {
      setLoading('正在加载浏览器几何引擎，首次打开可能需要约一分钟…');
      if (!window.loadPyodide) await loadScript(new URL('pyodide.js', assetBase));
      const pyodide = await window.loadPyodide({indexURL: pyodideBase});
      await pyodide.loadPackage(['shapely', 'matplotlib']);
      const names = ['make_mask.py', 'manufacturing.py', 'area_statistics.py', 'web_bridge.py'];
      const sources = await Promise.all(names.map(name => textAsset(name)));
      names.forEach((name, index) => pyodide.FS.writeFile(`/home/pyodide/${name}`, sources[index], {encoding: 'utf8'}));
      try {
        const fontResponse = await nativeFetch(fontUrl, {cache: 'force-cache'});
        if (fontResponse.ok) {
          const bytes = new Uint8Array(await fontResponse.arrayBuffer());
          pyodide.FS.writeFile('/home/pyodide/NotoSansSC.ttf', bytes);
          pyodide.runPython("import os; os.environ['OHM_MASK_FONT']='/home/pyodide/NotoSansSC.ttf'");
        }
      } catch (error) {
        console.warn('中文矢量字体加载失败，将使用浏览器计算环境的后备字体。', error);
      }
      pyodide.runPython('from web_bridge import call as web_call, set_current_spec as web_set_spec');
      const call = pyodide.globals.get('web_call');
      const setSpec = pyodide.globals.get('web_set_spec');
      setLoading('几何引擎已就绪，正在载入项目…');
      return {pyodide, call, setSpec};
    })().catch(error => {
      enginePromise = null;
      throw error;
    });
    return enginePromise;
  }

  async function loadStore() {
    if (storePromise) return storePromise;
    storePromise = (async () => {
      try {
        const saved = JSON.parse(localStorage.getItem(storeKey));
        if (saved && saved.current && saved.projects?.[saved.current]) return saved;
      } catch (_) {}
      const response = await nativeFetch(new URL('default_project.json', assetBase), {cache: 'no-cache'});
      if (!response.ok) throw new Error('无法加载默认项目');
      const spec = await response.json();
      const id = uuid();
      const store = {current: id, projects: {[id]: {id, spec, modified: Date.now()}}};
      localStorage.setItem(storeKey, JSON.stringify(store));
      return store;
    })();
    return storePromise;
  }

  function saveStore(store) {
    try {
      localStorage.setItem(storeKey, JSON.stringify(store));
    } catch (error) {
      throw new Error('浏览器本地存储空间不足，请先导出项目JSON备份');
    }
  }

  async function pythonCall(action, body, spec) {
    const engine = await ensureEngine();
    engine.setSpec(JSON.stringify(spec));
    return JSON.parse(engine.call(action, JSON.stringify(body || {})));
  }

  function projectCount(spec) {
    const windows = spec?.skeleton?.windows || {};
    if (windows.type === 'array') return Number(windows.nx || 1) * Number(windows.ny || 1);
    if (windows.type === 'list') return windows.positions?.length || 0;
    return 0;
  }

  function bodyFromRequest(init) {
    if (!init?.body) return {};
    if (typeof init.body === 'string') return JSON.parse(init.body);
    throw new Error('纯网页版仅接受JSON请求');
  }

  function bytesFromBase64(value) {
    const binary = atob(value);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes;
  }

  function mimeFor(name) {
    if (name.endsWith('.zip')) return 'application/zip';
    if (name.endsWith('.svg')) return 'image/svg+xml;charset=utf-8';
    if (name.endsWith('.json')) return 'application/json;charset=utf-8';
    if (name.endsWith('.csv')) return 'text/csv;charset=utf-8';
    if (name.endsWith('.dxf')) return 'application/dxf';
    return 'text/plain;charset=utf-8';
  }

  function attachDownloads(result) {
    generatedUrls.forEach(URL.revokeObjectURL);
    generatedUrls = [];
    const urls = {};
    for (const item of result._blobs || []) {
      const url = URL.createObjectURL(new Blob([bytesFromBase64(item.base64)], {type: mimeFor(item.name)}));
      generatedUrls.push(url);
      urls[item.name] = url;
    }
    delete result._blobs;
    result.file_urls = urls;
  }

  async function manageProject(route, body, store) {
    if (body.project_key && body.project_key !== store.current) throw new Error('当前项目已经切换，请刷新本页');
    if (route === 'project-open') {
      if (!store.projects[body.id]) throw new Error('项目不存在，请重新打开项目列表');
      store.current = body.id;
      saveStore(store);
      return {ok: true, project_key: body.id, path: '浏览器本地存储'};
    }
    const current = store.projects[store.current];
    let spec = route === 'project-import' ? clone(body.spec) : clone(current.spec);
    if (!spec || typeof spec !== 'object') throw new Error('请导入完整项目JSON');
    if (route === 'project-new') {
      spec.foil.cell = [];
      delete spec.ito_effective;
      delete spec.laser_marking;
    }
    spec.name = String(body.name || spec.name || '').trim();
    delete spec.outputs;
    delete spec._base_dir;
    if ([...Object.values(store.projects)].some(item => item.spec.name.toLocaleLowerCase() === spec.name.toLocaleLowerCase())) {
      throw new Error('已有同名项目，请修改名称；不会覆盖已有项目');
    }
    const checked = await pythonCall('project', {}, spec);
    if (checked.status !== 200) throw new Error(checked.body.error);
    const id = uuid();
    store.projects[id] = {id, spec, modified: Date.now()};
    store.current = id;
    saveStore(store);
    return {ok: true, project_key: id, path: '浏览器本地存储'};
  }

  async function handleApi(path, method, init) {
    const store = await loadStore();
    const current = store.projects[store.current];
    if (method === 'GET' && path === '/api/projects') {
      const projects = Object.values(store.projects)
        .sort((a, b) => b.modified - a.modified)
        .map(item => ({
          id: item.id,
          name: item.spec.name,
          path: '浏览器本地存储',
          current: item.id === store.current,
          modified: item.modified,
          cells: projectCount(item.spec)
        }));
      return jsonResponse({ok: true, projects, library_dir: '浏览器本地存储（建议定期导出JSON备份）'});
    }
    if (method === 'GET' && path === '/api/project') {
      const result = await pythonCall('project', {}, current.spec);
      result.body.project_key = store.current;
      result.body.project_dir = '浏览器本地存储';
      result.body.project_file = '浏览器本地存储';
      return jsonResponse(result.body, result.status);
    }
    if (method !== 'POST') return jsonResponse({error: '操作不存在'}, 404);
    const body = bodyFromRequest(init);
    const route = path.replace(/^\/api\//, '');
    if (['project-new', 'project-copy', 'project-open', 'project-import'].includes(route)) {
      try {
        return jsonResponse(await manageProject(route, body, store));
      } catch (error) {
        return jsonResponse({error: error.message}, 422);
      }
    }
    if (route === 'shutdown') return jsonResponse({error: '纯网页版无需结束本地服务'}, 422);
    if (body.project_key && body.project_key !== store.current) {
      return jsonResponse({error: '当前项目已经切换，请刷新本页'}, 422);
    }
    const result = await pythonCall(route, body, current.spec);
    if (result.body._spec) {
      current.spec = result.body._spec;
      current.modified = Date.now();
      delete result.body._spec;
      saveStore(store);
    }
    if (result.body._blobs) attachDownloads(result.body);
    return jsonResponse(result.body, result.status);
  }

  window.fetch = async (input, init = {}) => {
    const requestUrl = typeof input === 'string' ? input : input.url;
    const url = new URL(requestUrl, location.href);
    if (url.origin === location.origin && url.pathname.startsWith('/api/')) {
      try {
        const method = String(init.method || (typeof input === 'string' ? 'GET' : input.method) || 'GET').toUpperCase();
        return await handleApi(url.pathname, method, init);
      } catch (error) {
        console.error(error);
        return jsonResponse({error: error.message || String(error)}, 500);
      }
    }
    return nativeFetch(input, init);
  };
})();

