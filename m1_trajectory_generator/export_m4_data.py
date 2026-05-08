"""从缓存导出M4可视化数据"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from m1_trajectory_generator.route_planner import RoutePlanner


def main():
    planner = RoutePlanner()

    cache_path = os.path.join(os.path.dirname(__file__), 'data', 'route_cache.json')
    with open(cache_path, 'r', encoding='utf-8') as f:
        cache = json.load(f)

    m4_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'm4_situation_visualization', 'data')
    os.makedirs(m4_data_dir, exist_ok=True)

    lines = []
    for wp_name, wp_data in planner.route_network.items():
        lat1 = wp_data['latitude']
        lon1 = wp_data['longitude']
        for conn in wp_data.get('connections', []):
            if conn in planner.route_network:
                conn_data = planner.route_network[conn]
                lat2 = conn_data['latitude']
                lon2 = conn_data['longitude']
                if lon1 < lon2 or (lon1 == lon2 and lat1 < lat2):
                    lines.append([lon1, lat1, lon2, lat2])

    network_path = os.path.join(m4_data_dir, 'route_network_lines.json')
    with open(network_path, 'w', encoding='utf-8') as f:
        json.dump(lines, f)
    print(f"航路网络: {len(lines)}条线段 → {network_path}")

    routes = []
    for key, rd in cache.items():
        coords = rd.get('waypoint_coords', [])
        if len(coords) < 2:
            continue
        route_coords = [[c['lon'], c['lat']] for c in coords]
        routes.append({"k": key, "c": route_coords})

    civil_path = os.path.join(m4_data_dir, 'civil_routes.json')
    with open(civil_path, 'w', encoding='utf-8') as f:
        json.dump(routes, f)
    print(f"民航航路: {len(routes)}条 → {civil_path}")


if __name__ == '__main__':
    main()
