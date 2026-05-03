from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
import json


@dataclass
class RadarConfig:
    """雷达配置
    
    属性说明：
    - radar_id: 雷达编号
    - location: 经纬度 [lon, lat]
    - height: 天线架高（米）
    - max_range: 最大探测距离（公里）
    - beam_width: 波束宽度（度）
    - scan_period: 扫描周期（秒）
    - tactical_role: 战术定位
    - range_error_std: 测距误差标准差（米）
    - azimuth_error_std: 方位角误差标准差（度）
    - elevation_error_std: 俯仰角误差标准差（度）
    """
    radar_id: str
    location: List[float]  # [lon, lat]
    height: float  # 天线架高（米）
    max_range: float  # 最大探测距离（公里）
    beam_width: float  # 波束宽度（度）
    scan_period: float  # 扫描周期（秒）
    tactical_role: str  # 战术定位
    range_error_std: float = 100.0  # 测距误差标准差（米）
    azimuth_error_std: float = 0.3  # 方位角误差标准差（度）
    elevation_error_std: float = 0.3  # 俯仰角误差标准差（度）


@dataclass
class TargetTruth:
    """目标真值
    
    属性说明：
    - target_id: 目标批号
    - time: 时间戳
    - lon: 经度
    - lat: 纬度
    - alt_m: 海拔高度（米）
    - speed_ms: 地速（米/秒）
    - heading_deg: 航向角（度，0-360，真北为0）
    - rcs_dbsm: 雷达散射截面积（dBsm）
    """
    target_id: str
    time: datetime
    lon: float
    lat: float
    alt_m: float
    speed_ms: float
    heading_deg: float
    rcs_dbsm: float


@dataclass
class TrackPoint:
    """轨迹点
    
    属性说明：
    - time: 观测时间戳
    - track_id: 航迹ID
    - target_id: 目标批号
    - source_radars: 数据源雷达列表
    - obs_lon: 观测经度
    - obs_lat: 观测纬度
    - obs_alt_m: 观测高度（米）
    - obs_speed_ms: 观测速度（米/秒）
    - obs_heading_deg: 观测航向角（度）
    - track_quality: 航迹质量
    - snr_avg_db: 平均信噪比（dB）
    """
    time: datetime
    track_id: str
    target_id: str
    source_radars: List[str]
    obs_lon: float
    obs_lat: float
    obs_alt_m: float
    obs_speed_ms: float
    obs_heading_deg: float
    track_quality: str
    snr_avg_db: float


@dataclass
class NetworkTracks:
    """系统级组网观测航迹
    
    属性说明：
    - frame_time: 帧时间
    - network_tracks: 网络航迹列表
    """
    frame_time: str
    network_tracks: List[TrackPoint]
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "frame_time": self.frame_time,
            "network_tracks": [
                {
                    "time": track.time.isoformat() + 'Z' if track.time.tzinfo is None else track.time.isoformat(),
                    "track_id": track.track_id,
                    "target_id": track.target_id,
                    "source_radars": track.source_radars,
                    "obs_lon": track.obs_lon,
                    "obs_lat": track.obs_lat,
                    "obs_alt_m": track.obs_alt_m,
                    "obs_speed_ms": track.obs_speed_ms,
                    "obs_heading_deg": track.obs_heading_deg,
                    "track_quality": track.track_quality,
                    "snr_avg_db": track.snr_avg_db
                }
                for track in self.network_tracks
            ]
        }
    
    def to_json(self) -> str:
        """转换为JSON格式"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    def save_to_file(self, file_path: str) -> None:
        """保存到文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
