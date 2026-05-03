"""
M1模块数据模型定义

本模块定义了意图驱动航迹生成器所需的所有数据结构，包括：
- 飞行阶段枚举
- 飞行任务类型枚举
- 飞行简令数据结构
- 轨迹点数据结构
- 航迹输出数据结构
- 航路点数据结构
- 机型性能数据结构
- 任务配置数据结构
- 地理位置数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict
import json


class FlightPhase(Enum):
    """
    飞行阶段枚举
    
    用于标识飞机在某一时刻所处的飞行状态，影响RCS计算和高度变化
    """
    GROUND_TAKEOFF = "GROUND_TAKEOFF"  # 起飞阶段：飞机在地面加速起飞，起落架放下
    CLIMBING = "CLIMBING"              # 爬升阶段：飞机起飞后爬升至巡航高度
    CRUISING = "CRUISING"              # 巡航阶段：飞机在巡航高度平飞
    DESCENDING = "DESCENDING"          # 下降阶段：飞机从巡航高度下降
    LANDING = "LANDING"                # 降落阶段：飞机进近降落，起落架放下


class MissionType(Enum):
    """
    飞行任务类型枚举
    
    不同的任务类型会影响：
    - 飞行高度（低空突防飞行高度低，高空侦察飞行高度高）
    - 飞行速度（拦截任务需要高速）
    - RCS特征（隐身任务RCS降低）
    - 飞行模式（地形跟随等）
    """
    NORMAL_FLIGHT = "正常飞行"                      # 正常飞行：按标准航线和高度飞行
    LOW_ALTITUDE_PENETRATION = "低空突防"           # 低空突防：利用地形掩护突破防空系统
    HIGH_ALTITUDE_RECONNAISSANCE = "高空侦察"       # 高空侦察：在高空进行情报收集
    PATROL = "巡逻"                                 # 巡逻：在指定区域进行空中巡逻
    INTERCEPT = "拦截"                              # 拦截：快速接近并拦截目标
    ESCORT = "护航"                                 # 护航：保护友方飞机
    ANTI_SHIP = "反舰"                              # 反舰：攻击海上目标
    GROUND_ATTACK = "对地攻击"                      # 对地攻击：攻击地面目标
    ELECTRONIC_WARFARE = "电子战"                   # 电子战：进行电子干扰和压制
    AIR_REFUELING = "空中加油"                      # 空中加油：为其他飞机提供燃油
    TRAINING = "训练"                               # 训练：进行飞行训练


@dataclass
class FlightIntent:
    """
    飞行简令数据结构
    
    存储从飞行简令文本中解析出的所有要素信息
    
    属性说明：
        target_id: 目标批号，唯一标识一架飞机，如"0001"
        platform_type: 机型，如"民航客机"、"歼-20"
        takeoff_time: 起飞时间，datetime对象
        loc_start: 起飞地点名称，如"北京大兴国际机场"
        mission_type: 飞行任务类型，MissionType枚举
        action_mid: 途径动作，如"途径"、"经停"
        loc_mid: 途径地点名称
        time_mid: 途径时间（仅时分秒，如"10:20:00"）
        action_end: 降落动作，如"降落"、"抵达"
        loc_end: 降落地点名称
        time_end: 降落时间（仅时分秒，如"12:40:00"）
    """
    target_id: str                    # 目标批号
    platform_type: str                # 机型
    takeoff_time: datetime            # 起飞时间
    loc_start: str                    # 起飞地点
    mission_type: Optional[MissionType] = None  # 飞行任务类型
    action_mid: Optional[str] = None  # 途径动作（途径/经停等）
    loc_mid: Optional[str] = None     # 途径地点
    time_mid: Optional[str] = None    # 途径时间（HH:MM:SS格式）
    action_end: Optional[str] = None  # 降落动作（降落/抵达等）
    loc_end: Optional[str] = None     # 降落地点
    time_end: Optional[str] = None    # 降落时间（HH:MM:SS格式）

    def to_dict(self) -> dict:
        """转换为字典格式，用于JSON序列化"""
        return {
            'target_id': self.target_id,
            'platform_type': self.platform_type,
            'mission_type': self.mission_type.value if self.mission_type else None,
            'takeoff_time': self.takeoff_time.isoformat(),
            'loc_start': self.loc_start,
            'action_mid': self.action_mid,
            'loc_mid': self.loc_mid,
            'time_mid': self.time_mid,
            'action_end': self.action_end,
            'loc_end': self.loc_end,
            'time_end': self.time_end
        }


@dataclass
class TrackPoint:
    """
    轨迹点数据结构
    
    存储飞机在某一时刻的所有状态信息，以1Hz频率生成
    
    属性说明：
        time: 时间戳，datetime对象
        lon: 经度，单位：度，范围：-180到180，东经为正
        lat: 纬度，单位：度，范围：-90到90，北纬为正
        alt_m: 海拔高度，单位：米，相对于平均海平面
        speed_ms: 地速，单位：米/秒，飞机相对于地面的速度
        heading_deg: 航向角，单位：度，范围：0到360，以真北为0度，顺时针增加
        vertical_rate_ms: 垂直速率，单位：米/秒，正值表示爬升，负值表示下降，0表示平飞
        rcs_dbsm: 雷达散射截面积，单位：分贝平方米(dBsm)，值越大越容易被雷达发现
        phase: 飞行阶段，FlightPhase枚举
    """
    time: datetime                    # 时间戳
    lon: float                        # 经度（度）
    lat: float                        # 纬度（度）
    alt_m: float                      # 海拔高度（米）
    speed_ms: float                   # 地速（米/秒）
    heading_deg: float                # 航向角（度，0-360）
    vertical_rate_ms: float           # 垂直速率（米/秒，正为爬升，负为下降）
    rcs_dbsm: float                   # 雷达散射截面积（dBsm）
    phase: FlightPhase                # 飞行阶段

    def to_dict(self) -> dict:
        """转换为字典格式，用于JSON序列化"""
        return {
            'time': self.time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'lon': round(self.lon, 6),
            'lat': round(self.lat, 6),
            'alt_m': round(self.alt_m, 1),
            'speed_ms': round(self.speed_ms, 1),
            'heading_deg': round(self.heading_deg, 1),
            'vertical_rate_ms': round(self.vertical_rate_ms, 1),
            'rcs_dbsm': round(self.rcs_dbsm, 1),
            'phase': self.phase.value
        }


@dataclass
class TrajectoryOutput:
    """
    航迹输出数据结构
    
    存储完整的航迹信息，包含目标信息和所有轨迹点
    
    属性说明：
        target_id: 目标批号
        platform_type: 机型
        mission_type: 飞行任务类型（字符串形式）
        track_points: 轨迹点列表，按时间顺序排列
    """
    target_id: str                    # 目标批号
    platform_type: str                # 机型
    mission_type: Optional[str] = None  # 飞行任务类型
    track_points: List[TrackPoint] = field(default_factory=list)  # 轨迹点列表

    def to_dict(self) -> dict:
        """转换为字典格式，用于JSON序列化"""
        return {
            'target_id': self.target_id,
            'platform_type': self.platform_type,
            'mission_type': self.mission_type,
            'track_points': [p.to_dict() for p in self.track_points]
        }

    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def save_to_file(self, filepath: str):
        """保存到JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())


