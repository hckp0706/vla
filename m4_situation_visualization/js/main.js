// M4 多维态势可视化界面 - 主JavaScript文件

// 全局变量
let viewer = null;
let m1DataList = [];
let m2DataList = [];
let m1TrackLayers = [];
let m2TrackLayers = [];
let layers = {
    adiz: null,
    territorialSea: null,
    province: null,
    city: null,
    airport: null,
    waypoint: null,
    routeNetwork: null,
    civilRoute: null,
    radar: null,
    ssr: null,
    iff: null,
    esm: null,
    comint: null,
    m1Track: null,
    m2Track: null
};

const IDENTITY_COLORS = {
    FRIEND: Cesium.Color.LIME,
    FOE: Cesium.Color.RED,
    UNKNOWN: Cesium.Color.YELLOW,
    NEUTRAL: Cesium.Color.DODGERBLUE
};

const IDENTITY_LABELS = {
    FRIEND: '友方',
    FOE: '敌方',
    UNKNOWN: '未知',
    NEUTRAL: '中立'
};

const IDENTITY_SOURCE_LABELS = {
    IFF_MODE5: '敌我识别 Mode 5',
    IFF_MODE4: '敌我识别 Mode 4',
    SSR_MODE_S: '二次雷达 Mode S',
    SSR_MODE_3A: '二次雷达 Mode 3/A',
    ESM_INFERENCE: '电子侦察推断',
    NONE: '无'
};

const M1_TRACK_COLORS = [
    Cesium.Color.RED,
    Cesium.Color.YELLOW,
    Cesium.Color.CYAN,
    Cesium.Color.LIME,
    Cesium.Color.MAGENTA,
    Cesium.Color.ORANGE,
    Cesium.Color.DEEPPINK,
    Cesium.Color.AQUAMARINE
];

// 雷达配置数据（来自M2方案）
const radarConfigs = [
    {
        id: 'RADAR_01',
        name: '青岛雷达',
        lon: 120.38,
        lat: 36.07,
        maxRange: 400
    },
    {
        id: 'RADAR_02',
        name: '上海雷达',
        lon: 121.47,
        lat: 31.23,
        maxRange: 250
    },
    {
        id: 'RADAR_03',
        name: '宁波雷达',
        lon: 121.54,
        lat: 29.86,
        maxRange: 200
    },
    {
        id: 'RADAR_04',
        name: '南京雷达',
        lon: 118.78,
        lat: 32.06,
        maxRange: 300
    },
    {
        id: 'RADAR_05',
        name: '合肥雷达',
        lon: 117.27,
        lat: 31.86,
        maxRange: 250
    }
];

const ssrConfigs = [
    { id: 'SSR_01', name: '青岛二次雷达', lon: 120.38, lat: 36.07, maxRange: 460, coLocated: 'RADAR_01' },
    { id: 'SSR_02', name: '上海二次雷达', lon: 121.47, lat: 31.23, maxRange: 460, coLocated: 'RADAR_02' },
    { id: 'SSR_03', name: '宁波二次雷达', lon: 121.54, lat: 29.86, maxRange: 460, coLocated: 'RADAR_03' },
    { id: 'SSR_04', name: '南京二次雷达', lon: 118.78, lat: 32.06, maxRange: 460, coLocated: 'RADAR_04' },
    { id: 'SSR_05', name: '合肥二次雷达', lon: 117.27, lat: 31.86, maxRange: 460, coLocated: 'RADAR_05' }
];

const iffConfigs = [
    { id: 'IFF_01', name: '青岛敌我识别器', lon: 120.38, lat: 36.07, maxRange: 460, coLocated: 'RADAR_01' },
    { id: 'IFF_02', name: '上海敌我识别器', lon: 121.47, lat: 31.23, maxRange: 460, coLocated: 'RADAR_02' },
    { id: 'IFF_04', name: '南京敌我识别器', lon: 118.78, lat: 32.06, maxRange: 460, coLocated: 'RADAR_04' },
    { id: 'IFF_05', name: '合肥敌我识别器', lon: 117.27, lat: 31.86, maxRange: 460, coLocated: 'RADAR_05' }
];

const esmConfigs = [
    { id: 'ESM_01', name: '舟山电子侦察', lon: 122.10, lat: 30.01, maxRange: 300 },
    { id: 'ESM_02', name: '上海电子侦察', lon: 121.47, lat: 31.23, maxRange: 280 },
    { id: 'ESM_03', name: '温州电子侦察', lon: 121.15, lat: 28.28, maxRange: 300 }
];

const comintConfigs = [
    { id: 'COMINT_01', name: '舟山通信侦察', lon: 122.10, lat: 30.01, maxRange: 200 },
    { id: 'COMINT_02', name: '上海通信侦察', lon: 121.47, lat: 31.23, maxRange: 180 }
];

const SENSOR_NAME_MAP = {};
radarConfigs.forEach(r => { SENSOR_NAME_MAP[r.id] = r.name; });
ssrConfigs.forEach(s => { SENSOR_NAME_MAP[s.id] = s.name; });
iffConfigs.forEach(i => { SENSOR_NAME_MAP[i.id] = i.name; });
esmConfigs.forEach(e => { SENSOR_NAME_MAP[e.id] = e.name; });
comintConfigs.forEach(c => { SENSOR_NAME_MAP[c.id] = c.name; });
SENSOR_NAME_MAP['ELINT_01'] = '电子情报分析';

function translateSensorId(id) {
    return SENSOR_NAME_MAP[id] || id;
}

// 初始化Cesium地图
function initMap() {
    Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJlYWE1OWUxNy1mMWZiLTQzYjYtYTQ0OS1kMWFjYmFkNjc5YzciLCJpZCI6NTc3MzMsImlhdCI6MTYyMjY0NDE4OH0.XcKpgANiY19MC4bdFUXMVEBToBmqS8kuYpUlxJHYZxk';
    
    viewer = new Cesium.Viewer('cesiumContainer', {
        timeline: false,
        animation: false,
        fullscreenButton: false,
        vrButton: false,
        geocoder: false,
        homeButton: true,
        infoBox: true,
        sceneModePicker: false,
        selectionIndicator: false,
        navigationHelpButton: false,
        baseLayerPicker: false,
        imageryProvider: new Cesium.UrlTemplateImageryProvider({
            url: 'http://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
            subdomains: ['1', '2', '3', '4'],
            maximumLevel: 18
        })
    });
    
    viewer.scene.globe.depthTestAgainstTerrain = false;
    
    viewer.camera.setView({
        destination: Cesium.Cartesian3.fromDegrees(120.0, 32.0, 1500000.0),
        orientation: {
            heading: Cesium.Math.toRadians(0.0),
            pitch: Cesium.Math.toRadians(-90.0),
            roll: 0.0
        }
    });
    
    loadBaseMapData();
}

// 加载底图数据
async function loadBaseMapData() {
    try {
        await Promise.all([
            loadADIZ(),
            loadTerritorialSea(),
            loadProvinces(),
            loadCities(),
            loadAirports(),
            loadWaypoints(),
            loadRadars(),
            loadSSRStations(),
            loadIFFStations(),
            loadESMStations(),
            loadCOMINTStations()
        ]);
        
        toggleLayer('adiz', false);
        toggleLayer('territorialSea', false);
        toggleLayer('province', false);
        toggleLayer('city', false);
        
        updateLayerCheckboxes();
        
        console.log('底图数据加载完成');
    } catch (error) {
        console.error('底图数据加载失败:', error);
    }
}

