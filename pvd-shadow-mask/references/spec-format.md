# 规格文件(spec.json)字段说明

UTF-8 JSON(允许 BOM)。单位统一 mm, 角度为度(逆时针)。

## 通用顶层字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `kind` | 否 | `single`(默认) / `evaporation` / `light_block` |
| `name` | 是 | 名称, 用作报告标题与默认文件名 |
| `label` | 否 | 写入 DXF `NOTES` 层的文字(不切割); 中文自动转 `\U+XXXX` |
| `min_web_mm` | 否 | 加工轮廓之间及到外框的最小筋宽阈值, 默认 0.30; 低于阈值报告警告 |
| `arc_segments_per_90` | 否 | 每 90° 圆弧的折线段数, 默认 16 |
| `curve_tolerance_mm` | 否 | 布尔合并时圆形离散的最大弦高误差, 默认 0.001 mm, 必须 > 0; 不替代既有圆角/槽的分段设置 |
| `outputs` | 否 | 覆盖输出文件名, 如 `{"assembly":"装配.dxf","foil":"片.dxf","skeleton":"架.dxf"}` |
| `ito_effective` | 否 | `{"features":[...]}`; 单格ITO有效区域参考图案, 相对基片中心, 蒸镀总成按阵列复制; 空数组建立空图层 |
| `laser_marking` | 否 | 全板打标文字数组: `text`, `center:[x,y]`, `height`, `angle`, `target`(skeleton/foil/both); 默认目标骨架 |

打标文字坐标相对整板主体中心, 不按单格阵列复制。`height`为实际字形总高(mm), `center`为字形包围框中心, 角度逆时针。使用本机 Microsoft YaHei 字体经 Matplotlib 转成闭合矢量字形, 输出 `LASER_MARK` 图层; 字形内外环保留, 加工方按打标填充/描边要求处理。文字必须在目标板实体上, 越界或覆盖开口会阻止生成。切割版应排除该图层, 独立激光打标文件只含字形轮廓。

ITO有效区域使用与图案开口相同的形状定义, 须在基片真实边界内。输出为品红色 `ITO_EFFECTIVE` 参考图层, 不参与切割轮廓、开孔占比或筋宽统计。装配图中的重复参考边界只输出一次。

> **厚度与材料不写进图纸**(下单时选择), 因此规格里没有必填的厚度字段, 工具也不会输出厚度标注。

### 外形对象(outline / substrate / silvered)

| type | 字段 |
|------|------|
| `rect` | `width`, `height`, `corner_radius`(默认 0) |
| `circle` | `diameter` |
| `polygon` | `points`: `[[x,y], ...]`(仅 `outline`/`silvered` 支持) |

`rect`/`circle` 以 **(0,0) 为中心**。所有孔使用同一坐标系。

### features(孔图案)

| type | 字段 |
|------|------|
| `circle_array` | `origin`(第0孔中心), `diameter`, `pitch_x`, `pitch_y`(默认=pitch_x), `nx`, `ny`, 可选 `angle`, `stagger`, `skip` |
| `rect_array` | 同上, `diameter` 换成 `width`, `height` |
| `circle` | `center:[x,y]`, `diameter` |
| `slot` | `center:[x,y]`, `length`(总长含两端半圆), `width`, `angle` |
| `polygon` | `points:[[x,y],...]`(≥3 点) |

### holes_csv(可选)

外部孔位表, 每行 `x,y,diameter` 或 `x,y,width,height`; `#` 注释、空行忽略。相对路径按 **json 所在目录**。
可用于 `spec`、`foil` 等任何含 features 的层级。

### frame_holes(可选, 安装孔)

未要求安装孔时省略 `frame_holes`, 工具不会自动添加。蒸镀对片的骨架与掩模片可各自按需要设置。

`diameter`(必填), 加 `inset`(四角放置) 或 `positions:[[x,y],...]`; `skip_corners` 跳过某些角。

---

## kind = `single`(通用单件)

```json
{
  "name": "...",
  "outline": { "type": "rect", "width": 100, "height": 100, "corner_radius": 3 },
  "features": [ ... ],
  "frame_holes": { "diameter": 3.2, "inset": 6 }
}
```
输出 1 个 DXF。

## kind = `evaporation`(蒸镀对片)

| 字段 | 必填 | 说明 |
|------|------|------|
| `substrate` | 是 | 基片(玻璃)外形, 仅 `rect`/`circle` |
| `clearance_mm` | 否 | **旷量 = 边长总差**, 默认 0.2; 单边 = 该值/2 |
| `skeleton.outline` | 是 | 2mm 骨架(母板)外框, 直接给尺寸 |
| `skeleton.windows` | 否 | 图案阵列; 不写则单个居中定位开口 |
| `skeleton.handle` | 否 | 把手(外形边缘凸台, 供手握取): `width`+`height`+`edge`+可选 `offset`; 可给数组 |
| `skeleton.pick_hole` | 否 | 定位开口边上或角上的取片缺口, 可给数组设置多个 |
| `skeleton.frame_holes` | 否 | 骨架安装孔 |
| `foil.outline` | 否 | 0.1mm 掩模片外形; 默认 = 骨架外形 |
| `foil.features` / `foil.cell` | 是 | **单格图案**(相对定位开口中心); `cell` 是 `features` 的别名, 两种写法等价 |
| `foil.per_window` | 否 | 是否在每个定位开口复制图案; 多定位开口时默认 true |
| `foil.frame_holes` | 否 | 掩模片安装孔(建议与骨架一致) |

`skeleton.windows` 两种写法:

