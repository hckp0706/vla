# M1：意图驱动航迹生成器

## 模块简介

M1是雷达组网仿真系统的数据源头模块，扮演"战场导演"角色。它将人类指挥员下达的飞行任务指令（飞行简令），结合真实的地理环境、空域航路规则和飞机性能参数，推演出符合物理规律与航空逻辑的1Hz高精度飞行轨迹数据，并传递给M2（雷达仿真引擎）。

## 核心功能

- **飞行简令解析**：使用正则表达式解析半结构化的飞行简令文本，支持新旧4种格式
- **三级降级航路规划**：EAIP官方数据 → GLM-5.1大模型 → 本地预设航路，确保系统在任何情况下都能生成轨迹
- **EAIP航路规划**：基于BFS算法在真实航路网络中查找最优路径
- **大模型航路点生成**：调用GLM-5.1 API生成航路点，支持军机/民航两种提示词模板
- **航路点验证**：对大模型返回的航路点进行结构、数量、坐标范围、距离等多重验证
- **知识库查询**：支持机场（模糊匹配）、机型、航路、任务类型的查询
- **大圆航线计算**：使用WGS84椭球模型计算地球表面最短路径
- **平滑转弯算法**：基于标准转弯率（3度/秒）实现圆弧平滑过渡
- **高度剖面计算**：模拟起飞→爬升→巡航→下降→降落全过程
- **跑道方向应用**：起飞/降落阶段使用真实跑道方向作为航向
- **动态RCS估算**：根据飞行姿态（机头/侧面/起落架）和任务类型计算雷达散射截面积
- **地形跟随模式**：低空突防、对地攻击等任务支持贴地飞行
- **ADS-B报文生成**：为民航飞机生成符合1090ES标准的ADS-B Out报文（军机不发送ADS-B）

## 系统架构

### 数据流程

```
飞行简令文本
    │
    ▼
IntentParser（解析简令）
    │
    ▼
FlightIntent（解析结果）
    │
    ▼
TrajectoryGenerator._get_route()（获取航路）
    │
    ├── 1. EAIP数据规划航线（优先）
    │       └── BFS搜索航路网络（route_network.json）
    │       └── 大圆航线附近航路点筛选
    ├── 2. 大模型生成航路点（降级）
    │       └── LLMClient → GLM-5.1 API
    │       └── WaypointValidator 验证
    └── 3. 本地预设航路（最终降级）
            └── KnowledgeBase 航路库
    │
    ▼
Waypoint列表（航路点序列）
    │
    ▼
_resolve_waypoints()（解析坐标，EAIP优先→知识库）
    │
    ▼
_generate_track_points()（生成1Hz轨迹）
    │   ├── 大圆航线插值（WGS84椭球模型）
    │   ├── 高度剖面计算（起飞→爬升→巡航→下降→降落）
    │   ├── 跑道方向应用（起飞前5%/降落后5%）
    │   ├── RCS动态估算（机头/侧面/起落架/任务因子）
    │   └── 地形跟随模式（巡航高度限制）
    │
    ▼
ADSBGenerator（生成ADS-B报文，仅民航）
    │   ├── 民航/军机判断
    │   ├── ICAO 24位地址生成
    │   ├── 航班呼号生成
    │   └── 单位换算（米→英尺、m/s→节、m/s→ft/min）
    │
    ▼
TrajectoryOutput（JSON轨迹文件，含ADS-B数据）
    │
    ▼
传递给M2（雷达仿真引擎）
```

### 三级降级策略

| 优先级 | 策略 | 数据源 | 触发条件 |
|--------|------|--------|----------|
| 1 | EAIP数据规划 | eaip_airports.json + route_network.json | 起终点在EAIP机场库中 |
| 2 | 大模型生成 | GLM-5.1 API | EAIP不可用或未匹配 |
| 3 | 本地预设航路 | KnowledgeBase预设航路 | 大模型禁用或调用失败 |

### 模块依赖关系

