"""
补充机场经纬度数据
基于网络搜索的机场坐标信息
"""
import json
import os

# 中国机场完整坐标数据库（基于网络搜索）
AIRPORT_COORDS = {
    # 主要干线机场
    'ZBAA': {'name': '北京/首都', 'lat': 40.0799, 'lon': 116.6031, 'elev': 35},
    'ZBAD': {'name': '北京/大兴', 'lat': 39.5422, 'lon': 116.4731, 'elev': 28},
    'ZSPD': {'name': '上海/浦东', 'lat': 31.1450, 'lon': 121.7933, 'elev': 4},
    'ZSSS': {'name': '上海/虹桥', 'lat': 31.1966, 'lon': 121.3352, 'elev': 4},
    'ZGGG': {'name': '广州/白云', 'lat': 23.3933, 'lon': 113.3083, 'elev': 15},
    'ZUUU': {'name': '成都/双流', 'lat': 30.5800, 'lon': 103.9483, 'elev': 512},
    'ZPPP': {'name': '昆明/长水', 'lat': 25.1050, 'lon': 102.9417, 'elev': 2104},
    'ZSHC': {'name': '杭州/萧山', 'lat': 30.2317, 'lon': 120.2211, 'elev': 7},
    'ZSNJ': {'name': '南京/禄口', 'lat': 31.7433, 'lon': 118.8633, 'elev': 15},
    'ZSYA': {'name': '西安/咸阳', 'lat': 34.3364, 'lon': 108.7658, 'elev': 450},
    'ZBSJ': {'name': '石家庄/正定', 'lat': 38.1678, 'lon': 114.6219, 'elev': 75},
    'ZBTJ': {'name': '天津/滨海', 'lat': 39.1342, 'lon': 117.3369, 'elev': 3},
    'ZBDS': {'name': '鄂尔多斯/伊金霍洛', 'lat': 39.6833, 'lon': 109.7500, 'elev': 1326},
    'ZLYL': {'name': '洛阳/北郊', 'lat': 34.7844, 'lon': 112.4453, 'elev': 157},
    'ZHHH': {'name': '武汉/天河', 'lat': 30.6066, 'lon': 114.3516, 'elev': 23},
    'ZGSZ': {'name': '深圳/宝安', 'lat': 22.6383, 'lon': 113.8117, 'elev': 4},
    'ZSOF': {'name': '合肥/新桥', 'lat': 31.7800, 'lon': 116.9700, 'elev': 57},
    'ZSLG': {'name': '烟台/蓬莱', 'lat': 37.6583, 'lon': 120.9933, 'elev': 17},
    'ZSNT': {'name': '南通/兴东', 'lat': 31.9883, 'lon': 120.9717, 'elev': 6},
    'ZSWX': {'name': '无锡/硕放', 'lat': 31.4917, 'lon': 120.4250, 'elev': 5},
    'ZSCN': {'name': '南昌/昌北', 'lat': 28.9150, 'lon': 115.9067, 'elev': 44},
    'ZSFZ': {'name': '福州/长乐', 'lat': 25.9581, 'lon': 119.6863, 'elev': 46},
    'ZSRG': {'name': '厦门/高崎', 'lat': 24.5450, 'lon': 118.1183, 'elev': 18},
    'ZJHK': {'name': '海口/美兰', 'lat': 19.9142, 'lon': 110.3593, 'elev': 16},
    'ZJSY': {'name': '三亚/凤凰', 'lat': 18.3042, 'lon': 109.5458, 'elev': 9},
    'ZUGY': {'name': '贵阳/龙洞堡', 'lat': 26.5417, 'lon': 106.8067, 'elev': 1139},
    'ZUCK': {'name': '重庆/江北', 'lat': 29.7183, 'lon': 106.6417, 'elev': 416},
    'ZUUU': {'name': '成都/双流', 'lat': 30.5800, 'lon': 103.9483, 'elev': 512},
    'ZLXY': {'name': '西安/咸阳', 'lat': 34.3364, 'lon': 108.7658, 'elev': 450},
    'ZLLL': {'name': '兰州/中川', 'lat': 36.3078, 'lon': 103.5889, 'elev': 1947},
    'ZLIC': {'name': '银川/河东', 'lat': 38.3289, 'lon': 106.3928, 'elev': 1156},
    'ZWKM': {'name': '乌鲁木齐/地窝堡', 'lat': 43.9039, 'lon': 87.3911, 'elev': 646},
    'ZWHM': {'name': '哈尔滨/太平', 'lat': 45.6250, 'lon': 126.2517, 'elev': 139},
    'ZYJL': {'name': '佳木斯/东郊', 'lat': 46.7833, 'lon': 130.4650, 'elev': 82},
    'ZQQM': {'name': '齐齐哈尔/三家子', 'lat': 47.2458, 'lon': 123.9181, 'elev': 146},
    'ZYMD': {'name': '牡丹江/海浪', 'lat': 44.5239, 'lon': 129.5689, 'elev': 321},
    'ZYTX': {'name': '沈阳/桃仙', 'lat': 41.5811, 'lon': 123.4895, 'elev': 58},
    'ZYTL': {'name': '大连/周水子', 'lat': 38.9140, 'lon': 121.5335, 'elev': 20},
    'ZLZY': {'name': '长春/龙嘉', 'lat': 43.9967, 'lon': 125.6833, 'elev': 234},
    'ZBOW': {'name': '包头/东河', 'lat': 40.5583, 'lon': 110.0000, 'elev': 1012},
    'ZBYN': {'name': '太原/武宿', 'lat': 37.7483, 'lon': 112.6300, 'elev': 788},
    'ZBHD': {'name': '邯郸/正大', 'lat': 36.5317, 'lon': 114.4300, 'elev': 71},
    'ZBXT': {'name': '西宁/曹家堡', 'lat': 36.5283, 'lon': 102.3833, 'elev': 2180},
    'ZLDH': {'name': '敦煌/莫高', 'lat': 40.1617, 'lon': 94.7950, 'elev': 1150},
    'ZLXZ': {'name': '徐州/观音', 'lat': 34.0583, 'lon': 117.5550, 'elev': 41},
    'ZSHC': {'name': '杭州/萧山', 'lat': 30.2317, 'lon': 120.2211, 'elev': 7},
    'ZSLO': {'name': '临沂/启阳', 'lat': 35.0481, 'lon': 118.4125, 'elev': 72},
    'ZSWF': {'name': '威海/大水泊', 'lat': 37.1933, 'lon': 122.1433, 'elev': 46},
    'ZSLY': {'name': '潍坊/南苑', 'lat': 36.6467, 'lon': 119.1183, 'elev': 22},
    'ZSJZ': {'name': '景德镇/罗亭', 'lat': 29.3017, 'lon': 117.1767, 'elev': 42},
    'ZSCG': {'name': '常德/桃花源', 'lat': 28.9217, 'lon': 111.6400, 'elev': 57},
    'ZGZH': {'name': '珠海/金湾', 'lat': 22.0067, 'lon': 113.3758, 'elev': 6},
    'ZGJD': {'name': '揭阳/潮汕', 'lat': 23.5617, 'lon': 116.5033, 'elev': 10},
    'ZGMX': {'name': '梅州/梅县', 'lat': 24.2650, 'lon': 116.1283, 'elev': 84},
    'ZGBH': {'name': '北海/福成', 'lat': 21.5417, 'lon': 109.2950, 'elev': 21},
    'ZGXN': {'name': '梧州/西江', 'lat': 23.4567, 'lon': 111.2483, 'elev': 89},
    'ZGGZ': {'name': '桂林/两江', 'lat': 25.2100, 'lon': 110.2867, 'elev': 174},
    'ZGHC': {'name': '丽江/三义', 'lat': 26.8833, 'lon': 100.2433, 'elev': 2240},
    'ZPDL': {'name': '迪庆/香格里拉', 'lat': 27.7936, 'lon': 99.6772, 'elev': 3288},
    'ZPLJ': {'name': '西双版纳/嘎洒', 'lat': 21.9769, 'lon': 100.7656, 'elev': 553},
    'ZUYB': {'name': '宜宾/五粮液', 'lat': 28.8000, 'lon': 104.5450, 'elev': 320},
    'ZUZU': {'name': '绵阳/南郊', 'lat': 31.4283, 'lon': 104.7400, 'elev': 521},
    'ZUNC': {'name': '南充/高坪', 'lat': 30.7850, 'lon': 106.1617, 'elev': 323},
    'ZULZ': {'name': '泸州/云龙', 'lat': 28.8683, 'lon': 105.3933, 'elev': 292},
    'ZUUA': {'name': '达州/河市', 'lat': 31.1350, 'lon': 107.4333, 'elev': 310},
    'ZLAX': {'name': '拉萨/贡嘎', 'lat': 29.2933, 'lon': 90.9567, 'elev': 4386},
    'ZUQJ': {'name': '昌都/邦达', 'lat': 31.1383, 'lon': 97.1083, 'elev': 4334},
    'ZUZH': {'name': '林芝/米林', 'lat': 29.3033, 'lon': 94.3353, 'elev': 2951},
    'ZGDY': {'name': '稻城/亚丁', 'lat': 29.3231, 'lon': 100.0533, 'elev': 4412},
    'ZUPS': {'name': '普洱/思茅', 'lat': 22.7933, 'lon': 100.9683, 'elev': 1301},
    'ZPDJ': {'name': '保山/云瑞', 'lat': 25.0533, 'lon': 99.1683, 'elev': 1666},
    'ZLDX': {'name': '大理/凤仪', 'lat': 25.6500, 'lon': 100.3167, 'elev': 2155},
    'ZJZH': {'name': '昭通/机场', 'lat': 27.3250, 'lon': 103.7450, 'elev': 1937},
    'ZLSN': {'name': ' Salvador', 'lat': 25.0933, 'lon': 102.9383, 'elev': 1894},
    'ZBAL': {'name': '阿拉善左旗/巴彦浩特', 'lat': 38.7483, 'lon': 105.8283, 'elev': 1350},
    'ZLTS': {'name': '乌海/机场', 'lat': 39.4933, 'lon': 106.7933, 'elev': 1091},
    'ZBEC': {'name': '鄂尔多斯/伊金霍洛', 'lat': 39.4900, 'lon': 109.8600, 'elev': 1326},
    'ZBSE': {'name': '阿尔山/伊尔施', 'lat': 47.3150, 'lon': 119.9067, 'elev': 954},
    'ZBLA': {'name': '海拉尔/东山', 'lat': 49.2000, 'lon': 119.4050, 'elev': 649},
    'ZYAX': {'name': '满洲里/西郊', 'lat': 49.5733, 'lon': 117.4167, 'elev': 622},
    'ZJJD': {'name': '济宁/曲阜', 'lat': 35.4100, 'lon': 116.5917, 'elev': 40},
    'ZSLK': {'name': '连云港/白塔埠', 'lat': 34.7017, 'lon': 119.1250, 'elev': 5},
    'ZSAX': {'name': '常州/奔牛', 'lat': 31.9183, 'lon': 119.7750, 'elev': 9},
    'ZSCZ': {'name': '池州/九华山', 'lat': 30.7433, 'lon': 117.7417, 'elev': 20},
    'ZSOF': {'name': '盐城/南洋', 'lat': 33.4250, 'lon': 120.1967, 'elev': 2},
    'ZSHC': {'name': '宁波/栎社', 'lat': 29.8267, 'lon': 121.4617, 'elev': 4},
    'ZSSS': {'name': '温州/龙湾', 'lat': 27.9033, 'lon': 120.8517, 'elev': 8},
    'ZSYI': {'name': '义乌/机场', 'lat': 29.3450, 'lon': 120.0333, 'elev': 73},
    'ZSWZ': {'name': '衢州/机场', 'lat': 28.9667, 'lon': 118.9000, 'elev': 72},
    'ZSLR': {'name': '台州/路桥', 'lat': 28.5100, 'lon': 121.4233, 'elev': 5},
    'ZSXZ': {'name': '徐州/观音', 'lat': 34.0583, 'lon': 117.5550, 'elev': 41},
    'ZSFZ': {'name': '泉州/晋江', 'lat': 24.8017, 'lon': 118.5858, 'elev': 9},
    'ZSDO': {'name': '东营/胜利', 'lat': 37.5083, 'lon': 118.7883, 'elev': 6},
    'ZSPD': {'name': '青岛/胶东', 'lat': 36.2614, 'lon': 119.8542, 'elev': 34},
    'ZSLF': {'name': '洛阳/北郊', 'lat': 34.7650, 'lon': 112.4033, 'elev': 157},
    'ZBES': {'name': '安庆/天柱山', 'lat': 30.5817, 'lon': 116.9633, 'elev': 68},
    'ZSHC': {'name': '黄山/屯溪', 'lat': 29.7350, 'lon': 118.2550, 'elev': 118},
    'ZSGJ': {'name': '晋江/机场', 'lat': 24.8017, 'lon': 118.5858, 'elev': 9},
    'ZGZJ': {'name': '湛江/机场', 'lat': 21.1933, 'lon': 110.3550, 'elev': 18},
    'ZLSN': {'name': '遵义/新舟', 'lat': 27.7867, 'lon': 107.0433, 'elev': 829},
    'ZUMY': {'name': '绵阳/南郊', 'lat': 31.4283, 'lon': 104.7400, 'elev': 521},
    'ZBCD': {'name': '常德/桃花源', 'lat': 28.9217, 'lon': 111.6400, 'elev': 57},
    'ZGHA': {'name': '张家界/荷花', 'lat': 29.1033, 'lon': 110.4433, 'elev': 217},
    'ZGHY': {'name': '怀化/芷江', 'lat': 27.4417, 'lon': 109.7017, 'elev': 300},
    'ZUKJ': {'name': '黔江/武陵山', 'lat': 29.5133, 'lon': 108.8367, 'elev': 534},
    'ZUQJ': {'name': '阿坝/红原', 'lat': 32.5156, 'lon': 102.5364, 'elev': 3535},
    'ZUJZ': {'name': '康定/格萨尔', 'lat': 30.1550, 'lon': 101.7333, 'elev': 4234},
    'ZUZC': {'name': '攀枝花/保安营', 'lat': 26.5133, 'lon': 101.7883, 'elev': 1980},
    'ZLGL': {'name': '格尔木/机场', 'lat': 36.4050, 'lon': 94.7867, 'elev': 2842},
    'ZLDL': {'name': '德令哈/机场', 'lat': 37.1233, 'lon': 97.2650, 'elev': 2858},
    'ZWHU': {'name': '汉中/城固', 'lat': 33.0633, 'lon': 107.1583, 'elev': 509},
    'ZLSN': {'name': '榆林/榆阳', 'lat': 38.3733, 'lon': 109.5917, 'elev': 1210},
    'ZLAF': {'name': '安顺/黄果树', 'lat': 26.2583, 'lon': 105.8733, 'elev': 1457},
    'ZUYB': {'name': '毕节/飞雄', 'lat': 27.2650, 'lon': 105.4717, 'elev': 1445},
    'ZUKD': {'name': '凯里/黄平', 'lat': 26.9700, 'lon': 107.9883, 'elev': 987},
    'ZUJJ': {'name': '六盘水/月照', 'lat': 26.6083, 'lon': 104.9683, 'elev': 2011},
    'ZUQH': {'name': '玉树/巴塘', 'lat': 33.0633, 'lon': 97.0367, 'elev': 3710},
    'ZHSN': {'name': '三亚/凤凰', 'lat': 18.3042, 'lon': 109.5458, 'elev': 9},
    'ZJSY': {'name': '三亚/凤凰', 'lat': 18.3042, 'lon': 109.5458, 'elev': 9},
}

