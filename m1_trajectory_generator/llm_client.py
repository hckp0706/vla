"""
大模型客户端模块

封装GLM-5.1 API调用，提供统一的接口供其他模块使用
"""

import json
import logging
import requests
from typing import Optional, Dict, Any

from .config import Config

logger = logging.getLogger(__name__)

class LLMClient:
    """
    大模型客户端
    
    封装GLM-5.1 API调用，提供统一的接口
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        初始化大模型客户端
        
        参数：
            api_key: API密钥，默认使用配置文件中的密钥
            model: 模型名称，默认使用配置文件中的模型
        """
        self.api_key = api_key or Config.LLM_API_KEY
        self.model = model or Config.LLM_MODEL
        self.api_url = Config.LLM_API_URL
        self.temperature = Config.LLM_TEMPERATURE
        self.max_tokens = Config.LLM_MAX_TOKENS
        
    def generate_route(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        调用大模型生成航路点
        
        参数：
            prompt: 提示词
            
        返回：
            包含航路点信息的字典，失败返回None
        """
        if not Config.LLM_ENABLED:
            logger.info("大模型功能已禁用")
            return None
            
        if not self.api_key:
            logger.error("未配置大模型API密钥")
            return None
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False
        }
        
        try:
            logger.info(f"调用大模型API，模型: {self.model}")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("choices") and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                logger.info(f"大模型返回内容长度: {len(content)}")
                
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    logger.error("大模型返回内容不是有效的JSON格式")
                    return None
            else:
                logger.error("大模型返回结果为空")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"大模型API调用失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"大模型处理异常: {str(e)}")
            return None
    
    def generate_prompt(self, intent_dict: Dict[str, Any]) -> str:
        """
        根据意图字典生成提示词
        
        参数：
            intent_dict: 包含任务信息的字典
            
        返回：
            生成的提示词字符串
        """
        platform_type = intent_dict.get("platform_type", "")
        mission_type = intent_dict.get("mission_type", "")
        loc_start = intent_dict.get("loc_start", "")
        loc_mid = intent_dict.get("loc_mid", "")
        loc_end = intent_dict.get("loc_end", "")
        
        # 构建途经点描述
        if loc_mid and loc_mid.strip():
            waypoint_desc = f"，途径{loc_mid}"
        else:
            waypoint_desc = ""
        
        # JSON格式输出模板（单独定义，避免与format冲突）
        json_format = """
{
  "route_name": "航线名称",
  "waypoints": [
    {
      "name": "航路点名称",
      "lon": 经度（浮点数）,
      "lat": 纬度（浮点数）,
      "alt_m": 建议高度（米，整数）,
      "description": "该航路点的作用和意义"
    }
  ],
  "notes": "额外说明（如航线特点、注意事项等，不要包含时间信息）"
}
        """.strip()
        
        # 判断机型类型
        if any(keyword in platform_type for keyword in ["歼", "战斗机", "军机", "F-", "P-"]):
            # 军机模板
            prompt = f"""你是一位经验丰富的军机飞行员，拥有丰富的战术飞行经验。

请为以下飞行任务设计合理的航路点（仅空间坐标，不包含时间信息）：
- 任务描述：从{loc_start}执行{mission_type if mission_type else "战术任务"}任务至{loc_end}{waypoint_desc}
- 机型：{platform_type}
- 任务类型：{mission_type if mission_type else "战术任务"}
- 起飞地点：{loc_start}
- 途经地点：{loc_mid if loc_mid else "无"}
- 目标区域：{loc_end}

重要说明：
1. 你只负责生成空间航路点，时间计算将由本地代码完成
2. 请不要在输出中包含任何时间信息（如到达时间、飞行时长等）
3. 建议高度仅作为参考，实际高度剖面将由本地代码根据机型性能生成

请按照以下要求设计航路点：
1. 航路点数量：建议8-12个关键导航点（不含起终点）
2. 每个航路点应包含：名称、经度、纬度、建议高度
3. 航路点应符合战术飞行要求，考虑：
   - 避开敌方雷达探测范围
   - 利用地形掩护（如山谷、海岸线）
   - 规划合理的转弯角度和机动点
   - 符合军机飞行规则和战术要求
4. 航路点之间的距离应合理（约50-100公里），便于战术机动
5. 请以JSON格式输出，格式如下：
{json_format}"""
        else:
            # 民航模板
            prompt = f"""你是一位经验丰富的民航飞行员，拥有丰富的航线规划经验。

请为以下飞行任务设计合理的航路点（仅空间坐标，不包含时间信息）：
- 任务描述：从{loc_start}飞往{loc_end}{waypoint_desc}
- 机型：{platform_type}
- 任务类型：{mission_type if mission_type else "客运航班"}
- 起飞地点：{loc_start}
- 途经地点：{loc_mid if loc_mid else "无"}
- 降落地点：{loc_end}

重要说明：
1. 你只负责生成空间航路点，时间计算将由本地代码完成
2. 请不要在输出中包含任何时间信息（如到达时间、飞行时长等）
3. 建议高度仅作为参考，实际高度剖面将由本地代码根据机型性能生成

请按照以下要求设计航路点：
1. 航路点数量：建议5-8个关键导航点（不含起终点）
2. 每个航路点应包含：名称、经度、纬度、建议高度
3. 航路点应符合实际飞行习惯，考虑：
   - 避开禁飞区和军事禁区
   - 利用已有的导航设施（如VOR、NDB导航台）
   - 考虑地形和气象条件
   - 符合民航飞行规则（如高度层分配）
4. 航路点之间的距离应合理（约150-200公里），便于飞机平稳转弯和高度调整
5. 请以JSON格式输出，格式如下：
{json_format}"""
        
        logger.debug(f"生成的提示词长度: {len(prompt)}")
        return prompt