```
main.py（命令行入口）
    │
    ├── TrajectoryGenerator（轨迹生成核心）
    │       ├── IntentParser（简令解析）
    │       ├── KnowledgeBase（本地知识库）
    │       ├── LLMClient（大模型客户端）
    │       │       └── Config（配置管理）
    │       ├── WaypointValidator（航路点验证）
    │       │       └── Config（配置管理）
    │       └── EAIPLoader（EAIP数据加载器）
    │
    └── Models（数据模型定义）
            ├── FlightPhase（飞行阶段枚举）
            ├── MissionType（任务类型枚举）
            ├── FlightIntent（飞行简令）
            ├── TrackPoint（轨迹点）
            ├── TrajectoryOutput（航迹输出）
            ├── Waypoint（航路点）
            ├── AircraftPerformance（机型性能）
            ├── MissionProfile（任务配置）
            └── GeoLocation（地理位置）
```

## 目录结构

```
m1_trajectory_generator/
├── __init__.py                    # 模块入口，导出核心类
├── __main__.py                    # 命令行入口
├── models.py                      # 数据模型定义（10个核心数据结构，含ADS-B）
├── parser.py                      # 飞行简令解析器（4种格式正则匹配）
├── knowledge_base.py              # 本地知识库（机场/机型/航路/任务配置）
├── trajectory_generator.py        # 轨迹生成核心引擎（大圆航线/高度剖面/RCS/转弯）
├── ads_b_generator.py             # ADS-B报文生成器（民航1090ES标准，军机不发送）
├── eaip_loader.py                 # EAIP官方数据加载器（机场/航路点查询）
├── llm_client.py                  # 大模型API客户端（GLM-5.1提示词生成与调用）
├── waypoint_validator.py          # 航路点验证器（结构/数量/坐标/距离验证）
├── config.py                      # 配置管理（大模型/降级/日志配置）
├── main.py                        # 命令行接口（参数解析/知识库查询）
├── requirements.txt               # 依赖列表
├── knowledge_base_extended.json   # 扩展知识库数据
├── data/                          # EAIP数据文件目录
│   ├── eaip_airports.json         # 184个EAIP机场数据（57个有精确坐标）
│   ├── enr_4_4_waypoints.json     # 1418个标准航路点坐标
│   └── route_network.json         # 航路网络拓扑（558KB）
├── tests/                         # 单元测试
│   ├── __init__.py
│   └── test_m1.py                 # 4个测试类，19个测试用例
└── output/                        # 输出目录
    └── m1_trajectories/           # 轨迹JSON文件
```

## 安装依赖

```bash
pip install -r requirements.txt
```

依赖列表：
- `geographiclib>=1.52`：WGS84大圆航线计算
- `numpy>=1.24.0`：数值计算
- `requests>=2.31.0`：大模型API调用

## 配置说明

### 大模型配置

通过 `config.py` 或环境变量配置：

| 配置项 | 默认值 | 环境变量 | 说明 |
|--------|--------|----------|------|
| LLM_ENABLED | True | LLM_ENABLED | 是否启用大模型 |
| LLM_API_KEY | - | LLM_API_KEY | GLM-5.1 API密钥 |
| LLM_MODEL | GLM-5.1 | LLM_MODEL | 模型名称 |
| LLM_API_URL | - | LLM_API_URL | API地址 |
| LLM_TEMPERATURE | 0.7 | LLM_TEMPERATURE | 生成温度 |
| LLM_MAX_TOKENS | 2000 | LLM_MAX_TOKENS | 最大token数 |
| FALLBACK_TO_LOCAL | True | - | 降级到本地航路 |
| MAX_WAYPOINTS | 10 | - | 航路点数量上限 |
| MIN_WAYPOINTS | 3 | - | 航路点数量下限 |
| LOG_LEVEL | INFO | - | 日志级别 |

### 命令行覆盖

