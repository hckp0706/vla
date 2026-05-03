"""
EAIP资料完整提取脚本
按照ICAO标准文件结构提取所有机场、航路点数据
"""
import os
import re
import json
import pdfplumber

EAIP_DIR = r'E:\VLA\2026 Nr.04'
OUTPUT_DIR = r'E:\VLA\output\eaip_data'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_all_airports_from_gen():
    """
    从GEN_2.4文件中提取完整机场列表
    """
    print("=== 1. 从GEN_2.4提取完整机场列表 ===")
    airports = []
    
    try:
        pdf_path = os.path.join(EAIP_DIR, 'GEN_2.4_Location indicators.pdf')
        pdf = pdfplumber.open(pdf_path)
        
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            
            # 解析机场列表 - 格式: 机场名 ICAO代码
            # 例子: 北京/首都 BEIJING/Capital ZBAA
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 匹配格式: 中/英文名 4字母ICAO代码
                # 模式: 中文名/英文名 英文名 4字母代码
                match = re.search(r'([A-Z]{4})$', line)
                if match:
                    icao_code = match.group(1)
                    
                    # 避免重复和非机场代码（如FIR代码）
                    if len(icao_code) != 4:
                        continue
                    if icao_code in [a['icao_code'] for a in airports]:
                        continue
                    
                    # 尝试从行中提取中文机场名
                    cn_name_part = re.search(r'([\u4e00-\u9fa5/]+)', line)
                    if cn_name_part:
                        cn_name = cn_name_part.group(1)
                    else:
                        cn_name = "未知机场"
                    
                    airport = {
                        'icao_code': icao_code,
                        'name_cn': cn_name,
                        'name_en': '',
                        'latitude': None,
                        'longitude': None,
                        'elevation': None
                    }
                    airports.append(airport)
                    print(f"  找到机场: {icao_code} - {cn_name}")
    
    except Exception as e:
        print(f"  提取机场列表出错: {e}")
    
    print(f"  从GEN_2.4共找到 {len(airports)} 个机场")
    return airports

def extract_airport_details(airport_data):
    """
    从单个机场PDF文件中提取详细数据
    """
    pdf_path = os.path.join(EAIP_DIR, f"{airport_data['icao_code']}.pdf")
    
    if not os.path.exists(pdf_path):
        return None
    
    try:
        pdf = pdfplumber.open(pdf_path)
        if len(pdf.pages) > 0:
            text = pdf.pages[0].extract_text()
            if text:
                # 提取机场名
                name_match = re.search(r'([A-Z]{4})/([A-Z0-9]+)[-\s]*([\u4e00-\u9fa5/]+)', text)
                if name_match:
                    airport_data['iata_code'] = name_match.group(2)
                    airport_data['name_cn'] = name_match.group(3)
                
                # 提取坐标
                coord_match = re.search(r'([NS])(\d+)°([\d.]+)′\s+([EW])(\d+)°([\d.]+)′', text)
                if coord_match:
                    lat_deg = float(coord_match.group(2))
                    lat_min = float(coord_match.group(3))
                    latitude = lat_deg + lat_min/60
                    if coord_match.group(1) == 'S':
                        latitude = -latitude
                    
                    lon_deg = float(coord_match.group(5))
                    lon_min = float(coord_match.group(6))
                    longitude = lon_deg + lon_min/60
                    if coord_match.group(4) == 'W':
                        longitude = -longitude
                    
                    airport_data['latitude'] = latitude
                    airport_data['longitude'] = longitude
                
                # 提取标高
                elev_match = re.search(r'ELEV.*?([\d.]+)\s*m', text)
                if elev_match:
                    airport_data['elevation'] = float(elev_match.group(1))
        
        return airport_data
    
    except Exception as e:
        print(f"  提取 {airport_data['icao_code']} 详细信息出错: {e}")
        return None

def extract_all_waypoints():
    """
    从ENR_4.4文件中提取所有航路点
    """
    print("\n=== 2. 从ENR_4.4提取航路点列表 ===")
    waypoints = []
    
    try:
        pdf_path = os.path.join(EAIP_DIR, 'ENR_4.4_Name-code designators for significant points.pdf')
        pdf = pdfplumber.open(pdf_path)
        
        for page_num, page in enumerate(pdf.pages):
            print(f"  处理第 {page_num + 1} 页...")
            text = page.extract_text()
            if not text:
                continue
            
            # 解析航路点格式
            # 格式:
            #   航路点名
            #   坐标: Nxx°xx'xx" Exxx°xx'xx"
            #   涉及的航路
            
            # 模式1: 单行方式
            lines = text.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # 检查是否是航路点名 (5字母代码)
                match = re.search(r'^([A-Z]{5})\s+([A-Z0-9\s]+)$', line)
                if match:
                    wp_name = match.group(1)
                    routes_str = match.group(2).strip()
                    
                    # 检查下一行是否是坐标
                    if i + 1 < len(lines):
                        coord_line = lines[i+1].strip()
                        coord_match = re.search(r'([NS])(\d+)°(\d+)′(\d+)″\s+([EW])(\d+)°(\d+)′(\d+)″', coord_line)
                        
                        if coord_match:
                            # 解析坐标
                            lat_deg = float(coord_match.group(2))
                            lat_min = float(coord_match.group(3))
                            lat_sec = float(coord_match.group(4))
                            latitude = lat_deg + lat_min/60 + lat_sec/3600
                            if coord_match.group(1) == 'S':
                                latitude = -latitude
                            
                            lon_deg = float(coord_match.group(6))
                            lon_min = float(coord_match.group(7))
                            lon_sec = float(coord_match.group(8))
                            longitude = lon_deg + lon_min/60 + lon_sec/3600
                            if coord_match.group(5) == 'W':
                                longitude = -longitude
                            
                            waypoint = {
                                'name': wp_name,
                                'latitude': latitude,
                                'longitude': longitude,
                                'routes': routes_str.split()
                            }
                            waypoints.append(waypoint)
                            print(f"    找到航路点: {wp_name} - ({latitude:.4f}, {longitude:.4f})")
                    
                    i += 2
                else:
                    i += 1
        
    except Exception as e:
        print(f"  提取航路点出错: {e}")
    
    print(f"  从ENR_4.4共找到 {len(waypoints)} 个航路点")
    return waypoints

def save_data_to_json(data, filename):
    file_path = os.path.join(OUTPUT_DIR, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 数据已保存到: {file_path}")

def main():
    print("=" * 60)
    print("EAIP资料完整提取")
    print("=" * 60)
    
    # 1. 提取机场列表
    airports = extract_all_airports_from_gen()
    
    # 2. 提取每个机场的详细数据
    print("\n=== 3. 提取各机场详细信息 ===")
    detailed_airports = []
    for i, airport in enumerate(airports):
        print(f"  处理 {i+1}/{len(airports)}: {airport['icao_code']}")
        detailed = extract_airport_details(airport)
        if detailed:
            detailed_airports.append(detailed)
    
    # 3. 提取航路点
    waypoints = extract_all_waypoints()
    
    # 4. 保存数据
    save_data_to_json(detailed_airports, 'airports_complete.json')
    save_data_to_json(waypoints, 'waypoints.json')
    
    # 5. 打印摘要
    print("\n" + "=" * 60)
    print("提取完成摘要")
    print("=" * 60)
    print(f"机场总数: {len(detailed_airports)}")
    print(f"有坐标的机场: {len([a for a in detailed_airports if a['latitude'] is not None])}")
    print(f"航路点总数: {len(waypoints)}")

if __name__ == '__main__':
    main()
