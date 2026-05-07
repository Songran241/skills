# IntelliOutfit — 智能穿搭助手

根据天气和衣橱自动推荐穿搭方案。基于 Open-Meteo 免费天气 API，结合穿搭法则引擎，为你生成可解释的每日穿搭建议。

## 功能

- **/outfit** — 获取明日穿搭推荐。根据天气自动匹配衣橱中的单品，输出 2-3 套搭配方案，每套包含配色逻辑和风格依据
- **/add-clothes** — 添加衣物。支持淘宝分享口令识别（自动解析品类、面料、保暖值）或照片识别（分析颜色、版型、风格）
- **/wardrobe** — 查看衣橱。按类别展示所有衣物及缺失提醒

## 快速开始

```bash
# 1. 复制示例配置文件
cp config.example.json config.json
cp wardrobe/catalog.example.json wardrobe/catalog.json

# 2. 编辑 config.json，填入你所在城市的经纬度和风格偏好
# 3. 通过 /add-clothes 添加你的衣物
# 4. 输入 /outfit 获取明日穿搭
```

## 项目结构

```
IntelliOutfit/
├── SKILL.md                    # Skill 定义（命令、触发、流程）
├── CLAUDE.md                   # 项目说明
├── .gitignore
├── config.example.json         # 配置模板
├── scripts/
│   ├── main.py                 # CLI 入口 (recommend / weather / wardrobe / add)
│   ├── weather.py              # 天气获取（Open-Meteo API，免费无需 Key）
│   ├── wardrobe.py             # 衣橱管理
│   └── recommender.py          # 推荐引擎
├── references/
│   ├── dressing-rules.md       # 穿搭法则（温度分层、配色、风格模板）
│   └── attribute-guide.md      # 衣物属性分类标准
└── wardrobe/
    ├── catalog.example.json     # 示例衣橱
    └── photos/                  # 衣物照片
```

## 穿搭法则

推荐引擎基于 `references/dressing-rules.md` 中的规则运行：

- **温度分层** — 7 个体感温度区间，自动决定叠穿层级和厚度
- **天气修正** — 降雨、大风、湿度、紫外线、温差自动调整单品要求
- **配色法则** — 三色原则、明度拉开、单焦点，5 个配色公式按安全性排序
- **风格模板** — 极简通勤、日系盐系、City Boy、轻机能、简约精致、运动休闲
- **风格一致性** — 鞋款与外层与风格的匹配矩阵，避免频道冲突

每套推荐都会引用具体法则，告诉你「为什么这么搭」。

## 配置

编辑 `config.json`：

```json
{
  "location": {
    "name": "你的城市",
    "latitude": 39.9042,
    "longitude": 116.4074
  },
  "preferences": {
    "style_bias": ["minimal", "japanese-casual"],
    "avoid_colors": []
  }
}
```

- `location` — 经纬度，用于天气 API。可在中国大陆正常访问
- `preferences.style_bias` — 偏好的风格列表，推荐时优先匹配
- `preferences.avoid_colors` — 想避开的颜色

## 技术栈

- Python 3（纯标准库，无第三方依赖）
- [Open-Meteo API](https://open-meteo.com/) — 免费天气数据，无需 API Key
- Claude Code Skill 框架
