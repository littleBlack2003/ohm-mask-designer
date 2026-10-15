# 参与贡献

[English](CONTRIBUTING.en.md) | **简体中文** | [繁體中文](CONTRIBUTING.zh-Hant.md)

欢迎提交 Issue 或 Pull Request，反馈问题、改进文档或扩展掩模设计与加工导出功能。

提交代码前，请运行：

```powershell
python -X utf8 -B -m unittest discover -s "图案开口设计器" -p "test_*.py"
python -X utf8 -B -m unittest discover -s "ohm-mask-skill/tests" -p "test_*.py"
node --check "图案开口设计器/static-api.js"
```

涉及几何或加工文件的修改，请在 Pull Request 中说明输入参数、预期结果和验证方法。

联系邮箱：<dasohm@163.com>
