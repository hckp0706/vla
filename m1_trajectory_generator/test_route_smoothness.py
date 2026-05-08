"""测试航路平滑性 - 验证方向优先和折返过滤修复效果"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from m1_trajectory_generator.route_planner import RoutePlanner


def check_route_smoothness(planner, start_icao, end_icao):
    result = planner.plan_route(start_icao, end_icao)
    if not result:
        print(f"  ❌ {start_icao}→{end_icao}: 规划失败")
        return None

    coords = result.waypoint_coords
    names = result.waypoint_names

    overall_bearing = planner._bearing(coords[0][0], coords[0][1], coords[-1][0], coords[-1][1])

    first_seg_bearing = planner._bearing(coords[0][0], coords[0][1], coords[1][0], coords[1][1])
    first_deviation = planner._turn_angle(first_seg_bearing, overall_bearing)

    max_turn = 0
    max_turn_idx = -1
    max_turn_names = ""
    for i in range(1, len(coords) - 1):
        h_in = planner._bearing(coords[i-1][0], coords[i-1][1], coords[i][0], coords[i][1]) % 360
        h_out = planner._bearing(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1]) % 360
        turn = planner._turn_angle(h_in, h_out)
        if turn > max_turn:
            max_turn = turn
            max_turn_idx = i
            max_turn_names = f"{names[i-1]}→{names[i]}→{names[i+1]}"

    backtrack_count = 0
    for i in range(1, len(coords) - 1):
        seg_bearing = planner._bearing(coords[i-1][0], coords[i-1][1], coords[i][0], coords[i][1])
        deviation = planner._turn_angle(seg_bearing, overall_bearing)
        if deviation > 90:
            backtrack_count += 1

    return {
        'start': start_icao,
        'end': end_icao,
        'n_points': len(names),
        'distance_km': result.total_distance_km,
        'first_deviation': first_deviation,
        'max_turn': max_turn,
        'max_turn_names': max_turn_names,
        'backtrack_count': backtrack_count,
        'names': names,
        'coords': coords
    }


def main():
    planner = RoutePlanner()

    test_routes = [
        ("ZBTJ", "ZSSS", "天津滨海→上海虹桥"),
        ("ZBAA", "ZSPD", "北京首都→上海浦东"),
        ("ZBAA", "ZGGG", "北京首都→广州白云"),
        ("ZSSS", "ZGSZ", "上海虹桥→深圳宝安"),
        ("ZPPP", "ZLXY", "昆明长水→西安咸阳"),
        ("ZWWW", "ZJSY", "乌鲁木齐→三亚凤凰"),
        ("ZUUU", "ZLXY", "成都双流→西安咸阳"),
        ("ZLXY", "ZSPD", "西安咸阳→上海浦东"),
        ("ZSFZ", "ZBAA", "福州长乐→北京首都"),
        ("ZHCC", "ZSSS", "郑州新郑→上海虹桥"),
    ]

    print("=" * 90)
    print("航路平滑性测试 - 验证方向优先+折返过滤修复")
    print("=" * 90)

    issues = []
    for start, end, desc in test_routes:
        r = check_route_smoothness(planner, start, end)
        if r is None:
            continue

        status = "✅"
        warnings = []

        if r['first_deviation'] > 60:
            status = "❌"
            warnings.append(f"首段偏差过大({r['first_deviation']:.0f}°)")
            issues.append((desc, "首段偏差", r['first_deviation']))

        if r['max_turn'] > 90:
            status = "⚠️"
            warnings.append(f"最大转弯过大({r['max_turn']:.0f}° @ {r['max_turn_names']})")
            issues.append((desc, "最大转弯", r['max_turn']))

        if r['backtrack_count'] > 0:
            status = "❌"
            warnings.append(f"有{r['backtrack_count']}段折返!")
            issues.append((desc, "折返", r['backtrack_count']))

        warn_str = f" ⚠ {', '.join(warnings)}" if warnings else ""
        print(f"  {status} {desc}: {r['n_points']}点, {r['distance_km']:.0f}km, "
              f"首段偏差{r['first_deviation']:.0f}°, 最大转弯{r['max_turn']:.0f}°{warn_str}")

        if r['first_deviation'] > 30 or r['backtrack_count'] > 0:
            print(f"     航路点: {' → '.join(r['names'])}")
            for idx, (name, (lat, lon)) in enumerate(zip(r['names'], r['coords'])):
                if idx == 0 or idx == len(r['coords']) - 1:
                    continue
                prev_lat, prev_lon = r['coords'][idx - 1]
                seg_bearing = planner._bearing(prev_lat, prev_lon, lat, lon)
                deviation = planner._turn_angle(seg_bearing, overall_bearing := planner._bearing(
                    r['coords'][0][0], r['coords'][0][1],
                    r['coords'][-1][0], r['coords'][-1][1]))
                flag = " ⬅ 折返!" if deviation > 90 else ""
                print(f"       {idx}. {name} ({lat:.3f}, {lon:.3f}) 航向{seg_bearing:.0f}° 偏差{deviation:.0f}°{flag}")

    print("\n" + "=" * 90)
    if issues:
        print(f"发现 {len(issues)} 个问题:")
        for desc, issue_type, value in issues:
            print(f"  - {desc}: {issue_type} = {value:.0f}")
    else:
        print("所有测试航路均通过平滑性检查!")

    print("\n--- 天津→上海 详细航路分析 ---")
    r = check_route_smoothness(planner, "ZBTJ", "ZSSS")
    if r:
        overall_bearing = planner._bearing(r['coords'][0][0], r['coords'][0][1],
                                           r['coords'][-1][0], r['coords'][-1][1])
        print(f"总体方向: {overall_bearing:.1f}° (天津→上海应朝南/东南飞)")
        print(f"航路点详情:")
        for idx, (name, (lat, lon)) in enumerate(zip(r['names'], r['coords'])):
            if idx == 0:
                print(f"  {idx}. {name} ({lat:.4f}, {lon:.4f}) [起飞]")
                continue
            prev_lat, prev_lon = r['coords'][idx - 1]
            seg_bearing = planner._bearing(prev_lat, prev_lon, lat, lon)
            seg_dist = planner.haversine_km(prev_lat, prev_lon, lat, lon)
            deviation = planner._turn_angle(seg_bearing, overall_bearing)
            flag = " ⬅❌ 折返!" if deviation > 90 else ""
            if idx == len(r['coords']) - 1:
                flag = " [降落]"
            print(f"  {idx}. {name} ({lat:.4f}, {lon:.4f}) 航向{seg_bearing:.0f}° 偏差{deviation:.0f}° +{seg_dist:.0f}km{flag}")


if __name__ == '__main__':
    main()
