# 參與貢獻

[English](CONTRIBUTING.en.md) | [简体中文](CONTRIBUTING.md) | [繁體中文](CONTRIBUTING.zh-Hant.md)

> 本頁為**台灣用語**版；通用繁體見 [CONTRIBUTING.zh-Hant.md](CONTRIBUTING.zh-Hant.md)。

歡迎提交 Issue 或 Pull Request，回報問題、改進文件或擴充掩模設計與加工匯出功能。

提交程式碼前，請執行：

```powershell
python -X utf8 -B -m unittest discover -s "Ohm Mask Designer" -p "test_*.py"
python -X utf8 -B -m unittest discover -s "ohm-mask-skill/tests" -p "test_*.py"
node --check "Ohm Mask Designer/static-api.js"
```

涉及幾何或加工檔案的修改，請在 Pull Request 中說明輸入參數、預期結果和驗證方法。

聯絡電子郵件：<dasohm@163.com>
