# VLA 项目使用指南

## 项目概述

VLA (Very Large Array) 是一个多模块的雷达网络仿真系统，包含以下主要模块：

- **M1**: 轨迹生成模块 - 生成目标的真实轨迹数据
- **M2**: 传感器仿真模块 - 模拟雷达对目标的观测
- **M4**: 态势可视化模块 - 可视化展示轨迹和雷达观测数据

## 目录结构

```
VLA/
├── m1_trajectory_generator/  # M1 轨迹生成模块
├── m2_sensor_simulation/     # M2 传感器仿真模块
├── m4_situation_visualization/ # M4 态势可视化模块
├── output/                   # 输出文件目录
│   ├── m1_trajectories/      # M1 生成的轨迹文件
│   └── m2_tracks/            # M2 生成的雷达观测文件
└── README.md                 # 本使用指南
```

## 安装要求

- Python 3.8+
- 依赖包：
  - M1: 无特殊依赖
  - M2: numpy, filterpy
  - M4: 无特殊依赖（使用Cesium.js在线库）

## 安装步骤

1. **克隆项目**
   ```bash
   git clone <项目地址>
   cd VLA
   ```

2. **安装依赖**
   ```bash
   # 安装M2依赖
   pip install numpy filterpy
   ```

## 使用指南

### M1 轨迹生成模块

**功能**：生成目标的真实轨迹数据，支持设定起飞点、途径点、降落点和时间。

**使用方法**：

```bash
python -m m1_trajectory_generator.main --intent "[目标批号] [机型] 于 [起飞时间] 从 [起飞点] 起飞，途径 [途径点] [途径时间]，降落 [降落点] [降落时间]。"
```

**示例**：

```bash
# 生成从北京到青岛再到上海的轨迹
python -m m1_trajectory_generator.main --intent "0014 民航客机 于 2026-04-22 23:00:00 从 北京大兴国际机场 起飞，途径 青岛胶东国际机场 00:30:00，降落 上海虹桥国际机场 02:00:00。"
```

**输出**：生成的轨迹文件保存在 `output/m1_trajectories/` 目录下，文件名格式为 `trajectory_[目标批号]_[时间戳].json`。

### M2 传感器仿真模块

**功能**：模拟多部雷达对目标的观测，生成带误差的雷达观测数据。

**使用方法**：

```bash
python -m m2_sensor_simulation.main --input <M1轨迹文件路径>
```

**示例**：

```bash
# 处理M1生成的轨迹文件
python -m m2_sensor_simulation.main --input "output/m1_trajectories/trajectory_0014_20260422_231114.json"
```

**输出**：生成的雷达观测文件保存在 `output/m2_tracks/` 目录下，每个雷达生成一个观测文件，以及一个融合航迹文件 `fused_tracks.json`。

### M4 态势可视化模块

**功能**：可视化展示M1生成的真实轨迹和M2生成的雷达观测数据。

**使用方法**：

1. **启动本地服务器**（可选）
   ```bash
   # 在VLA目录下启动服务器
   python -m http.server 8000
   ```

2. **打开可视化界面**
   - 方法1：直接打开 `m4_situation_visualization/index.html` 文件
   - 方法2：通过本地服务器访问 `http://localhost:8000/m4_situation_visualization/index.html`

3. **加载数据**
   - 点击「选择 M1 JSON」按钮，选择M1生成的轨迹文件
   - 点击「选择 M2 JSON」按钮，选择M2生成的融合航迹文件
   - 点击「一键渲染态势」按钮，查看可视化效果

**界面控制**：
- **底图图层开关**：控制显示/隐藏各种底图元素
- **轨迹图层开关**：控制显示/隐藏M1和M2轨迹
- **鼠标悬停**：显示元素名称
- **点击轨迹点**：显示详细信息

## 配置说明

### M2 雷达配置

M2模块的雷达参数可以通过修改 `m2_sensor_simulation/radar_config.json` 文件进行配置。每个雷达包含以下参数：

- `radar_id`：雷达编号
- `name`：雷达名称
- `location`：雷达位置 [经度, 纬度]
- `height`：天线架高（米）
- `max_range`：最大探测距离（公里）
- `beam_width`：波束宽度（度）
- `scan_period`：扫描周期（秒）
- `tactical_role`：战术定位
- `range_error_std`：测距误差标准差（米）
- `azimuth_error_std`：方位角误差标准差（度）
- `elevation_error_std`：俯仰角误差标准差（度）

### M4 可视化配置

M4模块的可视化效果可以通过修改 `m4_situation_visualization/js/main.js` 文件进行配置，包括：

- 雷达威力图颜色
- M1轨迹颜色和样式
- M2轨迹点颜色和样式
- 图层显示状态

## 数据格式

### M1 轨迹文件格式

```json
{
  "target_id": "0014",
  "platform_type": "民航客机",
  "start_time": "2026-04-22T23:00:00",
  "end_time": "2026-04-23T01:06:21",
  "track_points": [
    {
      "time": "2026-04-22T23:00:00",
      "lon": 116.594,
      "lat": 39.509,
      "alt_m": 0,
      "speed_ms": 0,
      "heading_deg": 0,
      "phase": "CLIMBING",
      "rcs_dbsm": 15
    },
    // 更多轨迹点...
  ]
}
```

### M2 融合航迹文件格式

```json
{
  "frame_time": "2026-04-22T23:11:34.153337Z",
  "network_tracks": [
    {
      "time": "2026-04-22T23:19:00+00:00",
      "track_id": "0014",
      "target_id": "0014",
      "source_radars": ["RADAR_01"],
      "obs_lon": 116.8353,
      "obs_lat": 38.0562,
      "obs_alt_m": 10000.07,
      "obs_speed_ms": 239.9941,
      "obs_heading_deg": 112.3013,
      "track_quality": "LOW",
      "snr_avg_db": 139.7901
    },
    // 更多观测点...
  ]
}
```

## 常见问题

1. **M1轨迹生成失败**
   - 检查飞行简令格式是否正确
   - 确保起飞点、途径点、降落点名称正确
   - 检查时间格式是否正确

2. **M2处理速度慢**
   - 减少轨迹点数量
   - 关闭详细日志输出

3. **M4界面加载失败**
   - 确保网络连接正常（需要加载Cesium.js）
   - 检查浏览器控制台是否有错误
   - 尝试使用Chrome或Firefox浏览器

4. **M2观测数据误差过小**
   - 修改 `m2_sensor_simulation/models.py` 中的误差参数
   - 或修改 `m2_sensor_simulation/radar_config.json` 中的误差配置

## 示例工作流

1. **生成轨迹**
   ```bash
   python -m m1_trajectory_generator.main --intent "0015 民航客机 于 2026-04-23 08:00:00 从 上海虹桥国际机场 起飞，降落 北京大兴国际机场 10:00:00。"
   ```

2. **仿真雷达观测**
   ```bash
   python -m m2_sensor_simulation.main --input "output/m1_trajectories/trajectory_0015_20260423_080000.json"
   ```

3. **可视化展示**
   - 打开 `m4_situation_visualization/index.html`
   - 加载M1和M2生成的文件
   - 查看轨迹和观测数据

## 技术支持

如有问题，请联系项目维护人员。

---

**版本**: 1.0.0
**更新日期**: 2026-04-22