// 加载东海防空识别区（ADIZ）
async function loadADIZ() {
    // 东海防空识别区边界坐标（根据公开资料）
    const adizCoords = [
        [128.0, 33.0],   // 东南角
        [128.0, 39.0],   // 东北角
        [125.0, 39.0],   // 北部边界
        [125.0, 40.0],   // 北部边界延伸
        [123.0, 40.0],   // 西北角
        [123.0, 39.0],   // 西北部
        [121.0, 39.0],   // 西部边界
        [121.0, 33.0],   // 西南部
        [124.0, 33.0],   // 南部边界
        [128.0, 33.0]    // 闭合
    ];
    
    layers.adiz = viewer.entities.add({
        name: '东海防空识别区',
        polygon: {
            hierarchy: Cesium.Cartesian3.fromDegreesArray(adizCoords.flat()),
            material: Cesium.Color.ORANGE.withAlpha(0.15),  // 使用橙色，与雷达威力图区分
            outline: true,
            outlineColor: Cesium.Color.ORANGE,
            outlineWidth: 3
        },
        label: {
            text: '东海防空识别区',
            font: '18px sans-serif',
            fillColor: Cesium.Color.ORANGE,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            outlineWidth: 2,
            outlineColor: Cesium.Color.BLACK,
            verticalOrigin: Cesium.VerticalOrigin.CENTER,
            horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
            pixelOffset: new Cesium.Cartesian2(0, 0),
            position: Cesium.Cartesian3.fromDegrees(125.0, 36.0, 0)
        }
    });
}

// 加载领海线（简化版）
async function loadTerritorialSea() {
    const territorialSeaCoords = [
        [121.0, 31.0],
        [122.0, 31.5],
        [123.0, 32.0],
        [124.0, 32.5],
        [125.0, 33.0],
        [125.0, 34.0],
        [124.0, 35.0],
        [123.0, 35.5],
        [122.0, 36.0],
        [121.0, 36.5],
        [120.0, 37.0],
        [119.0, 37.0],
        [118.0, 36.5],
        [117.0, 36.0],
        [117.0, 35.0],
        [118.0, 34.0],
        [119.0, 33.0],
        [120.0, 32.0],
        [121.0, 31.0]
    ];
    
    layers.territorialSea = viewer.entities.add({
        name: '领海线',
        polygon: {
            hierarchy: Cesium.Cartesian3.fromDegreesArray(territorialSeaCoords.flat()),
            material: Cesium.Color.BLUE.withAlpha(0.2),
            outline: true,
            outlineColor: Cesium.Color.BLUE,
            outlineWidth: 1
        }
    });
}

// 加载省级边界（简化版）
async function loadProvinces() {
    const provinces = [
        {
            name: '山东省',
            coords: [
                [115.0, 34.0], [118.0, 34.0], [119.0, 35.0], [120.0, 36.0],
                [121.0, 37.0], [122.0, 38.0], [122.0, 39.0], [121.0, 39.0],
                [120.0, 38.0], [119.0, 37.0], [118.0, 36.0], [117.0, 35.0],
                [116.0, 35.0], [115.0, 34.0]
            ]
        },
        {
            name: '江苏省',
            coords: [
                [116.0, 31.0], [118.0, 31.0], [119.0, 32.0], [120.0, 33.0],
                [121.0, 34.0], [121.0, 35.0], [120.0, 35.0], [119.0, 34.0],
                [118.0, 33.0], [117.0, 32.0], [116.0, 32.0], [116.0, 31.0]
            ]
        },
        {
            name: '浙江省',
            coords: [
                [118.0, 27.0], [120.0, 27.0], [121.0, 28.0], [122.0, 29.0],
                [123.0, 30.0], [122.0, 31.0], [121.0, 31.0], [120.0, 30.0],
                [119.0, 29.0], [118.0, 28.0], [118.0, 27.0]
            ]
        },
        {
            name: '上海市',
            coords: [
                [121.0, 31.0], [121.5, 31.0], [122.0, 31.5], [121.5, 31.5],
                [121.0, 31.0]
            ]
        }
    ];
    
    layers.province = new Cesium.CustomDataSource('provinces');
    
    provinces.forEach(province => {
        layers.province.entities.add({
            name: province.name,
            polyline: {
                positions: Cesium.Cartesian3.fromDegreesArray(province.coords.flat()),
                width: 1,
                material: Cesium.Color.GRAY.withAlpha(0.5)
            }
        });
    });
    
    layers.province.show = false;  // 默认不显示
    viewer.dataSources.add(layers.province);
}

// 加载主要城市
async function loadCities() {
    const cities = [
        { name: '济南', lon: 117.0, lat: 36.65 },
        { name: '青岛', lon: 120.38, lat: 36.07 },
        { name: '南京', lon: 118.78, lat: 32.06 },
        { name: '上海', lon: 121.47, lat: 31.23 },
        { name: '杭州', lon: 120.17, lat: 30.25 },
        { name: '宁波', lon: 121.54, lat: 29.86 }
    ];
    
    layers.city = new Cesium.CustomDataSource('cities');
    
    cities.forEach(city => {
        layers.city.entities.add({
            name: city.name,
            position: Cesium.Cartesian3.fromDegrees(city.lon, city.lat),
            point: {
                pixelSize: 8,
                color: Cesium.Color.WHITE,
                outlineColor: Cesium.Color.BLACK,
                outlineWidth: 1
            },
            label: {
                text: city.name,
                font: '14px sans-serif',
                fillColor: Cesium.Color.WHITE,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                outlineWidth: 1,
                outlineColor: Cesium.Color.BLACK,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -10)
            }
        });
    });
    
    layers.city.show = false;  // 默认不显示
    viewer.dataSources.add(layers.city);
}

// 加载主要机场
async function loadAirports() {
    layers.airport = new Cesium.CustomDataSource('airports');
    
    try {
        const response = await fetch('data/airports.json');
        const airports = await response.json();
        
        airports.forEach(airport => {
            const runwayInfo = airport.runway_dirs && airport.runway_dirs.length > 0 
                ? `跑道方向: ${airport.runway_dirs.map(d => d + '°').join('/')}` 
                : '';
            const elevInfo = airport.elev ? `海拔: ${airport.elev.toFixed(0)}m` : '';
            
            layers.airport.entities.add({
                name: airport.name,
                position: Cesium.Cartesian3.fromDegrees(airport.lon, airport.lat),
                point: {
                    pixelSize: 10,
                    color: Cesium.Color.WHITE,
                    outlineColor: Cesium.Color.BLACK,
                    outlineWidth: 2
                },
                label: {
                    text: airport.name + '\n' + airport.icao,
                    font: '11px sans-serif',
                    fillColor: Cesium.Color.WHITE,
                    style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                    outlineWidth: 1,
                    outlineColor: Cesium.Color.BLACK,
                    verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                    pixelOffset: new Cesium.Cartesian2(0, -12),
                    show: true,
                    scaleByDistance: new Cesium.NearFarScalar(1e5, 1.0, 2e7, 0.3),
                    translucencyByDistance: new Cesium.NearFarScalar(1e5, 1.0, 2e7, 0.3)
                },
                description: `
                    <div style="font-family: Arial, sans-serif; padding: 8px;">
                        <h3 style="color: #fff; margin: 0 0 8px 0;">✈ ${airport.name}</h3>
                        <table style="font-size:13px;">
                            <tr><td style="color:#aaa;padding:2px 6px;">ICAO代码</td><td style="padding:2px 6px;">${airport.icao}</td></tr>
                            ${airport.iata ? `<tr><td style="color:#aaa;padding:2px 6px;">IATA代码</td><td style="padding:2px 6px;">${airport.iata}</td></tr>` : ''}
                            <tr><td style="color:#aaa;padding:2px 6px;">经度</td><td style="padding:2px 6px;">${airport.lon.toFixed(4)}°</td></tr>
                            <tr><td style="color:#aaa;padding:2px 6px;">纬度</td><td style="padding:2px 6px;">${airport.lat.toFixed(4)}°</td></tr>
                            ${elevInfo ? `<tr><td style="color:#aaa;padding:2px 6px;">海拔</td><td style="padding:2px 6px;">${elevInfo}</td></tr>` : ''}
                            ${runwayInfo ? `<tr><td style="color:#aaa;padding:2px 6px;">跑道</td><td style="padding:2px 6px;">${runwayInfo}</td></tr>` : ''}
                        </table>
                    </div>`
            });
        });
        
        console.log('eAIP机场数据加载完成，共', airports.length, '个机场');
    } catch (error) {
        console.error('机场数据加载失败:', error);
    }
    
    viewer.dataSources.add(layers.airport);
}

