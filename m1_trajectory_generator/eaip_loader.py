"""
EAIP数据加载模块

本模块负责加载和管理从中国民航局EAIP（En-route Aeronautical Information Publication）
提取的官方数据，包括机场和航路点信息。

数据来源：
- 2026 Nr.04 EAIP文件

功能：
1. 加载机场数据
2. 加载航路点数据
3. 提供机场和航路点查询接口
4. 支持名称模糊匹配
"""

import json
import os
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class EAIPAirport:
    """EAIP机场数据类"""
    def __init__(self, icao_code: str, name_cn: str, latitude: float, longitude: float, 
                 elevation: float = None, iata_code: str = None, runway_direction: tuple = None):
        self.icao_code = icao_code
        self.name_cn = name_cn
        self.iata_code = iata_code
        self.latitude = latitude
        self.longitude = longitude
        self.elevation = elevation
        self.runway_direction = runway_direction if runway_direction else (0, 180)

    def has_coordinates(self) -> bool:
        """检查是否有坐标信息"""
        return self.latitude is not None and self.longitude is not None
    
    def has_runway_info(self) -> bool:
        """检查是否有跑道信息"""
        return self.runway_direction is not None and self.runway_direction != (0, 180)

class EAIPWaypoint:
    """EAIP航路点数据类"""
    def __init__(self, name: str, latitude: float, longitude: float):
        self.name = name
        self.latitude = latitude
        self.longitude = longitude

class EAIPLoader:
    """EAIP数据加载器"""
    
    def __init__(self):
        self.airports: Dict[str, EAIPAirport] = {}
        self.airports_by_name: Dict[str, EAIPAirport] = {}
        self.waypoints: Dict[str, EAIPWaypoint] = {}
        self._load_data()
    
    def _load_data(self):
        """加载EAIP数据"""
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        
        airport_file = os.path.join(data_dir, 'eaip_airports.json')
        if os.path.exists(airport_file):
            self._load_airports(airport_file)
        else:
            backup_file = os.path.join(os.path.dirname(__file__), '../output/eaip_data/eaip_airports.json')
            if os.path.exists(backup_file):
                self._load_airports(backup_file)
            else:
                logger.warning("EAIP机场数据文件不存在")
        
        waypoint_file = os.path.join(data_dir, 'enr_4_4_waypoints.json')
        if os.path.exists(waypoint_file):
            self._load_waypoints(waypoint_file)
        else:
            logger.warning("EAIP航路点数据文件不存在")
    
    def _load_airports(self, filepath: str):
        """加载机场数据"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            runway_count = 0
            for item in data:
                if item.get('latitude') is not None and item.get('longitude') is not None:
                    # 解析跑道方向数据
                    runway_dir = item.get('runway_direction')
                    if runway_dir and isinstance(runway_dir, list) and len(runway_dir) >= 2:
                        runway_dir = (runway_dir[0], runway_dir[1])
                        runway_count += 1
                    else:
                        runway_dir = None
                    
                    airport = EAIPAirport(
                        icao_code=item['icao_code'],
                        name_cn=item['name_cn'],
                        latitude=item['latitude'],
                        longitude=item['longitude'],
                        elevation=item.get('elevation'),
                        iata_code=item.get('iata_code'),
                        runway_direction=runway_dir
                    )
                    self.airports[item['icao_code']] = airport
                    self.airports_by_name[item['name_cn']] = airport
            
            logger.info(f"已加载 {len(self.airports)} 个EAIP机场数据（含坐标），其中 {runway_count} 个有机场跑道信息")
        except Exception as e:
            logger.error(f"加载EAIP机场数据失败: {e}")
    
    def _load_waypoints(self, filepath: str):
        """加载航路点数据"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for item in data:
                waypoint = EAIPWaypoint(
                    name=item['name'],
                    latitude=item['latitude'],
                    longitude=item['longitude']
                )
                self.waypoints[item['name']] = waypoint
            
            logger.info(f"已加载 {len(self.waypoints)} 个EAIP航路点数据")
        except Exception as e:
            logger.error(f"加载EAIP航路点数据失败: {e}")
    
    def get_airport_by_icao(self, icao_code: str) -> Optional[EAIPAirport]:
        """根据ICAO代码获取机场"""
        return self.airports.get(icao_code.upper())
    
    def get_airport_by_name(self, name: str) -> Optional[EAIPAirport]:
        """根据中文名称获取机场"""
        return self.airports_by_name.get(name)
    
    def search_airport(self, query: str) -> Optional[EAIPAirport]:
        """搜索机场（支持模糊匹配）"""
        query = query.strip()
        
        if query in self.airports_by_name:
            return self.airports_by_name[query]
        
        query_upper = query.upper()
        if query_upper in self.airports:
            return self.airports[query_upper]
        
        query_simplified = self._simplify_name(query)
        
        for name, airport in self.airports_by_name.items():
            if query in name or name in query:
                return airport
            
            name_simplified = self._simplify_name(name)
            if query_simplified in name_simplified or name_simplified in query_simplified:
                return airport
        
        return None
    
    def _simplify_name(self, name: str) -> str:
        """简化名称，去除常见后缀"""
        suffixes = ['国际机场', '机场', '航空港', '航站']
        result = name
        for suffix in suffixes:
            result = result.replace(suffix, '')
        result = result.replace('/', '')
        return result.strip()
    
    def get_waypoint(self, name: str) -> Optional[EAIPWaypoint]:
        """获取航路点"""
        return self.waypoints.get(name.upper())
    
    def has_airport_data(self) -> bool:
        """检查是否有可用的机场数据"""
        return len(self.airports) > 0
    
    def has_waypoint_data(self) -> bool:
        """检查是否有可用的航路点数据"""
        return len(self.waypoints) > 0

    def get_all_airport_names(self) -> List[str]:
        """获取所有机场名称列表"""
        return list(self.airports_by_name.keys())

    def get_all_waypoint_names(self) -> List[str]:
        """获取所有航路点名称列表"""
        return list(self.waypoints.keys())