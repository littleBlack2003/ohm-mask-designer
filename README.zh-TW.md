# Ohm Mask Designer

[English](README.en.md) | [简体中文](README.md) | [繁體中文](README.zh-Hant.md)


> 本頁為**台灣用語**版；通用繁體請見 [README.zh-Hant.md](README.zh-Hant.md)。

<p align="center">
  <img src="assets/ohm-logo.svg" alt="武漢歐姆科技有限公司 Logo" width="520">
</p>

Ohm Mask Designer（歐姆掩模設計器）是一款本機瀏覽器應用程式，用於從基板、掩模片和骨架尺寸開始，完成蒸鍍掩模總成設計、圖案開口編輯、ITO 有效面積分析、幾何驗證和加工檔案匯出。

純網頁版：[https://littleblack2003.github.io/ohm-mask-designer/](https://littleblack2003.github.io/ohm-mask-designer/)

Windows 免安裝版：[下載最新版本](https://github.com/littleBlack2003/ohm-mask-designer/releases/latest)。完整解壓縮後按兩下「歐姆掩模設計器.exe」，無需安裝 Python 或 AutoCAD。

網頁版使用 Pyodide 在瀏覽器內執行與桌面版相同的 Python/Shapely 幾何演算法。專案儲存在目前瀏覽器的本機儲存空間中，建議定期匯出專案 JSON 備份；生成的 DXF、SVG、CSV 和 ZIP 直接下載到本機。首次開啟需要連網載入瀏覽器計算執行環境和中文向量字型。

## 主要功能

- 分別設定矩形或圓形基板、掩模片和骨架尺寸。
- 掩模片可跟隨骨架外形，也可使用獨立矩形或圓形外形。
- 工作區按「骨架、單片圖案、掩模片、打標、總成預覽、mask」排列，各頁只顯示目前任務需要的工具。
- 單片圖案顯示間距可調的基片內部網格；其他工作區可用畫布右下角按鈕開關置頂的 10 mm 工程網格、中心軸和座標數字，預設關閉。
- 骨架頁可直接設定外框、把手、總曠量和基板定位開口陣列，畫布同步顯示實際加工輪廓。
- 尺寸設定按基本資訊、基板、骨架、定位開口與圖案陣列、掩模片、測試 mask 和高級設定分頁編輯。
- 設定圖案陣列、定位開口、把手、取片缺口和可選安裝孔。
- 繪製矩形、圓形、長槽和多邊形圖案開口，並支援移動、陣列和居中。
- 將圖案開口標記為活性區域、公共電極區域或未標記，並按用途統計和匯出。
- 獨立編輯 ITO 有效區域和雷射打標文字圖層。
- 統計開孔數量，僅對活性區域計算有效面積及解析面積不確定度。
- 按「活性區域開口 ∩ ITO有效區域」確定活性有效區域，自動生成基板等外形的測試遮光掩模加工圖；通光孔預設按 80% 邊長縮小並吸附到 0.1 mm，嚴格位於活性有效區域內。
- 驗證輪廓邊界、重疊、最小筋寬以及掩模片對定位開口的覆蓋。
- 匯出掩模片與骨架切割 DXF、雷射打標 DXF、裝配參考、SVG 預覽、CSV、JSON 和加工檔案包。

## 從原始碼啟動

需要 Python 3.10 或更高版本。

```powershell
python -m pip install -r requirements.txt
python -X utf8 -B "图案开口设计器/launch.py"
```

Windows 使用者也可以按兩下 `图案开口设计器/启动设计器.cmd`。設計器會在本機啟動服務並開啟 `http://127.0.0.1:8765/`，不需要 AutoCAD。

## 測試

```powershell
python -X utf8 -B -m unittest discover -s "图案开口设计器" -p "test_*.py"
python -X utf8 -B -m unittest discover -s "ohm-mask-skill/tests" -p "test_*.py"
```

## 目錄

- `图案开口设计器/`：瀏覽器 GUI、專案管理、統計、驗證和加工匯出。
- `ohm-mask-skill/`：Codex Skill、幾何生成腳本、格式規範和範例。
- `默认25mm基底/`：可重現的範例專案設定。

詳細使用方法見 [`图案开口设计器/使用说明.md`](图案开口设计器/使用说明.md)。

## 貢獻致謝

本專案的設計、實作與文件由 **DeepSeek V4.1 Flash** 與 **GPT 6.1 Sol** 協作貢獻完成，涵蓋掩模幾何演算法、瀏覽器工作台、四語文件與打包發行。

## 開源授權與聯絡

本專案由**武漢歐姆科技有限公司**發起並維護，以 [Apache License 2.0](LICENSE) 開源，未附加額外授權限制。歡迎使用、修改、分發和參與貢獻。提交程式碼前請閱讀 [參與貢獻說明](CONTRIBUTING.md)。

- GitHub：<https://github.com/littleBlack2003/ohm-mask-designer>
- 電子郵件：<dasohm@163.com>

武漢歐姆科技有限公司提供掩模製作服務，自帶完整加工圖紙的客戶可以獲得優惠報價。詳情見 [掩模製作服務](SERVICE.md)。