```json
{ "type": "array", "origin": [-72,-62], "pitch_x": 48, "pitch_y": 62, "nx": 4, "ny": 3, "angle": 0, "stagger": false }
```
```json
{ "type": "list", "positions": [[-72,-62], [-24,-62], ...], "angle": 0 }
```

- **骨架定位开口** = `substrate` 每边外扩 `clearance_mm/2`(如 15 -> 15.2), 在每个定位开口位置生成, 落在 `WINDOW` 层。
- **直角规则**: 矩形基片未设置圆角或 `corner_radius: 0` 时, 定位开口保持直角, 旷量只增大边长, 不自动添加圆角。基片明确设置正圆角时, 定位开口圆角半径为基片圆角半径加单边旷量。角部取片缺口单独按其圆径合并。
- **把手** `skeleton.handle`: 在骨架外形某条边凸出一块方台, 供手握搬取; `width`(沿边宽) + `height`(凸出高) +
  可选 `edge`(默认 top)、`offset`。无论哪条边, `width` 沿边、`height` 为凸出量。与外形合并为一条闭合 `OUTLINE`, 连接处无切割线; 掩模片沿用默认外形时带同样的把手。把手必须沿一段边连接主体; 脱离或仅点接触会报错。圆形主体的切线位置不能直接连接矩形把手, 此时需给出可连接的多边形外形。
- **取片缺口** `skeleton.pick_hole`: 可放在定位开口的边上或角上, 与定位开口重叠, 方便镊子取片。`diameter` 必填, 位置用以下两种方式之一:
  - 边上: `edge` = `top` / `bottom` / `left` / `right`(默认 top), `offset` 沿边平移, `inset` 往开口内移。
  - 角上: `corner` = `top_left` / `top_right` / `bottom_left` / `bottom_right`, 即左上/右上/左下/右下。默认圆心在矩形定位开口外包络的角点; `inset` 沿 X/Y 两方向各向内移动同一距离。圆角矩形也可使用, 实际缺口按并集生成; 圆形开口没有角, 不支持 `corner`。
  - `edge` 与 `corner` 互斥, 角部位置不使用非零 `offset`; 方位相对单格局部坐标, 随阵列旋转。
  - 可给数组混合配置边上和角上的多个缺口。所有缺口与定位开口做布尔并集, 最终闭合轮廓统一落在 `WINDOW` 层。跨接多个定位开口、脱离定位开口或完全藏在定位开口里会报错。

  ```json
  "pick_hole": { "diameter": 4, "corner": "top_right" }
  ```
- `foil.per_window: true` 时, `foil.features` 相对每个定位开口中心复制一份(批量母板); `false` 时按绝对坐标只画一次。
- 掩模片功能孔须落在**任一定位开口**内, 并且在掩模片真实外形内。骨架合并后的定位开口/缺口与所有安装孔也须在所属部件真实外形内; 越界或加工轮廓相交/重叠/相切会报错并阻止 DXF 输出。
- 四角安装孔的 `inset` 以主体外形为基准, 不因把手合并而移动。掩模片的安装孔按 `foil.frame_holes` 设置, 不自动继承骨架安装孔。
- 安装孔完全可选; 省略骨架和掩模片的 `frame_holes` 即生成无安装孔的对片。

输出 3 个 DXF: `<名>_装配图.dxf` / `<名>_掩模片.dxf` / `<名>_骨架.dxf`。

## kind = `light_block`(测试遮光 mask)

| 字段 | 必填 | 说明 |
|------|------|------|
| `substrate` | 是 | 外形 = 基片大小(仅 `rect`/`circle`) |
| `silvered` | 否 | 片子镀银区外形; 不写则按外形校验 |
| `aperture_inset_mm` | 否 | 通光孔相对镀银区**单边**内缩量, 默认 0.3 |
| `features` | 是 | 多孔通光图案 |
| `frame_holes` | 否 | 安装孔 |

- 所有孔校验是否落在 `silvered` 内缩 `aperture_inset_mm` 的区域内。
- 内缩采用到真实边界的最短距离, 保留圆形、圆角与凹多边形边界; 不使用包围盒代替。
- `silvered` 会作为 `REFERENCE` 参考层画在图上(不切割)。
- GUI蒸镀总成项目会自动派生测试遮光mask：外形默认复制 `substrate`，通光孔取 `region_role: active` 的图案开口与 `ito_effective` 的交集；`common` 和 `unassigned` 不生成通光孔。

输出 1 个 DXF。

## 校验与失败行为

- 尺寸须 > 0, 阵列数量须为正整数; 坐标须为有限数值, 多边形不得自交或退化。
- 开孔占比按功能孔、定位开口缺口与安装孔的几何并集面积计算; 分母为含把手的外形面积。圆形面积统计采用精细离散近似。
- 筋宽覆盖所有加工轮廓及到外框的距离, 报告取圆形离散误差的保守下界; 接近阈值时结合精度与工艺确认。
- `[错误]` 不写 DXF, CLI 退出码 2; 可定位的几何错误仍写校验报告。无效尺寸/轮廓或合并失败直接输出规格错误。
- `[警告]` 会输出 DXF, 需评估工艺可行性。失败不会删除旧 DXF, 必须确认本次报告及输出状态。

## 示例

- 通用单件: [../examples/basic_array.json](../examples/basic_array.json)
- 蒸镀对片: [../examples/evaporation_pair.json](../examples/evaporation_pair.json)
- 测试遮光: [../examples/light_block.json](../examples/light_block.json)
- 右上角取片缺口、无安装孔: [../examples/corner_pick.json](../examples/corner_pick.json)
