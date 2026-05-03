"""
完整的EAIP资料提取脚本
从GEN_2.4、ENR_4.1、ENR_4.4中提取所有地点和坐标数据
"""
import os
import re
import json
import glob
import pdfplumber

EAIP_DIR = r'E:\VLA\2026 Nr.04'
OUTPUT_DIR = r'E:\VLA\output\eaip_data'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 常见机场坐标数据库（用于补充没有PDF文件的机场）
KNOWN_AIRPORTS = {
    'ZBAD': {'name': '北京大兴国际机场', 'lat': 39.5422, 'lon': 116.4731, 'elev': 28.5},
    'ZSQD': {'name': '青岛胶东国际机场', 'lat': 36.2614, 'lon': 119.8542, 'elev': 34.0},
    'ZLXY': {'name': '西安咸阳国际机场', 'lat': 34.3364, 'lon': 108.7658, 'elev': 450.0},
    'ZSSS': {'name': '上海虹桥国际机场', 'lat': 31.1966, 'lon': 121.3352, 'elev': 3.6},
    'ZHHH': {'name': '武汉天河国际机场', 'lat': 30.6066, 'lon': 114.3516, 'elev': 23.3},
    'ZLYL': {'name': '洛阳北郊机场', 'lat': 34.7844, 'lon': 112.4453, 'elev': 157.0},
    'ZSNJ': {'name': '南京禄口国际机场', 'lat': 31.7433, 'lon': 118.8633, 'elev': 14.9},
    'ZSFZ': {'name': '福州长乐国际机场', 'lat': 25.9581, 'lon': 119.6863, 'elev': 45.8},
    'ZYTL': {'name': '大连周水子国际机场', 'lat': 38.9140, 'lon': 121.5335, 'elev': 19.8},
    'ZYTX': {'name': '沈阳桃仙国际机场', 'lat': 41.5811, 'lon': 123.4895, 'elev': 58.3},
    'ZWWW': {'name': '乌鲁木齐天山国际机场', 'lat': 43.9039, 'lon': 87.3911, 'elev': 645.6},
    'ZULS': {'name': '拉萨贡嘎国际机场', 'lat': 29.2933, 'lon': 90.9567, 'elev': 4386.0},
    'ZLLL': {'name': '兰州中川国际机场', 'lat': 36.3078, 'lon': 103.5889, 'elev': 1947.0},
    'ZJHK': {'name': '海口美兰国际机场', 'lat': 19.9142, 'lon': 110.3593, 'elev': 15.7},
    'ZJSY': {'name': '三亚凤凰国际机场', 'lat': 18.3042, 'lon': 109.5458, 'elev': 8.8},
    'ZGKL': {'name': '桂林两江国际机场', 'lat': 25.2100, 'lon': 110.2867, 'elev': 173.5},
    'ZBSJ': {'name': '石家庄正定国际机场', 'lat': 38.1678, 'lon': 114.6219, 'elev': 75.3},
    'ZBTJ': {'name': '天津滨海国际机场', 'lat': 39.1342, 'lon': 117.3369, 'elev': 2.8},
    'ZBDS': {'name': '鄂尔多斯伊金霍洛国际机场', 'lat': 39.6833, 'lon': 109.7500, 'elev': 1326.0},
    'ZBMZ': {'name': '满洲里西郊国际机场', 'lat': 49.5733, 'lon': 117.4167, 'elev': 622.0},
}

def extract_gen_2_4_airports():
    """从GEN_2.4提取所有机场"""
    print("=== 1. 从GEN_2.4提取机场列表 ===")
    airports = []
    
    pdf_path = os.path.join(EAIP_DIR, 'GEN_2.4_Location indicators.pdf')
    pdf = pdfplumber.open(pdf_path)
    
    seen_codes = set()
    
    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue
        
        lines = text.split('\n')
        for line in lines:
            # 跳过标题行
            if "中华人民共和国" in line or "地名代码" in line or "译码" in line:
                continue
            
            # 提取所有4字母ICAO代码
            codes = re.findall(r'([A-Z]{4})', line)
            
            for code in codes:
                # 跳过非机场代码
                if code in ['RCAA', 'VHHK', 'ZBPE', 'ZGZU', 'ZPKM', 'ZLHW', 'ZWUQ', 'ZSHA', 'ZYSH', 'ZJSA']:
                    continue
                if code in seen_codes:
                    continue
                seen_codes.add(code)
                
                # 查找中文名
                idx = line.find(code)
                cn_name = "未知机场"
                if idx != -1:
                    before_text = line[:idx][-40:]
                    cn_match = re.search(r'([\u4e00-\u9fa5]+)', before_text)
                    if cn_match:
                        cn_name = cn_match.group(1)
                
                airports.append({
                    'icao_code': code,
                    'name_cn': cn_name,
                    'iata_code': '',
                    'latitude': None,
                    'longitude': None,
                    'elevation': None,
                    'source': 'GEN_2.4'
                })
                print(f"    找到机场: {code} - {cn_name}")
    
    print(f"  GEN_2.4共找到 {len(airports)} 个机场")
    return airports

