"""
正确的EAIP资料提取脚本
分析了实际文件格式后重新编写
"""
import os
import re
import json
import pdfplumber

EAIP_DIR = r'E:\VLA\2026 Nr.04'
OUTPUT_DIR = r'E:\VLA\output\eaip_data'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def parse_gen_2_4_properly():
    """
    正确解析GEN_2.4文件 - 这是左右两列的格式
    """
    print("=== 1. 解析GEN_2.4机场列表 ===")
    airports = []
    
    pdf_path = os.path.join(EAIP_DIR, 'GEN_2.4_Location indicators.pdf')
    pdf = pdfplumber.open(pdf_path)
    
    for page_num, page in enumerate(pdf.pages):
        print(f"  处理第 {page_num + 1} 页...")
        text = page.extract_text()
        if not text:
            continue
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 跳过标题行
            if "中华人民共和国" in line or "地名代码" in line or "译码" in line:
                continue
            
            # 该行可能包含1或2个机场
            # 格式: 中文名/英文名 英文名 4字母代码 4字母代码 中文名/英文名 英文名
            # 或者: 中文名 英文名 4字母代码 ...
            
            # 提取所有4字母ICAO代码
            icao_codes = re.findall(r'[A-Z]{4}', line)
            
            for icao in icao_codes:
                # 跳过明显的非机场代码
                if icao in ['RCAA', 'VHHK', 'ZBPE', 'ZGZU', 'ZPKM', 'ZLHW', 'ZWUQ', 'ZSHA', 'ZYSH', 'ZJSA']:
                    continue
                if icao.endswith('FIR'):
                    continue
                if 'CITY' in line and icao in line:
                    continue
                
                # 查找该ICAO代码对应的中文名
                # 在ICAO代码前的部分找中文名
                idx = line.find(icao)
                if idx == -1:
                    continue
                
                # 查看前面的内容
                before_text = line[:idx]
                cn_name = "未知机场"
                
                # 匹配 中文名/英文名 格式
                slash_match = re.search(r'([\u4e00-\u9fa5]+/[\u4e00-\u9fa5]+)', before_text)
                if slash_match:
                    cn_name = slash_match.group(1)
                else:
                    # 匹配 中文名 格式
                    cn_match = re.search(r'([\u4e00-\u9fa5]+)', before_text[-30:])
                    if cn_match:
                        cn_name = cn_match.group(1)
                
                # 避免重复
                if icao in [a['icao_code'] for a in airports]:
                    continue
                
                airports.append({
                    'icao_code': icao,
                    'name_cn': cn_name,
                    'name_en': '',
                    'iata_code': '',
                    'latitude': None,
                    'longitude': None,
                    'elevation': None
                })
                print(f"    找到: {icao} - {cn_name}")
    
    print(f"  共找到 {len(airports)} 个机场")
    return airports

def extract_airport_details(airport):
    """
    从单个机场文件中提取详细数据
    """
    pdf_path = os.path.join(EAIP_DIR, f"{airport['icao_code']}.pdf")
    if not os.path.exists(pdf_path):
        return None
    
    try:
        pdf = pdfplumber.open(pdf_path)
        if len(pdf.pages) == 0:
            return None
        
        text = pdf.pages[0].extract_text()
        if not text:
            return None
        
        # 提取机场名
        name_match = re.search(r'([A-Z]{4})/([A-Z0-9]{3})[-\s]*([\u4e00-\u9fa5/]+)', text)
        if name_match:
            airport['iata_code'] = name_match.group(2)
            airport['name_cn'] = name_match.group(3)
        
        # 提取坐标 - 格式: N40°04.4′ E116°35.9′
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
            
            airport['latitude'] = latitude
            airport['longitude'] = longitude
        
        # 提取标高
        elev_match = re.search(r'ELEV.*?([\d.]+)\s*m', text)
        if elev_match:
            airport['elevation'] = float(elev_match.group(1))
        
        return airport
    
    except Exception as e:
        return None

def extract_waypoints_enr_4_4():
    """
    解析ENR_4.4文件中的航路点
    """
    print("\n=== 2. 解析ENR_4.4航路点 ===")
    waypoints = []
    
    pdf_path = os.path.join(EAIP_DIR, 'ENR_4.4_Name-code designators for significant points.pdf')
    pdf = pdfplumber.open(pdf_path)
    
    for page_num, page in enumerate(pdf.pages):
        print(f"  处理第 {page_num + 1} 页...")
        text = page.extract_text()
        if not text:
            continue
        
        # 使用表格提取
        tables = page.extract_tables()
        if tables:
            for table in tables:
                for row in table:
                    if not row or len(row) < 3:
                        continue
                    
                    # 每行的格式通常是: [航路点, 坐标, 航路]
                    # 需要仔细分析表格结构
                    row_str = str(row)
                    
                    # 寻找5字母航路点代码
                    wp_codes = re.findall(r'[A-Z]{5}', row_str)
                    if wp_codes:
                        wp_name = wp_codes[0]
                        
                        # 寻找坐标
                        coord_match = re.search(r'([NS])(\d+)°(\d+)′(\d+)″\s+([EW])(\d+)°(\d+)′(\d+)″', row_str)
                        if coord_match:
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
                            
                            waypoints.append({
                                'name': wp_name,
                                'latitude': latitude,
                                'longitude': longitude,
                                'routes': []
                            })
                            print(f"    航路点: {wp_name} - ({latitude:.4f}, {longitude:.4f})")
                            continue
                    
                    # 备用方案 - 直接从文本中解析
                    lines = text.split('\n')
                    for line in lines:
                        if re.match(r'^[A-Z]{5}\s', line):
                            parts = line.split()
                            if len(parts) >= 2:
                                wp_name = parts[0]
                                if wp_name in [w['name'] for w in waypoints]:
                                    continue
                                waypoints.append({
                                    'name': wp_name,
                                    'latitude': None,
                                    'longitude': None,
                                    'routes': []
                                })
    
    print(f"  找到 {len(waypoints)} 个航路点")
    return waypoints

def main():
    print("=" * 60)
    print("EAIP资料提取(改进版)")
    print("=" * 60)
    
    # 1. 解析GEN_2.4机场列表
    airports = parse_gen_2_4_properly()
    
    # 2. 尝试为每个机场提取详细信息
    print("\n=== 3. 提取各机场详细信息 ===")
    detailed_airports = []
    for i, airport in enumerate(airports):
        if (i + 1) % 10 == 0:
            print(f"  进度: {i + 1}/{len(airports)}")
        
        detailed = extract_airport_details(airport)
        if detailed:
            detailed_airports.append(detailed)
    
    # 3. 解析航路点
    waypoints = extract_waypoints_enr_4_4()
    
    # 4. 保存数据
    with open(os.path.join(OUTPUT_DIR, 'airports_final.json'), 'w', encoding='utf-8') as f:
        json.dump(detailed_airports, f, ensure_ascii=False, indent=2)
    
    with open(os.path.join(OUTPUT_DIR, 'waypoints_final.json'), 'w', encoding='utf-8') as f:
        json.dump(waypoints, f, ensure_ascii=False, indent=2)
    
    # 5. 输出摘要
    print("\n" + "=" * 60)
    print("提取完成")
    print("=" * 60)
    print(f"机场总数: {len(detailed_airports)}")
    with_coords = len([a for a in detailed_airports if a['latitude'] is not None])
    print(f"有坐标机场: {with_coords}")
    print(f"航路点总数: {len(waypoints)}")
    print(f"数据已保存到: {OUTPUT_DIR}")

if __name__ == '__main__':
    main()
