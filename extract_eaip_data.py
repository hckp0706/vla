"""
EAIP资料数据提取脚本

从中国民航局EAIP PDF文件中提取机场和航路数据
"""

import os
import re
import json
import pdfplumber

# EAIP资料目录
EAIP_DIR = r'E:\VLA\2026 Nr.04'

def extract_airport_data(pdf_path):
    """
    从机场PDF文件中提取数据
    
    参数：
        pdf_path: PDF文件路径
    
    返回：
        包含机场信息的字典
    """
    airport_data = {
        'icao_code': '',
        'iata_code': '',
        'name_cn': '',
        'name_en': '',
        'city_cn': '',
        'city_en': '',
        'country': '中国',
        'latitude': None,
        'longitude': None,
        'elevation': None,
        'magnetic_variation': None,
        'runways': []
    }
    
    # 从文件名提取ICAO代码
    filename = os.path.basename(pdf_path)
    match = re.match(r'([A-Z]{4})\.pdf', filename)
    if match:
        airport_data['icao_code'] = match.group(1)
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # 读取第一页内容
            if len(pdf.pages) > 0:
                page = pdf.pages[0]
                text = page.extract_text()
                
                if text:
                    # 提取机场名称和代码
                    # 格式：ZBAA/PEK-北京/首都BEIJING/Capital
                    name_pattern = r'([A-Z]{4})/([A-Z]{3})-\s*([\u4e00-\u9fa5]+)/([\u4e00-\u9fa5]*)\s*([A-Za-z\s]+)/([A-Za-z\s]+)'
                    match = re.search(name_pattern, text)
                    if match:
                        airport_data['icao_code'] = match.group(1)
                        airport_data['iata_code'] = match.group(2)
                        airport_data['city_cn'] = match.group(3)
                        airport_data['name_cn'] = match.group(4) if match.group(4) else match.group(3) + '机场'
                        airport_data['city_en'] = match.group(5).strip()
                        airport_data['name_en'] = match.group(6).strip()
                    
                    # 提取坐标（格式：N40°04.4′ E116°35.9′）
                    coord_pattern = r'([NS])(\d{1,3})°(\d{1,2})\.(\d+)′\s+([EW])(\d{1,3})°(\d{1,2})\.(\d+)′'
                    match = re.search(coord_pattern, text)
                    if match:
                        # 解析纬度
                        lat_dir = match.group(1)
                        lat_deg = float(match.group(2))
                        lat_min = float(f"{match.group(3)}.{match.group(4)}")
                        latitude = lat_deg + lat_min/60
                        if lat_dir == 'S':
                            latitude = -latitude
                        airport_data['latitude'] = latitude
                        
                        # 解析经度
                        lon_dir = match.group(5)
                        lon_deg = float(match.group(6))
                        lon_min = float(f"{match.group(7)}.{match.group(8)}")
                        longitude = lon_deg + lon_min/60
                        if lon_dir == 'W':
                            longitude = -longitude
                        airport_data['longitude'] = longitude
                    
                    # 提取标高（格式：35.3 m/31.8℃）
                    elev_pattern = r'ELEV.*?(\d+\.\d+)\s*m'
                    match = re.search(elev_pattern, text)
                    if match:
                        airport_data['elevation'] = float(match.group(1))
    
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
    
    return airport_data