async function loadWaypoints() {
    layers.waypoint = new Cesium.CustomDataSource('waypoints');
    
    try {
        const response = await fetch('data/waypoints.json');
        const waypoints = await response.json();
        
        waypoints.forEach(wp => {
            const routeInfo = wp.routes && wp.routes.length > 0 
                ? wp.routes.join(', ') 
                : '';
            
            layers.waypoint.entities.add({
                name: wp.name,
                position: Cesium.Cartesian3.fromDegrees(wp.lon, wp.lat),
                point: {
                    pixelSize: 5,
                    color: Cesium.Color.DARKGOLDENROD,
                    outlineColor: Cesium.Color.GOLD.withAlpha(0.8),
                    outlineWidth: 1,
                    scaleByDistance: new Cesium.NearFarScalar(1e5, 1.0, 2e7, 0.3),
                    translucencyByDistance: new Cesium.NearFarScalar(1e5, 1.0, 2e7, 0.0)
                },
                label: {
                    text: wp.name,
                    font: '9px sans-serif',
                    fillColor: Cesium.Color.GOLD,
                    style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                    outlineWidth: 1,
                    outlineColor: Cesium.Color.BLACK,
                    verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                    pixelOffset: new Cesium.Cartesian2(0, -7),
                    show: true,
                    scaleByDistance: new Cesium.NearFarScalar(1e5, 1.0, 1e7, 0.0),
                    translucencyByDistance: new Cesium.NearFarScalar(1e5, 1.0, 1e7, 0.0)
                },
                description: `
                    <div style="font-family: Arial, sans-serif; padding: 8px;">
                        <h3 style="color: khaki; margin: 0 0 8px 0;">📍 航路点 ${wp.name}</h3>
                        <table style="font-size:13px;">
                            <tr><td style="color:#aaa;padding:2px 6px;">名称</td><td style="padding:2px 6px;">${wp.name}</td></tr>
                            <tr><td style="color:#aaa;padding:2px 6px;">经度</td><td style="padding:2px 6px;">${wp.lon.toFixed(4)}°</td></tr>
                            <tr><td style="color:#aaa;padding:2px 6px;">纬度</td><td style="padding:2px 6px;">${wp.lat.toFixed(4)}°</td></tr>
                            ${routeInfo ? `<tr><td style="color:#aaa;padding:2px 6px;">所属航路</td><td style="padding:2px 6px;">${routeInfo}</td></tr>` : ''}
                        </table>
                    </div>`
            });
        });
        
        console.log('eAIP航路点数据加载完成，共', waypoints.length, '个航路点');
    } catch (error) {
        console.error('航路点数据加载失败:', error);
    }
    
    viewer.dataSources.add(layers.waypoint);
}

async function loadRouteNetwork() {
    layers.routeNetwork = new Cesium.CustomDataSource('routeNetwork');
    
    try {
        const response = await fetch('data/route_network_lines.json');
        const lines = await response.json();
        
        for (let i = 0; i < lines.length; i++) {
            const seg = lines[i];
            layers.routeNetwork.entities.add({
                polyline: {
                    positions: Cesium.Cartesian3.fromDegreesArrayHeights([
                        seg[0], seg[1], 0,
                        seg[2], seg[3], 0
                    ]),
                    width: 1,
                    material: new Cesium.PolylineDashMaterialProperty({
                        color: Cesium.Color.fromCssColorString('#5B7FA5').withAlpha(0.25),
                        dashLength: 16.0
                    })
                }
            });
        }
        
        console.log('航路网络加载完成:', lines.length, '条线段');
    } catch (error) {
        console.warn('航路网络数据加载失败:', error);
    }
    
    viewer.dataSources.add(layers.routeNetwork);
}

async function loadCivilRoutes() {
    layers.civilRoute = new Cesium.CustomDataSource('civilRoute');
    
    try {
        const response = await fetch('data/civil_routes.json');
        const routes = await response.json();
        
        for (let i = 0; i < routes.length; i++) {
            const route = routes[i];
            const coords = route.c;
            if (coords.length < 2) continue;
            
            const degArray = [];
            for (let j = 0; j < coords.length; j++) {
                degArray.push(coords[j][0], coords[j][1]);
            }
            
            layers.civilRoute.entities.add({
                name: route.k,
                polyline: {
                    positions: Cesium.Cartesian3.fromDegreesArray(degArray),
                    width: 1.5,
                    material: new Cesium.Color(0.2, 0.8, 1.0, 0.12)
                }
            });
        }
        
        console.log('民航航路加载完成:', routes.length, '条航线');
    } catch (error) {
        console.warn('民航航路数据加载失败:', error);
    }
    
    viewer.dataSources.add(layers.civilRoute);
}

// 加载雷达部署
async function loadRadars() {
    layers.radar = new Cesium.CustomDataSource('radars');
    
    // 使用浅绿色作为雷达威力图颜色
    const radarColor = Cesium.Color.LIGHTGREEN;
    
    radarConfigs.forEach(radar => {
        layers.radar.entities.add({
            name: radar.name,
            position: Cesium.Cartesian3.fromDegrees(radar.lon, radar.lat),
            point: {
                pixelSize: 12,
                color: Cesium.Color.DARKGREEN,  // 使用深绿色
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 2
            },
            label: {
                text: radar.name,
                font: '12px sans-serif',
                fillColor: Cesium.Color.WHITE,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                outlineWidth: 1,
                outlineColor: Cesium.Color.BLACK,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -14)
            }
        });
        
        layers.radar.entities.add({
            name: radar.name + '探测包络',
            position: Cesium.Cartesian3.fromDegrees(radar.lon, radar.lat),
            ellipse: {
                semiMinorAxis: radar.maxRange * 1000,
                semiMajorAxis: radar.maxRange * 1000,
                material: radarColor.withAlpha(0.25),  // 浅黄色底色，增加透明度
                outline: true,
                outlineColor: radarColor.withAlpha(0.6),
                outlineWidth: 2
            }
        });
    });
    
    viewer.dataSources.add(layers.radar);
}

