"""
M1模块飞行简令解析器

本模块负责将人类可读的飞行简令文本解析为程序可处理的数据结构。

简令格式示例：
    标准格式（带途径点）：
    "0001 民航客机 客运航班 于 2026-04-20 09:20:30 从 北京大兴国际机场 起飞，途径 西安咸阳国际机场，降落 上海虹桥国际机场。"
    
    简化格式（不带途径点）：
    "0002 歼-20 低空突防 于 2026-04-20 10:00:00 从 北京大兴国际机场 起飞，降落 上海虹桥国际机场。"

解析方式：使用正则表达式进行模式匹配，提取各要素

关键规则：
    - 仅起飞时间为必填项
    - 途径点时间和降落时间由系统自动计算
    - 任务类型作为第三参数（机型之后）
"""

import re
import logging
from datetime import datetime
from typing import Optional
from .models import FlightIntent, MissionType

logger = logging.getLogger(__name__)


class IntentParser:
    """
    飞行简令解析器
    
    使用正则表达式解析飞行简令文本，提取以下要素：
        - target_id: 目标批号
        - platform_type: 机型
        - mission_type: 飞行任务类型（可选，第三参数）
        - takeoff_time: 起飞时间
        - loc_start: 起飞地点
        - action_mid: 途径动作（可选）
        - loc_mid: 途径地点（可选）
        - action_end: 降落动作
        - loc_end: 降落地点
    """
    
    # 带途径点的简令正则表达式（新格式）
    # 格式：[批号] [机型] [任务类型] 于 [起飞时间] 从 [起飞地点] 起飞，[途径动作] [途径地点]，[降落动作] [降落地点]
    INTENT_PATTERN_WITH_WAYPOINT_NEW = re.compile(
        r"(?P<target_id>\d+)\s+"                                    # 批号：数字序列
        r"(?P<platform_type>[\u4e00-\u9fa5a-zA-Z0-9\-]+)\s+"        # 机型：中文、英文、数字、连字符
        r"(?P<mission_type>[\u4e00-\u9fa5]+)?\s*"                   # 任务类型（可选，第三参数）：中文
        r"于\s+"
        r"(?P<takeoff_time>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+"  # 起飞时间：YYYY-MM-DD HH:MM:SS
        r"从\s+"
        r"(?P<loc_start>[\u4e00-\u9fa5a-zA-Z0-9]+)\s+"              # 起飞地点：中文、英文、数字
        r"起飞"
        r"，?\s*(?P<action_mid>[\u4e00-\u9fa5]+)\s+"                 # 途径动作：中文（如"途径"、"经停"）
        r"(?P<loc_mid>[\u4e00-\u9fa5a-zA-Z0-9]+)"                   # 途径地点
        r"，?\s*(?P<action_end>[\u4e00-\u9fa5]+)\s+"                # 降落动作：中文（如"降落"、"抵达"）
        r"(?P<loc_end>[\u4e00-\u9fa5a-zA-Z0-9]+)"                   # 降落地点
        r"。?"
    )

    # 简化格式简令正则表达式（新格式，不带途径点）
    # 格式：[批号] [机型] [任务类型] 于 [起飞时间] 从 [起飞地点] 起飞，[降落动作] [降落地点]
    INTENT_PATTERN_SIMPLE_NEW = re.compile(
        r"(?P<target_id>\d+)\s+"                                    # 批号：数字序列
        r"(?P<platform_type>[\u4e00-\u9fa5a-zA-Z0-9\-]+)\s+"        # 机型：中文、英文、数字、连字符
        r"(?P<mission_type>[\u4e00-\u9fa5]+)?\s*"                   # 任务类型（可选，第三参数）：中文
        r"于\s+"
        r"(?P<takeoff_time>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+"  # 起飞时间：YYYY-MM-DD HH:MM:SS
        r"从\s+"
        r"(?P<loc_start>[\u4e00-\u9fa5a-zA-Z0-9]+)\s+"              # 起飞地点：中文、英文、数字
        r"起飞"
        r"，?\s*(?P<action_end>[\u4e00-\u9fa5]+)\s+"                 # 降落动作：中文
        r"(?P<loc_end>[\u4e00-\u9fa5a-zA-Z0-9]+)"                   # 降落地点
        r"。?"
    )
    
    # 旧格式正则表达式（兼容旧版本）
    INTENT_PATTERN_WITH_WAYPOINT_OLD = re.compile(
        r"(?P<target_id>\d+)\s+"                                    # 批号：数字序列
        r"(?P<platform_type>[\u4e00-\u9fa5a-zA-Z0-9\-]+)\s+"        # 机型：中文、英文、数字、连字符
        r"于\s+"
        r"(?P<takeoff_time>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+"  # 起飞时间：YYYY-MM-DD HH:MM:SS
        r"从\s+"
        r"(?P<loc_start>[\u4e00-\u9fa5a-zA-Z0-9]+)\s+"              # 起飞地点：中文、英文、数字
        r"起飞"
        r"(?:，?\s*执行\s*(?P<mission_type>[\u4e00-\u9fa5]+)\s*任务)?"  # 任务类型（可选）：中文
        r"，?\s*(?P<action_mid>[\u4e00-\u9fa5]+)\s+"                 # 途径动作：中文（如"途径"、"经停"）
        r"(?P<loc_mid>[\u4e00-\u9fa5a-zA-Z0-9]+)\s+"                # 途径地点
        r"(?P<time_mid>\d{2}:\d{2}:\d{2})"                          # 途径时间：HH:MM:SS
        r"，?\s*(?P<action_end>[\u4e00-\u9fa5]+)\s+"                # 降落动作：中文（如"降落"、"抵达"）
        r"(?P<loc_end>[\u4e00-\u9fa5a-zA-Z0-9]+)\s+"                # 降落地点
        r"(?P<time_end>\d{2}:\d{2}:\d{2})"                          # 降落时间：HH:MM:SS
        r"。?"
    )

    INTENT_PATTERN_SIMPLE_OLD = re.compile(
        r"(?P<target_id>\d+)\s+"                                    # 批号：数字序列
        r"(?P<platform_type>[\u4e00-\u9fa5a-zA-Z0-9\-]+)\s+"        # 机型：中文、英文、数字、连字符
        r"于\s+"
        r"(?P<takeoff_time>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+"  # 起飞时间：YYYY-MM-DD HH:MM:SS
        r"从\s+"
        r"(?P<loc_start>[\u4e00-\u9fa5a-zA-Z0-9]+)\s+"              # 起飞地点：中文、英文、数字
        r"起飞"
        r"(?:，?\s*执行\s*(?P<mission_type>[\u4e00-\u9fa5]+)\s*任务)?"  # 任务类型（可选）：中文
        r"，?\s*(?P<action_end>[\u4e00-\u9fa5]+)\s+"                 # 降落动作：中文
        r"(?P<loc_end>[\u4e00-\u9fa5a-zA-Z0-9]+)"                    # 降落地点
        r"(?:\s+(?P<time_end>\d{2}:\d{2}:\d{2}))?"                 # 降落时间：HH:MM:SS（可选）
        r"。?"
    )

    # 任务类型关键字映射表
    # 将简令中的任务类型文本映射到MissionType枚举
    MISSION_KEYWORDS = {
        '正常飞行': MissionType.NORMAL_FLIGHT,
        '低空突防': MissionType.LOW_ALTITUDE_PENETRATION,
        '高空侦察': MissionType.HIGH_ALTITUDE_RECONNAISSANCE,
        '巡逻': MissionType.PATROL,
        '拦截': MissionType.INTERCEPT,
        '护航': MissionType.ESCORT,
        '反舰': MissionType.ANTI_SHIP,
        '对地攻击': MissionType.GROUND_ATTACK,
        '电子战': MissionType.ELECTRONIC_WARFARE,
        '空中加油': MissionType.AIR_REFUELING,
        '训练': MissionType.TRAINING,
    }

    def __init__(self, base_date: Optional[str] = None):
        """
        初始化解析器
        
        参数：
            base_date: 基准日期字符串，用于补全途径时间和降落时间的日期部分
                      格式：YYYY-MM-DD
        """
        self.base_date = base_date

    def _parse_mission_type(self, mission_text: Optional[str]) -> Optional[MissionType]:
        """
        解析任务类型文本
        
        支持精确匹配和模糊匹配：
            - 精确匹配：文本完全匹配关键字
            - 模糊匹配：文本包含关键字
        
        参数：
            mission_text: 任务类型文本，如"低空突防"
        
        返回：
            MissionType枚举，未匹配返回None
        """
        if not mission_text:
            return None
        
        mission_text = mission_text.strip()
        
        # 精确匹配
        if mission_text in self.MISSION_KEYWORDS:
            return self.MISSION_KEYWORDS[mission_text]
        
        # 模糊匹配：检查文本是否包含某个关键字
        for keyword, mission_type in self.MISSION_KEYWORDS.items():
            if keyword in mission_text:
                return mission_type
        
        return MissionType.NORMAL_FLIGHT

    def parse(self, intent_text: str) -> Optional[FlightIntent]:
        """
        解析飞行简令文本
        
        优先尝试新格式，再尝试旧格式以保持兼容性
        
        参数：
            intent_text: 飞行简令文本
        
        返回：
            FlightIntent对象，解析失败返回None
        """
        intent_text = intent_text.strip()
        
        # 尝试匹配新格式（带途径点）
        match = self.INTENT_PATTERN_WITH_WAYPOINT_NEW.match(intent_text)
        if match:
            logger.debug("匹配新格式（带途径点）")
            return self._build_intent(match, has_waypoint=True)
        
        # 尝试匹配新格式（简化）
        match = self.INTENT_PATTERN_SIMPLE_NEW.match(intent_text)
        if match:
            logger.debug("匹配新格式（简化）")
            return self._build_intent(match, has_waypoint=False)
        
        # 尝试匹配旧格式（带途径点）
        match = self.INTENT_PATTERN_WITH_WAYPOINT_OLD.match(intent_text)
        if match:
            logger.debug("匹配旧格式（带途径点）")
            return self._build_intent(match, has_waypoint=True)
        
        # 尝试匹配旧格式（简化）
        match = self.INTENT_PATTERN_SIMPLE_OLD.match(intent_text)
        if match:
            logger.debug("匹配旧格式（简化）")
            return self._build_intent(match, has_waypoint=False)
        
        return None

    def _build_intent(self, match, has_waypoint: bool) -> FlightIntent:
        """
        根据正则匹配结果构建FlightIntent对象
        
        参数：
            match: 正则匹配对象
            has_waypoint: 是否包含途径点
        
        返回：
            FlightIntent对象
        """
        groups = match.groupdict()
        
        # 提取基本要素
        target_id = groups['target_id']
        platform_type = groups['platform_type']
        takeoff_time_str = groups['takeoff_time']
        loc_start = groups['loc_start']
        
        # 解析起飞时间
        takeoff_time = datetime.strptime(takeoff_time_str, '%Y-%m-%d %H:%M:%S')
        
        # 解析任务类型
        mission_text = groups.get('mission_type')
        mission_type = self._parse_mission_type(mission_text)
        
        # 提取途径和降落信息
        if has_waypoint:
            action_mid = groups.get('action_mid')
            loc_mid = groups.get('loc_mid')
            time_mid = groups.get('time_mid')
            action_end = groups.get('action_end')
            loc_end = groups.get('loc_end')
            time_end = groups.get('time_end')
        else:
            action_mid = None
            loc_mid = None
            time_mid = None
            action_end = groups.get('action_end')
            loc_end = groups.get('loc_end')
            time_end = groups.get('time_end')
        
        # 如果设置了基准日期，补全途径时间和降落时间的日期部分
        if time_mid and self.base_date:
            time_mid = f"{self.base_date} {time_mid}"
        if time_end and self.base_date:
            time_end = f"{self.base_date} {time_end}"
        
        return FlightIntent(
            target_id=target_id,
            platform_type=platform_type,
            takeoff_time=takeoff_time,
            loc_start=loc_start,
            mission_type=mission_type,
            action_mid=action_mid,
            loc_mid=loc_mid,
            time_mid=time_mid,
            action_end=action_end,
            loc_end=loc_end,
            time_end=time_end
        )

    def validate(self, intent: FlightIntent) -> tuple:
        """
        验证解析结果
        
        参数：
            intent: FlightIntent对象
        
        返回：
            (is_valid, errors, warnings) 元组
            - is_valid: 是否有效
            - errors: 错误列表
            - warnings: 警告列表
        """
        errors = []
        warnings = []
        
        # 检查必填字段
        if not intent.target_id:
            errors.append("缺少目标批号")
        
        if not intent.platform_type:
            errors.append("缺少机型")
        
        if not intent.takeoff_time:
            errors.append("缺少起飞时间")
        
        if not intent.loc_start:
            errors.append("缺少起飞地点")
        
        # 检查可选字段
        if intent.loc_end and not intent.time_end:
            warnings.append(f"指定了降落地点 {intent.loc_end} 但未指定降落时间")
        
        if not intent.mission_type:
            warnings.append("未指定飞行任务类型，将使用默认的正常飞行模式")
        
        return len(errors) == 0, errors, warnings

    def parse_and_validate(self, intent_text: str) -> tuple:
        """
        解析并验证飞行简令
        
        参数：
            intent_text: 飞行简令文本
        
        返回：
            (intent, is_valid, errors, warnings) 元组
            - intent: FlightIntent对象，解析失败为None
            - is_valid: 是否有效
            - errors: 错误列表
            - warnings: 警告列表
        """
        intent = self.parse(intent_text)
        if not intent:
            return None, False, ["无法解析飞行简令格式"], []
        
        is_valid, errors, warnings = self.validate(intent)
        return intent, is_valid, errors, warnings
