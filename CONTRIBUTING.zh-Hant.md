# 參與貢獻

[English](CONTRIBUTING.en.md) | [简体中文](CONTRIBUTING.md) | **繁體中文**

> 本頁為通用繁體；台灣用語版見 [CONTRIBUTING.zh-TW.md](CONTRIBUTING.zh-TW.md)。

歡迎提交 Issue 或 Pull Request，反饋問題、改進文檔或擴展掩模設計與加工導出功能。

提交代碼前，請運行：

```powershell
python -X utf8 -B -m unittest discover -s "Ohm Mask Designer" -p "test_*.py"
python -X utf8 -B -m unittest discover -s "ohm-mask-skill/tests" -p "test_*.py"
node --check "Ohm Mask Designer/static-api.js"
```

涉及幾何或加工文件的修改，請在 Pull Request 中說明輸入參數、預期結果和驗證方法。

聯繫郵箱：<dasohm@163.com>
