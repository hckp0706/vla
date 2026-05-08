"""
ADS-B报文生成器

本模块实现ADS-B Out报文的仿真生成，遵循1090ES（1090MHz Extended Squitter）标准。
仅为民航飞机生成ADS-B报文，军机（尤其是敌方军机）不会发送ADS-B。

主要功能：
- 判断飞机是否为民航（应发送ADS-B）
- 为民航飞机生成ICAO 24位地址
- 生成航班呼号（Callsign）
- 将轨迹点数据转换为ADS-B报文格式
- 单位换算：米→英尺、m/s→节、m/s→ft/min

ADS-B 1090ES 标准参考：
- DF=17（S模式扩展自发电文）
- TC=1-4：飞机识别号（Callsign）
- TC=9-18：空中位置报文（CPR编码）
- TC=19：空中速度报文
- 广播频率：1090MHz
- 发送间隔：0.5-1秒
"""

import hashlib
import logging
from typing import Optional, List

from .models import TrackPoint, ADSBMessage, FlightPhase, AircraftPerformance

logger = logging.getLogger(__name__)

_M_TO_FT = 3.28084
_MS_TO_KT = 1.94384
_MS_TO_FPM = 196.85


_MILITARY_KEYWORDS = [
    "歼", "轰", "运", "直", "空警", "预警", "加油", "电子战",
    "F-", "F/", "F/A", "B-", "A-", "C-", "E-", "RC-", "RQ-",
    "P-8", "P-1", "U-2", "KC-",
    "苏-", "Su-", "米格", "MiG", "图-", "Tu-",
    "F-2", "F-15J", "F-15K", "F-16K", "F-35A",
    "KF-21", "F-2A",
    "翼龙", "捕食者", "全球鹰", "死神", "彩虹",
    "直升机", "武装直升机",
    "阿帕奇", "黑鹰", "海鹰", "支奴干", "鱼鹰",
    "军机", "战斗机", "轰炸机", "侦察机", "预警机", "巡逻机", "无人机",
]

_CIVIL_KEYWORDS = [
    "民航", "客机", "波音", "空客", "Boeing", "Airbus",
    "737", "747", "777", "787", "A320", "A330", "A350", "A380",
    "EMB", "ERJ", "CRJ", "ARJ",
]

_AIRLINE_CODES = {
    "民航客机": "CCA",
    "波音737": "CSN",
    "波音747": "CCA",
    "波音777": "CCA",
    "波音787": "CCA",
    "空客A320": "CSN",
    "空客A330": "CCA",
    "空客A350": "CCA",
    "空客A380": "CCA",
}

_EMITTER_CATEGORY_MAP = {
    "民航客机": 4,
    "波音737": 3,
    "波音747": 5,
    "波音777": 5,
    "波音787": 5,
    "空客A320": 3,
    "空客A330": 4,
    "空客A350": 4,
    "空客A380": 5,
}

_DEFAULT_EMITTER_CATEGORY = 3


def is_civil_aircraft(platform_type: str) -> bool:
    """
    判断飞机是否为民航飞机（应发送ADS-B）
    
    判断逻辑：
    1. 包含民航关键词 → 民航
    2. 包含军机关键词 → 军机
    3. 无法判断 → 默认军机（安全假设：不确定时视为不发送ADS-B）
    """
    for kw in _CIVIL_KEYWORDS:
        if kw in platform_type:
            return True
    for kw in _MILITARY_KEYWORDS:
        if kw in platform_type:
            return False
    return False


def generate_icao24(target_id: str, platform_type: str) -> str:
    """
    为飞机生成ICAO 24位地址
    
    使用确定性哈希算法，确保同一架飞机每次生成相同的ICAO地址。
    ICAO 24位地址是全球唯一的飞机标识符，范围：000000~FFFFFF。
    
    参数：
        target_id: 目标批号
        platform_type: 机型名称
    
    返回：
        6位十六进制字符串，如"7806E2"
    """
    key = f"{target_id}_{platform_type}".encode('utf-8')
    hash_bytes = hashlib.sha256(key).digest()
    icao_int = int.from_bytes(hash_bytes[:3], 'big') & 0x00FFFFFF
    return f"{icao_int:06X}"


def generate_callsign(target_id: str, platform_type: str) -> str:
    """
    为民航飞机生成航班呼号
    
    格式：航空公司IATA代码 + 航班号（3-4位数字）
    如：CCA1234（国航1234）、CSN5678（南航5678）
    
    参数：
        target_id: 目标批号
        platform_type: 机型名称
    
    返回：
        航班呼号，最多8个字符
    """
    airline_code = _AIRLINE_CODES.get(platform_type, "CCA")
    try:
        flight_num = int(target_id.lstrip('0') or '1')
    except ValueError:
        flight_num = 1
    flight_num = flight_num % 9000 + 1000
    callsign = f"{airline_code}{flight_num}"
    return callsign[:8].ljust(8)


