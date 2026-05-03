"""
M1模块轨迹生成器

本模块是M1的核心计算引擎，负责将飞行简令转换为1Hz频率的轨迹数据。

主要功能：
1. 航路展开：将起降两点展开为完整的航路点序列（支持大模型生成）
2. 大圆航线计算：使用地球椭球模型计算最短路径
3. 平滑转弯算法：消除航向突变，实现圆弧平滑过渡
4. 高度剖面计算：模拟起飞→爬升→巡航→下降→降落全过程
5. 动态RCS估算：根据飞行状态计算雷达散射截面积
6. 时间计算：根据机型性能和航路距离自动计算途经点和降落时间

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
from .llm_client import LLMClient
from .waypoint_validator import WaypointValidator
from .config import Config
from .eaip_loader import EAIPLoader

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
        - 大模型航路点生成：调用GLM-5.1生成更真实的航路点
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
        # 初始化大模型客户端
        self.llm_client = LLMClient()
        # 初始化EAIP数据加载器
        self.eaip_loader = EAIPLoader()
        logger.info(f"EAIP数据加载完成：{len(self.eaip_loader.airports)}个机场, {len(self.eaip_loader.waypoints)}个航路点")
        
        # 加载航路网络
        self.route_network = self._load_route_network()
        logger.info(f"航路网络加载完成：{len(self.route_network)}个节点")
    
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
        
        降级策略：EAIP数据 → 大模型 → 本地预设航路
        
        参数：
            intent: 飞行意图对象
        
        返回：
            航路点名称列表
        """
        # 优先使用EAIP数据规划航线
        eaip_route = self._generate_route_with_eaip(intent)
        if eaip_route:
            logger.info(f"使用EAIP数据生成的航路点，共{len(eaip_route)}个")
            return eaip_route
        
        # EAIP数据不可用时，使用大模型生成航路点
        llm_waypoints = self._generate_route_with_llm(intent)
        if llm_waypoints:
            logger.info(f"使用大模型生成的航路点，共{len(llm_waypoints)}个")
            return llm_waypoints
        
        # 降级到本地预设航路
        logger.info("EAIP和大模型均失败，使用本地预设航路")
        if intent.loc_end and intent.loc_mid:
            route1 = self.kb.get_route(intent.loc_start, intent.loc_mid, intent.platform_type)
            route2 = self.kb.get_route(intent.loc_mid, intent.loc_end, intent.platform_type)
            if route1 and route2:
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
    
    def _generate_route_with_eaip(self, intent: FlightIntent) -> Optional[List[str]]:
        """
        使用EAIP数据生成航路点
        
        参数：
            intent: 飞行意图对象
        
        返回：
            航路点名称列表，失败返回None
        """
        if not self.eaip_loader.has_airport_data():
            logger.info("EAIP机场数据不可用")
            return None
        
        start_airport = self.eaip_loader.search_airport(intent.loc_start)
        end_airport = self.eaip_loader.search_airport(intent.loc_end) if intent.loc_end else None
        
        if not start_airport:
            logger.info(f"EAIP中未找到起点: {intent.loc_start}")
            return None
        
        if end_airport:
            logger.info(f"EAIP匹配到航线: {start_airport.name_cn} -> {end_airport.name_cn}")
            return self._plan_route_with_eaip_waypoints(start_airport, end_airport)
        
        logger.info(f"EAIP中未找到终点: {intent.loc_end}")
        return None
    
    def _plan_route_with_eaip_waypoints(self, start: 'EAIPAirport', end: 'EAIPAirport') -> List[str]:
        """
        使用EAIP航路点规划航线
        
        参数：
            start: 起点机场
            end: 终点机场
        
        返回：
            航路点名称列表（包含起终点）
        """
        route = [start.name_cn]
        
        if self.eaip_loader.has_waypoint_data():
            waypoints = self._select_waypoints_between(start, end)
            logger.info(f"选择的EAIP航路点: {waypoints}")
            route.extend(waypoints)
        
        route.append(end.name_cn)
        return route
    
    def _find_nearest_waypoints(self, airport: 'EAIPAirport', count: int = 3) -> List[str]:
        """
        找到离机场最近的航路点
        
        参数：
            airport: 机场对象
            count: 返回数量
        
        返回：
            航路点名称列表
        """
        if not self.eaip_loader.has_waypoint_data():
            return []
        
        distances = []
        for name, wp in self.eaip_loader.waypoints.items():
            dist = self._haversine_distance(airport.latitude, airport.longitude, wp.latitude, wp.longitude)
            distances.append((name, dist))
        
        distances.sort(key=lambda x: x[1])
        return [name for name, _ in distances[:count]]
    
    def _find_best_network_route(self, start_candidates: List[str], end_candidates: List[str]) -> Optional[List[str]]:
        """
        在航路网络中找到最优路径
        
        参数：
            start_candidates: 起点候选航路点
            end_candidates: 终点候选航路点
        
        返回：
            最优航路点列表
        """
        best_route = None
        min_length = float('inf')
        
        for start_wp in start_candidates:
            for end_wp in end_candidates:
                if start_wp == end_wp:
                    continue
                
                route = self._find_route_in_network(start_wp, end_wp)
                if route:
                    full_route = self._fill_missing_waypoints(route)
                    if full_route and len(full_route) < min_length:
                        best_route = full_route
                        min_length = len(full_route)
        
        return best_route
    
    def _fill_missing_waypoints(self, route: List[str]) -> List[str]:
        """
        填充航路上缺失的中间航路点
        
        参数：
            route: 航路点列表
        
        返回：
            完整的航路点列表
        """
        if len(route) < 2:
            return route
        
        full_route = [route[0]]
        
        for i in range(len(route) - 1):
            current = route[i]
            next_wp = route[i + 1]
            
            connecting_route = self._find_common_route(current, next_wp)
            if connecting_route:
                full_route.extend(connecting_route[1:])
            else:
                full_route.append(next_wp)
        
        return full_route
    
    def _find_common_route(self, wp1: str, wp2: str) -> Optional[List[str]]:
        """
        找到两个航路点之间的公共航路
        
        参数：
            wp1: 航路点1
            wp2: 航路点2
        
        返回：
            公共航路上的航路点列表
        """
        if wp1 not in self.route_network or wp2 not in self.route_network:
            return None
        
        routes1 = set(self.route_network[wp1].get('routes', []))
        routes2 = set(self.route_network[wp2].get('routes', []))
        common_routes = routes1.intersection(routes2)
        
        if not common_routes:
            return None
        
        for route_id in common_routes:
            path = self._get_route_path(route_id, wp1, wp2)
            if path:
                return path
        
        return None
    
    def _get_route_path(self, route_id: str, start_wp: str, end_wp: str) -> Optional[List[str]]:
        """
        获取指定航路上两个航路点之间的路径
        
        参数：
            route_id: 航路编号
            start_wp: 起点航路点
            end_wp: 终点航路点
        
        返回：
            航路点列表
        """
        route_waypoints = []
        
        for wp_name, wp_data in self.route_network.items():
            if route_id in wp_data.get('routes', []):
                route_waypoints.append((wp_name, wp_data['latitude'], wp_data['longitude']))
        
        if not route_waypoints:
            return None
        
        start_lat = self.route_network[start_wp]['latitude']
        start_lon = self.route_network[start_wp]['longitude']
        end_lat = self.route_network[end_wp]['latitude']
        end_lon = self.route_network[end_wp]['longitude']
        
        route_waypoints.sort(key=lambda x: self._haversine_distance(start_lat, start_lon, x[1], x[2]))
        
        result = []
        found_start = False
        
        for wp_name, lat, lon in route_waypoints:
            if wp_name == start_wp:
                found_start = True
            if found_start:
                result.append(wp_name)
                if wp_name == end_wp:
                    break
        
        return result if found_start and end_wp in result else None
    
    def _load_route_network(self) -> dict:
        """
        加载航路网络
        
        返回：
            航路网络字典
        """
        import json
        import os
        
        network_path = os.path.join(os.path.dirname(__file__), 'data', 'route_network.json')
        
        if os.path.exists(network_path):
            try:
                with open(network_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载航路网络失败: {e}")
        
        return {}
    
    def _find_route_in_network(self, start_wp: str, end_wp: str) -> Optional[List[str]]:
        """
        在航路网络中查找最优路径
        
        参数：
            start_wp: 起点航路点名称
            end_wp: 终点航路点名称
        
        返回：
            航路点名称列表，失败返回None
        """
        if not self.route_network:
            return None
        
        if start_wp not in self.route_network or end_wp not in self.route_network:
            return None
        
        from collections import deque
        
        queue = deque()
        queue.append((start_wp, [start_wp]))
        visited = {start_wp: 0}
        
        start_lat = self.route_network[start_wp]['latitude']
        start_lon = self.route_network[start_wp]['longitude']
        end_lat = self.route_network[end_wp]['latitude']
        end_lon = self.route_network[end_wp]['longitude']
        total_distance = self._haversine_distance(start_lat, start_lon, end_lat, end_lon)
        
        while queue:
            current, path = queue.popleft()
            
            if current == end_wp:
                return path
            
            if len(path) >= 20:
                continue
            
            current_lat = self.route_network[current]['latitude']
            current_lon = self.route_network[current]['longitude']
            
            for neighbor in self.route_network[current].get('connections', []):
                if neighbor in visited and visited[neighbor] <= len(path):
                    continue
                
                neighbor_lat = self.route_network[neighbor]['latitude']
                neighbor_lon = self.route_network[neighbor]['longitude']
                
                dist_to_neighbor = self._haversine_distance(current_lat, current_lon, neighbor_lat, neighbor_lon)
                dist_to_end = self._haversine_distance(neighbor_lat, neighbor_lon, end_lat, end_lon)
                dist_from_start = self._haversine_distance(start_lat, start_lon, neighbor_lat, neighbor_lon)
                
                if dist_to_neighbor > 10.0:
                    continue
                
                if dist_from_start > total_distance + 5.0:
                    continue
                
                visited[neighbor] = len(path)
                queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def _select_waypoints_between(self, start: 'EAIPAirport', end: 'EAIPAirport') -> List[str]:
        """
        选择起终点之间的航路点，确保航线平滑且方向正确
        
        参数：
            start: 起点机场
            end: 终点机场
        
        返回：
            航路点名称列表
        """
        candidates = []
        
        for name, wp in self.eaip_loader.waypoints.items():
            if self._is_point_near_great_circle(start, end, wp):
                distance = self._distance_to_great_circle(start, end, wp)
                progress = self._calculate_progress(start, end, wp)
                
                if self._is_correct_direction(start, end, wp, progress):
                    candidates.append((name, progress, distance))
        
        candidates.sort(key=lambda x: (x[1], x[2]))
        
        selected = []
        last_progress = -1
        last_lat = start.latitude
        last_lon = start.longitude
        
        for name, progress, distance in candidates:
            if progress - last_progress > 0.05:
                wp = self.eaip_loader.waypoints[name]
                
                if wp.latitude > last_lat + 1.0:
                    continue
                
                lon_diff = wp.longitude - last_lon
                
                if lon_diff > 0.5:
                    continue
                
                if abs(wp.longitude - last_lon) > 2.0:
                    continue
                
                selected.append(name)
                last_progress = progress
                last_lat = wp.latitude
                last_lon = wp.longitude
                
                if len(selected) >= 6:
                    break
        
        return selected
    
    def _is_correct_direction(self, start: 'EAIPAirport', end: 'EAIPAirport', point, progress: float) -> bool:
        """
        判断航路点是否在正确的方向上
        
        参数：
            start: 起点
            end: 终点
            point: 待判断点
            progress: 进度值
        
        返回：
            是否在正确方向上
        """
        expected_lat = start.latitude - (start.latitude - end.latitude) * progress
        expected_lon = start.longitude + (end.longitude - start.longitude) * progress
        
        lat_diff = abs(point.latitude - expected_lat)
        lon_diff = abs(point.longitude - expected_lon)
        
        return lat_diff < 1.5 and lon_diff < 1.5
    
    def _is_point_near_great_circle(self, start: 'EAIPAirport', end: 'EAIPAirport', point) -> bool:
        """
        判断点是否靠近大圆航线
        
        参数：
            start: 起点
            end: 终点
            point: 待判断的点
        
        返回：
            是否靠近大圆航线
        """
        distance = self._distance_to_great_circle(start, end, point)
        return distance < 1.5
    
    def _distance_to_great_circle(self, start: 'EAIPAirport', end: 'EAIPAirport', point) -> float:
        """
        计算点到大圆航线的距离（度）
        
        参数：
            start: 起点
            end: 终点
            point: 待计算点
        
        返回：
            距离（度）
        """
        lat1, lon1 = start.latitude, start.longitude
        lat2, lon2 = end.latitude, end.longitude
        lat3, lon3 = point.latitude, point.longitude
        
        d13 = self._haversine_distance(lat1, lon1, lat3, lon3)
        d12 = self._haversine_distance(lat1, lon1, lat2, lon2)
        d23 = self._haversine_distance(lat2, lon2, lat3, lon3)
        
        if d12 < 0.0001:
            return d13
        
        s = (d13 + d12 + d23) / 2.0
        area_sq = s * (s - d13) * (s - d12) * (s - d23)
        
        if area_sq < 0:
            return min(d13, d23)
        
        height = 2.0 * math.sqrt(max(0, area_sq)) / d12
        return height
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        使用haversine公式计算两点间距离（度）
        
        参数：
            lat1, lon1: 点1坐标
            lat2, lon2: 点2坐标
        
        返回：
            距离（度）
        """
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return math.degrees(c)
    
    def _calculate_progress(self, start: 'EAIPAirport', end: 'EAIPAirport', point) -> float:
        """
        计算点在航线上的进度（0=起点，1=终点）
        
        参数：
            start: 起点
            end: 终点
            point: 待计算点
        
        返回：
            进度值（0-1）
        """
        d13 = self._haversine_distance(start.latitude, start.longitude, point.latitude, point.longitude)
        d12 = self._haversine_distance(start.latitude, start.longitude, end.latitude, end.longitude)
        
        if d12 < 0.0001:
            return 0.0
        
        return min(1.0, max(0.0, d13 / d12))
    
    def _generate_route_with_llm(self, intent: FlightIntent) -> Optional[List[str]]:
        """
        使用大模型生成航路点
        
        参数：
            intent: 飞行意图对象
        
        返回：
            航路点名称列表，失败返回None
        """
        if not Config.LLM_ENABLED:
            logger.info("大模型功能已禁用")
            return None
        
        try:
            # 构建意图字典
            intent_dict = {
                "platform_type": intent.platform_type,
                "mission_type": intent.mission_type.value if intent.mission_type else "",
                "loc_start": intent.loc_start,
                "loc_mid": intent.loc_mid or "",
                "loc_end": intent.loc_end or ""
            }
            
            # 生成提示词
            prompt = self.llm_client.generate_prompt(intent_dict)
            logger.info("生成大模型提示词完成")
            
            # 调用大模型
            result = self.llm_client.generate_route(prompt)
            if not result:
                logger.warning("大模型返回空结果")
                return None
            
            # 验证航路点数据
            is_valid, errors = WaypointValidator.validate(result)
            if not is_valid:
                logger.warning(f"航路点验证失败: {', '.join(errors)}")
                return None
            
            # 提取航路点名称
            waypoints = result.get("waypoints", [])
            if not waypoints:
                logger.warning("大模型返回的航路点列表为空")
                return None
            
            # 构建航路点名称列表（包含起终点）
            route_names = []
            
            # 添加起点
            if intent.loc_start:
                route_names.append(intent.loc_start)
            
            # 添加大模型生成的中间航路点
            for wp in waypoints:
                name = wp.get("name")
                if name:
                    route_names.append(name)
            
            # 添加终点
            if intent.loc_end:
                route_names.append(intent.loc_end)
            
            # 去重（保持顺序）
            route_names = self._remove_duplicates_preserve_order(route_names)
            
            # 验证数量
            if len(route_names) < Config.MIN_WAYPOINTS:
                logger.warning(f"航路点数量不足，最少需要{Config.MIN_WAYPOINTS}个")
                return None
            
            # 将大模型生成的航路点添加到知识库（临时）
            self._add_llm_waypoints_to_kb(waypoints)
            
            logger.info(f"大模型航路点生成成功，共{len(route_names)}个航路点")
            return route_names
            
        except Exception as e:
            logger.error(f"大模型航路点生成异常: {str(e)}")
            return None
    
    def _remove_duplicates_preserve_order(self, lst: List[str]) -> List[str]:
        """
        移除列表中的重复项，保持顺序
        
        参数：
            lst: 输入列表
        
        返回：
            去重后的列表
        """
        seen = set()
        result = []
        for item in lst:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result
    
    def _add_llm_waypoints_to_kb(self, waypoints: List[dict]) -> None:
        """
        将大模型生成的航路点添加到知识库（临时存储）
        
        参数：
            waypoints: 大模型返回的航路点列表
        """
        for wp in waypoints:
            name = wp.get("name")
            lon = wp.get("lon")
            lat = wp.get("lat")
            alt_m = wp.get("alt_m", 0)
            
            if name and lon is not None and lat is not None:
                # 创建临时航路点对象
                temp_wp = Waypoint(
                    name=name,
                    lon=lon,
                    lat=lat,
                    alt_m=alt_m,
                    description=wp.get("description", "")
                )
                # 添加到知识库（临时覆盖）
                self.kb.waypoints[name] = temp_wp
                logger.debug(f"添加临时航路点: {name} ({lon:.4f}, {lat:.4f})")
    
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
            wp = self._get_waypoint_from_eaip_or_kb(name)
            if wp:
                waypoints.append(wp)
            else:
                logger.warning(f"无法解析航路点: {name}")
        return waypoints if waypoints else None
    
    def _get_waypoint_from_eaip_or_kb(self, name: str) -> Optional[Waypoint]:
        """
        从EAIP或知识库获取航路点

        参数：
            name: 航路点名称

        返回：
            Waypoint对象，失败返回None
        """
        eaip_wp = self.eaip_loader.get_waypoint(name)
        if eaip_wp:
            return Waypoint(
                name=eaip_wp.name,
                lon=eaip_wp.longitude,
                lat=eaip_wp.latitude,
                alt_m=0.0
            )
        
        return self.kb.get_waypoint(name)
    
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