function loadSSRStations() {
    layers.ssr = new Cesium.CustomDataSource('ssr');
    const ssrColor = Cesium.Color.CYAN;
    
    ssrConfigs.forEach(ssr => {
        layers.ssr.entities.add({
            name: ssr.name,
            position: Cesium.Cartesian3.fromDegrees(ssr.lon, ssr.lat),
            point: {
                pixelSize: 10,
                color: Cesium.Color.DARKCYAN,
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 2
            },
            label: {
                text: ssr.name,
                font: '11px sans-serif',
                fillColor: Cesium.Color.CYAN,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                outlineWidth: 1,
                outlineColor: Cesium.Color.BLACK,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -14)
            },
            description: `
                <div style="font-family: Arial, sans-serif; padding: 8px;">
                    <h3 style="color: #00bcd4; margin: 0 0 8px 0;">📻 二次雷达站</h3>
                    <table style="font-size:13px;">
                        <tr><td style="color:#aaa;padding:2px 6px;">编号</td><td style="padding:2px 6px;">${ssr.id}</td></tr>
                        <tr><td style="color:#aaa;padding:2px 6px;">名称</td><td style="padding:2px 6px;">${ssr.name}</td></tr>
                        <tr><td style="color:#aaa;padding:2px 6px;">最大探测距离</td><td style="padding:2px 6px;">${ssr.maxRange} km</td></tr>
                        <tr><td style="color:#aaa;padding:2px 6px;">共址雷达</td><td style="padding:2px 6px;">${translateSensorId(ssr.coLocated)}</td></tr>
                    </table>
                </div>`
        });
        
        layers.ssr.entities.add({
            name: ssr.name + '探测包络',
            position: Cesium.Cartesian3.fromDegrees(ssr.lon, ssr.lat),
            ellipse: {
                semiMinorAxis: ssr.maxRange * 1000,
                semiMajorAxis: ssr.maxRange * 1000,
                material: ssrColor.withAlpha(0.12),
                outline: true,
                outlineColor: ssrColor.withAlpha(0.4),
                outlineWidth: 1
            }
        });
    });
    
    viewer.dataSources.add(layers.ssr);
}

function loadIFFStations() {
    layers.iff = new Cesium.CustomDataSource('iff');
    const iffColor = Cesium.Color.MEDIUMPURPLE;
    
    iffConfigs.forEach(iff => {
        layers.iff.entities.add({
            name: iff.name,
            position: Cesium.Cartesian3.fromDegrees(iff.lon, iff.lat),
            point: {
                pixelSize: 10,
                color: Cesium.Color.PURPLE,
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 2,
                heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
            },
            label: {
                text: iff.name,
                font: '11px sans-serif',
                fillColor: Cesium.Color.MEDIUMPURPLE,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                outlineWidth: 1,
                outlineColor: Cesium.Color.BLACK,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -14)
            },
            description: `
                <div style="font-family: Arial, sans-serif; padding: 8px;">
                    <h3 style="color: #9c27b0; margin: 0 0 8px 0;">🔑 敌我识别器站</h3>
                    <table style="font-size:13px;">
                        <tr><td style="color:#aaa;padding:2px 6px;">编号</td><td style="padding:2px 6px;">${iff.id}</td></tr>
                        <tr><td style="color:#aaa;padding:2px 6px;">名称</td><td style="padding:2px 6px;">${iff.name}</td></tr>
                        <tr><td style="color:#aaa;padding:2px 6px;">最大探测距离</td><td style="padding:2px 6px;">${iff.maxRange} km</td></tr>
                        <tr><td style="color:#aaa;padding:2px 6px;">共址雷达</td><td style="padding:2px 6px;">${translateSensorId(iff.coLocated)}</td></tr>
                    </table>
                </div>`
        });
        
        layers.iff.entities.add({
            name: iff.name + '探测包络',
            position: Cesium.Cartesian3.fromDegrees(iff.lon, iff.lat),
            ellipse: {
                semiMinorAxis: iff.maxRange * 1000,
                semiMajorAxis: iff.maxRange * 1000,
                material: iffColor.withAlpha(0.10),
                outline: true,
                outlineColor: iffColor.withAlpha(0.35),
                outlineWidth: 1
            }
        });
    });
    
    viewer.dataSources.add(layers.iff);
}

function loadESMStations() {
    layers.esm = new Cesium.CustomDataSource('esm');
    const esmColor = Cesium.Color.ORANGE;
    
    esmConfigs.forEach(esm => {
        layers.esm.entities.add({
            name: esm.name,
            position: Cesium.Cartesian3.fromDegrees(esm.lon, esm.lat),
            point: {
                pixelSize: 10,
                color: Cesium.Color.DARKORANGE,
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 2
            },
            label: {
                text: esm.name,
                font: '11px sans-serif',
                fillColor: Cesium.Color.ORANGE,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                outlineWidth: 1,
                outlineColor: Cesium.Color.BLACK,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -14)
            },
            description: `
                <div style="font-family: Arial, sans-serif; padding: 8px;">
                    <h3 style="color: #ff9800; margin: 0 0 8px 0;">👂 电子侦察站</h3>
                    <table style="font-size:13px;">
                        <tr><td style="color:#aaa;padding:2px 6px;">编号</td><td style="padding:2px 6px;">${esm.id}</td></tr>
                        <tr><td style="color:#aaa;padding:2px 6px;">名称</td><td style="padding:2px 6px;">${esm.name}</td></tr>
                        <tr><td style="color:#aaa;padding:2px 6px;">最大截获距离</td><td style="padding:2px 6px;">${esm.maxRange} km</td></tr>
                        <tr><td style="color:#aaa;padding:2px 6px;">类型</td><td style="padding:2px 6px;">无源电子侦察</td></tr>
                    </table>
                </div>`
        });
        
        layers.esm.entities.add({
            name: esm.name + '截获包络',
            position: Cesium.Cartesian3.fromDegrees(esm.lon, esm.lat),
            ellipse: {
                semiMinorAxis: esm.maxRange * 1000,
                semiMajorAxis: esm.maxRange * 1000,
                material: esmColor.withAlpha(0.08),
                outline: true,
                outlineColor: esmColor.withAlpha(0.3),
                outlineWidth: 1
            }
        });
    });
    
    viewer.dataSources.add(layers.esm);
}

function loadCOMINTStations() {
    layers.comint = new Cesium.CustomDataSource('comint');
    const comintColor = Cesium.Color.PINK;
    
    comintConfigs.forEach(comint => {
        layers.comint.entities.add({
            name: comint.name,
            position: Cesium.Cartesian3.fromDegrees(comint.lon, comint.lat),
            point: {
                pixelSize: 10,
                color: Cesium.Color.DEEPPINK,
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 2
            },
            label: {
                text: comint.name,
                font: '11px sans-serif',
                fillColor: Cesium.Color.PINK,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                outlineWidth: 1,
                outlineColor: Cesium.Color.BLACK,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -14)
            },
            description: `
                <div style="font-family: Arial, sans-serif; padding: 8px;">
                    <h3 style="color: #e91e63; margin: 0 0 8px 0;">📞 通信侦察站</h3>
                    <table style="font-size:13px;">
                        <tr><td style="color:#aaa;padding:2px 6px;">编号</td><td style="padding:2px 6px;">${comint.id}</td></tr>
                        <tr><td style="color:#aaa;padding:2px 6px;">名称</td><td style="padding:2px 6px;">${comint.name}</td></tr>
                        <tr><td style="color:#aaa;padding:2px 6px;">最大截获距离</td><td style="padding:2px 6px;">${comint.maxRange} km</td></tr>
                        <tr><td style="color:#aaa;padding:2px 6px;">类型</td><td style="padding:2px 6px;">通信情报侦察</td></tr>
                    </table>
                </div>`
        });
        
        layers.comint.entities.add({
            name: comint.name + '截获包络',
            position: Cesium.Cartesian3.fromDegrees(comint.lon, comint.lat),
            ellipse: {
                semiMinorAxis: comint.maxRange * 1000,
                semiMajorAxis: comint.maxRange * 1000,
                material: comintColor.withAlpha(0.08),
                outline: true,
                outlineColor: comintColor.withAlpha(0.3),
                outlineWidth: 1
            }
        });
    });
    
    viewer.dataSources.add(layers.comint);
}