def get_emitter_category(platform_type: str) -> int:
    """
    获取飞机的ADS-B发射类别代码
    
    参照ADS-B标准中的DF=17 TC=4报文格式：
    1 = A型（重型喷气机，如B747、A380）
    2 = B型（中型喷气机，如B777、A350）
    3 = C型（中型螺旋桨/支线喷气机，如B737、A320）
    4 = D型（轻型螺旋桨/支线飞机）
    5 = 重型（>= 136吨，B747、A380）
    6 = 高旋翼（直升机）
    
    参数：
        platform_type: 机型名称
    
    返回：
        发射类别代码
    """
    return _EMITTER_CATEGORY_MAP.get(platform_type, _DEFAULT_EMITTER_CATEGORY)


def generate_squawk(phase: FlightPhase) -> str:
    """
    根据飞行阶段生成应答机编码（Squawk码）
    
    常用编码：
    - 2000：IFR飞行（仪表飞行规则），巡航阶段使用
    - 1200：VFR飞行（目视飞行规则），训练飞行使用
    - 1201：VFR飞行（特殊）
    - 7700：紧急情况
    - 7600：无线电故障
    - 7500：劫机
    
    参数：
        phase: 飞行阶段
    
    返回：
        4位八进制字符串，如"2000"
    """
    if phase in (FlightPhase.GROUND_TAKEOFF, FlightPhase.LANDING):
        return "2000"
    elif phase == FlightPhase.CRUISING:
        return "2000"
    elif phase == FlightPhase.CLIMBING:
        return "2000"
    elif phase == FlightPhase.DESCENDING:
        return "2000"
    else:
        return "2000"


class ADSBGenerator:
    """
    ADS-B报文生成器
    
    为民航飞机的每个轨迹点生成对应的ADS-B Out报文。
    军机（尤其是敌方军机）不发送ADS-B报文。
    """
    
    def __init__(self, target_id: str, platform_type: str):
        """
        初始化ADS-B生成器
        
        参数：
            target_id: 目标批号
            platform_type: 机型名称
        """
        self.target_id = target_id
        self.platform_type = platform_type
        self.is_civil = is_civil_aircraft(platform_type)
        
        if self.is_civil:
            self.icao24 = generate_icao24(target_id, platform_type)
            self.callsign = generate_callsign(target_id, platform_type)
            self.emitter_category = get_emitter_category(platform_type)
            logger.info(
                f"民航飞机 {platform_type}，启用ADS-B: "
                f"ICAO={self.icao24}, Callsign={self.callsign}"
            )
        else:
            self.icao24 = ""
            self.callsign = ""
            self.emitter_category = 0
            logger.info(f"军机 {platform_type}，不发送ADS-B报文")
    
    def generate_message(self, track_point: TrackPoint) -> Optional[ADSBMessage]:
        """
        为单个轨迹点生成ADS-B报文
        
        参数：
            track_point: 轨迹点数据
        
        返回：
            ADSBMessage对象（民航），或None（军机）
        """
        if not self.is_civil:
            return None
        
        on_ground = track_point.phase in (
            FlightPhase.GROUND_TAKEOFF, FlightPhase.LANDING
        )
        
        altitude_ft = track_point.alt_m * _M_TO_FT
        ground_speed_kt = track_point.speed_ms * _MS_TO_KT
        vertical_rate_fpm = track_point.vertical_rate_ms * _MS_TO_FPM
        squawk = generate_squawk(track_point.phase)
        
        return ADSBMessage(
            icao24=self.icao24,
            callsign=self.callsign,
            altitude_ft=altitude_ft,
            ground_speed_kt=ground_speed_kt,
            track=track_point.heading_deg,
            vertical_rate_fpm=vertical_rate_fpm,
            lat=track_point.lat,
            lon=track_point.lon,
            on_ground=on_ground,
            squawk=squawk,
            emitter_category=self.emitter_category,
            message_type="adsb_icao"
        )
    
    def generate_messages(self, track_points: List[TrackPoint]) -> List[ADSBMessage]:
        """
        为轨迹点列表批量生成ADS-B报文
        
        参数：
            track_points: 轨迹点列表
        
        返回：
            ADSBMessage列表（民航），或空列表（军机）
        """
        if not self.is_civil:
            return []
        
        messages = []
        for tp in track_points:
            msg = self.generate_message(tp)
            if msg:
                messages.append(msg)
        
        logger.info(f"生成 {len(messages)} 条ADS-B报文")
        return messages