@dataclass
class Waypoint:
    """
    航路点数据结构
    
    存储航路上的一个导航点信息
    
    属性说明：
        name: 航路点名称，如"AGVAR"、"北京大兴国际机场"
        lon: 经度，单位：度
        lat: 纬度，单位：度
        alt_m: 海拔高度，单位：米，用于地形跟随计算
    """
    name: str                          # 航路点名称
    lon: float                         # 经度（度）
    lat: float                         # 纬度（度）
    alt_m: float = 0.0                 # 海拔高度（米）

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'name': self.name,
            'lon': self.lon,
            'lat': self.lat,
            'alt_m': self.alt_m
        }


@dataclass
class AircraftPerformance:
    """
    机型性能数据结构
    
    存储某一机型的飞行性能参数和电磁特征
    
    属性说明：
        name: 机型名称，如"民航客机"、"歼-20"
        cruise_speed_ms: 巡航速度，单位：米/秒，飞机在巡航阶段的标准速度
        cruise_alt_m: 巡航高度，单位：米，飞机巡航时的标准飞行高度
        climb_rate_ms: 爬升率，单位：米/秒，飞机起飞后的垂直爬升速度
        descent_rate_ms: 下降率，单位：米/秒，飞机降落前的垂直下降速度
        nose_rcs_dbsm: 机头RCS，单位：dBsm，飞机正前方的雷达散射截面积
        side_rcs_dbsm: 侧面RCS，单位：dBsm，飞机侧面的雷达散射截面积（通常比机头大）
        gear_rcs_increment: 起落架RCS增量，单位：dBsm，放下起落架后RCS的增加值
        max_speed_ms: 最大速度，单位：米/秒，飞机能达到的最大速度
        min_speed_ms: 最小速度，单位：米/秒，飞机保持飞行的最小速度（失速速度）
        description: 机型描述，中文说明该机型的特点和用途
    
    RCS说明：
        RCS（雷达散射截面积）反映飞机被雷达发现的难易程度
        - 正值越大，越容易被发现（如大型客机）
        - 负值表示隐身性能好（如歼-20约-10dBsm，F-22约-15dBsm）
        - 民航客机机头RCS约5dBsm，侧面约15dBsm
        - 隐身战机机头RCS可达-10到-20dBsm
    """
    name: str                          # 机型名称
    cruise_speed_ms: float             # 巡航速度（米/秒）
    cruise_alt_m: float                # 巡航高度（米）
    climb_rate_ms: float               # 爬升率（米/秒）
    descent_rate_ms: float             # 下降率（米/秒）
    nose_rcs_dbsm: float               # 机头RCS（dBsm）
    side_rcs_dbsm: float               # 侧面RCS（dBsm）
    gear_rcs_increment: float          # 起落架RCS增量（dBsm）
    max_speed_ms: float = 0.0          # 最大速度（米/秒）
    min_speed_ms: float = 50.0         # 最小速度（米/秒）
    description: str = ""              # 机型描述

    def __post_init__(self):
        """初始化后处理：如果未指定最大速度，默认为巡航速度的1.2倍"""
        if self.max_speed_ms == 0.0:
            self.max_speed_ms = self.cruise_speed_ms * 1.2


