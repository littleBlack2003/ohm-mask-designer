"""Backend output localisation (en / zh-Hant / zh-TW). Source language is zh-Hans.

Used by server.py and web_bridge.py to localise generated file names, error
messages and report text. Language comes from the request `lang` field.
"""
SUPPORTED = ('zh-Hans', 'en', 'zh-Hant', 'zh-TW')

# File-name segments (longest first at apply time).
SEG = {
    'en': {
        '测试遮光掩模': 'test-mask', '含ITO参考': 'with-ITO-reference', '几何校验报告': 'geometry-validation-report',
        '有效面积不确定度': 'area-uncertainty', '面积计算说明': 'area-calculation-notes', '完整设计参数': 'full-design-params',
        '加工文件包': 'manufacturing-package', '装配参考': 'assembly-reference', '装配预览': 'assembly-preview',
        '激光打标': 'laser-marking', '加工说明': 'manufacturing-notes', '生成说明': 'generation-notes',
        '校验报告': 'validation-report', '切割': 'cutting', '掩模片': 'foil', '骨架': 'frame',
    },
    'zh-Hant': {
        '测试遮光掩模': '測試遮光掩模', '含ITO参考': '含ITO參考', '几何校验报告': '幾何校驗報告',
        '有效面积不确定度': '有效面積不確定度', '面积计算说明': '面積計算說明', '完整设计参数': '完整設計參數',
        '加工文件包': '加工文件包', '装配参考': '裝配參考', '装配预览': '裝配預覽', '激光打标': '激光打標',
        '加工说明': '加工說明', '生成说明': '生成說明', '校验报告': '校驗報告', '切割': '切割',
        '掩模片': '掩模片', '骨架': '骨架',
    },
    'zh-TW': {
        '测试遮光掩模': '測試遮光掩模', '含ITO参考': '含ITO參考', '几何校验报告': '幾何驗證報告',
        '有效面积不确定度': '有效面積不確定度', '面积计算说明': '面積計算說明', '完整设计参数': '完整設計參數',
        '加工文件包': '加工檔案包', '装配参考': '裝配參考', '装配预览': '裝配預覽', '激光打标': '雷射打標',
        '加工说明': '加工說明', '生成说明': '生成說明', '校验报告': '驗證報告', '切割': '切割',
        '掩模片': '掩模片', '骨架': '骨架',
    },
}

