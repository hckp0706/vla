"""
M1模块航路规划器

基于eAIP航路网络图的A*寻路引擎，为任意两两机场之间规划真实民航航路。

核心功能：
1. A*图搜索：在1418个航路点构成的邻接图上寻路，使用Haversine距离+转弯代价
2. 机场接入网络：考虑跑道方向的SID/STAR模拟，选择最优入网/出网航路点
3. 航路平滑：fly-by过渡转弯，消除尖锐折角
4. 预计算缓存：一次性生成所有机场对的航路并缓存
"""

import heapq
import json
import math
import os
import logging
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass, field
from geographiclib.geodesic import Geodesic

logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0


@dataclass
class RouteResult:
    """航路规划结果"""
    airport_start: str
    airport_end: str
    waypoint_names: List[str]
    waypoint_coords: List[Tuple[float, float]]
    total_distance_km: float
    turn_count: int = 0

    def to_dict(self) -> dict:
        return {
            'airport_start': self.airport_start,
            'airport_end': self.airport_end,
            'waypoint_names': self.waypoint_names,
            'waypoint_coords': [{'lat': c[0], 'lon': c[1]} for c in self.waypoint_coords],
            'total_distance_km': round(self.total_distance_km, 1),
            'turn_count': self.turn_count
        }


