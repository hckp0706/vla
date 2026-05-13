# -*- coding: utf-8 -*-
import math
from typing import Optional

MAJOR_CITIES = [
    ("北京", 116.41, 39.90),
    ("上海", 121.47, 31.23),
    ("天津", 117.20, 39.08),
    ("重庆", 106.55, 29.56),
    ("石家庄", 114.51, 38.04),
    ("太原", 112.55, 37.87),
    ("沈阳", 123.43, 41.80),
    ("长春", 125.32, 43.88),
    ("哈尔滨", 126.63, 45.75),
    ("南京", 118.78, 32.06),
    ("杭州", 120.15, 30.29),
    ("合肥", 117.27, 31.86),
    ("福州", 119.30, 26.08),
    ("南昌", 115.89, 28.68),
    ("济南", 117.00, 36.67),
    ("郑州", 113.65, 34.76),
    ("武汉", 114.30, 30.59),
    ("长沙", 112.98, 28.23),
    ("广州", 113.26, 23.13),
    ("南宁", 108.37, 22.82),
    ("海口", 110.35, 20.02),
    ("成都", 104.07, 30.67),
    ("贵阳", 106.71, 26.65),
    ("昆明", 102.83, 25.02),
    ("拉萨", 91.11, 29.65),
    ("西安", 108.94, 34.27),
    ("兰州", 103.83, 36.06),
    ("西宁", 101.78, 36.62),
    ("银川", 106.27, 38.47),
    ("乌鲁木齐", 87.62, 43.83),
    ("呼和浩特", 111.75, 40.84),
    ("台北", 121.52, 25.05),
    ("深圳", 114.07, 22.55),
    ("珠海", 113.58, 22.27),
    ("厦门", 118.09, 24.48),
    ("大连", 121.61, 38.91),
    ("青岛", 120.38, 36.07),
    ("宁波", 121.55, 29.87),
    ("苏州", 120.62, 31.30),
    ("无锡", 120.30, 31.57),
    ("温州", 120.70, 28.00),
    ("烟台", 121.45, 37.46),
    ("威海", 122.12, 37.51),
    ("连云港", 119.22, 34.60),
    ("南通", 120.86, 32.01),
    ("日照", 119.53, 35.42),
    ("舟山", 122.11, 30.01),
    ("泉州", 118.68, 24.87),
    ("湛江", 110.36, 21.27),
    ("三亚", 109.51, 18.25),
    ("桂林", 110.29, 25.27),
]

KEY_REGIONS = [
    ("渤海海域", 117.5, 122.0, 37.0, 41.0),
    ("黄海海域", 119.0, 126.0, 33.0, 39.5),
    ("东海海域", 117.0, 131.0, 24.0, 33.0),
    ("南海海域", 105.0, 120.0, 3.0, 23.5),
    ("台湾海峡", 118.0, 120.5, 22.0, 25.5),
    ("琼州海峡", 109.5, 110.8, 19.8, 20.5),
    ("朝鲜半岛周边", 124.0, 130.0, 34.0, 43.0),
    ("日本列岛周边", 129.0, 146.0, 30.0, 45.5),
]

MAJOR_AIRPORTS = [
    ("北京首都国际机场", "ZBAA", 116.58, 40.08),
    ("北京大兴国际机场", "ZBAD", 116.41, 39.51),
    ("上海浦东国际机场", "ZSPD", 121.81, 31.14),
    ("上海虹桥国际机场", "ZSSS", 121.34, 31.20),
    ("广州白云国际机场", "ZGGG", 113.30, 23.39),
    ("深圳宝安国际机场", "ZGSZ", 113.81, 22.64),
    ("成都天府国际机场", "ZUTF", 104.50, 30.31),
    ("成都双流国际机场", "ZUUU", 103.95, 30.57),
    ("重庆江北国际机场", "ZUCK", 106.64, 29.72),
    ("杭州萧山国际机场", "ZSHC", 120.43, 30.24),
    ("武汉天河国际机场", "ZHCC", 114.21, 30.78),
    ("南京禄口国际机场", "ZSNJ", 118.86, 31.74),
    ("青岛胶东国际机场", "ZSQD", 120.05, 36.40),
    ("厦门高崎国际机场", "ZSAM", 118.13, 24.54),
    ("长沙黄花国际机场", "ZGHA", 113.22, 28.19),
    ("郑州新郑国际机场", "ZHCC", 113.84, 34.52),
    ("西安咸阳国际机场", "ZLXY", 108.75, 34.44),
    ("大连周水子国际机场", "ZYTL", 121.54, 38.97),
    ("海口美兰国际机场", "ZJHK", 110.46, 19.93),
    ("三亚凤凰国际机场", "ZJSY", 109.41, 18.30),
    ("昆明长水国际机场", "ZPPP", 102.93, 25.10),
    ("哈尔滨太平国际机场", "ZYHB", 126.25, 45.62),
    ("沈阳桃仙国际机场", "ZYTX", 123.48, 41.64),
    ("长春龙嘉国际机场", "ZYCC", 125.68, 43.88),
    ("乌鲁木齐地窝堡国际机场", "ZWUU", 87.47, 43.91),
    ("福州长乐国际机场", "ZSFZ", 119.66, 25.93),
    ("济南遥墙国际机场", "ZSJN", 117.22, 36.76),
    ("宁波栎社国际机场", "ZSNB", 121.46, 29.83),
    ("温州龙湾国际机场", "ZSWZ", 120.85, 27.91),
    ("烟台蓬莱国际机场", "ZSYT", 120.99, 37.67),
]


def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    R = 6371.0
    lon1_r, lat1_r, lon2_r, lat2_r = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2_r - lon1_r
    dlat = lat2_r - lat1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def reverse_lookup_city(lon: float, lat: float, threshold_km: float = 100) -> Optional[str]:
    best_name = None
    best_dist = float("inf")
    for name, city_lon, city_lat in MAJOR_CITIES:
        d = haversine_distance(lon, lat, city_lon, city_lat)
        if d < best_dist:
            best_dist = d
            best_name = name
    if best_name is not None and best_dist <= threshold_km:
        return f"{best_name}附近"
    return None


def reverse_lookup_region(lon: float, lat: float) -> Optional[str]:
    for name, lon_min, lon_max, lat_min, lat_max in KEY_REGIONS:
        if lon_min <= lon <= lon_max and lat_min <= lat <= lat_max:
            return f"{name}上空"
    return None


def reverse_lookup_airport(lon: float, lat: float, threshold_km: float = 5) -> Optional[str]:
    best_name = None
    best_dist = float("inf")
    for name, icao, apt_lon, apt_lat in MAJOR_AIRPORTS:
        d = haversine_distance(lon, lat, apt_lon, apt_lat)
        if d < best_dist:
            best_dist = d
            best_name = name
    if best_name is not None and best_dist <= threshold_km:
        return f"{best_name}附近"
    return None


def reverse_lookup(lon: float, lat: float) -> str:
    result = reverse_lookup_airport(lon, lat, threshold_km=5)
    if result is not None:
        return result
    result = reverse_lookup_city(lon, lat, threshold_km=100)
    if result is not None:
        return result
    result = reverse_lookup_region(lon, lat)
    if result is not None:
        return result
    return f"坐标({lon},{lat})附近"