// 加载M1真值轨迹
function loadM1Track(data, color, trackIndex) {
    if (!data || !data.track_points) {
        console.error('M1数据格式错误');
        return;
    }
    
    const layerName = 'm1Track_' + (data.target_id || trackIndex);
    const layer = new Cesium.CustomDataSource(layerName);
    m1TrackLayers.push(layer);
    
    const trackColor = color || M1_TRACK_COLORS[trackIndex % M1_TRACK_COLORS.length];
    
    const targetLabel = (data.platform_type || '目标') + '-' + (data.target_id || '');
    const hasAdsb = data.has_adsb;
    const missionType = data.mission_type || '';
    
    const coordsWithHeight = [];
    data.track_points.forEach(point => {
        coordsWithHeight.push(point.lon, point.lat, point.alt_m);
    });
    
    layer.entities.add({
        name: 'M1真值轨迹-' + targetLabel,
        polyline: {
            positions: Cesium.Cartesian3.fromDegreesArrayHeights(coordsWithHeight),
            width: 4,
            material: new Cesium.PolylineGlowMaterialProperty({
                glowPower: 0.3,
                color: trackColor
            }),
            depthFailMaterial: new Cesium.PolylineGlowMaterialProperty({
                glowPower: 0.3,
                color: trackColor
            })
        }
    });
    
    const pointInterval = Math.max(1, Math.floor(data.track_points.length / 50));
    data.track_points.forEach((point, index) => {
        if (index % pointInterval === 0) {
            let descHtml = `
                <div style="font-family: Arial, sans-serif; padding: 10px;">
                    <h3 style="margin: 0 0 10px 0; color: #4fc3f7;">M1轨迹点详细信息</h3>
                    <p><strong>目标批号:</strong> ${data.target_id}</p>
                    <p><strong>机型:</strong> ${data.platform_type}</p>
                    <p><strong>任务类型:</strong> ${missionType}</p>
                    <p><strong>时间:</strong> ${point.time}</p>
                    <p><strong>经度:</strong> ${point.lon.toFixed(6)}°</p>
                    <p><strong>纬度:</strong> ${point.lat.toFixed(6)}°</p>
                    <p><strong>高度:</strong> ${point.alt_m.toFixed(1)} m</p>
                    <p><strong>速度:</strong> ${point.speed_ms.toFixed(1)} m/s</p>
                    <p><strong>航向:</strong> ${point.heading_deg.toFixed(1)}°</p>
                    <p><strong>飞行阶段:</strong> ${point.phase}</p>`;
            if (point.adsb) {
                descHtml += `
                    <hr style="border-color: #4fc3f7; margin: 8px 0;">
                    <h3 style="margin: 0 0 10px 0; color: #81c784;">ADS-B信息</h3>
                    <p><strong>ICAO24:</strong> ${point.adsb.icao24}</p>
                    <p><strong>呼号:</strong> ${point.adsb.callsign}</p>
                    <p><strong>气压高度:</strong> ${point.adsb.altitude_ft.toFixed(0)} ft</p>
                    <p><strong>地速:</strong> ${point.adsb.ground_speed_kt.toFixed(1)} kt</p>
                    <p><strong>航迹角:</strong> ${point.adsb.track.toFixed(1)}°</p>
                    <p><strong>垂直速率:</strong> ${point.adsb.vertical_rate_fpm.toFixed(0)} fpm</p>
                    <p><strong>地面:</strong> ${point.adsb.on_ground ? '是' : '否'}</p>
                    <p><strong>Squawk:</strong> ${point.adsb.squawk}</p>`;
            }
            descHtml += `</div>`;
            
            layer.entities.add({
                name: `M1轨迹点-${targetLabel}-${index}`,
                position: Cesium.Cartesian3.fromDegrees(point.lon, point.lat, point.alt_m),
                point: {
                    pixelSize: 5,
                    color: trackColor,
                    outlineColor: Cesium.Color.WHITE,
                    outlineWidth: 1
                },
                description: descHtml
            });
        }
    });
    
    if (data.track_points.length > 0) {
        const startPoint = data.track_points[0];
        layer.entities.add({
            name: 'M1轨迹起点-' + targetLabel,
            position: Cesium.Cartesian3.fromDegrees(startPoint.lon, startPoint.lat, startPoint.alt_m),
            point: {
                pixelSize: 10,
                color: Cesium.Color.GREEN,
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 2
            },
            label: {
                text: '起点-' + targetLabel,
                font: '11px sans-serif',
                fillColor: Cesium.Color.GREEN,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                outlineWidth: 1,
                outlineColor: Cesium.Color.WHITE,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -12)
            }
        });
        
        const endPoint = data.track_points[data.track_points.length - 1];
        layer.entities.add({
            name: 'M1轨迹终点-' + targetLabel,
            position: Cesium.Cartesian3.fromDegrees(endPoint.lon, endPoint.lat, endPoint.alt_m),
            point: {
                pixelSize: 10,
                color: trackColor,
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 2
            },
            label: {
                text: '终点-' + targetLabel,
                font: '11px sans-serif',
                fillColor: trackColor,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                outlineWidth: 1,
                outlineColor: Cesium.Color.WHITE,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -12)
            }
        });
    }
    
    viewer.dataSources.add(layer);
    console.log('M1轨迹加载完成:', targetLabel, '共', data.track_points.length, '个点, ADS-B:', hasAdsb);
}

