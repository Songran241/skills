---
name: outfit
description: 智能穿搭助手 — 根据天气和衣橱自动推荐穿搭方案。支持添加衣物、查看衣橱、获取穿搭建议。
---

# IntelliOutfit — 智能穿搭助手

根据天气和衣橱自动推荐穿搭方案。

## 快速开始

```bash
# 1. 复制示例配置文件
cp config.example.json config.json
cp wardrobe/catalog.example.json wardrobe/catalog.json

# 2. 编辑 config.json，填入你所在城市的经纬度
# 3. 通过 /add-clothes 命令添加你的衣物
```

## 项目结构

```
├── SKILL.md                    # 本文件
├── .gitignore
├── config.example.json         # 配置模板（提交到 Git）
├── config.json                 # 个人配置（已 gitignore）
├── scripts/
│   ├── main.py                 # CLI 入口 (recommend / weather / wardrobe / add)
│   ├── weather.py              # 天气获取（Open-Meteo API）
│   ├── wardrobe.py             # 衣橱管理
│   └── recommender.py          # 推荐引擎
├── references/
│   ├── dressing-rules.md       # 穿搭法则（温度、配色、风格）
│   └── attribute-guide.md      # 衣物属性分类标准
└── wardrobe/
    ├── catalog.example.json     # 示例衣橱（提交到 Git）
    ├── catalog.json             # 个人衣橱（已 gitignore）
    └── photos/                  # 衣物照片
```

## 命令

### /outfit — 获取穿搭建议

触发：用户输入 `/outfit`、`穿搭建议`、`今天穿什么`、`明天穿什么`、`推荐穿搭`

流程：
1. 运行 `python3 scripts/main.py recommend` 获取推荐 JSON
2. 读取 `references/dressing-rules.md` 获取穿搭法则上下文
3. 将推荐结果转化为自然语言输出，包含：
   - 明天的天气概况（温度范围、天气类型、降雨概率、风力）
   - 2-3 套穿搭方案，每套包含：
     - 风格名称和配色思路
     - 每件单品的名称、颜色，如有图片则附上路径
     - 特殊提醒（雨天防水、温差叠穿等）
4. 如果有单品对应的照片存在于 `wardrobe/photos/` 中，使用 Read 工具读取照片展示给用户

输出格式示例：
```
🗓 明天北京 12-22°C 多云，降雨概率 20%

方案一 【极简通勤】
🧥 米白棉质衬衫 + 深灰直筒西裤 + 白色板鞋
配色思路：上浅下深，全中性色安全搭配
```

### /add-clothes — 添加衣物

触发：用户输入 `/add-clothes`、`添加衣服`、`录入衣服`，或发送淘宝分享口令/衣物照片

#### 通道 A：淘宝分享口令识别

当用户发送类似以下格式的淘宝分享口令时：
```
【淘宝】https://e.tb.cn/h.xxx?tk=xxx 「商品标题」
```

流程：
1. 提取「」之间的商品标题文本
2. 对照 `references/attribute-guide.md` 中的分类标准，从标题中分析衣物属性：
   - 品类 (category + subcategory)
   - 材质 (material)
   - 保暖能力 (warmth): 1~5 跨品类绝对值，根据材质和描述词推断（详见 attribute-guide.md）
   - 物理体积 (bulk): 1~3，判断叠穿兼容性（轻薄/适中/厚重）
   - 版型 (fit): 宽松/修身/常规
   - 颜色: 从标题中提取颜色词，如有 "X色可选" 则追问具体颜色
   - 风格 (style)
   - 适用温度范围 (temp_range): 根据厚度和材质推断
3. 将分析结果展示给用户确认
4. 用户确认后，构造 JSON 调用 `python3 scripts/main.py add --data '<json>'`
5. 如标题信息不全，追问用户补充关键属性

#### 通道 B：照片识别

当用户发送衣物照片时：

**场景 B1 — 直接拍衣服（平铺/悬挂/穿着）**
1. 使用 Read 工具打开照片，分析衣物：
   - 品类：领型、袖长、衣长判断
   - 颜色和图案
   - 面料质感：针织纹理/棉质/牛仔/皮质等
   - 保暖与厚度：面料质感判断 warmth，透光感/蓬松度判断 bulk
   - 版型：肩线位置、衣身宽度
   - 风格
