"""
深度分析EAIP文件夹中的所有PDF文件
梳理出对M1航迹生成模块有用的信息
"""
import os
import re
import glob
import pdfplumber

EAIP_DIR = r'E:\VLA\2026 Nr.04'

def analyze_all_pdfs():
    """分析所有PDF文件"""
    pdf_files = glob.glob(os.path.join(EAIP_DIR, '*.pdf'))
    print(f"发现 {len(pdf_files)} 个PDF文件\n")
    
    # 分类分析
    analysis = {
        'general': [],      # GEN系列：通用信息
        'enroute': [],      # ENR系列：航路信息
        'aerodrome': [],    # AD系列和机场代码PDF：机场信息
        'other': []         # 其他
    }
    
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        
        if filename.startswith('GEN'):
            analysis['general'].append(filename)
        elif filename.startswith('ENR'):
            analysis['enroute'].append(filename)
        elif re.match(r'^[A-Z]{4}\.pdf$', filename) or filename.startswith('AD_'):
            analysis['aerodrome'].append(filename)
        else:
            analysis['other'].append(filename)
    
    return analysis

def analyze_file_content(pdf_path, max_chars=2000):
    """分析单个PDF文件的内容"""
    try:
        pdf = pdfplumber.open(pdf_path)
        page_count = len(pdf.pages)
        
        if page_count == 0:
            return {
                'page_count': 0,
                'has_text': False,
                'preview': '',
                'content_type': 'empty'
            }
        
        first_page = pdf.pages[0]
        text = first_page.extract_text()
        
        if not text:
            return {
                'page_count': page_count,
                'has_text': False,
                'preview': '',
                'content_type': 'image_only'
            }
        
        preview = text[:max_chars]
        
        # 判断内容类型
        content_type = 'unknown'
        if 'Location indicators' in text:
            content_type = 'location_indicators'
        elif 'navigation aids' in text.lower():
            content_type = 'navigation_aids'
        elif 'significant points' in text.lower():
            content_type = 'significant_points'
        elif 'Air routes' in text:
            content_type = 'air_routes'
        elif 'Aerodrome' in text and '/' in text:
            content_type = 'aerodrome_details'
        elif 'CTA' in text or 'control area' in text.lower():
            content_type = 'control_area'
        
        return {
            'page_count': page_count,
            'has_text': True,
            'preview': preview,
            'content_type': content_type
        }
    
    except Exception as e:
        return {
            'page_count': 0,
            'has_text': False,
            'preview': str(e),
            'content_type': 'error'
        }

def extract_useful_info():
    """提取对M1有用的所有信息"""
    print("=" * 60)
    print("EAIP PDF文件深度分析")
    print("=" * 60)
    
    # 1. 先分类所有文件
    analysis = analyze_all_pdfs()
    
    print("\n【文件分类】")
    print(f"  GEN通用信息: {len(analysis['general'])} 个")
    for f in analysis['general']:
        print(f"    - {f}")
    
    print(f"\n  ENR航路信息: {len(analysis['enroute'])} 个")
    for f in analysis['enroute']:
        print(f"    - {f}")
    
    print(f"\n  AD/机场信息: {len(analysis['aerodrome'])} 个")
    print(f"    (显示前10个):")
    for f in analysis['aerodrome'][:10]:
        print(f"    - {f}")
    if len(analysis['aerodrome']) > 10:
        print(f"    ... 还有 {len(analysis['aerodrome']) - 10} 个")
    
    # 2. 详细分析关键文件
    print("\n" + "=" * 60)
    print("关键文件详细分析")
    print("=" * 60)
    
    key_files = [
        'GEN_2.4_Location indicators.pdf',
        'ENR_4.1_Radio navigation aids — en-route.pdf',
        'ENR_4.4_Name-code designators for significant points.pdf',
        'ENR_3.2.1_Air routes of Series A.pdf',
        'AD_1.3_Index to aerodromes and heliports.pdf'
    ]
    
    useful_info = {
        'airports': [],
        'waypoints': [],
        'navigation_aids': [],
        'routes': [],
        'useful_files': []
    }
    
    for filename in key_files:
        pdf_path = os.path.join(EAIP_DIR, filename)
        if not os.path.exists(pdf_path):
            print(f"\n❌ 文件不存在: {filename}")
            continue
        
        print(f"\n📄 {filename}")
        content = analyze_file_content(pdf_path)
        print(f"   页数: {content['page_count']}")
        print(f"   类型: {content['content_type']}")
        
        # 根据类型提取有用信息
        if content['content_type'] == 'location_indicators':
            useful_info['useful_files'].append({
                'filename': filename,
                'type': '机场代码列表',
                'value': '包含所有中国机场的ICAO代码和名称'
            })
        
        elif content['content_type'] == 'navigation_aids':
            useful_info['useful_files'].append({
                'filename': filename,
                'type': '导航设施',
                'value': '包含VOR/DME等导航台的坐标和频率'
            })
        
        elif content['content_type'] == 'significant_points':
            useful_info['useful_files'].append({
                'filename': filename,
                'type': '航路点',
                'value': '包含标准航路点的坐标和所属航路'
            })
        
        elif content['content_type'] == 'air_routes':
            useful_info['useful_files'].append({
                'filename': filename,
                'type': '航线网络',
                'value': '包含A/V/W等系列航路的完整航线'
            })
        
        # 显示预览
        if content['has_text'] and content['preview']:
            preview_lines = content['preview'].split('\n')[:5]
            print("   内容预览:")
            for line in preview_lines:
                print(f"     {line[:80]}")
    
    # 3. 列出所有机场PDF文件
    print("\n" + "=" * 60)
    print("机场PDF文件列表")
    print("=" * 60)
    
    airport_files = sorted([f for f in analysis['aerodrome'] if re.match(r'^[A-Z]{4}\.pdf$', f)])
    print(f"共找到 {len(airport_files)} 个机场PDF文件")
    
    # 统计有多少个机场有详细数据
    print("\n部分机场文件:")
    for f in airport_files[:20]:
        pdf_path = os.path.join(EAIP_DIR, f)
        content = analyze_file_content(pdf_path)
        status = "✅" if content['has_text'] else "❌"
        print(f"  {status} {f}")
    
    # 4. 输出总结
    print("\n" + "=" * 60)
    print("M1可用信息总结")
    print("=" * 60)
    
    print("\n【对M1有用的数据类型】")
    print("""
┌─────────────────────────────────────────────────────────────────┐
│  数据类型        │ 来源文件                          │ 用途          │
├─────────────────────────────────────────────────────────────────┤
│  机场坐标        │ GEN_2.4 + 机场PDF文件            │ 航线起终点    │
│  导航设施(VOR)   │ ENR_4.1                          │ 航路点        │
│  标准航路点      │ ENR_4.4                          │ 航路点        │
│  航线网络        │ ENR_3.2.x系列                    │ 航线规划      │
│  机场标高        │ 机场PDF文件                      │ 高度计算      │
└─────────────────────────────────────────────────────────────────┘
""")
    
    print("【推荐提取优先级】")
    print("""
1. ✅ 高优先级: GEN_2.4（机场列表）+ 机场PDF（详细坐标）
2. ✅ 高优先级: ENR_4.4（735个标准航路点）
3. ⚠️ 中优先级: ENR_4.1（导航设施）
4. ⚠️ 中优先级: ENR_3.2.x（航线网络）
""")
    
    return useful_info

if __name__ == '__main__':
    extract_useful_info()
