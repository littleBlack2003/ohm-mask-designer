# Ohm Mask Designer

[English](README.en.md) | [简体中文](README.md) | **繁體中文**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

> 本頁為通用繁體；台灣用語版見 [README.zh-TW.md](README.zh-TW.md)。

<p align="center">
  <img src="assets/ohm-logo.svg" alt="武漢歐姆科技有限公司 Logo" width="520">
</p>

Ohm Mask Designer（歐姆掩模設計器）是一款本地瀏覽器應用，用於從基板、掩模片和骨架尺寸開始，完成蒸鍍掩模總成設計、圖案開口編輯、ITO 有效面積分析、幾何校驗和加工文件導出。

純網頁版：[https://littleblack2003.github.io/ohm-mask-designer/](https://littleblack2003.github.io/ohm-mask-designer/)

Windows 便攜版：[下載最新版本](https://github.com/littleBlack2003/ohm-mask-designer/releases/latest)。完整解壓後雙擊「歐姆掩模設計器.exe」，無需安裝 Python 或 AutoCAD。

網頁版使用 Pyodide 在瀏覽器內運行與桌面版相同的 Python/Shapely 幾何算法。項目保存在當前瀏覽器的本地存儲中，建議定期導出項目 JSON 備份；生成的 DXF、SVG、CSV 和 ZIP 直接下載到本機。首次打開需要聯網加載瀏覽器計算運行時和中文矢量字體。

## 主要功能

- 分別設置矩形或圓形基板、掩模片和骨架尺寸。
- 掩模片可跟隨骨架外形，也可使用獨立矩形或圓形外形。
- 工作區按「骨架、單片圖案、掩模片、打標、總成預覽、mask」排列，各頁只顯示當前任務需要的工具。
- 單片圖案顯示間距可調的基片內部網格；其他工作區可用畫布右下角按鈕開關置頂的 10 mm 工程網格、中心軸和坐標數字，默認關閉。
- 骨架頁可直接設置外框、把手、總曠量和基板定位開口陣列，畫布同步顯示實際加工輪廓。
- 尺寸設置按基本信息、基板、骨架、定位開口與圖案陣列、掩模片、測試 mask 和高級設置分頁編輯。
- 設置圖案陣列、定位開口、把手、取片缺口和可選安裝孔。
- 繪製矩形、圓形、長槽和多邊形圖案開口，並支持移動、陣列和居中。
- 將圖案開口標記為活性區域、公共電極區域或未標記，並按用途統計和導出。
- 獨立編輯 ITO 有效區域和激光打標文字圖層。
- 統計開孔數量，僅對活性區域計算有效面積及解析面積不確定度。
- 按「活性區域開口 ∩ ITO有效區域」確定活性有效區域，自動生成基板等外形的測試遮光掩模加工圖；通光孔默認按80% 邊長縮小並吸附到0.1 mm，嚴格位於活性有效區域內。
- 校驗輪廓邊界、重疊、最小筋寬以及掩模片對定位開口的覆蓋。
- 導出掩模片與骨架切割 DXF、激光打標 DXF、裝配參考、SVG 預覽、CSV、JSON 和加工文件包。

## 從源碼啟動

需要 Python 3.10 或更高版本。

```powershell
python -m pip install -r requirements.txt
python -X utf8 -B "图案开口设计器/launch.py"
```

Windows 用戶也可以雙擊 `图案开口设计器/启动设计器.cmd`。設計器會在本機啟動服務並打開 `http://127.0.0.1:8765/`，不需要 AutoCAD。

## 測試

```powershell
python -X utf8 -B -m unittest discover -s "图案开口设计器" -p "test_*.py"
python -X utf8 -B -m unittest discover -s "ohm-mask-skill/tests" -p "test_*.py"
```

## 目錄

- `图案开口设计器/`：瀏覽器 GUI、項目管理、統計、校驗和加工導出。
- `ohm-mask-skill/`：Codex Skill、幾何生成腳本、格式規範和示例。
- `默认25mm基底/`：可復現的示例項目配置。

詳細使用方法見 [`图案开口设计器/使用说明.md`](图案开口设计器/使用说明.md)。

## 貢獻致謝

本項目的設計、實現與文檔由 **DeepSeek V4.1 Flash** 與 **GPT 6.1 Sol** 協作貢獻完成，涵蓋掩模幾何算法、瀏覽器工作檯、四語文檔與打包發布。

## 開源許可與聯繫

本項目由**武漢歐姆科技有限公司**發起並維護，以 [Apache License 2.0](LICENSE) 開源，未附加額外許可限制。歡迎使用、修改、分發和參與貢獻。提交代碼前請閱讀 [參與貢獻說明](CONTRIBUTING.md)。

- GitHub：<https://github.com/littleBlack2003/ohm-mask-designer>
- 聯繫郵箱：<dasohm@163.com>

武漢歐姆科技有限公司提供掩模製作服務，自帶完整加工圖紙的客戶可以獲得優惠報價。詳情見 [掩模製作服務](SERVICE.md)。