```bash
# 强制使用本地预设航路，不调用大模型
python -m m1_trajectory_generator -i "..." --use-local-route

# 指定大模型API密钥
python -m m1_trajectory_generator -i "..." --llm-api-key YOUR_KEY
```

## 使用方法

### 命令行方式

```bash
# 正常飞行
python -m m1_trajectory_generator -i "0001 民航客机 于 2026-04-20 09:20:30 从 北京大兴国际机场 起飞，降落 上海虹桥国际机场。"

# 低空突防任务
python -m m1_trajectory_generator -i "0002 歼-20 于 2026-04-20 10:00:00 从 北京大兴国际机场 起飞，执行低空突防任务，降落 上海虹桥国际机场。"

# 带途径点的飞行
python -m m1_trajectory_generator -i "0003 民航客机 于 2026-04-20 09:20:30 从 北京大兴国际机场 起飞，途径 西安咸阳国际机场，降落 上海虹桥国际机场。"

# 从文件读取简令
python -m m1_trajectory_generator -f intent.txt -o output/trajectory.json

# 强制使用本地航路（不调用大模型）
python -m m1_trajectory_generator -i "..." --use-local-route
```

### 查询知识库

```bash
# 列出所有机场
python -m m1_trajectory_generator --list-airports

# 列出所有机型
python -m m1_trajectory_generator --list-aircraft

# 列出所有航路
python -m m1_trajectory_generator --list-routes

# 列出所有任务类型
python -m m1_trajectory_generator --list-missions
```

### Python代码方式

```python
from m1_trajectory_generator import TrajectoryGenerator, KnowledgeBase

# 创建生成器
kb = KnowledgeBase()
generator = TrajectoryGenerator(kb)

# 生成轨迹
intent_text = "0001 民航客机 于 2026-04-20 09:20:30 从 北京大兴国际机场 起飞，降落 上海虹桥国际机场。"
trajectory = generator.generate(intent_text)

# 保存结果
if trajectory:
    trajectory.save_to_file("output.json")
    print(f"生成 {len(trajectory.track_points)} 个轨迹点")
```

## 飞行简令格式

### 新格式（推荐）

**带途径点**：
```
[批号] [机型] [任务类型] 于 [起飞时间] 从 [起飞地点] 起飞，[途径动作] [途径地点]，[降落动作] [降落地点]。
```

**简化格式**：
```
[批号] [机型] [任务类型] 于 [起飞时间] 从 [起飞地点] 起飞，[降落动作] [降落地点]。
```

### 旧格式（兼容）

**带途径点**：
```
[批号] [机型] 于 [起飞时间] 从 [起飞地点] 起飞，执行[任务类型]任务，[途径动作] [途径地点] [途径时间]，[降落动作] [降落地点] [降落时间]。
```

**简化格式**：
```
[批号] [机型] 于 [起飞时间] 从 [起飞地点] 起飞，执行[任务类型]任务，[降落动作] [降落地点]。
```

### 格式说明

| 要素 | 格式 | 是否必填 | 示例 |
|------|------|----------|------|
| 批号 | 数字 | 是 | 0001 |
| 机型 | 中文/英文 | 是 | 民航客机、歼-20、F-22 |
| 任务类型 | 中文 | 否 | 低空突防、高空侦察、巡逻 |
| 起飞时间 | YYYY-MM-DD HH:MM:SS | 是 | 2026-04-20 09:20:30 |
| 起飞地点 | 中文地名 | 是 | 北京大兴国际机场、成田国际机场 |
| 途径地点 | 中文地名 | 否 | 西安咸阳国际机场 |
| 途径时间 | HH:MM:SS | 否（旧格式） | 10:20:00 |
| 降落地点 | 中文地名 | 是 | 上海虹桥国际机场 |
| 降落时间 | HH:MM:SS | 否（旧格式） | 12:40:00 |

> **注意**：新格式中任务类型作为第三个参数（机型之后），无需"执行...任务"句式。仅起飞时间为必填项，途径时间和降落时间由系统根据机型性能自动计算。

