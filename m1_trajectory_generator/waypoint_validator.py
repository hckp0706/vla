"""
航路点验证模块

验证大模型返回的航路点数据的有效性
"""

import logging
from typing import List, Dict, Any, Optional, Tuple

from .config import Config

logger = logging.getLogger(__name__)

class WaypointValidator:
    """
    航路点验证器
    
    验证大模型返回的航路点数据的有效性
    """
    
    # 坐标范围限制
    MIN_LAT = -90.0
    MAX_LAT = 90.0
    MIN_LON = -180.0
    MAX_LON = 180.0
    
    # 高度范围限制（米）
    MIN_ALT = 0.0
    MAX_ALT = 30000.0
    
    # 相邻航路点最小距离（米）
    MIN_SEGMENT_DISTANCE = 1000.0  # 1公里
    
    # 相邻航路点最大距离（米）
    MAX_SEGMENT_DISTANCE = 500000.0  # 500公里
    
    @staticmethod
    def validate(waypoints_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证航路点数据
        
        参数：
            waypoints_data: 大模型返回的航路点数据
            
        返回：
            (是否有效, 错误信息列表)
        """
        errors = []
        
        # 1. 验证JSON结构
        if not isinstance(waypoints_data, dict):
            errors.append("返回数据不是有效的JSON对象")
            return False, errors
            
        if "waypoints" not in waypoints_data:
            errors.append("缺少waypoints字段")
            return False, errors
            
        waypoints = waypoints_data["waypoints"]
        
        # 2. 验证航路点列表
        if not isinstance(waypoints, list):
            errors.append("waypoints必须是列表")
            return False, errors
            
        # 3. 验证航路点数量
        num_waypoints = len(waypoints)
        if num_waypoints < Config.MIN_WAYPOINTS:
            errors.append(f"航路点数量不足，最少需要{Config.MIN_WAYPOINTS}个，当前{num_waypoints}个")
        if num_waypoints > Config.MAX_WAYPOINTS:
            errors.append(f"航路点数量过多，最多允许{Config.MAX_WAYPOINTS}个，当前{num_waypoints}个")
            
        # 4. 验证每个航路点
        for i, wp in enumerate(waypoints):
            wp_errors = WaypointValidator._validate_single_waypoint(wp, i)
            errors.extend(wp_errors)
            
        # 5. 验证相邻航路点距离
        dist_errors = WaypointValidator._validate_segment_distances(waypoints)
        errors.extend(dist_errors)
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.warning(f"航路点验证失败，错误数量: {len(errors)}")
            for error in errors:
                logger.warning(f"  - {error}")
        
        return is_valid, errors
    
    @staticmethod
    def _validate_single_waypoint(waypoint: Dict[str, Any], index: int) -> List[str]:
        """
        验证单个航路点
        
        参数：
            waypoint: 航路点数据
            index: 航路点索引
            
        返回：
            错误信息列表
        """
        errors = []
        
        if not isinstance(waypoint, dict):
            errors.append(f"航路点[{index}]不是字典类型")
            return errors
            
        # 验证必填字段
        required_fields = ["name", "lon", "lat"]
        for field in required_fields:
            if field not in waypoint:
                errors.append(f"航路点[{index}]缺少{field}字段")
        
        # 验证名称
        name = waypoint.get("name")
        if name and (not isinstance(name, str) or len(name.strip()) == 0):
            errors.append(f"航路点[{index}]名称无效")
        
        # 验证经度
        lon = waypoint.get("lon")
        if lon is not None:
            if not isinstance(lon, (int, float)):
                errors.append(f"航路点[{index}]经度必须是数字")
            elif lon < WaypointValidator.MIN_LON or lon > WaypointValidator.MAX_LON:
                errors.append(f"航路点[{index}]经度超出范围({WaypointValidator.MIN_LON}~{WaypointValidator.MAX_LON}): {lon}")
        
        # 验证纬度
        lat = waypoint.get("lat")
        if lat is not None:
            if not isinstance(lat, (int, float)):
                errors.append(f"航路点[{index}]纬度必须是数字")
            elif lat < WaypointValidator.MIN_LAT or lat > WaypointValidator.MAX_LAT:
                errors.append(f"航路点[{index}]纬度超出范围({WaypointValidator.MIN_LAT}~{WaypointValidator.MAX_LAT}): {lat}")
        
        # 验证高度（可选字段）
        alt_m = waypoint.get("alt_m")
        if alt_m is not None:
            if not isinstance(alt_m, (int, float)):
                errors.append(f"航路点[{index}]高度必须是数字")
            elif alt_m < WaypointValidator.MIN_ALT or alt_m > WaypointValidator.MAX_ALT:
                errors.append(f"航路点[{index}]高度超出范围({WaypointValidator.MIN_ALT}~{WaypointValidator.MAX_ALT}): {alt_m}")
        
        return errors
    
    @staticmethod
    def _validate_segment_distances(waypoints: List[Dict[str, Any]]) -> List[str]:
        """
        验证相邻航路点之间的距离
        
        参数：
            waypoints: 航路点列表
            
        返回：
            错误信息列表
        """
        errors = []
        
        if len(waypoints) < 2:
            return errors
            
        for i in range(len(waypoints) - 1):
            wp1 = waypoints[i]
            wp2 = waypoints[i + 1]
            
            # 检查是否有坐标
            if "lon" not in wp1 or "lat" not in wp1:
                continue
            if "lon" not in wp2 or "lat" not in wp2:
                continue
                
            # 计算距离（简化计算，使用近似公式）
            distance = WaypointValidator._calculate_distance(
                wp1["lat"], wp1["lon"],
                wp2["lat"], wp2["lon"]
            )
            
            if distance < WaypointValidator.MIN_SEGMENT_DISTANCE:
                errors.append(f"航路点[{i}]到[{i+1}]距离过近: {distance:.0f}米")
            if distance > WaypointValidator.MAX_SEGMENT_DISTANCE:
                errors.append(f"航路点[{i}]到[{i+1}]距离过远: {distance:.0f}米")
        
        return errors
    
    @staticmethod
    def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        计算两点之间的距离（米）
        
        使用简化的球面距离公式
        
        参数：
            lat1: 起点纬度（度）
            lon1: 起点经度（度）
            lat2: 终点纬度（度）
            lon2: 终点经度（度）
            
        返回：
            距离（米）
        """
        import math
        
        # 转换为弧度
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # 球面距离公式（Haversine公式）
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        # 地球半径（米）
        R = 6371000
        
        return R * c