function loadM2Track(data, fileIndex) {
    if (!data || !data.network_tracks) {
        console.error('M2数据格式错误');
        return;
    }
    
    const layerName = 'm2Track_' + fileIndex;
    const layer = new Cesium.CustomDataSource(layerName);
    m2TrackLayers.push(layer);
    
    const isComprehensive = data.network_tracks.some(t => t.identity !== undefined);
    
    const trackMap = new Map();
    
    data.network_tracks.forEach(track => {
        const trackId = track.track_id;
        if (!trackMap.has(trackId)) {
            trackMap.set(trackId, []);
        }
        const point = {
            time: new Date(track.time),
            lon: track.obs_lon,
            lat: track.obs_lat,
            alt: track.obs_alt_m,
            speed: track.obs_speed_ms,
            heading: track.obs_heading_deg,
            quality: track.track_quality,
            snr: track.snr_avg_db,
            radars: track.source_radars || []
        };
        if (isComprehensive) {
            point.identity = track.identity || 'UNKNOWN';
            point.identity_source = track.identity_source || 'NONE';
            point.identity_confidence = track.identity_confidence || 0.0;
            point.squawk = track.squawk || '';
            point.callsign = track.callsign || '';
            point.icao24 = track.icao24 || '';
            point.altitude_source = track.altitude_source || 'RADAR';
            point.altitude_ft = track.altitude_ft || 0.0;
            point.emitter_type = track.emitter_type || '';
            point.emitter_threat_level = track.emitter_threat_level || 0;
            point.comm_activity = track.comm_activity || '';
            point.position_source = track.position_source || 'TRUTH';
            point.source_sensors = track.source_sensors || [];
            point.sensor_count = track.sensor_count || 0;
        }
        trackMap.get(trackId).push(point);
    });
    
    trackMap.forEach((points, trackId) => {
        points.sort((a, b) => a.time - b.time);
        
        let dominantIdentity = 'UNKNOWN';
        if (isComprehensive) {
            const identityCounts = {};
            points.forEach(p => {
                identityCounts[p.identity] = (identityCounts[p.identity] || 0) + 1;
            });
            dominantIdentity = Object.entries(identityCounts).sort((a, b) => b[1] - a[1])[0][0];
        }
        const trackColor = isComprehensive ? (IDENTITY_COLORS[dominantIdentity] || Cesium.Color.DARKBLUE) : Cesium.Color.DARKBLUE;
        
        const sensorSegments = [];
        const truthSegments = [];
        let currentSensorSeg = [];
        let currentTruthSeg = [];
        let lastTime = null;
        
        for (let i = 0; i < points.length; i++) {
            const p = points[i];
            if (lastTime !== null) {
                const timeDiff = (p.time - lastTime) / 1000;
                if (timeDiff > 30) {
                    if (currentSensorSeg.length >= 2) sensorSegments.push(currentSensorSeg.slice());
                    if (currentTruthSeg.length >= 2) truthSegments.push(currentTruthSeg.slice());
                    currentSensorSeg = [];
                    currentTruthSeg = [];
                    lastTime = p.time;
                    continue;
                }
            }
            
            const hasSensor = isComprehensive ? (p.sensor_count > 0) : (p.radars.length > 0);
            
            if (hasSensor) {
                currentSensorSeg.push(p);
                if (currentTruthSeg.length >= 2) {
                    truthSegments.push(currentTruthSeg.slice());
                }
                currentTruthSeg = [];
            } else {
                currentTruthSeg.push(p);
                if (currentSensorSeg.length >= 2) {
                    sensorSegments.push(currentSensorSeg.slice());
                }
                currentSensorSeg = [];
            }
            
            lastTime = p.time;
        }
        if (currentSensorSeg.length >= 2) sensorSegments.push(currentSensorSeg);
        if (currentTruthSeg.length >= 2) truthSegments.push(currentTruthSeg);
        
        sensorSegments.forEach((seg, segIdx) => {
            const coords = [];
            seg.forEach(p => coords.push(p.lon, p.lat, p.alt));
            layer.entities.add({
                name: `M2航迹线(传感器)-${trackId}-${segIdx}`,
                polyline: {
                    positions: Cesium.Cartesian3.fromDegreesArrayHeights(coords),
                    width: 3,
                    material: new Cesium.PolylineGlowMaterialProperty({
                        glowPower: 0.2,
                        color: trackColor
                    }),
                    depthFailMaterial: new Cesium.PolylineGlowMaterialProperty({
                        glowPower: 0.2,
                        color: trackColor
                    })
                }
            });
        });
        
        truthSegments.forEach((seg, segIdx) => {
            const coords = [];
            seg.forEach(p => coords.push(p.lon, p.lat, p.alt));
            layer.entities.add({
                name: `M2航迹线(推算)-${trackId}-${segIdx}`,
                polyline: {
                    positions: Cesium.Cartesian3.fromDegreesArrayHeights(coords),
                    width: 2,
                    material: new Cesium.PolylineDashMaterialProperty({
                        color: trackColor.withAlpha(0.5),
                        dashLength: 12.0,
                        dashPattern: 255.0
                    }),
                    depthFailMaterial: new Cesium.PolylineDashMaterialProperty({
                        color: trackColor.withAlpha(0.3),
                        dashLength: 12.0,
                        dashPattern: 255.0
                    })
                }
            });
        });
        
        const sensorPointCount = points.filter(p => isComprehensive ? p.sensor_count > 0 : p.radars.length > 0).length;
        console.log(`M2航迹-${trackId}(${dominantIdentity})，共${points.length}个点，传感器覆盖${sensorPointCount}个`);
        
        points.forEach((point, pointIndex) => {
            const hasSensor = isComprehensive ? (point.sensor_count > 0) : (point.radars.length > 0);
            
            let showPoint = false;
            if (hasSensor) {
                showPoint = true;
            } else {
                const interval = Math.max(1, Math.floor(points.length / 100));
                if (pointIndex % interval === 0 || pointIndex === 0 || pointIndex === points.length - 1) {
                    showPoint = true;
                }
            }
            if (!showPoint) return;
            
            let descHtml = `
                <div style="font-family: Arial, sans-serif; padding: 10px; max-width: 400px;">
                    <h3 style="margin: 0 0 10px 0; color: #4fc3f7;">M2综合融合航迹点</h3>
                    <table style="width:100%;border-collapse:collapse;font-size:13px;">
                        <tr><td style="padding:2px 6px;color:#aaa;">航迹ID</td><td style="padding:2px 6px;">${trackId}</td></tr>
                        <tr><td style="padding:2px 6px;color:#aaa;">时间</td><td style="padding:2px 6px;">${point.time.toLocaleString()}</td></tr>
                        <tr><td style="padding:2px 6px;color:#aaa;">经度</td><td style="padding:2px 6px;">${point.lon.toFixed(6)}°</td></tr>
                        <tr><td style="padding:2px 6px;color:#aaa;">纬度</td><td style="padding:2px 6px;">${point.lat.toFixed(6)}°</td></tr>
                        <tr><td style="padding:2px 6px;color:#aaa;">高度</td><td style="padding:2px 6px;">${point.alt.toFixed(1)} m</td></tr>
                        <tr><td style="padding:2px 6px;color:#aaa;">速度</td><td style="padding:2px 6px;">${point.speed.toFixed(1)} m/s</td></tr>
                        <tr><td style="padding:2px 6px;color:#aaa;">航向</td><td style="padding:2px 6px;">${point.heading.toFixed(1)}°</td></tr>
                    </table>`;
            
            if (isComprehensive) {
                const identityLabel = IDENTITY_LABELS[point.identity] || point.identity;
                const identitySourceLabel = IDENTITY_SOURCE_LABELS[point.identity_source] || point.identity_source;
                const identityColorMap = {FRIEND: '#4caf50', FOE: '#f44336', UNKNOWN: '#ff9800', NEUTRAL: '#2196f3'};
                const idColor = identityColorMap[point.identity] || '#9e9e9e';
                
                const posSourceLabels = {
                    RADAR: '雷达观测',
                    IFF_MODE5: '敌我识别器位置报告',
                    SSR_ALT: '二次雷达高度+上次位置',
                    LAST_KNOWN: '上次已知位置',
                    TRUTH: '无传感器覆盖(推算)'
                };
                const posSourceLabel = posSourceLabels[point.position_source] || point.position_source;
                
                descHtml += `
                    <hr style="border-color: #4fc3f7; margin: 8px 0;">
                    <h3 style="margin: 0 0 8px 0; color: #81c784;">🛡️ 敌我识别</h3>
                    <table style="width:100%;border-collapse:collapse;font-size:13px;">
                        <tr><td style="padding:2px 6px;color:#aaa;">识别结果</td><td style="padding:2px 6px;"><span style="color:${idColor};font-weight:bold;font-size:14px;">${identityLabel}</span></td></tr>
                        <tr><td style="padding:2px 6px;color:#aaa;">识别来源</td><td style="padding:2px 6px;">${identitySourceLabel}</td></tr>
                        <tr><td style="padding:2px 6px;color:#aaa;">置信度</td><td style="padding:2px 6px;">${(point.identity_confidence * 100).toFixed(0)}%</td></tr>
                        <tr><td style="padding:2px 6px;color:#aaa;">位置来源</td><td style="padding:2px 6px;">${posSourceLabel}</td></tr>
                    </table>`;
                
                const sensorTypes = [];
                const radarSensors = point.source_sensors.filter(s => s.startsWith('RADAR'));
                const ssrSensors = point.source_sensors.filter(s => s.startsWith('SSR'));
                const iffSensors = point.source_sensors.filter(s => s.startsWith('IFF'));
                const esmSensors = point.source_sensors.filter(s => s.startsWith('ESM'));
                const elintSensors = point.source_sensors.filter(s => s.startsWith('ELINT'));
                const comintSensors = point.source_sensors.filter(s => s.startsWith('COMINT'));
                
                if (radarSensors.length > 0) sensorTypes.push({icon: '📡', name: '雷达', sensors: radarSensors});
                if (ssrSensors.length > 0) sensorTypes.push({icon: '📻', name: '二次雷达', sensors: ssrSensors});
                if (iffSensors.length > 0) sensorTypes.push({icon: '🔑', name: '敌我识别器', sensors: iffSensors});
                if (esmSensors.length > 0) sensorTypes.push({icon: '👂', name: '电子侦察', sensors: esmSensors});
                if (elintSensors.length > 0) sensorTypes.push({icon: '🔍', name: '电子情报', sensors: elintSensors});
                if (comintSensors.length > 0) sensorTypes.push({icon: '📞', name: '通信侦察', sensors: comintSensors});
                
                descHtml += `
                    <hr style="border-color: #81c784; margin: 8px 0;">
                    <h3 style="margin: 0 0 8px 0; color: #64b5f6;">📊 传感器融合详情 (${point.sensor_count}个传感器)</h3>`;
                
                if (sensorTypes.length > 0) {
                    descHtml += `<table style="width:100%;border-collapse:collapse;font-size:13px;">`;
                    sensorTypes.forEach(st => {
                        descHtml += `<tr><td style="padding:2px 6px;">${st.icon} ${st.name}</td><td style="padding:2px 6px;">${st.sensors.map(s => translateSensorId(s)).join(', ')}</td></tr>`;
                    });
                    descHtml += `</table>`;
                } else {
                    descHtml += `<p style="color:#888;font-size:12px;">本时刻无传感器覆盖</p>`;
                }
                
                if (point.squawk || point.callsign || point.icao24) {
                    descHtml += `
                        <hr style="border-color: #64b5f6; margin: 8px 0;">
                        <h3 style="margin: 0 0 8px 0; color: #ffb74d;">📻 二次雷达信息</h3>
                        <table style="width:100%;border-collapse:collapse;font-size:13px;">`;
                    if (point.squawk) descHtml += `<tr><td style="padding:2px 6px;color:#aaa;">应答码</td><td style="padding:2px 6px;">${point.squawk}</td></tr>`;
                    if (point.callsign) descHtml += `<tr><td style="padding:2px 6px;color:#aaa;">呼号</td><td style="padding:2px 6px;">${point.callsign.trim()}</td></tr>`;
                    if (point.icao24) descHtml += `<tr><td style="padding:2px 6px;color:#aaa;">航空器地址</td><td style="padding:2px 6px;">${point.icao24}</td></tr>`;
                    descHtml += `<tr><td style="padding:2px 6px;color:#aaa;">高度来源</td><td style="padding:2px 6px;">${point.altitude_source}</td></tr>`;
                    if (point.altitude_ft > 0) descHtml += `<tr><td style="padding:2px 6px;color:#aaa;">二次雷达高度</td><td style="padding:2px 6px;">${point.altitude_ft.toFixed(0)} ft</td></tr>`;
                    descHtml += `</table>`;
                }
                
                if (point.emitter_type) {
                    descHtml += `
                        <hr style="border-color: #ffb74d; margin: 8px 0;">
                        <h3 style="margin: 0 0 8px 0; color: #ef5350;">🔍 电子侦察/电子情报信息</h3>
                        <table style="width:100%;border-collapse:collapse;font-size:13px;">
                            <tr><td style="padding:2px 6px;color:#aaa;">辐射源类型</td><td style="padding:2px 6px;">${point.emitter_type}</td></tr>
                            <tr><td style="padding:2px 6px;color:#aaa;">威胁等级</td><td style="padding:2px 6px;">${'★'.repeat(point.emitter_threat_level)}${'☆'.repeat(5 - point.emitter_threat_level)}</td></tr>
                        </table>`;
                }
                
                if (point.comm_activity) {
                    descHtml += `
                        <hr style="border-color: #ce93d8; margin: 8px 0;">
                        <h3 style="margin: 0 0 8px 0; color: #ce93d8;">📞 通信侦察信息</h3>
                        <p style="font-size:13px;"><strong>通信活动:</strong> ${point.comm_activity}</p>`;
                }
            }
            
            descHtml += `</div>`;
            
            const pointColor = isComprehensive ? (IDENTITY_COLORS[point.identity] || Cesium.Color.DARKBLUE) : Cesium.Color.DARKBLUE;
            
            let pixelSize, outlineWidth, outlineColor, pointAlpha;
            if (hasSensor) {
                if (point.position_source === 'RADAR' || point.radars.length > 0) {
                    pixelSize = 8;
                    outlineWidth = 2;
                    outlineColor = Cesium.Color.WHITE;
                    pointAlpha = 1.0;
                } else {
                    pixelSize = 6;
                    outlineWidth = 1;
                    outlineColor = Cesium.Color.WHITE;
                    pointAlpha = 0.9;
                }
            } else {
                pixelSize = 4;
                outlineWidth = 0;
                outlineColor = Cesium.Color.TRANSPARENT;
                pointAlpha = 0.4;
            }
            
            layer.entities.add({
                name: `M2点迹-${trackId}-${pointIndex}`,
                position: Cesium.Cartesian3.fromDegrees(point.lon, point.lat, point.alt),
                point: {
                    pixelSize: pixelSize,
                    color: pointColor.withAlpha(pointAlpha),
                    outlineColor: outlineColor,
                    outlineWidth: outlineWidth
                },
                description: descHtml
            });
        });
        
        if (points.length > 0) {
            const firstPoint = points[0];
            const firstColor = isComprehensive ? (IDENTITY_COLORS[firstPoint.identity] || Cesium.Color.DARKBLUE) : Cesium.Color.DARKBLUE;
            const identityText = isComprehensive ? ` [${IDENTITY_LABELS[firstPoint.identity] || firstPoint.identity}]` : '';
            layer.entities.add({
                name: 'M2航迹起点-' + trackId,
                position: Cesium.Cartesian3.fromDegrees(firstPoint.lon, firstPoint.lat, firstPoint.alt),
                point: {
                    pixelSize: 10,
                    color: Cesium.Color.GREEN,
                    outlineColor: Cesium.Color.WHITE,
                    outlineWidth: 2
                },
                label: {
                    text: 'M2起点-' + trackId + identityText,
                    font: '11px sans-serif',
                    fillColor: firstColor,
                    style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                    outlineWidth: 1,
                    outlineColor: Cesium.Color.WHITE,
                    verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                    pixelOffset: new Cesium.Cartesian2(0, -12)
                }
            });
            
            const lastPoint = points[points.length - 1];
            const lastColor = isComprehensive ? (IDENTITY_COLORS[lastPoint.identity] || Cesium.Color.DARKBLUE) : Cesium.Color.DARKBLUE;
            layer.entities.add({
                name: 'M2航迹终点-' + trackId,
                position: Cesium.Cartesian3.fromDegrees(lastPoint.lon, lastPoint.lat, lastPoint.alt),
                point: {
                    pixelSize: 10,
                    color: lastColor,
                    outlineColor: Cesium.Color.WHITE,
                    outlineWidth: 2
                },
                label: {
                    text: 'M2终点-' + trackId,
                    font: '11px sans-serif',
                    fillColor: lastColor,
                    style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                    outlineWidth: 1,
                    outlineColor: Cesium.Color.WHITE,
                    verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                    pixelOffset: new Cesium.Cartesian2(0, -12)
                }
            });
        }
    });
    
    viewer.dataSources.add(layer);
    console.log('M2融合航迹加载完成，共', data.network_tracks.length, '个点, 综合模式:', isComprehensive);
}

