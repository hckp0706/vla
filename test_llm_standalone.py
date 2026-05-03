#!/usr/bin/env python3
"""
测试大模型客户端（独立版本）
"""

import json
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_llm():
    api_key = "1aa5046636ef4adcb98c37c39f1e973a.2BBvQ2bAaDMJDOZ8"
    model = "GLM-5.1"
    api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    
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
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
        "stream": False
    }
    
    print("正在调用大模型...")
    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print("大模型调用成功！")
            print("状态码:", response.status_code)
            print("返回结果:", json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"大模型调用失败，状态码: {response.status_code}")
            print("错误信息:", response.text)
            
    except Exception as e:
        print(f"大模型调用出错: {e}")

if __name__ == '__main__':
    test_llm()