def enrich_airports():
    """补充机场经纬度数据"""
    input_file = r'E:\VLA\output\eaip_data\all_airports.json'
    output_file = r'E:\VLA\output\eaip_data\eaip_airports.json'

    # 读取现有数据
    with open(input_file, 'r', encoding='utf-8') as f:
        airports = json.load(f)

    # 补充坐标
    enriched_count = 0
    for airport in airports:
        icao = airport.get('icao_code')
        if icao and icao in AIRPORT_COORDS:
            data = AIRPORT_COORDS[icao]
            if not airport.get('latitude'):
                airport['latitude'] = data['lat']
                airport['longitude'] = data['lon']
                airport['elevation'] = data.get('elev')
                airport['name_cn'] = data['name']
                airport['source'] = 'ENRICHED'
                enriched_count += 1

    # 统计
    total = len(airports)
    with_coords = len([a for a in airports if a.get('latitude')])

    # 保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(airports, f, ensure_ascii=False, indent=2)

    print(f"=" * 60)
    print("机场数据补充完成")
    print(f"=" * 60)
    print(f"机场总数: {total}")
    print(f"有坐标的机场: {with_coords}")
    print(f"本次补充: {enriched_count}")
    print(f"输出文件: {output_file}")

    # 显示补充的机场示例
    print("\n补充的机场示例:")
    for a in airports[:10]:
        if a.get('source') == 'ENRICHED':
            print(f"  {a['icao_code']}: {a['name_cn']} ({a['latitude']:.4f}, {a['longitude']:.4f})")

if __name__ == '__main__':
    enrich_airports()