## 支持的任务类型

| 任务类型 | 描述 | 典型高度 | 典型速度 | 高度因子 | 速度因子 | 地形跟随 | 低可探测 |
|----------|------|----------|----------|----------|----------|----------|----------|
| 正常飞行 | 按标准航线和高度飞行 | 10000m | 250m/s | 1.0 | 1.0 | 否 | 否 |
| 低空突防 | 利用地形掩护突破防空系统 | 500m | 280m/s | 0.1 | 0.9 | 是 | 否 |
| 高空侦察 | 在高空进行情报收集 | 15000m | 200m/s | 1.5 | 0.8 | 否 | 否 |
| 巡逻 | 在指定区域进行空中巡逻 | 8000m | 200m/s | 1.0 | 0.7 | 否 | 否 |
| 拦截 | 快速接近并拦截目标 | 10000m | 350m/s | 0.8 | 1.2 | 否 | 否 |
| 护航 | 保护友方飞机 | 10000m | 250m/s | 1.0 | 1.0 | 否 | 否 |
| 反舰 | 攻击海上目标 | 1000m | 280m/s | 0.3 | 0.9 | 是 | 否 |
| 对地攻击 | 攻击地面目标 | 800m | 280m/s | 0.2 | 0.9 | 是 | 否 |
| 电子战 | 进行电子干扰和压制 | 8000m | 200m/s | 1.0 | 0.8 | 否 | 否 |
| 空中加油 | 为其他飞机提供燃油 | 9000m | 180m/s | 1.2 | 0.7 | 否 | 否 |
| 训练 | 进行飞行训练 | 5000m | 200m/s | 1.0 | 0.8 | 否 | 否 |

## 输出格式

输出为JSON格式，包含以下字段：

### 民航飞机输出（含ADS-B）

```json
{
  "target_id": "0001",
  "platform_type": "民航客机",
  "mission_type": "正常飞行",
  "has_adsb": true,
  "track_points": [
    {
      "time": "2026-04-20T09:20:30Z",
      "lon": 116.594,
      "lat": 39.509,
      "alt_m": 25.0,
      "speed_ms": 240.0,
      "heading_deg": 180.0,
      "vertical_rate_ms": 0.0,
      "rcs_dbsm": 13.0,
      "phase": "GROUND_TAKEOFF",
      "adsb": {
        "icao24": "0DB2EC",
        "callsign": "CCA1001 ",
        "altitude_ft": 82.0,
        "ground_speed_kt": 466.5,
        "track": 180.0,
        "vertical_rate_fpm": 0.0,
        "lat": 39.509,
        "lon": 116.594,
        "on_ground": true,
        "squawk": "2000",
        "emitter_category": 4,
        "message_type": "adsb_icao"
      }
    }
  ]
}
```

### 军机输出（无ADS-B）

```json
{
  "target_id": "0002",
  "platform_type": "歼-20",
  "mission_type": "低空突防",
  "has_adsb": false,
  "track_points": [
    {
      "time": "2026-04-20T10:00:00Z",
      "lon": 116.594,
      "lat": 39.509,
      "alt_m": 25.0,
      "speed_ms": 280.0,
      "heading_deg": 180.0,
      "vertical_rate_ms": 0.0,
      "rcs_dbsm": -5.0,
      "phase": "GROUND_TAKEOFF"
    }
  ]
}
```

### ADS-B报文字段说明

| 字段 | 单位 | 说明 |
|------|------|------|
| icao24 | - | ICAO 24位地址（十六进制），全球唯一标识一架飞机 |
| callsign | - | 航班呼号/注册号，如"CCA1234" |
| altitude_ft | 英尺 | 气压高度（基于1013.25hPa标准大气压） |
| ground_speed_kt | 节 | 地速（海里/小时） |
| track | 度 | 地面航迹角（0-360，真北为0） |
| vertical_rate_fpm | 英尺/分钟 | 垂直速率（正为爬升，负为下降） |
| lat | 度 | 纬度 |
| lon | 度 | 经度 |
| on_ground | - | 是否在地面（起飞/降落阶段为true） |
| squawk | - | 应答机编码（4位八进制，如"2000"） |
| emitter_category | - | 飞机类别代码（3=中型、4=中型偏大、5=重型） |
| message_type | - | 报文类型标识（"adsb_icao"） |

