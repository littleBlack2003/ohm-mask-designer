# Contributing

[English](CONTRIBUTING.en.md) | [简体中文](CONTRIBUTING.md) | [繁體中文](CONTRIBUTING.zh-Hant.md)

Issues and pull requests are welcome — report problems, improve the docs, or extend the mask-design and manufacturing-export features.

Before submitting code, please run:

```powershell
python -X utf8 -B -m unittest discover -s "Ohm Mask Designer" -p "test_*.py"
python -X utf8 -B -m unittest discover -s "ohm-mask-skill/tests" -p "test_*.py"
node --check "Ohm Mask Designer/static-api.js"
```

For changes touching geometry or manufacturing files, describe the input parameters, expected results, and verification method in the pull request.

Email: <dasohm@163.com>
