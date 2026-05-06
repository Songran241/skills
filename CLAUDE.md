# IntelliOutfit — 智能穿搭助手

根据天气和衣橱自动推荐穿搭方案。

> 本项目的 Skill 定义见 `SKILL.md`。所有命令（`/outfit`、`/add-clothes`、`/wardrobe`）的完整说明以 SKILL.md 为准。

## 项目结构

```
IntelliOutfit/
├── SKILL.md                    # Skill 定义（命令、触发、流程）
├── CLAUDE.md                   # 本文件
├── config.json                 # 位置、偏好设置
├── scripts/
│   ├── main.py                 # CLI 入口
│   ├── weather.py              # 天气获取（Open-Meteo API）
│   ├── wardrobe.py             # 衣橱管理
│   └── recommender.py          # 推荐引擎
├── wardrobe/
│   ├── catalog.json            # 衣物元数据库
│   └── photos/                 # 衣物照片
└── references/
    ├── dressing-rules.md       # 穿搭法则（温度、配色、风格）
    └── attribute-guide.md      # 衣物属性分类标准
```

## CLI 命令

| 命令 | 说明 |
|------|------|
| `python3 scripts/main.py recommend` | 获取穿搭推荐 JSON |
| `python3 scripts/main.py weather` | 获取天气数据 JSON |
| `python3 scripts/main.py wardrobe` | 查看衣橱统计 |
| `python3 scripts/main.py add --data '<json>'` | 添加衣物 |

## 配置

编辑 `config.json`：
- `location`: 经纬度（用于天气 API）
- `preferences.style_bias`: 偏好的风格列表
- `preferences.avoid_colors`: 避免的颜色