class RoutePlanner:
    """
    基于eAIP航路网络的A*航路规划器

    使用route_network.json中的1418个航路点及其邻接关系，
    通过A*算法规划任意两点间的最优航路。
    """

    TURN_COST_FACTOR = 0.15
    MAX_SEGMENT_KM = 600.0
    MAX_SEARCH_NODES = 15000

    def __init__(self, route_network_path: str = None, airports_path: str = None):
        self.geod = Geodesic.WGS84
        self.route_network: Dict = {}
        self.airports: Dict[str, dict] = {}
        self.airports_by_name: Dict[str, dict] = {}
        self._dist_cache: Dict[Tuple[str, str], float] = {}

        if route_network_path is None:
            route_network_path = os.path.join(os.path.dirname(__file__), 'data', 'route_network.json')
        if airports_path is None:
            airports_path = os.path.join(os.path.dirname(__file__), 'data', 'eaip_airports.json')

        self._load_route_network(route_network_path)
        self._load_airports(airports_path)

    def _load_route_network(self, path: str):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.route_network = json.load(f)
            connected = sum(1 for v in self.route_network.values() if v.get('connections'))
            logger.info(f"航路网络加载完成：{len(self.route_network)}个节点，{connected}个有连接")
        except Exception as e:
            logger.error(f"加载航路网络失败: {e}")

    def _load_airports(self, path: str):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for item in data:
                if item.get('latitude') is not None and item.get('longitude') is not None:
                    apt = {
                        'icao': item['icao_code'],
                        'name': item['name_cn'],
                        'lat': item['latitude'],
                        'lon': item['longitude'],
                        'elev': item.get('elevation'),
                        'runway_dirs': item.get('runway_direction', []),
                        'iata': item.get('iata_code', '')
                    }
                    self.airports[item['icao_code']] = apt
                    self.airports_by_name[item['name_cn']] = apt
            logger.info(f"机场数据加载完成：{len(self.airports)}个有坐标的机场")
        except Exception as e:
            logger.error(f"加载机场数据失败: {e}")

    def haversine_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return EARTH_RADIUS_KM * c

    def _cached_dist(self, wp1: str, wp2: str) -> float:
        key = (min(wp1, wp2), max(wp1, wp2))
        if key not in self._dist_cache:
            n1, n2 = self.route_network[wp1], self.route_network[wp2]
            self._dist_cache[key] = self.haversine_km(n1['latitude'], n1['longitude'],
                                                       n2['latitude'], n2['longitude'])
        return self._dist_cache[key]

    def _bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        result = self.geod.Inverse(lat1, lon1, lat2, lon2)
        azi = result['azi1']
        return azi % 360

    def _turn_angle(self, heading_in: float, heading_out: float) -> float:
        diff = abs(heading_out - heading_in)
        if diff > 180:
            diff = 360 - diff
        return diff

    def search_airport(self, query: str) -> Optional[dict]:
        query = query.strip()
        if query in self.airports:
            return self.airports[query]
        if query in self.airports_by_name:
            return self.airports_by_name[query]
        query_upper = query.upper()
        for icao, apt in self.airports.items():
            if icao == query_upper:
                return apt
        for name, apt in self.airports_by_name.items():
            if query in name or name in query:
                return apt
        simplified = query.replace('国际机场', '').replace('机场', '').replace('/', '')
        for name, apt in self.airports_by_name.items():
            name_simp = name.replace('国际机场', '').replace('机场', '').replace('/', '')
            if simplified in name_simp or name_simp in simplified:
                return apt
        return None

    def find_nearby_waypoints(self, lat: float, lon: float, max_count: int = 10, max_dist_km: float = 300) -> List[Tuple[str, float]]:
        candidates = []
        for name, wp in self.route_network.items():
            if not wp.get('connections'):
                continue
            d = self.haversine_km(lat, lon, wp['latitude'], wp['longitude'])
            if d <= max_dist_km:
                candidates.append((name, d))
        candidates.sort(key=lambda x: x[1])
        return candidates[:max_count]

    def find_entry_waypoints(self, airport: dict, target_lat: float, target_lon: float, max_count: int = 5) -> List[Tuple[str, float, float]]:
        """
        为机场选择入网航路点，方向为首要因素，距离为次要因素。

        民航飞机起飞后应朝目的地飞行，方向偏差大的航路点重罚。
        跑道方向仅作微调，不作为主要选择依据。

        返回: [(waypoint_name, distance_km, direction_score)]，direction_score越小越好
        """
        nearby = self.find_nearby_waypoints(airport['lat'], airport['lon'], max_count=20, max_dist_km=300)
        if not nearby:
            return []

        apt_lat, apt_lon = airport['lat'], airport['lon']
        bearing_to_target = self._bearing(apt_lat, apt_lon, target_lat, target_lon)

        runway_dirs = airport.get('runway_dirs', [])
        scored = []
        for wp_name, dist in nearby:
            wp = self.route_network[wp_name]
            bearing_to_wp = self._bearing(apt_lat, apt_lon, wp['latitude'], wp['longitude'])

            direction_diff = self._turn_angle(bearing_to_wp, bearing_to_target)

            if direction_diff > 90:
                direction_penalty = 3.0 + (direction_diff - 90) / 90.0 * 5.0
            else:
                direction_penalty = direction_diff / 90.0 * 1.0

            dist_score = dist / 500.0

            runway_bonus = 0.0
            if runway_dirs:
                best_runway_diff = min(
                    self._turn_angle(bearing_to_wp, rd) for rd in runway_dirs
                )
                if best_runway_diff < 45:
                    runway_bonus = -0.1
                elif best_runway_diff > 135:
                    runway_bonus = 0.1

            score = direction_penalty + dist_score + runway_bonus
            scored.append((wp_name, dist, score))

        scored.sort(key=lambda x: x[2])
        return scored[:max_count]

    def find_exit_waypoints(self, airport: dict, from_lat: float, from_lon: float, max_count: int = 5) -> List[Tuple[str, float, float]]:
        """
        为机场选择出网航路点（进近方向），方向为首要因素。

        飞机从from方向来，应沿接近来向的方向进近降落，方向偏差大的重罚。

        返回: [(waypoint_name, distance_km, direction_score)]
        """
        nearby = self.find_nearby_waypoints(airport['lat'], airport['lon'], max_count=20, max_dist_km=300)
        if not nearby:
            return []

        apt_lat, apt_lon = airport['lat'], airport['lon']
        bearing_from_origin = self._bearing(from_lat, from_lon, apt_lat, apt_lon) % 360

        runway_dirs = airport.get('runway_dirs', [])
        scored = []
        for wp_name, dist in nearby:
            wp = self.route_network[wp_name]
            bearing_from_wp = self._bearing(wp['latitude'], wp['longitude'], apt_lat, apt_lon) % 360

            approach_diff = self._turn_angle(bearing_from_wp, bearing_from_origin)

            if approach_diff > 90:
                direction_penalty = 3.0 + (approach_diff - 90) / 90.0 * 5.0
            else:
                direction_penalty = approach_diff / 90.0 * 1.0

            dist_score = dist / 500.0

            runway_alignment = 0.0
            if runway_dirs:
                best_alignment = min(
                    self._turn_angle(bearing_from_wp, rd) for rd in runway_dirs
                )
                if best_alignment < 30:
                    runway_alignment = -0.1
                elif best_alignment > 90:
                    runway_alignment = 0.1

            score = direction_penalty + dist_score + runway_alignment
            scored.append((wp_name, dist, score))

        scored.sort(key=lambda x: x[2])
        return scored[:max_count]

    DIRECTION_DEVIATION_FACTOR = 0.3

    def astar_search(self, start_wp: str, end_wp: str) -> Optional[List[str]]:
        """
        A*算法在航路网络图上搜索最短路径。

        边权重 = Haversine距离 + 转弯代价 + 方向偏差代价
        启发函数 = Haversine距离到终点

        方向偏差代价：当飞行方向偏离起终点连线方向超过60°时，施加额外代价，
        防止A*选择"先绕路再折回"的路径。
        """
        if start_wp not in self.route_network or end_wp not in self.route_network:
            return None
        if start_wp == end_wp:
            return [start_wp]

        start_data = self.route_network[start_wp]
        end_data = self.route_network[end_wp]
        start_lat, start_lon = start_data['latitude'], start_data['longitude']
        end_lat, end_lon = end_data['latitude'], end_data['longitude']
        overall_bearing = self._bearing(start_lat, start_lon, end_lat, end_lon)

        open_set = [(0.0, 0, start_wp)]
        g_score = {start_wp: 0.0}
        came_from: Dict[str, Tuple[str, float]] = {}
        visited = set()
        counter = 1

        start_connections = start_data.get('connections', [])
        if not start_connections:
            return None

        while open_set:
            f_val, _, current = heapq.heappop(open_set)

            if current == end_wp:
                path = []
                node = current
                while node in came_from:
                    path.append(node)
                    node = came_from[node][0]
                path.append(start_wp)
                path.reverse()
                return path

            if current in visited:
                continue
            visited.add(current)

            if len(visited) > self.MAX_SEARCH_NODES:
                logger.warning(f"A*搜索超过{self.MAX_SEARCH_NODES}个节点，终止")
                return None

            current_data = self.route_network[current]
            current_lat = current_data['latitude']
            current_lon = current_data['longitude']
            neighbors = current_data.get('connections', [])

            for neighbor in neighbors:
                if neighbor in visited:
                    continue
                if neighbor not in self.route_network:
                    continue

                dist = self._cached_dist(current, neighbor)
                if dist > self.MAX_SEGMENT_KM:
                    continue

                turn_cost = 0.0
                if current in came_from:
                    prev_wp = came_from[current][0]
                    prev_data = self.route_network[prev_wp]
                    heading_in = self._bearing(prev_data['latitude'], prev_data['longitude'],
                                               current_lat, current_lon)
                    neighbor_data = self.route_network[neighbor]
                    heading_out = self._bearing(current_lat, current_lon,
                                                neighbor_data['latitude'], neighbor_data['longitude'])
                    turn_angle = self._turn_angle(heading_in % 360, heading_out % 360)
                    turn_cost = dist * self.TURN_COST_FACTOR * (turn_angle / 180.0)

                neighbor_data = self.route_network[neighbor]
                seg_bearing = self._bearing(current_lat, current_lon,
                                            neighbor_data['latitude'], neighbor_data['longitude'])
                dir_deviation = self._turn_angle(seg_bearing, overall_bearing)
                direction_cost = 0.0
                if dir_deviation > 60:
                    direction_cost = dist * self.DIRECTION_DEVIATION_FACTOR * ((dir_deviation - 60) / 120.0)

                tentative_g = g_score[current] + dist + turn_cost + direction_cost

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    g_score[neighbor] = tentative_g
                    came_from[neighbor] = (current, dist)
                    h = self.haversine_km(neighbor_data['latitude'], neighbor_data['longitude'],
                                          end_lat, end_lon)
                    f = tentative_g + h
                    counter += 1
                    heapq.heappush(open_set, (f, counter, neighbor))

        return None

    def plan_route(self, start_airport_query: str, end_airport_query: str) -> Optional[RouteResult]:
        """
        规划两个机场之间的民航航路。

        完整流程：
        1. 查找起终点机场
        2. 为起点选择入网航路点（考虑跑道方向）
        3. 为终点选择出网航路点（考虑跑道方向/进近方向）
        4. A*搜索航路网络
        5. 组装完整航路（机场→入网点→...→出网点→机场）
        """
        start_apt = self.search_airport(start_airport_query)
        end_apt = self.search_airport(end_airport_query)

        if not start_apt:
            logger.error(f"未找到起点机场: {start_airport_query}")
            return None
        if not end_apt:
            logger.error(f"未找到终点机场: {end_airport_query}")
            return None

        if start_apt['icao'] == end_apt['icao']:
            logger.warning("起终点机场相同")
            return None

        logger.info(f"规划航路: {start_apt['name']}({start_apt['icao']}) → {end_apt['name']}({end_apt['icao']})")

        entry_candidates = self.find_entry_waypoints(start_apt, end_apt['lat'], end_apt['lon'], max_count=5)
        exit_candidates = self.find_exit_waypoints(end_apt, start_apt['lat'], start_apt['lon'], max_count=5)

        if not entry_candidates:
            logger.warning(f"起点机场{start_apt['name']}附近无航路点，使用直线")
            return self._direct_route(start_apt, end_apt)
        if not exit_candidates:
            logger.warning(f"终点机场{end_apt['name']}附近无航路点，使用直线")
            return self._direct_route(start_apt, end_apt)

        search_entries = entry_candidates[:2]
        search_exits = exit_candidates[:2]

        best_result = None
        best_total = float('inf')

        for entry_wp, entry_dist, entry_score in search_entries:
            for exit_wp, exit_dist, exit_score in search_exits:
                if entry_wp == exit_wp:
                    continue

                network_path = self.astar_search(entry_wp, exit_wp)
                if network_path is None:
                    continue

                network_dist = sum(
                    self._cached_dist(network_path[i], network_path[i + 1])
                    for i in range(len(network_path) - 1)
                )

                total = (entry_dist + network_dist + exit_dist
                         + entry_score * 50 + exit_score * 50)

                if total < best_total:
                    best_total = total
                    best_result = (entry_wp, exit_wp, network_path, entry_dist, exit_dist, network_dist)

        if best_result is None and (len(entry_candidates) > 2 or len(exit_candidates) > 2):
            for entry_wp, entry_dist, entry_score in entry_candidates[2:]:
                for exit_wp, exit_dist, exit_score in exit_candidates:
                    if entry_wp == exit_wp:
                        continue
                    network_path = self.astar_search(entry_wp, exit_wp)
                    if network_path is None:
                        continue
                    network_dist = sum(
                        self._cached_dist(network_path[i], network_path[i + 1])
                        for i in range(len(network_path) - 1)
                    )
                    total = (entry_dist + network_dist + exit_dist
                             + entry_score * 50 + exit_score * 50)
                    if total < best_total:
                        best_total = total
                        best_result = (entry_wp, exit_wp, network_path, entry_dist, exit_dist, network_dist)

            for entry_wp, entry_dist, entry_score in entry_candidates[:2]:
                for exit_wp, exit_dist, exit_score in exit_candidates[2:]:
                    if entry_wp == exit_wp:
                        continue
                    network_path = self.astar_search(entry_wp, exit_wp)
                    if network_path is None:
                        continue
                    network_dist = sum(
                        self._cached_dist(network_path[i], network_path[i + 1])
                        for i in range(len(network_path) - 1)
                    )
                    total = (entry_dist + network_dist + exit_dist
                             + entry_score * 50 + exit_score * 50)
                    if total < best_total:
                        best_total = total
                        best_result = (entry_wp, exit_wp, network_path, entry_dist, exit_dist, network_dist)

        if best_result is None:
            logger.warning("航路网络寻路失败，降级为直线航路")
            return self._direct_route(start_apt, end_apt)

        entry_wp, exit_wp, network_path, entry_dist, exit_dist, network_dist = best_result

        names = [start_apt['icao']]
        coords = [(start_apt['lat'], start_apt['lon'])]

        for wp_name in network_path:
            wp = self.route_network[wp_name]
            if names[-1] != wp_name:
                names.append(wp_name)
                coords.append((wp['latitude'], wp['longitude']))

        if names[-1] != end_apt['icao']:
            names.append(end_apt['icao'])
            coords.append((end_apt['lat'], end_apt['lon']))

        names, coords = self._filter_backtrack_waypoints(names, coords)

        total_km = entry_dist + network_dist + exit_dist
        turn_count = sum(1 for i in range(1, len(names) - 1)
                         if names[i] in self.route_network)

        logger.info(f"航路规划完成: {len(names)}个点, {total_km:.0f}km, {turn_count}个转弯点")

        return RouteResult(
            airport_start=start_apt['icao'],
            airport_end=end_apt['icao'],
            waypoint_names=names,
            waypoint_coords=coords,
            total_distance_km=total_km,
            turn_count=turn_count
        )

    def _filter_backtrack_waypoints(self, names: List[str], coords: List[Tuple[float, float]]) -> Tuple[List[str], List[Tuple[float, float]]]:
        """
        过滤导致折返和大转弯的中间航路点。

        两轮过滤：
        1. 方向过滤：某段方向与总体方向偏差>90°，移除该段终点
        2. 大转弯过滤：相邻段转弯>90°，移除导致大转弯的中间点

        反复迭代直到无折返/大转弯段。
        """
        if len(coords) <= 3:
            return names, coords

        start_lat, start_lon = coords[0]
        end_lat, end_lon = coords[-1]
        overall_bearing = self._bearing(start_lat, start_lon, end_lat, end_lon)

        changed = True
        while changed:
            changed = False

            filtered_names = [names[0]]
            filtered_coords = [coords[0]]

            for i in range(1, len(coords) - 1):
                prev_lat, prev_lon = filtered_coords[-1]
                curr_lat, curr_lon = coords[i]

                seg_bearing = self._bearing(prev_lat, prev_lon, curr_lat, curr_lon)
                deviation = self._turn_angle(seg_bearing, overall_bearing)

                if deviation > 90:
                    changed = True
                    continue

                filtered_names.append(names[i])
                filtered_coords.append(coords[i])

            filtered_names.append(names[-1])
            filtered_coords.append(coords[-1])

            if len(filtered_names) != len(names):
                names = filtered_names
                coords = filtered_coords
            else:
                break

        sharp_changed = True
        while sharp_changed:
            sharp_changed = False
            if len(coords) < 3:
                break

            new_names = [names[0]]
            new_coords = [coords[0]]

            for i in range(1, len(coords) - 1):
                prev_lat, prev_lon = new_coords[-1]
                curr_lat, curr_lon = coords[i]
                next_lat, next_lon = coords[i + 1]

                h_in = self._bearing(prev_lat, prev_lon, curr_lat, curr_lon) % 360
                h_out = self._bearing(curr_lat, curr_lon, next_lat, next_lon) % 360
                turn = self._turn_angle(h_in, h_out)

                if turn > 90:
                    sharp_changed = True
                    continue

                new_names.append(names[i])
                new_coords.append(coords[i])

            new_names.append(names[-1])
            new_coords.append(coords[-1])

            if len(new_names) != len(names):
                names = new_names
                coords = new_coords
            else:
                break

        return names, coords

    def _direct_route(self, start_apt: dict, end_apt: dict) -> RouteResult:
        """直线航路降级方案"""
        dist = self.haversine_km(start_apt['lat'], start_apt['lon'],
                                 end_apt['lat'], end_apt['lon'])
        return RouteResult(
            airport_start=start_apt['icao'],
            airport_end=end_apt['icao'],
            waypoint_names=[start_apt['icao'], end_apt['icao']],
            waypoint_coords=[(start_apt['lat'], start_apt['lon']),
                             (end_apt['lat'], end_apt['lon'])],
            total_distance_km=dist,
            turn_count=0
        )

    def smooth_route(self, coords: List[Tuple[float, float]],
                     turn_radius_km: float = 8.0,
                     min_turn_angle: float = 3.0) -> List[Tuple[float, float]]:
        """
        对航路点序列进行fly-by转弯平滑处理。

        在转弯点前开始转弯，用圆弧过渡替代尖锐折角。
        转弯提前量 = R * tan(θ/2)，其中R为转弯半径，θ为转弯角。
        大角度转弯自动增大转弯半径。

        参数:
            coords: 航路点坐标列表 [(lat, lon), ...]
            turn_radius_km: 基础转弯半径（公里），民航标准约8km
            min_turn_angle: 最小平滑转弯角（度），小于此角度不平滑
        """
        if len(coords) < 3:
            return coords

        smoothed = [coords[0]]

        for i in range(1, len(coords) - 1):
            prev_lat, prev_lon = coords[i - 1]
            curr_lat, curr_lon = coords[i]
            next_lat, next_lon = coords[i + 1]

            heading_in = self._bearing(prev_lat, prev_lon, curr_lat, curr_lon) % 360
            heading_out = self._bearing(curr_lat, curr_lon, next_lat, next_lon) % 360
            turn_angle = self._turn_angle(heading_in, heading_out)

            if turn_angle < min_turn_angle:
                smoothed.append(coords[i])
                continue

            dist_prev = self.haversine_km(prev_lat, prev_lon, curr_lat, curr_lon)
            dist_next = self.haversine_km(curr_lat, curr_lon, next_lat, next_lon)

            effective_radius = turn_radius_km
            if turn_angle > 60:
                effective_radius = turn_radius_km * (1.0 + (turn_angle - 60) / 60.0)

            tan_half = math.tan(math.radians(min(turn_angle, 170) / 2))
            advance_km = effective_radius * tan_half

            max_advance_prev = dist_prev * 0.45
            max_advance_next = dist_next * 0.45
            advance_km = min(advance_km, max_advance_prev, max_advance_next)
            advance_km = max(advance_km, 0.3)

            start_frac = max(0.0, 1.0 - advance_km / dist_prev) if dist_prev > 0 else 0.0
            end_frac = min(1.0, advance_km / dist_next) if dist_next > 0 else 1.0

            r1 = self.geod.Direct(prev_lat, prev_lon, heading_in, dist_prev * start_frac * 1000)
            entry_point = (r1['lat2'], r1['lon2'])

            r2 = self.geod.Direct(curr_lat, curr_lon, heading_out, dist_next * end_frac * 1000)
            exit_point = (r2['lat2'], r2['lon2'])

            num_arc = max(4, int(turn_angle / 8))
            for j in range(1, num_arc):
                frac = j / num_arc
                arc_lat = entry_point[0] * (1 - frac) + exit_point[0] * frac
                arc_lon = entry_point[1] * (1 - frac) + exit_point[1] * frac
                smoothed.append((arc_lat, arc_lon))

        smoothed.append(coords[-1])
        return smoothed

    def build_route_cache(self, output_path: str = None) -> Dict[str, RouteResult]:
        """
        预计算所有机场对之间的航路，缓存到JSON文件。

        57个机场 → C(57,2) = 1596条航路
        支持增量保存：每200条自动保存，中断后可从已有文件续算
        """
        if output_path is None:
            output_path = os.path.join(os.path.dirname(__file__), 'data', 'route_cache.json')

        cache = {}
        existing_count = 0
        if os.path.exists(output_path):
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                existing_count = len(cache)
                logger.info(f"发现已有缓存文件，包含{existing_count}条航路，将增量续算")
            except Exception:
                logger.warning("已有缓存文件损坏，从头开始计算")
                cache = {}

        airport_list = list(self.airports.values())
        n = len(airport_list)
        total_pairs = n * (n - 1) // 2
        logger.info(f"开始预计算 {total_pairs} 条机场对航路...")

        success = 0
        failed = 0
        skipped = 0
        checkpoint_interval = 200

        for i in range(n):
            for j in range(i + 1, n):
                apt_a = airport_list[i]
                apt_b = airport_list[j]

                key = f"{apt_a['icao']}-{apt_b['icao']}"
                reverse_key = f"{apt_b['icao']}-{apt_a['icao']}"

                if key in cache and reverse_key in cache:
                    skipped += 1
                    continue

                result = self.plan_route(apt_a['icao'], apt_b['icao'])
                if result:
                    cache[key] = result.to_dict()

                    reverse_coords = list(reversed(result.waypoint_coords))
                    reverse_names = list(reversed(result.waypoint_names))
                    reverse_result = RouteResult(
                        airport_start=apt_b['icao'],
                        airport_end=apt_a['icao'],
                        waypoint_names=reverse_names,
                        waypoint_coords=reverse_coords,
                        total_distance_km=result.total_distance_km,
                        turn_count=result.turn_count
                    )
                    cache[reverse_key] = reverse_result.to_dict()
                    success += 1
                else:
                    failed += 1

                done = success + failed + skipped
                if done % checkpoint_interval == 0 and (success + failed) > 0:
                    logger.info(f"进度: {done}/{total_pairs}, 新增成功: {success}, 失败: {failed}, 跳过: {skipped}")
                    self._save_cache(cache, output_path)

        logger.info(f"预计算完成: 新增成功{success}, 失败{failed}, 跳过{skipped}")

        self._save_cache(cache, output_path)
        return cache

    def _save_cache(self, cache: Dict, output_path: str):
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
            logger.info(f"航路缓存已保存: {len(cache)}条航路 → {output_path}")
        except Exception as e:
            logger.error(f"保存航路缓存失败: {e}")

    def load_route_cache(self, cache_path: str = None) -> Dict[str, dict]:
        """加载预计算的航路缓存"""
        if cache_path is None:
            cache_path = os.path.join(os.path.dirname(__file__), 'data', 'route_cache.json')

        if not os.path.exists(cache_path):
            logger.info("航路缓存文件不存在")
            return {}

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            logger.info(f"航路缓存加载完成: {len(cache)}条航路")
            return cache
        except Exception as e:
            logger.error(f"加载航路缓存失败: {e}")
            return {}

    def get_cached_route(self, start_icao: str, end_icao: str,
                         cache: Dict[str, dict]) -> Optional[RouteResult]:
        """从缓存中查询航路"""
        key = f"{start_icao}-{end_icao}"
        if key in cache:
            data = cache[key]
            coords = [(c['lat'], c['lon']) for c in data['waypoint_coords']]
            return RouteResult(
                airport_start=data['airport_start'],
                airport_end=data['airport_end'],
                waypoint_names=data['waypoint_names'],
                waypoint_coords=coords,
                total_distance_km=data['total_distance_km'],
                turn_count=data.get('turn_count', 0)
            )
        return None