2. 对照 `references/attribute-guide.md` 映射为标准属性值
3. 展示分析结果，请求用户确认或补充
4. 用户确认后，将照片复制到 `wardrobe/photos/<item-id>.jpg` 并构造 JSON 入库

**场景 B2 — 拍商品详情页截图（淘宝/电商截图）**
1. 使用 Read 工具打开截图，直接读取页面信息：
   - 商品标题文本
   - SKU 选择区（颜色选项）
   - 尺码表
   - 模特上身效果（判断版型、长度）
   - 面料细节图
   - 详情文案中的材质成分
2. 综合以上信息，对照 `references/attribute-guide.md` 生成完整属性
3. 展示分析结果，请求确认
4. 确认后入库

#### 属性推断规则

- **warmth 推断**（1=无保暖, 2=微保暖, 3=轻保暖, 4=中保暖, 5=强保暖）：
  - 网面、亚麻、薄棉、夏装 → warmth 1
  - 常规棉、单层、无填充、标准衬衫/牛仔裤 → warmth 2
  - 加绒、法兰绒、薄填充（轻羽绒/抓绒）、厚卫衣 → warmth 3
  - 厚填充、厚针织、羊毛、常规羽绒服 → warmth 4
  - 高克重填充、派克、厚羊毛大衣 → warmth 5
  - 羽绒服 warmth 最低从 3 起（再薄也有填充物）
  - 软壳衣/冲锋衣（无填充）warmth = 2（防风但不保暖）

- **bulk 推断**（1=轻薄, 2=适中, 3=厚重）：
  - 单层面料、可折叠很小 → bulk 1（含薄款羽绒服！）
  - 常规厚度、有衬里、标准夹克 → bulk 2
  - 高克重、多层结构、厚填充 → bulk 3
  - 羽绒服：薄款 bulk=1，常规 bulk=2，厚款 bulk=3

- **temp_range 推断**（基于 warmth + 品类）：
  - warmth 1 → [22, 35]（夏装）
  - warmth 2 → [10, 25]（春秋过渡）
  - warmth 3 → [5, 18]（春秋主力，薄羽绒可达 [0, 15]）
  - warmth 4 → [-5, 12]（冬装）
  - warmth 5 → [-20, 5]（严冬）
  - 防风/防水额外调低下限 3°C，透气面料（羊毛/羊绒）调高上限 3°C

- **风格推断**：
  - 纯色、无logo、简洁 → minimalist
  - 大logo、印花、宽松 → streetwear
  - 有领、纽扣门襟 → 偏 formal
  - 运动品牌、功能面料 → sporty

### /wardrobe — 查看衣橱

触发：用户输入 `/wardrobe`、`我的衣橱`、`衣橱里有什么`

流程：
1. 运行 `python3 scripts/main.py wardrobe` 获取衣橱数据
2. 按类别展示所有衣物（名称、颜色、保暖程度、适用温度），标注缺失类别
3. 如有照片则附上缩略图

## 穿搭法则依据

所有穿搭建议基于 `references/dressing-rules.md`，该文件包含：
- 温度分层（7 个温度区间的穿搭层级）
- 天气修正（降雨/大风/湿度/紫外线/温差的调整规则）
- 配色法则（色系定义、三条铁律、5 个配色公式、避雷清单）
- 风格模板（6 种风格及适用场景）
- 叠穿法则（三层叠穿 + 配色要点）
- 场景自适应（办公室/雨天/约会/户外等）

Claude 在输出穿搭建议时，应引用法则中的配色原理和风格公式，让用户理解"为什么这么搭"。

## 天气数据

天气数据通过 Open-Meteo API 获取（免费、无需 API Key）。默认位置在 `config.json` 中配置。

如需切换城市，修改 `config.json` 中的 `latitude` 和 `longitude`。

## 核心原则

1. **推荐可解释**：每套搭配都要说明配色逻辑和风格依据
2. **确认再入库**：识别出的衣物属性必须经用户确认后才写入 catalog.json
3. **法则可调**：dressing-rules.md 是纯文本，用户随时可改，Claude 也应在用户反馈后主动提出优化法则的建议
4. **图片可视化**：搭配输出时尽量展示实际衣物照片，让建议更直观