# Exact error messages.
MSG = {
    'en': {
        '项目不存在，请重新打开项目列表': 'Project not found; please reopen the project list',
        '请导入完整项目JSON': 'Please import a complete project JSON',
        '最多80个单格图案对象': 'At most 80 single-cell pattern objects',
        '总成最多1600个图案开口': 'At most 1600 pattern openings per assembly',
        '已有同名项目，请修改名称；不会覆盖已有项目': 'A project with this name exists; rename it (existing projects are not overwritten)',
        '项目目录无效': 'Invalid project directory',
        '本版本支持蒸镀掩模总成项目': 'This version supports evaporation mask-assembly projects',
        '项目名称须为1～100个字符，不能包含文件名保留字符': 'Project name must be 1–100 characters with no reserved filename characters',
        '项目名称不能使用系统保留名称': 'Project name cannot use a system-reserved name',
        '最多400个定位开口': 'At most 400 positioning openings',
        '单格图案须为数组，最多80个图案对象': 'Single-cell pattern must be an array of at most 80 pattern objects',
        '图案对象须为JSON对象': 'Pattern object must be a JSON object',
        '图案开口区域用途须为 unassigned、active 或 common': 'Pattern-aperture region role must be unassigned, active, or common',
        '项目设置须为对象': 'Project settings must be an object',
        'ITO参考图案须为数组，最多40个区域对象': 'ITO reference patterns must be an array of at most 40 region objects',
        '图案开口过多：总成最多1600个开口': 'Too many pattern openings: at most 1600 per assembly',
        '图案开口过多：总成最多1600个开口，请减少单格复制数量': 'Too many pattern openings: at most 1600 per assembly; reduce the per-cell copies',
        '请先绘制单格图案开口': 'Please draw single-cell pattern openings first',
        '几何校验未通过，未生成DXF': 'Geometry validation failed; no DXF was generated',
        '操作不存在': 'Unknown operation', '文件不存在': 'File not found', '页面不存在': 'Page not found',
        '请求来源不匹配': 'Request origin mismatch', '请求大小无效': 'Invalid request size',
        '请求须为JSON对象': 'Request must be a JSON object',
        '当前项目已经切换，请刷新本页': 'The current project has changed; please refresh this page',
        '当前服务不支持从页面退出': 'This service does not support exiting from the page',
        '不确定度设置必须为对象': 'Uncertainty settings must be an object',
        '请选择矩形分布公差或正态分布标准不确定度': 'Choose rectangular-distribution tolerance or normal-distribution standard uncertainty',
        '误差输入须为0～10 mm的有限数值': 'Error input must be a finite value between 0 and 10 mm',
        '不支持的面积图案类型': 'Unsupported area pattern type',
        '请先绘制ITO有效区域；未定义ITO时不假定整个基片均有效': 'Draw the ITO effective area first; without ITO the whole substrate is not assumed effective',
        '图案开口相交或重叠，请处理后再计算每个pixel的不确定度': 'Pattern openings intersect or overlap; resolve them before computing per-pixel uncertainty',
        '请先将至少一个图案开口标记为活性区域；公共电极和未标记开口不计算面积不确定度': 'Tag at least one pattern opening as an active region first; common-electrode and untagged openings are not computed',
        '尺寸误差过大，可能产生非正尺寸；请减小误差': 'Size error too large; may produce a non-positive size — reduce it',
        '长槽尺寸误差可能使总长小于槽宽，请减小误差或使用圆形': 'Slot size error may make the total length smaller than the width; reduce it or use a circle',
        '活性区域与ITO交集产生带岛孔的复杂轮廓，暂不能自动生成测试遮光掩模': 'The active-region ∩ ITO intersection yields a complex contour with islands; the test mask cannot be auto-generated yet',
        '通光孔缩放后未能严格位于活性有效区域内；请降低边长比例或简化区域轮廓': 'Through-holes are not strictly inside the active effective area after scaling; lower the edge ratio or simplify the contour',
        'test_mask 必须是对象': 'test_mask must be an object',
        'test_mask.aperture_scale 必须大于0且小于1，才能使通光孔小于活性有效区域': 'test_mask.aperture_scale must be between 0 and 1 so through-holes are smaller than the active effective area',
        'test_mask.size_snap_mm 必须 > 0': 'test_mask.size_snap_mm must be > 0',
        '当前图案使用全板绝对坐标，无法自动派生单片测试遮光掩模；请改为每格复制图案': 'The pattern uses whole-panel absolute coordinates; a single-cell test mask cannot be derived — use per-cell pattern copy',
        '已有活性区域，但未定义ITO有效区域，无法确定测试遮光掩模的通光孔': 'Active regions exist but no ITO effective area is defined; test-mask through-holes cannot be determined',
        '活性区域与ITO有效区域没有交集，未生成测试遮光掩模': 'No intersection between active regions and the ITO effective area; test mask not generated',
        '项目数据须为JSON对象': 'Project data must be a JSON object',
        '浏览器本地存储': 'Browser local storage', '浏览器下载': 'Browser download',
    },
    'zh-Hant': {
        '请导入完整项目JSON': '請導入完整項目JSON', '项目目录无效': '項目目錄無效',
        '本版本支持蒸镀掩模总成项目': '本版本支持蒸鍍掩模總成項目', '最多400个定位开口': '最多400個定位開口',
        '图案对象须为JSON对象': '圖案對象須為JSON對象', '项目设置须为对象': '項目設置須為對象',
        '操作不存在': '操作不存在', '文件不存在': '文件不存在', '页面不存在': '頁面不存在',
        '请求来源不匹配': '請求來源不匹配', '请求大小无效': '請求大小無效', '请求须为JSON对象': '請求須為JSON對象',
        '不支持的面积图案类型': '不支持的面積圖案類型', '浏览器本地存储': '瀏覽器本地存儲', '浏览器下载': '瀏覽器下載',
    },
    'zh-TW': {
        '请导入完整项目JSON': '請匯入完整專案 JSON', '项目目录无效': '專案目錄無效',
        '本版本支持蒸镀掩模总成项目': '本版本支援蒸鍍掩模總成專案', '最多400个定位开口': '最多 400 個定位開口',
        '图案对象须为JSON对象': '圖案物件須為 JSON 物件', '项目设置须为对象': '專案設定須為物件',
        '操作不存在': '操作不存在', '文件不存在': '檔案不存在', '页面不存在': '頁面不存在',
        '请求来源不匹配': '請求來源不符', '请求大小无效': '請求大小無效', '请求须为JSON对象': '請求須為 JSON 物件',
        '不支持的面积图案类型': '不支援的面積圖案類型', '浏览器本地存储': '瀏覽器本機儲存', '浏览器下载': '瀏覽器下載',
    },
}


def _seg(s, lang):
    for k in sorted(SEG.get(lang, {}), key=len, reverse=True):
        if k in s:
            s = s.replace(k, SEG[lang][k])
    return s


def filename(name, lang='zh-Hans'):
    if lang == 'zh-Hans' or not name:
        return name
    return _seg(name, lang)


