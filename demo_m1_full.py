"""
M1完整流程演示脚本

展示从飞行简令到轨迹生成的完整流程，包括：
1. 大模型提示词生成
2. 大模型输出结果
3. 本地代码时间计算
4. 最终轨迹生成
"""

import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from m1_trajectory_generator.llm_client import LLMClient
from m1_trajectory_generator.waypoint_validator import WaypointValidator

# ==============================================
# 步骤1: 准备飞行任务
# ==============================================
print("=" * 70)
print("步骤1: 准备飞行任务")
print("=" * 70)

intent_dict = {
    "platform_type": "空客A320",
    "mission_type": "客运航班",
    "loc_start": "北京大兴国际机场",
    "loc_mid": "西安咸阳国际机场",
    "loc_end": "上海虹桥国际机场"
}

print("飞行任务信息:")
print(f"  批号: 0020")
print(f"  机型: {intent_dict['platform_type']}")
print(f"  任务类型: {intent_dict['mission_type']}")
print(f"  起点: {intent_dict['loc_start']}")
print(f"  途经点: {intent_dict['loc_mid']}")
print(f"  终点: {intent_dict['loc_end']}")
print()

# ==============================================
# 步骤2: 生成大模型提示词
# ==============================================
print("=" * 70)
print("步骤2: 生成大模型提示词")
print("=" * 70)

client = LLMClient()
prompt = client.generate_prompt(intent_dict)

print("生成的提示词:")
print("-" * 50)
print(prompt)
print("-" * 50)
print(f"提示词长度: {len(prompt)} 字符")
print()

# ==============================================
# 步骤3: 模拟大模型输出（因为真实API可能无法访问）
# ==============================================
print("=" * 70)
print("步骤3: 大模型输出结果")
print("=" * 70)

# 模拟大模型返回的航路点（10个，符合验证要求）
llm_output = {
    "route_name": "北京-西安-上海民航航线",
    "waypoints": [
        {
            "name": "BAYAN",
            "lon": 116.0,
            "lat": 39.0,
            "alt_m": 9000,
            "description": "北京北部导航点，爬升阶段结束"
        },
        {
            "name": "ZHANG",
            "lon": 114.5,
            "lat": 37.8,
            "alt_m": 10000,
            "description": "张家口附近导航点"
        },
        {
            "name": "TAIYU",
            "lon": 112.5,
            "lat": 37.8,
            "alt_m": 10000,
            "description": "太原附近导航点"
        },
        {
            "name": "LINF",
            "lon": 111.0,
            "lat": 36.0,
            "alt_m": 10000,
            "description": "临汾附近导航点"
        },
        {
            "name": "XIANN",
            "lon": 108.95,
            "lat": 34.27,
            "alt_m": 10000,
            "description": "西安咸阳国际机场上空"
        },
        {
            "name": "HANZH",
            "lon": 110.5,
            "lat": 33.0,
            "alt_m": 10000,
            "description": "汉中附近导航点"
        },
        {
            "name": "SHIY",
            "lon": 111.5,
            "lat": 32.0,
            "alt_m": 10000,
            "description": "十堰附近导航点"
        },
        {
            "name": "WUHAN",
            "lon": 114.3,
            "lat": 30.5,
            "alt_m": 10000,
            "description": "武汉附近导航点"
        },
        {
            "name": "NANJ",
            "lon": 118.8,
            "lat": 32.0,
            "alt_m": 10000,
            "description": "南京附近导航点"
        },
        {
            "name": "SHANG",
            "lon": 121.0,
            "lat": 31.0,
            "alt_m": 10000,
            "description": "上海东部导航点"
        }
    ],
    "notes": "该航线沿传统民航航路飞行，途经华北、西北、华东地区"
}

print("大模型返回的航路点JSON:")
print("-" * 50)
print(json.dumps(llm_output, ensure_ascii=False, indent=2))
print("-" * 50)
print(f"航路点数量: {len(llm_output['waypoints'])} 个")
print()

# ==============================================
# 步骤4: 验证航路点数据
# ==============================================
print("=" * 70)
print("步骤4: 验证航路点数据")
print("=" * 70)

is_valid, errors = WaypointValidator.validate(llm_output)

if is_valid:
    print("✓ 航路点验证通过")
else:
    print("✗ 航路点验证失败:")
    for error in errors:
        print(f"  - {error}")
print()

# ==============================================
# 步骤5: 运行M1生成轨迹
# ==============================================
print("=" * 70)
print("步骤5: 运行M1生成轨迹")
print("=" * 70)

# 使用本地预设航路生成轨迹
import subprocess
result = subprocess.run(
    ["python", "-m", "m1_trajectory_generator", 
     "-i", "0020 空客A320 客运航班 于 2026-05-03 09:00:00 从 北京大兴国际机场 起飞，途径 西安咸阳国际机场，降落 上海虹桥国际机场。"],
    capture_output=True,
    text=True,
    cwd=os.path.dirname(os.path.abspath(__file__))
)

print("M1运行输出:")
print("-" * 50)
print(result.stdout)
if result.stderr:
    print("STDERR:")
    print(result.stderr)
print("-" * 50)

# ==============================================
# 步骤6: 显示轨迹结果
# ==============================================
print("=" * 70)
print("步骤6: 轨迹生成结果")
print("=" * 70)

# 找到最新的轨迹文件
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'm1_trajectories')
if os.path.exists(output_dir):
    files = sorted([f for f in os.listdir(output_dir) if f.startswith('trajectory_0020')], reverse=True)
    if files:
        latest_file = files[0]
        file_path = os.path.join(output_dir, latest_file)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            trajectory = json.load(f)
        
        print(f"轨迹文件: {latest_file}")
        print(f"目标批号: {trajectory.get('target_id')}")
        print(f"机型: {trajectory.get('platform_type')}")
        print(f"任务类型: {trajectory.get('mission_type')}")
        print(f"轨迹点数量: {len(trajectory.get('track_points', []))}")
        
        track_points = trajectory.get('track_points', [])
        if track_points:
            first = track_points[0]
            last = track_points[-1]
            print(f"\n航线统计:")
            print(f"  起飞时间: {first['time']}")
            print(f"  降落时间: {last['time']}")
            print(f"  起飞位置: ({first['lon']:.4f}, {first['lat']:.4f})")
            print(f"  降落位置: ({last['lon']:.4f}, {last['lat']:.4f})")
            print(f"  巡航高度: {max(p['alt_m'] for p in track_points):.0f} m")
            print(f"  平均速度: {sum(p['speed_ms'] for p in track_points)/len(track_points):.1f} m/s")

print("\n" + "=" * 70)
print("演示完成！")
print(f"轨迹文件已保存到: {output_dir}")
print("可在M4中加载此轨迹进行可视化展示")
print("=" * 70)