// 文件加载处理
function handleFileSelect(event, type) {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    
    for (let f = 0; f < files.length; f++) {
        const file = files[f];
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const data = JSON.parse(e.target.result);
                
                if (data.track_points && data.target_id) {
                    if (type === 'm2') {
                        alert('您选择的是M1文件，请选择M2文件');
                        return;
                    }
                    m1DataList.push(data);
                    console.log('M1数据加载成功，目标批号:', data.target_id, '机型:', data.platform_type);
                } else if (data.network_tracks) {
                    if (type === 'm1') {
                        alert('您选择的是M2文件，请选择M1文件');
                        return;
                    }
                    m2DataList.push(data);
                    const isComp = data.network_tracks.some(t => t.identity !== undefined);
                    console.log('M2数据加载成功，观测点数量:', data.network_tracks.length, '综合模式:', isComp);
                } else {
                    alert('无法识别的文件格式，请选择M1或M2生成的JSON文件');
                    return;
                }
            } catch (error) {
                console.error('JSON解析错误:', error);
                alert('JSON文件格式错误');
            }
        };
        reader.readAsText(file);
    }
}

// 渲染态势
function renderSituation() {
    if (m1DataList.length > 0) {
        m1DataList.forEach((data, index) => {
            loadM1Track(data, null, index);
        });
    }
    
    if (m2DataList.length > 0) {
        m2DataList.forEach((data, index) => {
            loadM2Track(data, index);
        });
    }
    
    if (m1DataList.length === 0 && m2DataList.length === 0) {
        alert('请先选择M1或M2数据文件');
    }
}

