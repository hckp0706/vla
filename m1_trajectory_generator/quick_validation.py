"""快速验证20条典型航路的平滑性"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from m1_trajectory_generator.route_planner import RoutePlanner


def check_route(planner, start_icao, end_icao):
    result = planner.plan_route(start_icao, end_icao)
    if not result:
        return None

    coords = result.waypoint_coords
    names = result.waypoint_names

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
            max_turn_names = f"{names[i]} ({names[i-1]}→{names[i]}→{names[i+1]})"

    backtrack_count = 0
    for i in range(1, len(coords) - 1):
        seg_bearing = planner._bearing(coords[i-1][0], coords[i-1][1], coords[i][0], coords[i][1])
        deviation = planner._turn_angle(seg_bearing, overall_bearing)
        if deviation > 90:
            backtrack_count += 1

    return {
        'n_points': len(names),
        'distance_km': result.total_distance_km,
        'first_deviation': first_deviation,
        'max_turn': max_turn,
        'max_turn_names': max_turn_names,
        'backtrack_count': backtrack_count,
    }


def main():
    planner = RoutePlanner()

    routes = [
        ("ZBTJ", "ZSSS", "天津→上海"),
        ("ZBAA", "ZSPD", "北京→上海浦东"),
        ("ZBAA", "ZGGG", "北京→广州"),
        ("ZSSS", "ZGSZ", "上海→深圳"),
        ("ZUUU", "ZLXY", "成都→西安"),
        ("ZLXY", "ZSPD", "西安→上海浦东"),
        ("ZPPP", "ZLXY", "昆明→西安"),
        ("ZWWW", "ZJSY", "乌鲁木齐→三亚"),
        ("ZSFZ", "ZBAA", "福州→北京"),
        ("ZGGG", "ZBAA", "广州→北京"),
        ("ZGSZ", "ZSSS", "深圳→上海"),
        ("ZHHH", "ZBAA", "武汉→北京"),
        ("ZHHH", "ZGGG", "武汉→广州"),
        ("ZLXY", "ZGGG", "西安→广州"),
        ("ZBAA", "ZWWW", "北京→乌鲁木齐"),
        ("ZSPD", "ZGGG", "上海浦东→广州"),
        ("ZUUU", "ZGGG", "成都→广州"),
        ("ZUUU", "ZSSS", "成都→上海"),
        ("ZPPP", "ZGGG", "昆明→广州"),
        ("ZJSY", "ZBAA", "三亚→北京"),
    ]

    print("=" * 90)
    print("20条典型航路平滑性验证")
    print("=" * 90)

    all_pass = True
    for start, end, desc in routes:
        r = check_route(planner, start, end)
        if r is None:
            print(f"  ❌ {desc}: 规划失败")
            all_pass = False
            continue

        status = "✅"
        warnings = []

        if r['first_deviation'] > 60:
            status = "❌"
            warnings.append(f"首段偏差{r['first_deviation']:.0f}°")
            all_pass = False

        if r['max_turn'] > 90:
            status = "⚠️"
            warnings.append(f"转弯{r['max_turn']:.0f}°")
            all_pass = False

        if r['backtrack_count'] > 0:
            status = "❌"
            warnings.append(f"折返{r['backtrack_count']}段")
            all_pass = False

        warn_str = f" ⚠ {', '.join(warnings)}" if warnings else ""
        print(f"  {status} {desc}: {r['n_points']}点, {r['distance_km']:.0f}km, "
              f"首段偏差{r['first_deviation']:.0f}°, 最大转弯{r['max_turn']:.0f}°{warn_str}")

    print("\n" + "=" * 90)
    if all_pass:
        print("✅ 所有20条航路均通过平滑性检查!")
    else:
        print("⚠️ 部分航路存在问题，需要进一步修复")


if __name__ == '__main__':
    main()
