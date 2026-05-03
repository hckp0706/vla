"""
专门提取ENR_4.4中的标准航路点数据
文件结构分析：左右两列格式，每列包含航路点名称、坐标、涉及的航路
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
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 查找5字母航路点代码
            wp_match = re.match(r'^([A-Z]{5})\s+([A-Z0-9\s]*)$', line)
            
            if wp_match:
                wp_name = wp_match.group(1)
                routes_str = wp_match.group(2).strip()
                
                # 跳过重复的航路点
                if wp_name in wp_names:
                    i += 1
                    continue
                wp_names.add(wp_name)
                
                # 检查下一行是否是坐标
                if i + 1 < len(lines):
                    coord_line = lines[i + 1].strip()
                    
                    # 匹配坐标格式: N36°00′02″ E117°22′04″
                    coord_match = re.search(
                        r'([NS])(\d{1,3})°(\d{1,2})′(\d{1,2})″\s+([EW])(\d{1,3})°(\d{1,2})′(\d{1,2})″',
                        coord_line
                    )
                    
                    if coord_match:
                        # 解析纬度
                        lat_dir = coord_match.group(1)
                        lat_deg = float(coord_match.group(2))
                        lat_min = float(coord_match.group(3))
                        lat_sec = float(coord_match.group(4))
                        latitude = lat_deg + lat_min/60 + lat_sec/3600
                        if lat_dir == 'S':
                            latitude = -latitude
                        
                        # 解析经度
                        lon_dir = coord_match.group(5)
                        lon_deg = float(coord_match.group(6))
                        lon_min = float(coord_match.group(7))
                        lon_sec = float(coord_match.group(8))
                        longitude = lon_deg + lon_min/60 + lon_sec/3600
                        if lon_dir == 'W':
                            longitude = -longitude
                        
                        # 解析涉及的航路
                        routes = routes_str.split() if routes_str else []
                        
                        waypoints.append({
                            'name': wp_name,
                            'latitude': round(latitude, 6),
                            'longitude': round(longitude, 6),
                            'routes': routes
                        })
                        
                        print(f"  ✅ {wp_name}: ({latitude:.6f}, {longitude:.6f}) - {len(routes)}条航路")
                        i += 2  # 跳过坐标行
                        continue
            
            i += 1
    
    # 保存数据
    output_file = os.path.join(OUTPUT_DIR, 'enr_4_4_waypoints.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(waypoints, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"提取完成！共找到 {len(waypoints)} 个航路点")
    print(f"数据已保存到: {output_file}")
    
    # 统计信息
    print("\n统计信息:")
    print(f"  航路点总数: {len(waypoints)}")
    print(f"  平均每个航路点涉及的航路数: {sum(len(wp['routes']) for wp in waypoints) / len(waypoints):.1f}")
    
    # 示例数据
    print("\n示例航路点:")
    for wp in waypoints[:5]:
        print(f"  {wp['name']}: ({wp['latitude']:.4f}, {wp['longitude']:.4f})")
    
    return waypoints

if __name__ == '__main__':
    extract_enr_4_4_waypoints()
