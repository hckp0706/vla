#!/usr/bin/env python3
"""
ENR_6.2 航路图数据提取器

从EAIP ENR_6.2_EN-ROUTE CHART.pdf文件中提取航路信息，包括：
1. 航路名称和编号
2. 航路途经的导航点
3. 航路的高度限制
4. 航路的方向信息

输出格式：
{
  "route_id": "A593",
  "name": "航路A593",
  "direction": "双向",
  "waypoints": ["WAYPOINT1", "WAYPOINT2", ...],
  "lower_limit": 7800,
  "upper_limit": 12000
}
"""

import os
import json
import re

def extract_routes_from_text(text):
    """
    从文本中提取航路信息
    
    参数：
        text: PDF提取的文本
    
    返回：
        航路列表
    """
    routes = []
    
    route_pattern = re.compile(r'([A-Z]\d{3})\s+(.+?)\s+(双向|单向)\s*', re.MULTILINE)
    waypoint_pattern = re.compile(r'([A-Z]{5})\s+(\d{4}\.\d{2}[NS])\s+(\d{5}\.\d{2}[EW])')
    
    for match in route_pattern.finditer(text):
        route_id = match.group(1)
        name = match.group(2).strip()
        direction = match.group(3)
        
        route_data = {
            "route_id": route_id,
            "name": name,
            "direction": direction,
            "waypoints": [],
            "lower_limit": None,
            "upper_limit": None
        }
        
        routes.append(route_data)
    
    return routes

def load_enr_4_4_waypoints(filepath):
    """
    加载ENR_4.4的航路点数据
    
    参数：
        filepath: 航路点文件路径
    
    返回：
        航路点字典
    """
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {wp['name']: wp for wp in data}
    return {}

def build_route_network(waypoints):
    """
    构建航路网络
    
    参数：
        waypoints: 航路点字典
    
    返回：
        航路网络（邻接表形式）
    """
    network = {}
    
    for wp_name, wp_data in waypoints.items():
        network[wp_name] = {
            'latitude': wp_data['latitude'],
            'longitude': wp_data['longitude'],
            'routes': wp_data.get('routes', []),
            'connections': []
        }
    
    for wp1_name, wp1_data in network.items():
        for route in wp1_data['routes']:
            for wp2_name, wp2_data in network.items():
                if wp1_name != wp2_name and route in wp2_data['routes']:
                    if wp2_name not in wp1_data['connections']:
                        wp1_data['connections'].append(wp2_name)
    
    return network

def find_optimal_route(network, start_wp, end_wp, max_hops=10):
    """
    使用BFS找到最优航路
    
    参数：
        network: 航路网络
        start_wp: 起点航路点
        end_wp: 终点航路点
        max_hops: 最大跳数
    
    返回：
        航路点列表
    """
    if start_wp not in network or end_wp not in network:
        return None
    
    from collections import deque
    
    queue = deque()
    queue.append((start_wp, [start_wp]))
    visited = {start_wp}
    
    while queue:
        current, path = queue.popleft()
        
        if current == end_wp:
            return path
        
        if len(path) >= max_hops:
            continue
        
        for neighbor in network[current]['connections']:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    
    return None

def save_route_network(network, filepath):
    """
    保存航路网络
    
    参数：
        network: 航路网络
        filepath: 输出文件路径
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(network, f, ensure_ascii=False, indent=2)

def main():
    enr_4_4_path = os.path.join(os.path.dirname(__file__), 'output', 'eaip_data', 'enr_4_4_waypoints.json')
    output_path = os.path.join(os.path.dirname(__file__), 'm1_trajectory_generator', 'data', 'route_network.json')
    
    print("加载ENR_4.4航路点数据...")
    waypoints = load_enr_4_4_waypoints(enr_4_4_path)
    print(f"已加载 {len(waypoints)} 个航路点")
    
    print("构建航路网络...")
    network = build_route_network(waypoints)
    
    print(f"航路网络包含 {len(network)} 个节点")
    
    print("保存航路网络...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    save_route_network(network, output_path)
    print(f"航路网络已保存到: {output_path}")
    
    print("\n示例航路查询:")
    test_routes = [
        ("ASAVA", "BIMEG"),
        ("BIMEG", "AGOGU"),
        ("AGOGU", "PABTA")
    ]
    
    for start, end in test_routes:
        route = find_optimal_route(network, start, end)
        if route:
            print(f"{start} -> {end}: {' -> '.join(route)}")
        else:
            print(f"{start} -> {end}: 未找到航路")

if __name__ == '__main__':
    main()