### ADS-B发射类别代码

| 代码 | 类别 | 典型机型 |
|------|------|----------|
| 1 | A型 | 轻型飞机 |
| 2 | B型 | 小型螺旋桨 |
| 3 | C型 | 中型（B737、A320） |
| 4 | D型 | 中型偏大（A330、A350） |
| 5 | 重型 | 大型（B747、A380、B777） |

### 轨迹点字段说明

| 字段 | 单位 | 说明 |
|------|------|------|
| time | ISO时间 | 时间戳（1Hz频率） |
| lon | 度 | 经度（东经为正，保留6位小数） |
| lat | 度 | 纬度（北纬为正，保留6位小数） |
| alt_m | 米 | 海拔高度（保留1位小数） |
| speed_ms | 米/秒 | 地速（保留1位小数） |
| heading_deg | 度 | 航向角（0-360，真北为0，保留1位小数） |
| vertical_rate_ms | 米/秒 | 垂直速率（正为爬升，负为下降，保留1位小数） |
| rcs_dbsm | dBsm | 雷达散射截面积（保留1位小数） |
| phase | 枚举 | 飞行阶段 |

### 飞行阶段枚举

| 阶段 | 说明 | RCS特征 |
|------|------|---------|
| GROUND_TAKEOFF | 起飞阶段（爬升进度<10%） | 起落架放下，RCS增加 |
| CLIMBING | 爬升阶段（爬升进度≥10%） | 正常RCS |
| CRUISING | 巡航阶段 | 正常RCS，转弯时侧面暴露 |
| DESCENDING | 下降阶段（下降进度<90%） | 正常RCS |
| LANDING | 降落阶段（下降进度≥90%） | 起落架放下，RCS增加 |

### RCS估算规则

RCS（雷达散射截面积）的动态计算遵循以下规则：

1. **基准值**：机头方向RCS（`nose_rcs_dbsm`）
2. **起降增量**：起飞/降落阶段起落架放下，RCS增加 `gear_rcs_increment`
3. **转弯增量**：转弯时侧面暴露，RCS从机头值向侧面值（`side_rcs_dbsm`）线性插值
4. **任务因子**：根据任务类型的 `rcs_factor` 调整（电子战1.2倍，低空突防0.8倍等）

## 知识库内容

### 机场数据

包含100+机场的经纬度坐标、海拔高度和跑道方向：

- **中国国内机场**：北京、上海、广州、深圳等80+民用机场（含跑道方向）
- **日本机场**：成田、羽田、关西、福冈、札幌、冲绳那霸等
- **韩国机场**：仁川、金浦、釜山、济州等
- **美军基地**：三泽、横田、嘉手纳、乌山、群山等

支持精确匹配、包含匹配和相似度匹配（≥0.4）三种模糊查询方式。

### 机型数据

包含60+机型的性能参数：

- **民航客机**：波音737/747/777/787、空客A320/A330/A350/A380等
- **中国军机**：歼-10/11/15/16/20/35、轰-6、运-20、直-10、空警-2000等
- **美国军机**：F-15/16/22/35、F/A-18、F-14、P-8A、U-2、RQ-4、E-3、E-8、RC-135、B-52/B-1B/B-2、C-130/C-17等
- **日本军机**：F-2、F-15J、F-35A、P-1等
- **韩国军机**：KF-21、F-15K、F-16K等
- **无人机**：翼龙、捕食者、全球鹰等

每个机型包含：巡航速度/高度、爬升/下降率、机头/侧面RCS、起落架RCS增量、最大/最小速度。

### 航路数据

包含20+条预设航路：

