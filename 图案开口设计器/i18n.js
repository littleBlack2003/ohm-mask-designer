/* UI i18n. Keyed by the Simplified-Chinese source string.
   Phase 1: static shell strings in index.html (data-free DOM walk).
   Phase 2/3 (JS-generated strings, backend messages) build on t(). */
'use strict';
(function () {
  const KEY = 'mask-ui-lang';
  const SUPPORTED = ['zh-Hans', 'en', 'zh-Hant', 'zh-TW'];
  const LABELS = { 'zh-Hans': '简体', 'en': 'English', 'zh-Hant': '繁體', 'zh-TW': '台灣' };

  let lang = 'zh-Hans';
  try { const s = localStorage.getItem(KEY); if (SUPPORTED.includes(s)) lang = s; } catch (e) {}

  // Only non-Simplified locales need entries; missing keys fall back to the source string.
  const DICT = {
    en: {
      '欧姆掩模设计器': 'Ohm Mask Designer', '本地工作台': 'Local workbench',
      '正在载入项目…': 'Loading project…', '项目': 'Project', '打开项目': 'Open project',
      '新建项目': 'New project', '另存副本': 'Save a copy', '尺寸设置': 'Size settings',
      '保存当前项目': 'Save current project', '保存': 'Save', '导出': 'Export',
      '生成文件': 'Generate files', '已载入': 'Loaded',
      '操作': 'Operate', '选择': 'Select', '平移画布': 'Pan canvas', '编辑内容': 'Edit content',
      '图案开口': 'Pattern apertures', 'ITO 区域': 'ITO area', '绘图': 'Draw',
      '矩形': 'Rectangle', '圆形': 'Circle', '长槽': 'Slot', '多边形': 'Polygon',
      '文字打标': 'Text marking', '添加文字': 'Add text',
      '选择后拖动，尺寸在右侧修改。': 'Select and drag; set sizes on the right.',
      '复制选中对象': 'Duplicate selection', '撤销': 'Undo', '重做': 'Redo', '删除': 'Delete',
      '开口列表': 'Opening list', '网格与吸附': 'Grid & snapping', '网格 / mm': 'Grid / mm',
      '吸附 / mm': 'Snap / mm', '启用吸附': 'Enable snapping', '导入图案': 'Import pattern',
      '项目参数': 'Project parameters',
      '骨架外框': 'Frame outline', '骨架': 'Frame', '单片图案': 'Single-cell pattern',
      '掩模片外框': 'Mask-foil outline', '掩模片': 'Mask foil', '外框打标': 'Outline marking',
      '打标（可选）': 'Marking (optional)', '总成预览（包含打标）': 'Assembly preview (incl. marking)',
      'mask（可选）': 'mask (optional)', 'mm　Y 轴向上': 'mm　Y up',
      '逐点绘制，双击或按 Enter 完成，Esc 取消。': 'Click point by point; double-click or Enter to finish, Esc to cancel.',
      '图案设计画布': 'Pattern design canvas', '拖动绘制，尺寸在右侧修改': 'Drag to draw; set sizes on the right',
      '缩小': 'Zoom out', '显示完整设计': 'Show full design', '适合窗口': 'Fit to window', '放大': 'Zoom in',
      '显示 10 mm 网格、中心轴和坐标数字': 'Show 10 mm grid, center axes, and coordinate numbers',
      '网格': 'Grid', '掩模': 'Mask', '开口': 'Opening', '打标': 'Marking',
      'A 活性区域': 'A Active region', 'C 公共电极': 'C Common electrode',
      '统计': 'Statistics', '正在统计…': 'Counting…', '面积计算': 'Area calc', '属性': 'Properties',
      '选择对象后修改参数。': 'Select an object to edit its parameters.', '阵列复制': 'Array copy',
      '列数': 'Columns', '行数': 'Rows', 'X 中心距 / mm': 'X pitch / mm', 'Y 中心距 / mm': 'Y pitch / mm',
      '复制阵列': 'Copy array', '全选': 'Select all', '居中': 'Center',
      '校验': 'Validation', '检查': 'Check', '自动检查': 'Auto-check', '查看结果': 'View results',
      '尚未绘制图案开口。': 'No pattern apertures drawn yet.',
      'Apache-2.0 开源项目': 'Apache-2.0 open-source project', '武汉欧姆科技有限公司': 'Wuhan Ohm Technology Co., Ltd.',
      '开孔数与活性区域有效面积不确定度': 'Opening count and active-region area uncertainty',
      '关闭面积统计': 'Close area statistics', '关闭': 'Close',
      '误差输入方式': 'Error input mode', '±公差（矩形分布）': '± tolerance (rectangular)',
      '标准不确定度（1σ）': 'Standard uncertainty (1σ)', '图案尺寸误差 / mm': 'Pattern size error / mm',
      'ITO尺寸误差 / mm': 'ITO size error / mm', '相对定位 X 误差 / mm': 'Relative positioning X error / mm',
      '相对定位 Y 误差 / mm': 'Relative positioning Y error / mm', '计算说明': 'Calculation notes',
      '计算活性区域面积不确定度': 'Compute active-region area uncertainty', '导出结果 CSV': 'Export result CSV',
      '点击计算，查看每个活性区域的结果。': 'Click Compute to see each active region\u2019s result.',
      '关闭尺寸设置': 'Close size settings', '尺寸设置页面': 'Size settings pages',
      '多个把手、多个取片缺口、自定义定位开口等复杂结构可在这里编辑。': 'Complex structures such as multiple handles, multiple pick notches, and custom positioning openings can be edited here.',
      '高级几何配置 JSON': 'Advanced geometry config JSON', '应用项目设置': 'Apply project settings',
      '恢复当前设置': 'Reset to current settings', '项目列表': 'Project list', '关闭项目列表': 'Close project list',
      '导入完整项目 JSON': 'Import full project JSON',
      '打开其他项目之前会保存当前项目。各项目使用独立的草稿和加工目录。': 'The current project is saved before opening another. Each project uses its own draft and manufacturing directory.',
      '保存并结束本地工作台': 'Save and shut down the local workbench', '创建项目': 'Create project',
      '取消创建项目': 'Cancel project creation', '取消': 'Cancel', '项目名称': 'Project name',
      '初始内容': 'Initial content', '沿用板件参数，清空图案': 'Reuse panel dimensions, clear pattern',
      '复制当前项目': 'Copy current project', '创建并打开': 'Create and open'
    },
    'zh-Hant': {
      '本地工作台': '本地工作檯', '正在载入项目…': '正在載入項目…', '项目': '項目', '打开项目': '打開項目',
      '新建项目': '新建項目', '另存副本': '另存副本', '尺寸设置': '尺寸設置', '保存当前项目': '保存當前項目',
      '保存': '保存', '导出': '導出', '生成文件': '生成文件', '已载入': '已載入',
      '操作': '操作', '选择': '選擇', '平移画布': '平移畫布', '编辑内容': '編輯內容',
      '图案开口': '圖案開口', '绘图': '繪圖', '矩形': '矩形', '圆形': '圓形', '长槽': '長槽',
      '多边形': '多邊形', '文字打标': '文字打標', '添加文字': '添加文字',
      '选择后拖动，尺寸在右侧修改。': '選擇後拖動，尺寸在右側修改。', '复制选中对象': '複製選中對象',
      '撤销': '撤銷', '重做': '重做', '删除': '刪除', '开口列表': '開口列表', '网格与吸附': '網格與吸附',
      '网格 / mm': '網格 / mm', '吸附 / mm': '吸附 / mm', '启用吸附': '啟用吸附', '导入图案': '導入圖案',
      '项目参数': '項目參數', '骨架外框': '骨架外框', '骨架': '骨架', '单片图案': '單片圖案',
      '掩模片外框': '掩模片外框', '掩模片': '掩模片', '外框打标': '外框打標', '打标（可选）': '打標（可選）',
      '总成预览（包含打标）': '總成預覽（包含打標）', 'mask（可选）': 'mask（可選）', 'mm　Y 轴向上': 'mm　Y 軸向上',
      '逐点绘制，双击或按 Enter 完成，Esc 取消。': '逐點繪製，雙擊或按 Enter 完成，Esc 取消。',
      '图案设计画布': '圖案設計畫布', '拖动绘制，尺寸在右侧修改': '拖動繪製，尺寸在右側修改',
      '缩小': '縮小', '显示完整设计': '顯示完整設計', '适合窗口': '適合窗口', '放大': '放大',
      '显示 10 mm 网格、中心轴和坐标数字': '顯示 10 mm 網格、中心軸和坐標數字', '网格': '網格',
      '掩模': '掩模', '开口': '開口', '打标': '打標', 'A 活性区域': 'A 活性區域', 'C 公共电极': 'C 公共電極',
      '统计': '統計', '正在统计…': '正在統計…', '面积计算': '面積計算', '属性': '屬性',
      '选择对象后修改参数。': '選擇對象後修改參數。', '阵列复制': '陣列複製', '列数': '列數', '行数': '行數',
      'X 中心距 / mm': 'X 中心距 / mm', 'Y 中心距 / mm': 'Y 中心距 / mm', '复制阵列': '複製陣列',
      '全选': '全選', '居中': '居中', '校验': '校驗', '检查': '檢查', '自动检查': '自動檢查',
      '查看结果': '查看結果', '尚未绘制图案开口。': '尚未繪製圖案開口。',
      'Apache-2.0 开源项目': 'Apache-2.0 開源項目', '武汉欧姆科技有限公司': '武漢歐姆科技有限公司',
      '开孔数与活性区域有效面积不确定度': '開孔數與活性區域有效面積不確定度',
      '关闭面积统计': '關閉面積統計', '关闭': '關閉', '误差输入方式': '誤差輸入方式',
      '±公差（矩形分布）': '±公差（矩形分布）', '标准不确定度（1σ）': '標準不確定度（1σ）',
      '图案尺寸误差 / mm': '圖案尺寸誤差 / mm', 'ITO尺寸误差 / mm': 'ITO尺寸誤差 / mm',
      '相对定位 X 误差 / mm': '相對定位 X 誤差 / mm', '相对定位 Y 误差 / mm': '相對定位 Y 誤差 / mm',
      '计算说明': '計算說明', '计算活性区域面积不确定度': '計算活性區域面積不確定度',
      '导出结果 CSV': '導出結果 CSV', '点击计算，查看每个活性区域的结果。': '點擊計算，查看每個活性區域的結果。',
      '关闭尺寸设置': '關閉尺寸設置', '尺寸设置页面': '尺寸設置頁面',
      '多个把手、多个取片缺口、自定义定位开口等复杂结构可在这里编辑。': '多個把手、多個取片缺口、自定義定位開口等複雜結構可在這裡編輯。',
      '高级几何配置 JSON': '高級幾何配置 JSON', '应用项目设置': '應用項目設置', '恢复当前设置': '恢復當前設置',
      '项目列表': '項目列表', '关闭项目列表': '關閉項目列表', '导入完整项目 JSON': '導入完整項目 JSON',
      '打开其他项目之前会保存当前项目。各项目使用独立的草稿和加工目录。': '打開其他項目之前會保存當前項目。各項目使用獨立的草稿和加工目錄。',
      '保存并结束本地工作台': '保存並結束本地工作檯', '创建项目': '創建項目', '取消创建项目': '取消創建項目',
      '取消': '取消', '项目名称': '項目名稱', '初始内容': '初始內容',
      '沿用板件参数，清空图案': '沿用板件參數，清空圖案', '复制当前项目': '複製當前項目', '创建并打开': '創建並打開'
    },
    'zh-TW': {
      '本地工作台': '本機工作台', '正在载入项目…': '正在載入專案…', '项目': '專案', '打开项目': '開啟專案',
      '新建项目': '新建專案', '另存副本': '另存副本', '尺寸设置': '尺寸設定', '保存当前项目': '儲存目前專案',
      '保存': '儲存', '导出': '匯出', '生成文件': '產生檔案', '已载入': '已載入',
      '操作': '操作', '选择': '選取', '平移画布': '平移畫布', '编辑内容': '編輯內容',
      '图案开口': '圖案開口', '绘图': '繪圖', '矩形': '矩形', '圆形': '圓形', '长槽': '長槽',
      '多边形': '多邊形', '文字打标': '文字打標', '添加文字': '新增文字',
      '选择后拖动，尺寸在右侧修改。': '選取後拖曳，尺寸在右側修改。', '复制选中对象': '複製選取物件',
      '撤销': '復原', '重做': '重做', '删除': '刪除', '开口列表': '開口清單', '网格与吸附': '網格與吸附',
      '网格 / mm': '網格 / mm', '吸附 / mm': '吸附 / mm', '启用吸附': '啟用吸附', '导入图案': '匯入圖案',
      '项目参数': '專案參數', '骨架外框': '骨架外框', '骨架': '骨架', '单片图案': '單片圖案',
      '掩模片外框': '掩模片外框', '掩模片': '掩模片', '外框打标': '外框打標', '打标（可选）': '打標（選用）',
      '总成预览（包含打标）': '總成預覽（含打標）', 'mask（可选）': 'mask（選用）', 'mm　Y 轴向上': 'mm　Y 軸向上',
      '逐点绘制，双击或按 Enter 完成，Esc 取消。': '逐點繪製，按兩下或按 Enter 完成，Esc 取消。',
      '图案设计画布': '圖案設計畫布', '拖动绘制，尺寸在右侧修改': '拖曳繪製，尺寸在右側修改',
      '缩小': '縮小', '显示完整设计': '顯示完整設計', '适合窗口': '符合視窗', '放大': '放大',
      '显示 10 mm 网格、中心轴和坐标数字': '顯示 10 mm 網格、中心軸和座標數字', '网格': '網格',
      '掩模': '掩模', '开口': '開口', '打标': '打標', 'A 活性区域': 'A 活性區域', 'C 公共电极': 'C 公共電極',
      '统计': '統計', '正在统计…': '正在統計…', '面积计算': '面積計算', '属性': '屬性',
      '选择对象后修改参数。': '選取物件後修改參數。', '阵列复制': '陣列複製', '列数': '欄數', '行数': '列數',
      'X 中心距 / mm': 'X 中心距 / mm', 'Y 中心距 / mm': 'Y 中心距 / mm', '复制阵列': '複製陣列',
      '全选': '全選', '居中': '置中', '校验': '驗證', '检查': '檢查', '自动检查': '自動檢查',
      '查看结果': '查看結果', '尚未绘制图案开口。': '尚未繪製圖案開口。',
      'Apache-2.0 开源项目': 'Apache-2.0 開源專案', '武汉欧姆科技有限公司': '武漢歐姆科技有限公司',
      '开孔数与活性区域有效面积不确定度': '開孔數與活性區域有效面積不確定度',
      '关闭面积统计': '關閉面積統計', '关闭': '關閉', '误差输入方式': '誤差輸入方式',
      '±公差（矩形分布）': '±公差（矩形分布）', '标准不确定度（1σ）': '標準不確定度（1σ）',
      '图案尺寸误差 / mm': '圖案尺寸誤差 / mm', 'ITO尺寸误差 / mm': 'ITO 尺寸誤差 / mm',
      '相对定位 X 误差 / mm': '相對定位 X 誤差 / mm', '相对定位 Y 误差 / mm': '相對定位 Y 誤差 / mm',
      '计算说明': '計算說明', '计算活性区域面积不确定度': '計算活性區域面積不確定度',
      '导出结果 CSV': '匯出結果 CSV', '点击计算，查看每个活性区域的结果。': '點選計算，查看每個活性區域的結果。',
      '关闭尺寸设置': '關閉尺寸設定', '尺寸设置页面': '尺寸設定頁面',
      '多个把手、多个取片缺口、自定义定位开口等复杂结构可在这里编辑。': '多個把手、多個取片缺口、自訂定位開口等複雜結構可在此編輯。',
      '高级几何配置 JSON': '高級幾何設定 JSON', '应用项目设置': '套用專案設定', '恢复当前设置': '還原目前設定',
      '项目列表': '專案清單', '关闭项目列表': '關閉專案清單', '导入完整项目 JSON': '匯入完整專案 JSON',
      '打开其他项目之前会保存当前项目。各项目使用独立的草稿和加工目录。': '開啟其他專案前會儲存目前專案。各專案使用獨立的草稿和加工目錄。',
      '保存并结束本地工作台': '儲存並結束本機工作台', '创建项目': '建立專案', '取消创建项目': '取消建立專案',
      '取消': '取消', '项目名称': '專案名稱', '初始内容': '初始內容',
      '沿用板件参数，清空图案': '沿用板件參數，清空圖案', '复制当前项目': '複製目前專案', '创建并打开': '建立並開啟'
    }
  };

  function t(s) {
    if (lang === 'zh-Hans' || s == null) return s;
    const d = DICT[lang];
    return (d && d[s]) || s;
  }

  // Translate static DOM once at load. Language changes reload the page, so no restore is needed.
  function apply(root) {
    if (lang === 'zh-Hans') return;
    root = root || document;
    const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    let n; while ((n = tw.nextNode())) nodes.push(n);
    for (const node of nodes) {
      const raw = node.nodeValue, key = raw && raw.trim();
      if (!key) continue;
      const tr = DICT[lang][key];
      if (tr && tr !== key) node.nodeValue = raw.replace(key, tr);
    }
    for (const attr of ['title', 'aria-label', 'placeholder']) {
      for (const el of root.querySelectorAll('[' + attr + ']')) {
        const tr = DICT[lang][el.getAttribute(attr)];
        if (tr) el.setAttribute(attr, tr);
      }
    }
    if (root === document) document.documentElement.lang = lang;
  }

  function setLang(next) {
    if (!SUPPORTED.includes(next) || next === lang) return;
    try { localStorage.setItem(KEY, next); } catch (e) {}
    location.reload();
  }

  function mountSwitcher() {
    const host = document.querySelector('.header-actions');
    if (!host || document.getElementById('ui-lang')) return;
    const wrap = document.createElement('select');
    wrap.id = 'ui-lang'; wrap.setAttribute('aria-label', 'UI language');
    wrap.style.width = 'auto';
    for (const code of SUPPORTED) {
      const o = document.createElement('option');
      o.value = code; o.textContent = LABELS[code]; if (code === lang) o.selected = true;
      wrap.appendChild(o);
    }
    wrap.onchange = () => setLang(wrap.value);
    host.insertBefore(wrap, host.firstChild);
  }

  function getLang() { return lang; }

  window.I18N = { t, apply, setLang, getLang, SUPPORTED, LABELS };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => { mountSwitcher(); apply(document); });
  else { mountSwitcher(); apply(document); }
})();
