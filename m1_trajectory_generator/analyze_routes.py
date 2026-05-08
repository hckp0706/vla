"""分析2条>90°转弯航路的详细问题"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from m1_trajectory_generator.route_planner import RoutePlanner


def analyze_route(planner, start, end, desc):
    result = planner.plan_route(start, end)
    if not result:
        print(f"  {desc}: 规划失败")
        return

    coords = result.waypoint_coords
    names = result.waypoint_names

    print(f"\n{'='*80}")
    print(f"{desc}: {len(names)}点, {result.total_distance_km:.0f}km")
    print(f"{'='*80}")

    overall_bearing = planner._bearing(coords[0][0], coords[0][1], coords[-1][0], coords[-1][1])
    print(f"总体方向: {overall_bearing:.1f}°")

    for i in range(len(coords)):
        if i == 0:
            print(f"  {i}. {names[i]} ({coords[i][0]:.4f}, {coords[i][1]:.4f}) [起飞]")
            continue

        prev_lat, prev_lon = coords[i-1]
        lat, lon = coords[i]
        seg_bearing = planner._bearing(prev_lat, prev_lon, lat, lon)
        seg_dist = planner.haversine_km(prev_lat, prev_lon, lat, lon)
        deviation = planner._turn_angle(seg_bearing, overall_bearing)

        turn_info = ""
        if 0 < i < len(coords) - 1:
            h_in = planner._bearing(prev_lat, prev_lon, lat, lon) % 360
            h_out = planner._bearing(lat, lon, coords[i+1][0], coords[i+1][1]) % 360
            turn = planner._turn_angle(h_in, h_out)
            turn_info = f" 转弯{turn:.0f}°" + (" ⚠️ 大转弯!" if turn > 90 else "")

        flag = " ⬅ 折返!" if deviation > 90 else ""
        if i == len(coords) - 1:
            flag = " [降落]"

        print(f"  {i}. {names[i]} ({lat:.4f}, {lon:.4f}) 航向{seg_bearing:.0f}° 偏差{deviation:.0f}° +{seg_dist:.0f}km{turn_info}{flag}")


def main():
    planner = RoutePlanner()
    analyze_route(planner, "ZBAA", "ZGGG", "北京首都→广州白云")
    analyze_route(planner, "ZLXY", "ZSPD", "西安咸阳→上海浦东")


if __name__ == '__main__':
    main()
