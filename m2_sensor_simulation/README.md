# M2：高保真传感器仿真引擎

## 模块简介

M2是雷达组网仿真系统的**“战场迷雾制造机”**。它接收M1的完美真值，严格遵循电磁波传播物理规律与雷达信号处理逻辑，剥落那些由于距离、地球曲率、地形遮挡或杂波抑制而“看不见”的目标，并给剩下的目标加上量测噪声与滤波平滑，最终输出组网融合后的目标航迹。

## 核心功能

- **雷达组网管理**：管理5部不同类型的雷达（青岛、上海、宁波、南京、合肥）
- **视距与地形遮挡判定**：考虑地球曲率影响的视距计算
- **波束驻留判定**：模拟机械扫描雷达的波束扫过过程
- **信号处理等效**：雷达方程计算、杂波抑制、CFAR检测
- **量测噪声注入**：基于SNR的噪声模型
- **航迹处理**：点迹关联、卡尔曼滤波平滑、航迹生命周期管理
- **并发计算**：多雷达并行处理，确保1秒内完成一帧计算

## 目录结构

```
m2_sensor_simulation/
├── __init__.py              # 模块入口
├── __main__.py              # 命令行入口
├── models.py                # 数据模型定义
├── radar.py                 # 雷达对象模型
├── sensor_simulation.py     # 传感器仿真引擎（核心算法）
├── main.py                  # 命令行接口
├── requirements.txt         # 依赖列表
├── tests/                   # 单元测试
│   ├── __init__.py
│   └── test_m2.py
└── output/                  # 输出目录
    └── m2_tracks/           # 航迹JSON文件
```

## 安装依赖

```bash
pip install filterpy pyproj numpy
```

## 使用方法

### 命令行方式

```bash
# 处理M1输出的轨迹文件
python -m m2_sensor_simulation -i output/m1_trajectories/trajectory_0001_20260422_121746.json

# 自定义输出路径
python -m m2_sensor_simulation -i trajectory.json -o output/tracks.json
```

### Python代码方式

```python
from m2_sensor_simulation import SensorSimulation

# 创建仿真引擎
simulation = SensorSimulation()

# 运行仿真
output = simulation.run_simulation('path/to/m1_trajectory.json')

# 保存输出
simulation.save_output(output, 'output/tracks.json')
```

## 雷达配置

| 雷达编号 | 部署地 | 经纬度 | 天线架高 | 最大探测距离 | 波束宽度 | 扫描周期 | 战术定位 |
|---------|--------|--------|---------|------------|---------|---------|----------|
| RADAR_01 | 青岛 | [120.38, 36.07] | 100m | 400km | 4.5° | 10秒/圈 | 远程对空警戒 |
| RADAR_02 | 上海 | [121.47, 31.23] | 50m | 250km | 2.0° | 6秒/圈 | 精密引导测高三坐标雷达 |
| RADAR_03 | 宁波 | [121.54, 29.86] | 30m | 200km | 1.5° | 4秒/圈 | 近海低空补盲快扫雷达 |
| RADAR_04 | 南京 | [118.78, 32.06] | 80m | 300km | 3.0° | 8秒/圈 | 内陆纵深节点 |
| RADAR_05 | 合肥 | [117.27, 31.86] | 50m | 250km | 2.0° | 6秒/圈 | 二线拦截引导雷达 |

## 输出格式

```json
{
  "frame_time": "2026-04-22T12:17:46Z",
  "network_tracks": [
    {
      "track_id": "0001",
      "source_radars": ["RADAR_01", "RADAR_04"],
      "obs_lon": 120.3815,
      "obs_lat": 36.0705,
      "obs_alt_m": 10050.0,
      "obs_speed_ms": 248.0,
      "obs_heading_deg": 92.0,
      "track_quality": "HIGH",
      "snr_avg_db": 18.5
    }
  ]
}
```

### 字段说明

| 字段 | 说明 |
|------|------|
| frame_time | 帧时间 |
| track_id | 航迹ID（透传M1的target_id） |
| source_radars | 数据源雷达列表 |
| obs_lon | 观测经度 |
| obs_lat | 观测纬度 |
| obs_alt_m | 观测高度（米） |
| obs_speed_ms | 观测速度（米/秒） |
| obs_heading_deg | 观测航向角（度） |
| track_quality | 航迹质量（HIGH/MEDIUM/LOW） |
| snr_avg_db | 平均信噪比（dB） |

## 运行测试

```bash
python -m pytest m2_sensor_simulation/tests/test_m2.py -v
```

## 依赖说明

- **filterpy**：用于卡尔曼滤波
- **pyproj**：用于坐标转换（预留）
- **numpy**：用于数值计算和随机噪声生成

## 注意事项

1. 输入文件必须是M1输出的标准JSON格式
2. 输出文件默认保存在 `output/m2_tracks/` 目录
3. 目标ID会透传M1的target_id，便于调试对比
4. 当目标连续3个扫描周期未被任何雷达发现时，会从航迹列表中删除
