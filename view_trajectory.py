import json
import os

# 找到最新的0020轨迹文件
output_dir = r'E:\VLA\output\m1_trajectories'
files = sorted([f for f in os.listdir(output_dir) if f.startswith('trajectory_0020')], reverse=True)

if files:
    latest_file = files[0]
    file_path = os.path.join(output_dir, latest_file)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("=" * 60)
    print("航迹信息")
    print("=" * 60)
    print(f"轨迹文件: {latest_file}")
    print(f"目标批号: {data.get('target_id')}")
    print(f"机型: {data.get('platform_type')}")
    print(f"任务类型: {data.get('mission_type')}")
    print(f"轨迹点数量: {len(data.get('track_points', []))}")
    print()

    print("前5个轨迹点:")
    track_points = data.get('track_points', [])
    for i, p in enumerate(track_points[:5]):
        print(f"  {i+1}: 时间={p['time']}, 位置=({p['lon']:.4f}, {p['lat']:.4f}), 高度={p['alt_m']:.0f}m, 速度={p['speed_ms']:.1f}m/s, 航向={p['heading_deg']:.1f}度")

    print()
    print("最后5个轨迹点:")
    for i, p in enumerate(track_points[-5:]):
        print(f"  {len(track_points)-4+i}: 时间={p['time']}, 位置=({p['lon']:.4f}, {p['lat']:.4f}), 高度={p['alt_m']:.0f}m, 速度={p['speed_ms']:.1f}m/s, 航向={p['heading_deg']:.1f}度")

    print()
    print("航段信息:")
    print(f"  起飞时间: {track_points[0]['time']}")
    print(f"  降落时间: {track_points[-1]['time']}")
    print(f"  起飞位置: ({track_points[0]['lon']:.4f}, {track_points[0]['lat']:.4f})")
    print(f"  降落位置: ({track_points[-1]['lon']:.4f}, {track_points[-1]['lat']:.4f})")
    print(f"  巡航高度: {max(p['alt_m'] for p in track_points):.0f} m")
else:
    print("未找到0020轨迹文件")