- **民航航路**：京沪、京广、沪广、京陕沪等国内航线；中日、中韩、日韩国际航线
- **军用航路**：低空突防走廊、东海巡逻、黄海巡逻、冲绳-横田、三泽-乌山等

### EAIP数据

基于中国民航局2026 Nr.04 EAIP文件提取：

| 数据文件 | 内容 | 数量 |
|----------|------|------|
| eaip_airports.json | 机场数据（ICAO代码、中文名、坐标、海拔、跑道方向） | 184个（57个有精确坐标，37个有跑道方向） |
| enr_4_4_waypoints.json | 标准航路点坐标 | 1418个 |
| route_network.json | 航路网络拓扑（节点连接关系） | 558KB |

## 真实轨迹生成模板

### 模板1：美国F-22隐身战斗机（冲绳→东京）

```bash
python -m m1_trajectory_generator -i "0001 F-22 于 2026-04-20 09:20:30 从 嘉手纳空军基地 起飞，执行高空侦察任务，降落 成田国际机场。"
```

**特点**：
- 隐身性能：RCS约-15dBsm
- 巡航高度：6000m
- 飞行速度：280m/s
- 航线：冲绳嘉手纳→东京成田

### 模板2：美国P-8A反潜巡逻机（韩国→日本）

```bash
python -m m1_trajectory_generator -i "0002 P-8A 于 2026-04-20 10:00:00 从 乌山空军基地 起飞，执行巡逻任务，降落 三泽空军基地。"
```

**特点**：
- 反潜巡逻：基于波音737平台
- 巡航高度：8000m
- 飞行速度：220m/s
- 航线：韩国乌山→日本三泽

### 模板3：美国U-2高空侦察机（东京→冲绳）

```bash
python -m m1_trajectory_generator -i "0003 U-2 于 2026-04-20 12:00:00 从 横田空军基地 起飞，执行高空侦察任务，降落 嘉手纳空军基地。"
```

**特点**：
- 高空飞行：巡航高度20000m
- 飞行速度：200m/s
- 侦察任务：专门用于高空情报收集
- 航线：东京横田→冲绳嘉手纳

### 模板4：日本F-35A隐身战斗机（东京→韩国）

```bash
python -m m1_trajectory_generator -i "0004 F-35A 于 2026-04-20 14:30:00 从 成田国际机场 起飞，执行拦截任务，降落 仁川国际机场。"
```

**特点**：
- 隐身性能：RCS约-10dBsm
- 巡航高度：5500m
- 飞行速度：280m/s
- 航线：东京成田→韩国仁川

### 模板5：韩国KF-21战斗机（首尔→东京）

```bash
python -m m1_trajectory_generator -i "0005 KF-21 于 2026-04-20 16:00:00 从 仁川国际机场 起飞，执行训练任务，降落 羽田国际机场。"
```

**特点**：
- 韩国自研：4.5代战斗机
- 巡航高度：5000m
- 飞行速度：280m/s
- 航线：韩国仁川→东京羽田

### 模板6：中国歼-20隐身战斗机（北京→上海）

```bash
python -m m1_trajectory_generator -i "0006 歼-20 于 2026-04-20 08:00:00 从 北京大兴国际机场 起飞，执行低空突防任务，降落 上海虹桥国际机场。"
```

**特点**：
- 隐身性能：RCS约-10dBsm
- 低空突防：飞行高度500m
- 飞行速度：280m/s
- 航线：北京大兴→上海虹桥

### 模板7：民航客机（北京→广州）

```bash
python -m m1_trajectory_generator -i "0007 波音737 于 2026-04-20 09:00:00 从 北京首都国际机场 起飞，降落 广州白云国际机场。"
```

**特点**：
- 民用航班：标准民航客机
- 巡航高度：10668m
- 飞行速度：230m/s
- 航线：北京首都→广州白云

### 模板8：轰炸机（西安→青岛）

