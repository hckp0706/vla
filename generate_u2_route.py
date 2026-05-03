#!/usr/bin/env python3
"""
U-2侦察机航线生成器

生成从韩国乌山空军基地到上海东部海域的侦察航线
"""

import json
import os
from datetime import datetime, timedelta

def generate_u2_trajectory():
    """生成U-2侦察机轨迹"""
    # 乌山空军基地坐标
    osan_lat = 37.135
    osan_lon = 127.039
    
    # 上海东部海域坐标
    target_lat = 31.2
    target_lon = 123.5
    
    # U-2侦察机参数
    cruise_speed_ms = 190  # 约684 km/h
    cruise_alt_m = 24000  # 24000米高空
    duration_minutes = 180  # 3小时任务时间
    
    # 计算轨迹点
    track_points = []
    start_time = datetime(2026, 5, 3, 6, 0, 0)
    
    # 起飞阶段
    for i in range(180):
        progress = i / 180
        lat = osan_lat - (osan_lat - target_lat) * progress * 0.3
        lon = osan_lon - (osan_lon - target_lon) * progress * 0.3
        alt = min(cruise_alt_m, i * 133.3)
        speed = min(cruise_speed_ms, i * 1.1)
        
        track_points.append({
            "time": (start_time + timedelta(seconds=i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "lon": lon,
            "lat": lat,
            "alt_m": alt,
            "speed_ms": speed,
            "heading_deg": 215,
            "vertical_rate_ms": 133.3 if alt < cruise_alt_m else 0,
            "rcs_dbsm": -20,
            "phase": "CLIMBING" if alt < cruise_alt_m else "CRUISING"
        })
    
    # 巡航阶段
    for i in range(3600):
        progress = (180 + i) / 3780
        lat = osan_lat - (osan_lat - target_lat) * progress
        lon = osan_lon - (osan_lon - target_lon) * progress
        
        track_points.append({
            "time": (start_time + timedelta(seconds=180 + i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "lon": lon,
            "lat": lat,
            "alt_m": cruise_alt_m,
            "speed_ms": cruise_speed_ms,
            "heading_deg": 215,
            "vertical_rate_ms": 0,
            "rcs_dbsm": -20,
            "phase": "CRUISING"
        })
    
    # 返航阶段
    for i in range(180):
        progress = (3780 + i) / 3960
        lat = osan_lat - (osan_lat - target_lat) * progress
        lon = osan_lon - (osan_lon - target_lon) * progress
        alt = cruise_alt_m - (i * 133.3)
        
        track_points.append({
            "time": (start_time + timedelta(seconds=3780 + i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "lon": lon,
            "lat": lat,
            "alt_m": max(0, alt),
            "speed_ms": cruise_speed_ms,
            "heading_deg": 215,
            "vertical_rate_ms": -133.3,
            "rcs_dbsm": -20,
            "phase": "DESCENDING"
        })
    
    trajectory = {
        "target_id": "U2-001",
        "platform_type": "U-2侦察机",
        "mission_type": "侦察任务",
        "track_points": track_points
    }
    
    output_dir = "E:\\VLA\\output\\m1_trajectories"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "trajectory_u2_osan_shanghai_20260503_060000.json")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(trajectory, f, ensure_ascii=False, indent=2)
    
    print(f"U-2侦察机轨迹已生成: {output_path}")
    print(f"轨迹点数量: {len(track_points)}")
    print(f"起飞时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"巡航高度: {cruise_alt_m}米")
    print(f"巡航速度: {cruise_speed_ms} m/s")

if __name__ == '__main__':
    generate_u2_trajectory()