def extract_route_data(pdf_path):
    """
    从航路PDF文件中提取数据
    
    参数：
        pdf_path: PDF文件路径
    
    返回：
        包含航路信息的列表
    """
    routes = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:5]:  # 读取前5页
                text = page.extract_text()
                if text:
                    # 提取航路点（格式：VOR/DME坐标）
                    # 示例格式：BEIJ N40°04.4′ E116°35.9′
                    waypoint_pattern = r'([A-Z]{3,4})\s+([NS])(\d{1,3})°(\d{1,2})\.(\d+)′\s+([EW])(\d{1,3})°(\d{1,2})\.(\d+)′'
                    matches = re.findall(waypoint_pattern, text)
                    for match in matches:
                        wp_name = match[0]
                        lat_dir = match[1]
                        lat_deg = float(match[2])
                        lat_min = float(f"{match[3]}.{match[4]}")
                        lon_dir = match[5]
                        lon_deg = float(match[6])
                        lon_min = float(f"{match[7]}.{match[8]}")
                        
                        latitude = lat_deg + lat_min/60
                        if lat_dir == 'S':
                            latitude = -latitude
                        
                        longitude = lon_deg + lon_min/60
                        if lon_dir == 'W':
                            longitude = -longitude
                        
                        routes.append({
                            'waypoint_name': wp_name,
                            'latitude': latitude,
                            'longitude': longitude
                        })
    
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
    
    return routes

def main():
    print("=" * 60)
    print("EAIP资料数据提取")
    print("=" * 60)
    
    # 1. 提取机场数据
    print("\n1. 提取机场数据...")
    airport_files = [f for f in os.listdir(EAIP_DIR) if re.match(r'^[A-Z]{4}\.pdf$', f)]
    airports = []
    
    for filename in airport_files:
        pdf_path = os.path.join(EAIP_DIR, filename)
        print(f"  处理: {filename}")
        data = extract_airport_data(pdf_path)
        if data['latitude'] is not None:
            airports.append(data)
            print(f"    ✓ 提取成功: {data['icao_code']}/{data['iata_code']} - {data['name_cn']}")
            elev_str = f"{data['elevation']:.1f}m" if data['elevation'] else "未知"
            print(f"      坐标: ({data['latitude']:.4f}, {data['longitude']:.4f}), 标高: {elev_str}")
        else:
            print(f"    ✗ 提取失败")
    
    # 2. 提取航路数据
    print("\n2. 提取航路数据...")
    route_files = [f for f in os.listdir(EAIP_DIR) if f.startswith('ENR_3') and f.endswith('.pdf')]
    all_routes = []
    
    for filename in route_files:
        pdf_path = os.path.join(EAIP_DIR, filename)
        print(f"  处理: {filename}")
        routes = extract_route_data(pdf_path)
        all_routes.extend(routes)
        print(f"    提取到 {len(routes)} 条航路点信息")
    
    # 3. 保存提取结果
    output_dir = r'E:\VLA\output\eaip_data'
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存机场数据
    airports_file = os.path.join(output_dir, 'airports.json')
    with open(airports_file, 'w', encoding='utf-8') as f:
        json.dump(airports, f, ensure_ascii=False, indent=2)
    print(f"\n机场数据已保存到: {airports_file}")
    
    # 保存航路数据
    routes_file = os.path.join(output_dir, 'routes.json')
    with open(routes_file, 'w', encoding='utf-8') as f:
        json.dump(all_routes, f, ensure_ascii=False, indent=2)
    print(f"航路数据已保存到: {routes_file}")
    
    # 4. 显示提取结果摘要
    print("\n" + "=" * 60)
    print("提取结果摘要")
    print("=" * 60)
    print(f"成功提取机场数量: {len(airports)}")
    if airports:
        print("\n机场列表:")
        for ap in airports:
            print(f"  - {ap['icao_code']}/{ap['iata_code']}: {ap['name_cn']} ({ap['city_cn']})")
            elev_str = f"{ap['elevation']:.1f}m" if ap['elevation'] else "未知"
            print(f"    坐标: ({ap['latitude']:.4f}, {ap['longitude']:.4f}), 标高: {elev_str}")
    
    print(f"\n提取航路点数量: {len(all_routes)}")
    if all_routes:
        print("\n航路点示例:")
        for wp in all_routes[:5]:
            print(f"  - {wp['waypoint_name']}: ({wp['latitude']:.4f}, {wp['longitude']:.4f})")
    
    return airports, all_routes

if __name__ == '__main__':
    main()