def extract_airport_details_from_pdf(icao_code):
    """从机场PDF文件提取详细信息"""
    pdf_path = os.path.join(EAIP_DIR, f"{icao_code}.pdf")
    if not os.path.exists(pdf_path):
        return None
    
    try:
        pdf = pdfplumber.open(pdf_path)
        if len(pdf.pages) == 0:
            return None
        
        text = pdf.pages[0].extract_text()
        if not text:
            return None
        
        result = {}
        
        # 提取机场名和IATA代码
        name_match = re.search(r'([A-Z]{4})/([A-Z0-9]{3})[-\s]*([\u4e00-\u9fa5/]+)', text)
        if name_match:
            result['iata_code'] = name_match.group(2)
            result['name_cn'] = name_match.group(3)
        
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
            
            result['latitude'] = latitude
            result['longitude'] = longitude
        
        # 提取标高
        elev_match = re.search(r'ELEV.*?([\d.]+)\s*m', text)
        if elev_match:
            result['elevation'] = float(elev_match.group(1))
        
        result['source'] = 'PDF'
        return result
    
    except Exception as e:
        return None

def extract_enr_4_1_navigation_aids():
    """从ENR_4.1提取导航设施（VOR/DME等）"""
    print("\n=== 2. 从ENR_4.1提取导航设施 ===")
    aids = []
    
    pdf_path = os.path.join(EAIP_DIR, 'ENR_4.1_Radio navigation aids — en-route.pdf')
    pdf = pdfplumber.open(pdf_path)
    
    for page_num, page in enumerate(pdf.pages):
        print(f"  处理第 {page_num + 1} 页...")
        text = page.extract_text()
        if not text:
            continue
        
        lines = text.split('\n')
        for line in lines:
            # 查找导航设施格式
            # 格式: VOR名称 VOR频率 坐标
            # 例如: BEIJ 114.10 N40°04.4′ E116°35.9′
            vor_match = re.search(r'([A-Z]{3,4})\s+(\d+\.\d+)\s+([NS])(\d+)°([\d.]+)′\s+([EW])(\d+)°([\d.]+)′', line)
            if vor_match:
                name = vor_match.group(1)
                freq = vor_match.group(2)
                lat_deg = float(vor_match.group(4))
                lat_min = float(vor_match.group(5))
                lat_dir = vor_match.group(3)
                lon_deg = float(vor_match.group(7))
                lon_min = float(vor_match.group(8))
                lon_dir = vor_match.group(6)
                
                latitude = lat_deg + lat_min/60
                if lat_dir == 'S':
                    latitude = -latitude
                
                longitude = lon_deg + lon_min/60
                if lon_dir == 'W':
                    longitude = -longitude
                
                aids.append({
                    'name': name,
                    'type': 'VOR/DME',
                    'frequency': freq,
                    'latitude': latitude,
                    'longitude': longitude
                })
                print(f"    VOR: {name} ({frequency}) - ({latitude:.4f}, {longitude:.4f})")
    
    print(f"  ENR_4.1共找到 {len(aids)} 个导航设施")
    return aids