// 清除航迹
function clearTracks() {
    m1TrackLayers.forEach(layer => {
        viewer.dataSources.remove(layer);
    });
    m1TrackLayers = [];
    
    m2TrackLayers.forEach(layer => {
        viewer.dataSources.remove(layer);
    });
    m2TrackLayers = [];
    
    m1DataList = [];
    m2DataList = [];
    
    console.log('航迹已清除');
}

// 图层控制
function toggleLayer(layerName, visible) {
    if (layerName === 'm1Track') {
        m1TrackLayers.forEach(layer => {
            layer.show = visible;
        });
        return;
    }
    
    if (layerName === 'm2Track') {
        m2TrackLayers.forEach(layer => {
            layer.show = visible;
        });
        return;
    }

    if (layerName === 'routeNetwork' && !layers.routeNetwork && visible) {
        loadRouteNetwork();
        return;
    }
    if (layerName === 'civilRoute' && !layers.civilRoute && visible) {
        loadCivilRoutes();
        return;
    }
    
    if (!layers[layerName]) return;
    
    if (layers[layerName] instanceof Cesium.CustomDataSource) {
        layers[layerName].show = visible;
    } else if (layers[layerName]) {
        layers[layerName].show = visible;
    }
}

function updateLayerCheckboxes() {
    const checkboxMap = {
        airport: 'layerAirport',
        waypoint: 'layerWaypoint',
        routeNetwork: 'layerRouteNetwork',
        civilRoute: 'layerCivilRoute',
        radar: 'layerRadar',
        ssr: 'layerSsr',
        iff: 'layerIff',
        esm: 'layerEsm',
        comint: 'layerComint'
    };
    
    Object.entries(checkboxMap).forEach(([layerName, checkboxId]) => {
        const cb = document.getElementById(checkboxId);
        if (cb && layers[layerName]) {
            cb.checked = layers[layerName].show;
        }
    });
}

// 初始化事件监听
function initEventListeners() {
    document.getElementById('m1File').addEventListener('change', (e) => handleFileSelect(e, 'm1'));
    document.getElementById('m2File').addEventListener('change', (e) => handleFileSelect(e, 'm2'));
    document.getElementById('renderBtn').addEventListener('click', renderSituation);
    document.getElementById('clearBtn').addEventListener('click', clearTracks);
    
    document.getElementById('layerAirport').addEventListener('change', (e) => toggleLayer('airport', e.target.checked));
    document.getElementById('layerWaypoint').addEventListener('change', (e) => toggleLayer('waypoint', e.target.checked));
    document.getElementById('layerRouteNetwork').addEventListener('change', (e) => toggleLayer('routeNetwork', e.target.checked));
    document.getElementById('layerCivilRoute').addEventListener('change', (e) => toggleLayer('civilRoute', e.target.checked));
    document.getElementById('layerRadar').addEventListener('change', (e) => toggleLayer('radar', e.target.checked));
    document.getElementById('layerSsr').addEventListener('change', (e) => toggleLayer('ssr', e.target.checked));
    document.getElementById('layerIff').addEventListener('change', (e) => toggleLayer('iff', e.target.checked));
    document.getElementById('layerEsm').addEventListener('change', (e) => toggleLayer('esm', e.target.checked));
    document.getElementById('layerComint').addEventListener('change', (e) => toggleLayer('comint', e.target.checked));
    document.getElementById('layerM1Track').addEventListener('change', (e) => toggleLayer('m1Track', e.target.checked));
    document.getElementById('layerM2Track').addEventListener('change', (e) => toggleLayer('m2Track', e.target.checked));
    
    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction(function(movement) {
        const pickedObject = viewer.scene.pick(movement.endPosition);
        if (Cesium.defined(pickedObject) && Cesium.defined(pickedObject.id)) {
            const entity = pickedObject.id;
            if (entity.name) {
                document.getElementById('infoBox').innerHTML = `<p><span class="info-label">名称:</span> <span class="info-value">${entity.name}</span></p>`;
            }
        } else {
            document.getElementById('infoBox').innerHTML = '<p>悬停图标显示名称</p>';
        }
    }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initMap();
    initEventListeners();
    console.log('M4 多维态势可视化界面初始化完成');
});