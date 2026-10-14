# Ohm Mask Designer

<p align="center">
  <img src="assets/ohm-logo.svg" alt="武汉欧姆科技有限公司 Logo" width="520">
</p>

Ohm Mask Designer（欧姆掩模设计器）是一款本地浏览器应用，用于从基板、掩模片和骨架尺寸开始，完成蒸镀掩模总成设计、图案开口编辑、ITO 有效面积分析、几何校验和加工文件导出。

纯网页版：[https://littleblack2003.github.io/ohm-mask-designer/](https://littleblack2003.github.io/ohm-mask-designer/)

Windows 便携版：[下载最新版本](https://github.com/littleBlack2003/ohm-mask-designer/releases/latest)。完整解压后双击“欧姆掩模设计器.exe”，无需安装 Python 或 AutoCAD。

网页版使用 Pyodide 在浏览器内运行与桌面版相同的 Python/Shapely 几何算法。项目保存在当前浏览器的本地存储中，建议定期导出项目 JSON 备份；生成的 DXF、SVG、CSV 和 ZIP 直接下载到本机。首次打开需要联网加载浏览器计算运行时和中文矢量字体。

## 主要功能

- 分别设置矩形或圆形基板、掩模片和骨架尺寸。
- 掩模片可跟随骨架外形，也可使用独立矩形或圆形外形。
- 工作区按“骨架、单片图案、掩模片、打标、总成预览、mask”排列，各页只显示当前任务需要的工具。
- 单片图案显示间距可调的基片内部网格；其他工作区可用画布右下角按钮开关 10 mm 工程网格及坐标数字，默认关闭。所有工作区均保留 X/Y 零轴。
- 骨架页可直接设置外框、把手、总旷量和基板定位开口阵列，画布同步显示实际加工轮廓。
- 设置图案阵列、定位开口、把手、取片缺口和可选安装孔。
- 绘制矩形、圆形、长槽和多边形图案开口，并支持移动、阵列和居中。
- 将图案开口标记为活性区域、公共电极区域或未标记，并按用途统计和导出。
- 独立编辑 ITO 有效区域和激光打标文字图层。
- 统计开孔数量，仅对活性区域计算有效面积及解析面积不确定度。
- 按“活性区域开口 ∩ ITO有效区域”确定活性有效区域，自动生成基板等外形的测试遮光掩模加工图；通光孔默认按80% 边长缩小并吸附到0.1 mm，严格位于活性有效区域内。
- 校验轮廓边界、重叠、最小筋宽以及掩模片对定位开口的覆盖。
- 导出掩模片与骨架切割 DXF、激光打标 DXF、装配参考、SVG 预览、CSV、JSON 和加工文件包。

## 从源码启动

需要 Python 3.10 或更高版本。

```powershell
python -m pip install -r requirements.txt
python -X utf8 -B "图案开口设计器/launch.py"
```

Windows 用户也可以双击 `图案开口设计器/启动设计器.cmd`。设计器会在本机启动服务并打开 `http://127.0.0.1:8765/`，不需要 AutoCAD。

## 测试

```powershell
python -X utf8 -B -m unittest discover -s "图案开口设计器" -p "test_*.py"
python -X utf8 -B -m unittest discover -s "pvd-shadow-mask/tests" -p "test_*.py"
```

## 目录

- `图案开口设计器/`：浏览器 GUI、项目管理、统计、校验和加工导出。
- `pvd-shadow-mask/`：Codex Skill、几何生成脚本、格式规范和示例。
- `默认25mm基底/`：可复现的示例项目配置。

详细使用方法见 [`图案开口设计器/使用说明.md`](图案开口设计器/使用说明.md)。

## 开源许可与联系

本项目由**武汉欧姆科技有限公司**发起并维护，以 [Apache License 2.0](LICENSE) 开源，未附加额外许可限制。欢迎使用、修改、分发和参与贡献。提交代码前请阅读 [参与贡献说明](CONTRIBUTING.md)。

- GitHub：<https://github.com/littleBlack2003/ohm-mask-designer>
- 联系邮箱：<dasohm@163.com>

武汉欧姆科技有限公司提供掩模制作服务，自带完整加工图纸的客户可以获得优惠报价。详情见 [掩模制作服务](SERVICE.md)。

