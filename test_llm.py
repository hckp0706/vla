#!/usr/bin/env python3
"""
测试大模型客户端
"""

import sys
sys.path.insert(0, 'm1_trajectory_generator')

from config import Config
from llm_client import LLMClient

def test_llm():
    client = LLMClient()
    
    prompt = """
你是一个专业的航空导航专家，请帮我生成从韩国乌山空军基地到上海浦东国际机场的飞行航路点。

要求：
1. 提供5-8个航路点
2. 每个航路点包含名称、纬度、经度
3. 按JSON格式输出

起点：乌山空军基地 (37.135°N, 127.039°E)
终点：上海浦东国际机场 (31.144°N, 121.805°E)

输出格式：
{
  "waypoints": [
    {"name": "WP1", "latitude": 37.0, "longitude": 127.0},
    {"name": "WP2", "latitude": 36.5, "longitude": 126.5},
    ...
  ]
}
"""
    
    print("正在调用大模型...")
    try:
        result = client.generate_route(prompt)
        if result:
            print("大模型调用成功！")
            print("返回结果:", result)
        else:
            print("大模型调用失败，返回None")
    except Exception as e:
        print(f"大模型调用出错: {e}")

if __name__ == '__main__':
    test_llm()