```bash
python -m m1_trajectory_generator -i "0008 轰-6 于 2026-04-20 11:00:00 从 西安咸阳国际机场 起飞，执行训练任务，降落 青岛胶东国际机场。"
```

**特点**：
- 战略轰炸机：中国主力轰炸机
- 巡航高度：8000m
- 飞行速度：250m/s
- 航线：西安咸阳→青岛胶东

## API参考

### TrajectoryGenerator

轨迹生成核心类。

```python
generator = TrajectoryGenerator(knowledge_base=None)
```

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `generate(intent_text)` | 根据飞行简令生成轨迹 | `TrajectoryOutput` 或 `None` |

### IntentParser

飞行简令解析器。

```python
parser = IntentParser(base_date=None)
```

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `parse(intent_text)` | 解析飞行简令 | `FlightIntent` 或 `None` |
| `validate(intent)` | 验证解析结果 | `(is_valid, errors, warnings)` |
| `parse_and_validate(intent_text)` | 解析并验证 | `(intent, is_valid, errors, warnings)` |

### KnowledgeBase

本地知识库。

```python
kb = KnowledgeBase()
```

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `get_geo_location(name)` | 查询地理位置（模糊匹配） | `GeoLocation` 或 `None` |
| `get_aircraft_performance(name)` | 查询机型性能（模糊匹配） | `AircraftPerformance` 或 `None` |
| `get_mission_profile(mission_type)` | 查询任务配置 | `MissionProfile` 或 `None` |
| `get_route(start, end, aircraft)` | 查询航路 | `List[str]` 或 `None` |
| `get_waypoint(name)` | 查询导航点 | `Waypoint` 或 `None` |
| `list_airports()` | 列出所有机场 | `List[str]` |
| `list_aircraft()` | 列出所有机型 | `List[str]` |
| `list_routes()` | 列出所有航路 | `List[str]` |

### EAIPLoader

EAIP数据加载器。

```python
loader = EAIPLoader()
```

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `get_airport_by_icao(icao_code)` | 根据ICAO代码获取机场 | `EAIPAirport` 或 `None` |
| `get_airport_by_name(name)` | 根据中文名称获取机场 | `EAIPAirport` 或 `None` |
| `search_airport(query)` | 搜索机场（模糊匹配） | `EAIPAirport` 或 `None` |
| `get_waypoint(name)` | 获取航路点 | `EAIPWaypoint` 或 `None` |
| `has_airport_data()` | 检查是否有机场数据 | `bool` |
| `has_waypoint_data()` | 检查是否有航路点数据 | `bool` |

### LLMClient

大模型客户端。

```python
client = LLMClient(api_key=None, model=None)
```

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `generate_prompt(intent_dict)` | 生成提示词（军机/民航模板） | `str` |
| `generate_route(prompt)` | 调用大模型生成航路点 | `dict` 或 `None` |

### WaypointValidator

航路点验证器。

```python
WaypointValidator.validate(waypoints_data)
```

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `validate(waypoints_data)` | 验证航路点数据 | `(is_valid, errors)` |

验证规则：
- JSON结构验证：必须是包含 `waypoints` 字段的字典
- 航路点数量：3-10个（可配置）
- 坐标范围：纬度 -90~90，经度 -180~180
- 高度范围：0-30000米
- 相邻航路点距离：1km-500km

### ADSBGenerator

ADS-B报文生成器，仅为民航飞机生成ADS-B Out报文。

```python
from m1_trajectory_generator import ADSBGenerator, is_civil_aircraft

# 判断是否为民航飞机
is_civil = is_civil_aircraft("民航客机")  # True
is_civil = is_civil_aircraft("歼-20")     # False

# 创建生成器
gen = ADSBGenerator(target_id="0001", platform_type="民航客机")
```

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `is_civil_aircraft(platform_type)` | 判断是否为民航飞机 | `bool` |
| `generate_message(track_point)` | 为单个轨迹点生成ADS-B报文 | `ADSBMessage` 或 `None` |
| `generate_messages(track_points)` | 批量生成ADS-B报文 | `List[ADSBMessage]` |