def extract_enr_4_4_waypoints():
    """从ENR_4.4提取航路点"""
    print("\n=== 3. 从ENR_4.4提取航路点 ===")
    waypoints = []
    
    pdf_path = os.path.join(EAIP_DIR, 'ENR_4.4_Name-code designators for significant points.pdf')
    pdf = pdfplumber.open(pdf_path)
    
    for page_num, page in enumerate(pdf.pages):
        print(f"  处理第 {page_num + 1} 页...")
        text = page.extract_text()
        if not text:
            continue
        
        lines = text.split('\n')
        for i in range(len(lines)):
            line = lines[i].strip()
            
            # 查找5字母航路点代码
            match = re.match(r'^([A-Z]{5})\s+([A-Z0-9\s]+)$', line)
            if match:
                wp_name = match.group(1)
                routes = match.group(2).strip()
                
                # 检查下一行是否是坐标
                if i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    coord_match = re.search(r'([NS])(\d+)°(\d+)′(\d+)″\s+([EW])(\d+)°(\d+)′(\d+)″', next_line)
                    if coord_match:
                        lat_deg = float(coord_match.group(2))
                        lat_min = float(coord_match.group(3))
                        lat_sec = float(coord_match.group(4))
                        lat_dir = coord_match.group(1)
                        
                        lon_deg = float(coord_match.group(6))
                        lon_min = float(coord_match.group(7))
                        lon_sec = float(coord_match.group(8))
                        lon_dir = coord_match.group(5)
                        
                        latitude = lat_deg + lat_min/60 + lat_sec/3600
                        if lat_dir == 'S':
                            latitude = -latitude
                        
                        longitude = lon_deg + lon_min/60 + lon_sec/3600
                        if lon_dir == 'W':
                            longitude = -longitude
                        
                        waypoints.append({
                            'name': wp_name,
                            'latitude': latitude,
                            'longitude': longitude,
                            'routes': routes.split()
                        })
                        print(f"    航路点: {wp_name} - ({latitude:.4f}, {longitude:.4f})")
    
    print(f"  ENR_4.4共找到 {len(waypoints)} 个航路点")
    return waypoints

def enrich_airports_with_external_data(airports):
    """使用已知数据库补充机场坐标"""
    print("\n=== 4. 补充缺失的机场坐标 ===")
    enriched_count = 0
    
    for airport in airports:
        icao = airport['icao_code']
        
        # 如果已经有坐标，跳过
        if airport['latitude'] is not None:
            continue
        
        # 尝试从已知数据库获取
        if icao in KNOWN_AIRPORTS:
            data = KNOWN_AIRPORTS[icao]
            airport['latitude'] = data['lat']
            airport['longitude'] = data['lon']
            airport['elevation'] = data['elev']
            airport['name_cn'] = data['name']
            airport['source'] = 'KNOWN_DATABASE'
            enriched_count += 1
            print(f"    补充: {icao} - {data['name']}")
    
    print(f"  共补充 {enriched_count} 个机场坐标")
    return airports

def main():
    print("=" * 60)
    print("EAIP资料完整提取")
    print("=" * 60)
    
    # 1. 提取GEN_2.4机场列表
    airports = extract_gen_2_4_airports()
    
    # 2. 从PDF提取机场详细信息
    print("\n=== 提取机场详细信息 ===")
    for airport in airports:
        details = extract_airport_details_from_pdf(airport['icao_code'])
        if details:
            airport.update(details)
    
    # 3. 补充缺失坐标
    airports = enrich_airports_with_external_data(airports)
    
    # 4. 提取ENR_4.1导航设施
    nav_aids = extract_enr_4_1_navigation_aids()
    
    # 5. 提取ENR_4.4航路点
    waypoints = extract_enr_4_4_waypoints()
    
    # 6. 保存数据
    with open(os.path.join(OUTPUT_DIR, 'all_airports.json'), 'w', encoding='utf-8') as f:
        json.dump(airports, f, ensure_ascii=False, indent=2)
    
    with open(os.path.join(OUTPUT_DIR, 'navigation_aids.json'), 'w', encoding='utf-8') as f:
        json.dump(nav_aids, f, ensure_ascii=False, indent=2)
    
    with open(os.path.join(OUTPUT_DIR, 'waypoints_full.json'), 'w', encoding='utf-8') as f:
        json.dump(waypoints, f, ensure_ascii=False, indent=2)
    
    # 7. 统计摘要
    print("\n" + "=" * 60)
    print("提取完成摘要")
    print("=" * 60)
    print(f"机场总数: {len(airports)}")
    print(f"有坐标的机场: {len([a for a in airports if a['latitude'] is not None])}")
    print(f"导航设施: {len(nav_aids)}")
    print(f"航路点: {len(waypoints)}")
    print(f"\n数据保存到: {OUTPUT_DIR}")

if __name__ == '__main__':
    main()
