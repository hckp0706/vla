"""全量航路平滑性验证 - 对所有有坐标的机场两两规划并检查"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from m1_trajectory_generator.route_planner import RoutePlanner
import itertools


def main():
    planner = RoutePlanner()

    airport_list = [apt for apt in planner.airports.values()
                    if apt['lat'] is not None and apt['lon'] is not None]
    print(f"有坐标的机场: {len(airport_list)}个")

    test_pairs = list(itertools.combinations(airport_list, 2))
    print(f"测试航路对: {len(test_pairs)}条")
    print("=" * 90)

    total = len(test_pairs)
    success = 0
    failed = 0
    issues_backtrack = 0
    issues_sharp_turn = 0
    issues_first_dev = 0
    issue_details = []

    for idx, (apt_a, apt_b) in enumerate(test_pairs):
        result = planner.plan_route(apt_a['icao'], apt_b['icao'])
        if not result:
            failed += 1
            continue

        success += 1
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
                max_turn_names = f"{names[i-1]}→{names[i]}→{names[i+1]}"

        backtrack_count = 0
        for i in range(1, len(coords) - 1):
            seg_bearing = planner._bearing(coords[i-1][0], coords[i-1][1], coords[i][0], coords[i][1])
            deviation = planner._turn_angle(seg_bearing, overall_bearing)
            if deviation > 90:
                backtrack_count += 1

        desc = f"{apt_a['name']}→{apt_b['name']}"
        has_issue = False

        if first_deviation > 60:
            issues_first_dev += 1
            has_issue = True
            issue_details.append((desc, "首段偏差", f"{first_deviation:.0f}°"))

        if max_turn > 90:
            issues_sharp_turn += 1
            has_issue = True
            issue_details.append((desc, "最大转弯", f"{max_turn:.0f}° @ {max_turn_names}"))

        if backtrack_count > 0:
            issues_backtrack += 1
            has_issue = True
            issue_details.append((desc, "折返", f"{backtrack_count}段"))

        if (idx + 1) % 100 == 0:
            print(f"  进度: {idx+1}/{total}, 成功{success}, 失败{failed}, "
                  f"问题: 折返{issues_backtrack}, 大转弯{issues_sharp_turn}, 首段偏差{issues_first_dev}")

    print("\n" + "=" * 90)
    print(f"全量验证完成!")
    print(f"  总计: {total}条, 成功: {success}, 失败: {failed}")
    print(f"  折返问题: {issues_backtrack}条")
    print(f"  大转弯(>90°): {issues_sharp_turn}条")
    print(f"  首段偏差(>60°): {issues_first_dev}条")
    print(f"  合格率: {(success - issues_backtrack - issues_sharp_turn) / max(success, 1) * 100:.1f}%")

    if issue_details:
        print(f"\n问题航路详情 (共{len(issue_details)}条):")
        for desc, issue_type, value in issue_details[:50]:
            print(f"  - {desc}: {issue_type} = {value}")
        if len(issue_details) > 50:
            print(f"  ... 还有{len(issue_details) - 50}条问题")


if __name__ == '__main__':
    main()
