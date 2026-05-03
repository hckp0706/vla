"""
ENR_4.4航路点提取 - 修正版
文件格式：三行一组，每行包含两个坐标/航路点
"""
import os
import re
import json
import pdfplumber

EAIP_DIR = r'E:\VLA\2026 Nr.04'
OUTPUT_DIR = r'E:\VLA\output\eaip_data'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_enr_4_4_waypoints():
    """从ENR_4.4提取所有航路点"""
    pdf_path = os.path.join(EAIP_DIR, 'ENR_4.4_Name-code designators for significant points.pdf')
    
    print("=" * 60)
    print("提取ENR_4.4标准航路点")
    print("=" * 60)
    
    pdf = pdfplumber.open(pdf_path)
    print(f"文件页数: {len(pdf.pages)}")
    
    waypoints = []
    wp_names = set()
    
    for page_num, page in enumerate(pdf.pages):
        print(f"\n处理第 {page_num + 1} 页...")
        text = page.extract_text()
        
        if not text:
            print("  无文本内容")
            continue
        
        lines = text.split('\n')
        
        # 跳过标题行（前8行是标题）
        start_idx = 0
        for i, line in enumerate(lines):
            if 'N' in line and '°' in line and '′' in line:
                start_idx = i
                break
        
        # 从标题后开始处理，每3行为一组
        for i in range(start_idx, len(lines) - 2, 3):
            lat_line = lines[i].strip()
            name_line = lines[i + 1].strip()
            lon_line = lines[i + 2].strip()
            
            # 匹配纬度坐标
            lat_pattern = r'([NS])(\d{1,3})°(\d{1,2})′(\d{1,2})″\s+([NS])(\d{1,3})°(\d{1,2})′(\d{1,2})″'
            lat_match = re.search(lat_pattern, lat_line)
            
            # 匹配经度坐标
            lon_pattern = r'([EW])(\d{1,3})°(\d{1,2})′(\d{1,2})″\s+([EW])(\d{1,3})°(\d{1,2})′(\d{1,2})″'
            lon_match = re.search(lon_pattern, lon_line)
            
            # 匹配航路点名称和航路
            name_pattern = r'([A-Z]{5})\s+([A-Z0-9\s]+?)\s+([A-Z]{5})\s+([A-Z0-9\s]+)'
            name_match = re.match(name_pattern, name_line)
            
            if lat_match and lon_match and name_match:
                # 解析第一个航路点
                wp1_name = name_match.group(1)
                wp1_routes = name_match.group(2).strip().split()
                
                lat1_deg = float(lat_match.group(2))
                lat1_min = float(lat_match.group(3))
                lat1_sec = float(lat_match.group(4))
                lat1 = lat1_deg + lat1_min/60 + lat1_sec/3600
                if lat_match.group(1) == 'S':
                    lat1 = -lat1
                
                lon1_deg = float(lon_match.group(2))
                lon1_min = float(lon_match.group(3))
                lon1_sec = float(lon_match.group(4))
                lon1 = lon1_deg + lon1_min/60 + lon1_sec/3600
                if lon_match.group(1) == 'W':
                    lon1 = -lon1
                
                if wp1_name not in wp_names:
                    wp_names.add(wp1_name)
                    waypoints.append({
                        'name': wp1_name,
                        'latitude': round(lat1, 6),
                        'longitude': round(lon1, 6),
                        'routes': wp1_routes
                    })
                    print(f"  ✅ {wp1_name}: ({lat1:.6f}, {lon1:.6f})")
                
                # 解析第二个航路点
                wp2_name = name_match.group(3)
                wp2_routes = name_match.group(4).strip().split()
                
                lat2_deg = float(lat_match.group(6))
                lat2_min = float(lat_match.group(7))
                lat2_sec = float(lat_match.group(8))
                lat2 = lat2_deg + lat2_min/60 + lat2_sec/3600
                if lat_match.group(5) == 'S':
                    lat2 = -lat2
                
                lon2_deg = float(lon_match.group(6))
                lon2_min = float(lon_match.group(7))
                lon2_sec = float(lon_match.group(8))
                lon2 = lon2_deg + lon2_min/60 + lon2_sec/3600
                if lon_match.group(5) == 'W':
                    lon2 = -lon2
                
                if wp2_name not in wp_names:
                    wp_names.add(wp2_name)
                    waypoints.append({
                        'name': wp2_name,
                        'latitude': round(lat2, 6),
                        'longitude': round(lon2, 6),
                        'routes': wp2_routes
                    })
                    print(f"  ✅ {wp2_name}: ({lat2:.6f}, {lon2:.6f})")
    
    # 保存数据
    output_file = os.path.join(OUTPUT_DIR, 'enr_4_4_waypoints.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(waypoints, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"提取完成！共找到 {len(waypoints)} 个航路点")
    print(f"数据已保存到: {output_file}")
    
    # 示例数据
    print("\n示例航路点:")
    for wp in waypoints[:5]:
        print(f"  {wp['name']}: ({wp['latitude']:.4f}, {wp['longitude']:.4f}) - 涉及航路: {wp['routes']}")
    
    return waypoints

if __name__ == '__main__':
    extract_enr_4_4_waypoints()