# Character-level Simplified->Traditional fallback for zh-Hant / zh-TW.
_S2T = str.maketrans({
    '请': '請', '项': '項', '设': '設', '须': '須', '为': '為', '数': '數', '组': '組', '图': '圖', '开': '開',
    '过': '過', '总': '總', '个': '個', '减': '減', '单': '單', '复': '複', '制': '製', '称': '稱', '验': '驗',
    '删': '刪', '统': '統', '环': '環', '转': '轉', '扫': '掃', '区': '區', '围': '圍', '电': '電', '极': '極',
    '标': '標', '记': '記', '积': '積', '绘': '繪', '计': '計', '处': '處', '后': '後', '误': '誤', '产': '產',
    '长': '長', '圆': '圓', '杂': '雜', '轮': '輪', '带': '帶', '岛': '島', '闭': '閉', '无': '無', '简': '簡',
    '当': '當', '绝': '絕', '对': '對', '载': '載', '页': '頁', '务': '務', '从': '從', '录': '錄', '内': '內',
    '键': '鍵', '态': '態', '应': '應', '与': '與', '这': '這', '带': '帶', '历': '歷', '导': '導', '间': '間',
    '并': '並', '块': '塊', '条': '條', '则': '則', '关': '關', '侧': '側', '丽': '麗', '击': '擊', '让': '讓',
    '认': '認', '边': '邊', '线': '線', '级': '級', '组': '組', '织': '織', '经': '經', '给': '給', '结': '結',
    '统': '統', '续': '續', '维': '維', '缩': '縮', '网': '網', '调': '調', '质': '質', '输': '輸', '车': '車',
    '载': '載', '运': '運', '达': '達', '选': '選', '逻': '邏', '错': '錯', '长': '長', '门': '門', '问': '問',
    '阵': '陣', '阳': '陽', '阴': '陰', '随': '隨', '隐': '隱', '难': '難', '项': '項', '顺': '順', '预': '預',
    '题': '題', '风': '風', '齐': '齊',
})


def _trad(s):
    return s.translate(_S2T)


def message(text, lang='zh-Hans'):
    if lang == 'zh-Hans' or not text:
        return text
    table = MSG.get(lang, {})
    if text in table:
        return table[text]
    for k in sorted(table, key=len, reverse=True):
        if k in text:
            text = text.replace(k, table[k])
    return _trad(text) if lang in ('zh-Hant', 'zh-TW') else text


# Report/notes labels (longest-first phrase replacement).
REPORT = {
    'en': {
        '骨架窗口': 'Frame window', '窗口阵列': 'Window array', '窗口数量': 'Window count', '基片尺寸': 'Substrate size',
        '最小筋宽': 'Min web', '开孔占比': 'Open ratio', '功能孔': 'Openings', '定位孔': 'Tooling', '取件孔': 'Pick',
        '把手': 'Handle', '窗口': 'Window', '外形': 'Outline', '旷量': 'Clearance', '骨架': 'Frame', '掩模片': 'Mask foil',
        '基片': 'substrate', '[警告]': '[WARN]', '[注意]': '[NOTE]',
        '所有孔均在允许边界内。': 'All openings are within the allowed boundary.',
        '注: 厚度/材料不在图纸标注': 'Note: thickness/material are not annotated on the drawing',
    },
    'zh-Hant': {
        '骨架窗口': '骨架窗口', '窗口阵列': '窗口陣列', '窗口数量': '窗口數量', '基片尺寸': '基片尺寸', '最小筋宽': '最小筋寬',
        '开孔占比': '開孔占比', '功能孔': '功能孔', '定位孔': '定位孔', '取件孔': '取片缺口', '把手': '把手', '窗口': '窗口',
        '外形': '外形', '旷量': '曠量', '骨架': '骨架', '掩模片': '掩模片', '基片': '基片', '[警告]': '[警告]', '[注意]': '[注意]',
    },
    'zh-TW': {
        '骨架窗口': '骨架窗口', '窗口阵列': '窗口陣列', '窗口数量': '窗口數量', '基片尺寸': '基板尺寸', '最小筋宽': '最小筋寬',
        '开孔占比': '開孔佔比', '功能孔': '開孔', '定位孔': '定位孔', '取件孔': '取片缺口', '把手': '把手', '窗口': '窗口',
        '外形': '外形', '旷量': '曠量', '骨架': '骨架', '掩模片': '掩模片', '基片': '基板', '[警告]': '[警告]', '[注意]': '[注意]',
    },
}


def report(text, lang='zh-Hans'):
    if lang == 'zh-Hans' or not text:
        return text
    table = REPORT.get(lang, {})
    for k in sorted(table, key=len, reverse=True):
        if k in text:
            text = text.replace(k, table[k])
    return _trad(text) if lang in ('zh-Hant', 'zh-TW') else text
