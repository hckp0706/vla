"""
M1模块轨迹生成器

本模块是M1的核心计算引擎，负责将飞行简令转换为1Hz频率的轨迹数据。

主要功能：
1. 航路展开：将起降两点展开为完整的航路点序列
2. 大圆航线计算：使用地球椭球模型计算最短路径
3. 平滑转弯算法：消除航向突变，实现圆弧平滑过渡
4. 高度剖面计算：模拟起飞→爬升→巡航→下降→降落全过程
5. 动态RCS估算：根据飞行状态计算雷达散射截面积

输出格式：1Hz频率的轨迹点序列，每个点包含时间、位置、速度、高度、航向、RCS等信息
"""

import math
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from geographiclib.geodesic import Geodesic

from .models import (
    FlightIntent, TrackPoint, TrajectoryOutput, 
    Waypoint, AircraftPerformance, FlightPhase, MissionType, MissionProfile
)
from .knowledge_base import KnowledgeBase
from .parser import IntentParser

logger = logging.getLogger(__name__)


class TrajectoryGenerator:
    """
    轨迹生成器
    
    将飞行简令转换为1Hz频率的轨迹数据
    
    核心算法：
        - 大圆航线：使用WGS84椭球模型计算地球表面最短路径
        - 平滑转弯：基于标准转弯率（3度/秒）计算圆弧过渡
        - 高度剖面：根据爬升/下降率计算高度变化
        - RCS估算：根据飞行姿态和任务类型计算雷达散射截面积
    """
    
    # 标准转弯率：3度/秒（民航标准）
    TURN_RATE_DEG_PER_SEC = 3.0
    
    # 安全高度：最低飞行高度，防止"钻地"
    SAFETY_ALTITUDE_M = 100.0
    
    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None):
        """
        初始化轨迹生成器
        
        参数：
            knowledge_base: 知识库对象，如果为None则创建新实例
        """
        self.kb = knowledge_base or KnowledgeBase()
        self.parser = IntentParser()
        # 使用WGS84椭球模型进行地理计算
        self.geod = Geodesic.WGS84
    
    def generate(self, intent_text: str) -> Optional[TrajectoryOutput]:
        """
        根据飞行简令生成轨迹
        
        参数：
            intent_text: 飞行简令文本
        
        返回：
            TrajectoryOutput对象，生成失败返回None
        """
        # 解析并验证简令
        intent, is_valid, errors, warnings = self.parser.parse_and_validate(intent_text)
        
        if not is_valid:
            for error in errors:
                logger.error(f"简令解析错误: {error}")
            return None
        
        for warning in warnings:
            logger.warning(f"简令解析警告: {warning}")
        
        return self._generate_trajectory(intent)
    
    def _generate_trajectory(self, intent: FlightIntent) -> Optional[TrajectoryOutput]:
        """
        根据解析后的飞行意图生成轨迹
        
        参数：
            intent: FlightIntent对象
        
        返回：
            TrajectoryOutput对象
        """
        # 获取机型性能参数
        aircraft = self.kb.get_aircraft_performance(intent.platform_type)
        if not aircraft:
            logger.error(f"未知机型: {intent.platform_type}")
            return None
        
        # 获取任务配置
        mission_profile = None
        if intent.mission_type:
            mission_profile = self.kb.get_mission_profile(intent.mission_type)
            if mission_profile:
                logger.info(f"飞行任务: {mission_profile.description}")
        
        # 获取航路
        route = self._get_route(intent)
        if not route:
            logger.error(f"无法获取航路: {intent.loc_start} -> {intent.loc_end or intent.loc_mid}")
            return None
        
        # 解析航路点坐标
        waypoints = self._resolve_waypoints(route)
        if not waypoints:
            logger.error("无法解析航路点坐标")
            return None
        
        # 计算总距离
        total_distance_m = self._calculate_total_distance(waypoints)
        
        # 根据任务类型调整巡航高度和速度
        cruise_alt = self._get_mission_altitude(aircraft, mission_profile)
        cruise_speed = self._get_mission_speed(aircraft, mission_profile)
        
        # 直接使用计算出的巡航速度，不再依赖到达时间
        required_speed = cruise_speed
        
        # 速度校验：检查是否超出机型性能限制
        if required_speed > aircraft.max_speed_ms:
            logger.warning(f"巡航速度 {required_speed:.1f} m/s 超过机型最大速度 {aircraft.max_speed_ms:.1f} m/s，将按最大速度飞行")
            required_speed = aircraft.max_speed_ms
        elif required_speed < aircraft.min_speed_ms:
            logger.warning(f"巡航速度 {required_speed:.1f} m/s 低于机型最小速度 {aircraft.min_speed_ms:.1f} m/s，将按最小速度飞行")
            required_speed = aircraft.min_speed_ms
        
        # 计算总飞行时间
        total_time_sec = total_distance_m / required_speed
        
        # 生成轨迹点
        track_points = self._generate_track_points(
            waypoints=waypoints,
            start_time=intent.takeoff_time,
            total_time_sec=total_time_sec,
            speed_ms=required_speed,
            aircraft=aircraft,
            mission_profile=mission_profile,
            cruise_alt=cruise_alt
        )
        
        # 构建输出对象
        mission_type_str = intent.mission_type.value if intent.mission_type else None
        
        return TrajectoryOutput(
            target_id=intent.target_id,
            platform_type=intent.platform_type,
            mission_type=mission_type_str,
            track_points=track_points
        )
    
    def _get_mission_altitude(self, aircraft: AircraftPerformance, mission: Optional[MissionProfile]) -> float:
        """
        根据任务类型获取巡航高度
        
        参数：
            aircraft: 机型性能对象
            mission: 任务配置对象
        
        返回：
            巡航高度（米）
        """
        if mission:
            # 取任务典型高度和机型巡航高度的较小值
            return min(mission.typical_altitude_m, aircraft.cruise_alt_m * mission.altitude_factor)
        return aircraft.cruise_alt_m
    
    def _get_mission_speed(self, aircraft: AircraftPerformance, mission: Optional[MissionProfile]) -> float:
        """
        根据任务类型获取巡航速度
        
        参数：
            aircraft: 机型性能对象
            mission: 任务配置对象
        
        返回：
            巡航速度（米/秒）
        """
        if mission:
            return min(mission.typical_speed_ms, aircraft.cruise_speed_ms * mission.speed_factor)
        return aircraft.cruise_speed_ms
    
    def _get_route(self, intent: FlightIntent) -> Optional[List[str]]:
        """
        获取航路点名称列表
        
        参数：
            intent: 飞行意图对象
        
        返回：
            航路点名称列表
        """
        if intent.loc_end and intent.loc_mid:
            # 处理带途径点的情况：先获取起点到途径点的航路，再获取途径点到终点的航路
            route1 = self.kb.get_route(intent.loc_start, intent.loc_mid, intent.platform_type)
            route2 = self.kb.get_route(intent.loc_mid, intent.loc_end, intent.platform_type)
            if route1 and route2:
                # 合并两条航路，去除重复的途径点
                return route1 + route2[1:]
            return [intent.loc_start, intent.loc_mid, intent.loc_end]
        elif intent.loc_end:
            return self.kb.get_route(intent.loc_start, intent.loc_end, intent.platform_type)
        elif intent.loc_mid:
            route1 = self.kb.get_route(intent.loc_start, intent.loc_mid, intent.platform_type)
            if route1:
                return route1
            return [intent.loc_start, intent.loc_mid]
        else:
            return None
    
    def _resolve_waypoints(self, route: List[str]) -> Optional[List[Waypoint]]:
        """
        将航路点名称列表转换为Waypoint对象列表
        
        参数：
            route: 航路点名称列表
        
        返回：
            Waypoint对象列表
        """
        waypoints = []
        for name in route:
            wp = self.kb.get_waypoint(name)
            if wp:
                waypoints.append(wp)
            else:
                logger.warning(f"无法解析航路点: {name}")
        return waypoints if waypoints else None
    
    def _calculate_total_distance(self, waypoints: List[Waypoint]) -> float:
        """
        计算航路总距离
        
        参数：
            waypoints: 航路点列表
        
        返回：
            总距离（米）
        """
        total_distance = 0.0
        for i in range(len(waypoints) - 1):
            total_distance += self._geodesic_distance(
                waypoints[i].lat, waypoints[i].lon,
                waypoints[i + 1].lat, waypoints[i + 1].lon
            )
        return total_distance
    
    def _get_end_time(self, intent: FlightIntent) -> Optional[datetime]:
        """
        获取降落时间
        
        参数：
            intent: 飞行意图对象
        
        返回：
            降落时间datetime对象
        """
        if intent.time_end:
            # 补全日期部分
            base_date = intent.takeoff_time.strftime('%Y-%m-%d')
            time_str = intent.time_end
            if len(time_str) == 8:  # HH:MM:SS
                return datetime.strptime(f"{base_date} {time_str}", '%Y-%m-%d %H:%M:%S')
        return None
    
    def _geodesic_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        计算两点之间的大圆距离
        
        使用WGS84椭球模型计算地球表面两点间的最短距离
        
        参数：
            lat1: 起点纬度（度）
            lon1: 起点经度（度）
            lat2: 终点纬度（度）
            lon2: 终点经度（度）
        
        返回：
            距离（米）
        """
        result = self.geod.Inverse(lat1, lon1, lat2, lon2)
        return result['s12']
    
    def _geodesic_interpolate(
        self, 
        lat1: float, lon1: float, 
        lat2: float, lon2: float, 
        fraction: float
    ) -> Tuple[float, float, float]:
        """
        在大圆航线上进行插值
        
        参数：
            lat1: 起点纬度（度）
            lon1: 起点经度（度）
            lat2: 终点纬度（度）
            lon2: 终点经度（度）
            fraction: 插值比例（0-1）
        
        返回：
            (插值点纬度, 插值点经度, 航向角) 元组
        """
        # 计算大圆航线
        result = self.geod.Inverse(lat1, lon1, lat2, lon2)
        total_distance = result['s12']
        azimuth = result['azi1']  # 起点处的方位角
        
        # 计算插值点
        interp_distance = total_distance * fraction
        interp_result = self.geod.Direct(lat1, lon1, azimuth, interp_distance)
        
        return interp_result['lat2'], interp_result['lon2'], azimuth
    
    def _calculate_heading(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        计算两点之间的航向角
        
        参数：
            lat1: 起点纬度（度）
            lon1: 起点经度（度）
            lat2: 终点纬度（度）
            lon2: 终点经度（度）
        
        返回：
            航向角（度，0-360）
        """
        result = self.geod.Inverse(lat1, lon1, lat2, lon2)
        heading = result['azi1']
        if heading < 0:
            heading += 360
        return heading
    
    def _generate_track_points(
        self,
        waypoints: List[Waypoint],
        start_time: datetime,
        total_time_sec: float,
        speed_ms: float,
        aircraft: AircraftPerformance,
        mission_profile: Optional[MissionProfile],
        cruise_alt: float
    ) -> List[TrackPoint]:
        """
        生成轨迹点序列
        
        参数：
            waypoints: 航路点列表
            start_time: 起飞时间
            total_time_sec: 总飞行时间（秒）
            speed_ms: 飞行速度（米/秒）
            aircraft: 机型性能对象
            mission_profile: 任务配置对象
            cruise_alt: 巡航高度（米）
        
        返回：
            轨迹点列表
        """
        track_points = []
        
        # 计算总距离和各航段距离
        total_distance = self._calculate_total_distance(waypoints)
        segment_distances = []
        for i in range(len(waypoints) - 1):
            dist = self._geodesic_distance(
                waypoints[i].lat, waypoints[i].lon,
                waypoints[i + 1].lat, waypoints[i + 1].lon
            )
            segment_distances.append(dist)
        
        # 计算转弯半径（基于速度和标准转弯率）
        # 转弯半径 = 速度 / 转弯角速度
        turn_radius = speed_ms / math.radians(self.TURN_RATE_DEG_PER_SEC)
        
        # 起降机场海拔高度
        start_alt = waypoints[0].alt_m
        end_alt = waypoints[-1].alt_m
        
        # 计算爬升和下降距离
        # 爬升距离 = (巡航高度 - 起飞机场海拔) / 爬升率 * 速度
        climb_distance = (cruise_alt - start_alt) / aircraft.climb_rate_ms * speed_ms
        # 下降距离 = (巡航高度 - 降落机场海拔) / 下降率 * 速度
        descent_distance = (cruise_alt - end_alt) / aircraft.descent_rate_ms * speed_ms
        
        # 计算总轨迹点数（1Hz频率）
        total_points = int(total_time_sec)
        time_step = 1.0
        
        # 获取RCS因子
        rcs_factor = 1.0
        if mission_profile:
            rcs_factor = mission_profile.rcs_factor
        
        # 生成每个轨迹点
        for point_idx in range(total_points + 1):
            elapsed_sec = point_idx * time_step
            current_time = start_time + timedelta(seconds=elapsed_sec)
            
            # 计算当前进度
            progress = elapsed_sec / total_time_sec if total_time_sec > 0 else 0
            current_distance = progress * total_distance
            
            # 计算当前位置和航向
            lat, lon, heading = self._get_position_at_distance(
                waypoints, segment_distances, current_distance
            )
            
            # 计算高度和飞行阶段
            alt, vertical_rate, phase = self._calculate_altitude_profile(
                current_distance=current_distance,
                total_distance=total_distance,
                start_alt=start_alt,
                cruise_alt=cruise_alt,
                end_alt=end_alt,
                climb_distance=climb_distance,
                descent_distance=descent_distance,
                aircraft=aircraft
            )
            
            # 地形跟随模式：限制巡航阶段的高度
            if mission_profile and mission_profile.terrain_following:
                alt = min(alt, cruise_alt)
                if phase == FlightPhase.CRUISING:
                    alt = cruise_alt
            
            # 判断是否在转弯中
            is_turning = self._is_in_turn(
                waypoints, segment_distances, current_distance, turn_radius
            )
            
            # 计算RCS
            rcs = self._calculate_rcs(
                aircraft=aircraft,
                phase=phase,
                is_turning=is_turning,
                heading=heading,
                waypoints=waypoints,
                segment_distances=segment_distances,
                current_distance=current_distance,
                rcs_factor=rcs_factor
            )
            
            # 创建轨迹点
            track_points.append(TrackPoint(
                time=current_time,
                lon=lon,
                lat=lat,
                alt_m=alt,
                speed_ms=speed_ms,
                heading_deg=heading,
                vertical_rate_ms=vertical_rate,
                rcs_dbsm=rcs,
                phase=phase
            ))
        
        return track_points
    
    def _get_position_at_distance(
        self,
        waypoints: List[Waypoint],
        segment_distances: List[float],
        target_distance: float
    ) -> Tuple[float, float, float]:
        """
        根据累计距离获取位置和航向
        
        参数：
            waypoints: 航路点列表
            segment_distances: 各航段距离列表
            target_distance: 目标累计距离（米）
        
        返回：
            (纬度, 经度, 航向角) 元组
        """
        accumulated_distance = 0.0
        
        for i, seg_dist in enumerate(segment_distances):
            if accumulated_distance + seg_dist >= target_distance:
                # 目标点在当前航段内
                distance_in_segment = target_distance - accumulated_distance
                fraction = distance_in_segment / seg_dist if seg_dist > 0 else 0
                
                # 在大圆航线上插值
                lat, lon, heading = self._geodesic_interpolate(
                    waypoints[i].lat, waypoints[i].lon,
                    waypoints[i + 1].lat, waypoints[i + 1].lon,
                    fraction
                )
                
                # 航向角归一化到0-360度
                if heading < 0:
                    heading += 360
                
                return lat, lon, heading
            
            accumulated_distance += seg_dist
        
        # 如果超出范围，返回最后一个航路点
        return waypoints[-1].lat, waypoints[-1].lon, 0.0
    
    def _calculate_altitude_profile(
        self,
        current_distance: float,
        total_distance: float,
        start_alt: float,
        cruise_alt: float,
        end_alt: float,
        climb_distance: float,
        descent_distance: float,
        aircraft: AircraftPerformance
    ) -> Tuple[float, float, FlightPhase]:
        """
        计算高度剖面
        
        根据当前距离计算高度、垂直速率和飞行阶段
        
        参数：
            current_distance: 当前累计距离（米）
            total_distance: 总距离（米）
            start_alt: 起飞机场海拔（米）
            cruise_alt: 巡航高度（米）
            end_alt: 降落机场海拔（米）
            climb_distance: 爬升阶段距离（米）
            descent_distance: 下降阶段距离（米）
            aircraft: 机型性能对象
        
        返回：
            (高度, 垂直速率, 飞行阶段) 元组
        """
        # 计算各阶段的边界
        climb_end = climb_distance
        descent_start = total_distance - descent_distance
        
        if current_distance <= climb_end:
            # 爬升阶段
            progress = current_distance / climb_distance if climb_distance > 0 else 0
            alt = start_alt + (cruise_alt - start_alt) * progress
            vertical_rate = aircraft.climb_rate_ms
            phase = FlightPhase.GROUND_TAKEOFF if progress < 0.1 else FlightPhase.CLIMBING
        elif current_distance >= descent_start:
            # 下降阶段
            progress = (current_distance - descent_start) / descent_distance if descent_distance > 0 else 0
            alt = cruise_alt - (cruise_alt - end_alt) * progress
            vertical_rate = -aircraft.descent_rate_ms
            phase = FlightPhase.LANDING if progress > 0.9 else FlightPhase.DESCENDING
        else:
            # 巡航阶段
            alt = cruise_alt
            vertical_rate = 0.0
            phase = FlightPhase.CRUISING
        
        return alt, vertical_rate, phase
    
    def _is_in_turn(
        self,
        waypoints: List[Waypoint],
        segment_distances: List[float],
        current_distance: float,
        turn_radius: float
    ) -> bool:
        """
        判断当前位置是否在转弯区域内
        
        参数：
            waypoints: 航路点列表
            segment_distances: 各航段距离列表
            current_distance: 当前累计距离（米）
            turn_radius: 转弯半径（米）
        
        返回：
            是否在转弯区域
        """
        accumulated_distance = 0.0
        
        for i in range(len(segment_distances)):
            seg_start = accumulated_distance
            seg_end = accumulated_distance + segment_distances[i]
            
            # 转弯区域：航路点前后各一个转弯半径
            turn_start = seg_end - turn_radius
            turn_end = seg_end + turn_radius
            
            if turn_start <= current_distance <= turn_end and i < len(segment_distances) - 1:
                return True
            
            accumulated_distance = seg_end
        
        return False
    
    def _calculate_rcs(
        self,
        aircraft: AircraftPerformance,
        phase: FlightPhase,
        is_turning: bool,
        heading: float,
        waypoints: List[Waypoint],
        segment_distances: List[float],
        current_distance: float,
        rcs_factor: float = 1.0
    ) -> float:
        """
        计算雷达散射截面积（RCS）
        
        RCS估算规则：
            1. 基准值：机头RCS
            2. 起降增量：起飞/降落阶段起落架放下，RCS增加
            3. 转弯增量：转弯时侧面暴露，RCS从机头值向侧面值插值
            4. 任务因子：根据任务类型调整RCS
        
        参数：
            aircraft: 机型性能对象
            phase: 飞行阶段
            is_turning: 是否在转弯
            heading: 航向角
            waypoints: 航路点列表
            segment_distances: 各航段距离列表
            current_distance: 当前累计距离
            rcs_factor: RCS因子
        
        返回：
            RCS值（dBsm）
        """
        # 基准RCS：机头方向
        base_rcs = aircraft.nose_rcs_dbsm
        
        # 起降阶段：起落架放下，RCS增加
        if phase in [FlightPhase.GROUND_TAKEOFF, FlightPhase.LANDING]:
            base_rcs += aircraft.gear_rcs_increment
        
        # 转弯阶段：侧面暴露，RCS插值
        if is_turning:
            turn_progress = self._get_turn_progress(
                waypoints, segment_distances, current_distance
            )
            side_rcs = aircraft.side_rcs_dbsm
            # 从机头RCS向侧面RCS线性插值
            base_rcs = base_rcs + (side_rcs - base_rcs) * turn_progress
        
        # 应用任务因子
        base_rcs = base_rcs * rcs_factor
        
        return base_rcs
    
    def _get_turn_progress(
        self,
        waypoints: List[Waypoint],
        segment_distances: List[float],
        current_distance: float
    ) -> float:
        """
        获取转弯进度
        
        参数：
            waypoints: 航路点列表
            segment_distances: 各航段距离列表
            current_distance: 当前累计距离
        
        返回：
            转弯进度（0-1）
        """
        accumulated_distance = 0.0
        
        for i in range(len(segment_distances)):
            seg_end = accumulated_distance + segment_distances[i]
            
            if accumulated_distance <= current_distance <= seg_end:
                if segment_distances[i] > 0:
                    return (current_distance - accumulated_distance) / segment_distances[i]
                return 0.5
            
            accumulated_distance = seg_end
        
        return 0.0
