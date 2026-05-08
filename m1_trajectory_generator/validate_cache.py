"""从缓存文件全量验证航路平滑性"""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from m1_trajectory_generator.route_planner import RoutePlanner


def main():
    planner = RoutePlanner()

    cache_path = os.path.join(os.path.dirname(__file__), 'data', 'route_cache.json')
    with open(cache_path, 'r', encoding='utf-8') as f:
        cache = json.load(f)

    print(f"缓存中航路总数: {len(cache)}")

    total = len(cache)
    success = 0
    issues_backtrack = 0
    issues_sharp_turn = 0
    issues_first_dev = 0
    issue_details = []

    for idx, (key, route_data) in enumerate(cache.items()):
        raw_coords = route_data.get('waypoint_coords')
        names = route_data.get('waypoint_names')
        if not raw_coords or len(raw_coords) < 2:
            continue

        coords = [(c['lat'], c['lon']) for c in raw_coords]

        success += 1
        overall_bearing = planner._bearing(coords[0][0], coords[0][1], coords[-1][0], coords[-1][1])

        first_seg_bearing = planner._bearing(coords[0][0], coords[0][1], coords[1][0], coords[1][1])
        first_deviation = planner._turn_angle(first_seg_bearing, overall_bearing)

        max_turn = 0
        max_turn_names = ""
        for i in range(1, len(coords) - 1):
            h_in = planner._bearing(coords[i-1][0], coords[i-1][1], coords[i][0], coords[i][1]) % 360
            h_out = planner._bearing(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1]) % 360
            turn = planner._turn_angle(h_in, h_out)
            if turn > max_turn:
                max_turn = turn
                if names and i < len(names) - 1:
                    max_turn_names = f"{names[i]} ({names[i-1]}→{names[i]}→{names[i+1]})"

        backtrack_count = 0
        for i in range(1, len(coords) - 1):
            seg_bearing = planner._bearing(coords[i-1][0], coords[i-1][1], coords[i][0], coords[i][1])
            deviation = planner._turn_angle(seg_bearing, overall_bearing)
            if deviation > 90:
                backtrack_count += 1

        desc = key
        if first_deviation > 60:
            issues_first_dev += 1
            issue_details.append((desc, "首段偏差", f"{first_deviation:.0f}°"))

        if max_turn > 90:
            issues_sharp_turn += 1
            issue_details.append((desc, "最大转弯", f"{max_turn:.0f}° @ {max_turn_names}"))

        if backtrack_count > 0:
            issues_backtrack += 1
            issue_details.append((desc, "折返", f"{backtrack_count}段"))

    print("\n" + "=" * 90)
    print(f"全量验证完成!")
    print(f"  总计: {total}条, 有效: {success}")
    print(f"  折返问题(段方向偏>90°): {issues_backtrack}条")
    print(f"  大转弯(>90°): {issues_sharp_turn}条")
    print(f"  首段偏差(>60°): {issues_first_dev}条")
    pass_count = success - max(issues_backtrack, issues_sharp_turn)
    print(f"  完全合格: {pass_count}条 ({pass_count/success*100:.1f}%)")

    if issue_details:
        print(f"\n问题航路详情 (共{len(issue_details)}条):")
        for desc, issue_type, value in issue_details:
            print(f"  - {desc}: {issue_type} = {value}")


if __name__ == '__main__':
    main()