**民航/军机判断规则**：
- 包含民航关键词（民航、客机、波音、空客等）→ 民航（发送ADS-B）
- 包含军机关键词（歼、轰、运、F-、B-、P-8等）→ 军机（不发送ADS-B）
- 无法判断 → 默认军机（安全假设）

## 运行测试

```bash
python -m pytest m1_trajectory_generator/tests/test_m1.py -v
```

测试覆盖：
- `TestIntentParser`：简令解析测试（4个用例）
- `TestKnowledgeBase`：知识库查询测试（7个用例）
- `TestTrajectoryGenerator`：轨迹生成测试（7个用例，含时间序列、高度剖面、航向连续性、RCS值、JSON输出等）
- `TestIntegration`：集成测试（1个完整流程用例）
- `TestADSBGenerator`：ADS-B生成测试（9个用例，含民航/军机判断、ICAO24生成、报文生成、地面阶段、JSON输出等）

## 依赖说明

| 依赖 | 版本 | 用途 |
|------|------|------|
| geographiclib | ≥1.52 | WGS84大圆航线计算，使用椭球模型 |
| numpy | ≥1.24.0 | 数值计算 |
| requests | ≥2.31.0 | GLM-5.1大模型API调用 |

## 注意事项

1. 时间格式必须严格遵循 `YYYY-MM-DD HH:MM:SS` 规范
2. 地名支持模糊匹配，但建议使用完整名称以提高匹配精度
3. 如果所需速度超出机型限制，系统会自动调整并记录警告
4. 输出文件默认保存在 `output/m1_trajectories/` 目录
5. 系统根据机型性能自动计算到达时间，无需手动指定
6. 支持的机场和机型可通过 `--list-airports` 和 `--list-aircraft` 查询
7. 使用 `--use-local-route` 可跳过大模型调用，使用本地预设航路
8. EAIP数据优先于大模型和本地预设航路，确保航线真实性
9. 跑道方向数据覆盖37个主要机场，起飞/降落阶段自动应用
10. 大模型生成的航路点会临时添加到知识库，用于后续坐标解析
11. ADS-B报文仅为民航飞机生成，军机（尤其是敌方军机）不发送ADS-B（`has_adsb=false`）
12. ADS-B中的ICAO 24位地址基于批号和机型确定性生成，同一架飞机每次生成相同地址
13. ADS-B高度单位为英尺（ft），速度单位为节（kt），垂直速率单位为英尺/分钟（fpm）

## 更新日志

### 2026-05-08 更新

1. **新增ADS-B报文生成**：为民航飞机生成符合1090ES标准的ADS-B Out报文
2. **民航/军机自动判断**：基于机型名称关键词自动判断是否为民航飞机
3. **ICAO 24位地址生成**：使用确定性哈希算法为每架民航飞机生成唯一ICAO地址
4. **航班呼号生成**：根据航空公司代码和批号自动生成航班呼号
5. **输出格式增强**：轨迹点中嵌入ADS-B报文字段，军机无此字段
6. **修复跑道方向方法名**：修正`_get_runway_direction`→`_get_airport_runway`

### 2026-05-07 更新

1. **集成跑道方向**：起飞/降落阶段使用真实跑道方向作为航向
2. **补充机场跑道数据**：跑道数据从22个增加到37个机场
3. **完善航路网络**：构建了包含1418个航路点的完整航路网络拓扑
4. **BFS路径规划**：实现基于真实航路网络的自动路径规划

### 2026-04-22 更新

1. **移除前端界面**：取消了M1相关的网页功能模块，专注于后端航迹生成功能
2. **优化时间计算**：不再依赖到达时间，仅基于出发时间和飞机性能参数计算飞行时间
3. **扩展知识库**：
   - **机场数据**：新增日本、韩国机场及美军基地
   - **机型数据**：新增美日韩军机，包括F-22、P-8A、F-35、U-2等