@dataclass
class MissionProfile:
    """
    任务配置数据结构
    
    存储某一飞行任务类型的配置参数，影响飞行高度、速度和RCS
    
    属性说明：
        mission_type: 任务类型，MissionType枚举
        description: 任务描述，中文说明该任务的特点
        altitude_factor: 高度因子，相对于标准巡航高度的倍数
            - 1.0表示标准高度
            - 0.1表示低空飞行（如低空突防）
            - 1.5表示高空飞行（如高空侦察）
        speed_factor: 速度因子，相对于标准巡航速度的倍数
            - 1.0表示标准速度
            - 1.2表示高速飞行（如拦截任务）
            - 0.8表示低速飞行（如巡逻任务）
        rcs_factor: RCS因子，相对于标准RCS的倍数
            - 1.0表示标准RCS
            - 大于1表示RCS增大（如电子战任务）
            - 小于1表示RCS降低（如隐身任务）
        typical_altitude_m: 典型高度，单位：米，该任务类型的典型飞行高度
        typical_speed_ms: 典型速度，单位：米/秒，该任务类型的典型飞行速度
        terrain_following: 是否启用地形跟随模式
            - True表示飞机贴地飞行，利用地形掩护
            - 用于低空突防、对地攻击等任务
        low_observable: 是否为低可探测飞行
            - True表示采取隐身措施
            - 用于隐身战机执行任务
    """
    mission_type: MissionType          # 任务类型
    description: str                   # 任务描述
    altitude_factor: float = 1.0       # 高度因子（相对于巡航高度）
    speed_factor: float = 1.0          # 速度因子（相对于巡航速度）
    rcs_factor: float = 1.0            # RCS因子
    typical_altitude_m: float = 10000.0  # 典型高度（米）
    typical_speed_ms: float = 250.0    # 典型速度（米/秒）
    terrain_following: bool = False    # 是否地形跟随
    low_observable: bool = False       # 是否低可探测
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'mission_type': self.mission_type.value,
            'description': self.description,
            'altitude_factor': self.altitude_factor,
            'speed_factor': self.speed_factor,
            'rcs_factor': self.rcs_factor,
            'typical_altitude_m': self.typical_altitude_m,
            'typical_speed_ms': self.typical_speed_ms,
            'terrain_following': self.terrain_following,
            'low_observable': self.low_observable
        }


@dataclass
class GeoLocation:
    """
    地理位置数据结构
    
    存储机场或导航点的地理位置信息
    
    属性说明：
        name: 地点名称，如"北京大兴国际机场"
        lon: 经度，单位：度，东经为正，西经为负
        lat: 纬度，单位：度，北纬为正，南纬为负
        alt_m: 海拔高度，单位：米，该地点的平均海拔高度
        runway_direction: 跑道方向，元组形式（主跑道方向，反方向）
            - 如(180, 360)表示跑道方向为180度和360度（南北向）
            - 用于计算起飞和降落时的初始航向
    """
    name: str                          # 地点名称
    lon: float                         # 经度（度）
    lat: float                         # 纬度（度）
    alt_m: float                       # 海拔高度（米）
    runway_direction: tuple = (0, 180)  # 跑道方向（度）

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'name': self.name,
            'lon': self.lon,
            'lat': self.lat,
            'alt_m': self.alt_m,
            'runway_direction': self.runway_direction
        }
