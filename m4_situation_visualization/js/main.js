// M4 多维态势可视化界面 - 主JavaScript文件

// 全局变量
let viewer = null;
let m1Data = null;
let m2Data = null;
let layers = {
    adiz: null,
    territorialSea: null,
    province: null,
    city: null,
    airport: null,
    radar: null,
    m1Track: null,
    m2Track: null
};

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
            loadRadars()
        ]);
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
    const airports = [
        { name: '上海虹桥机场', lon: 121.34, lat: 31.20 },
        { name: '上海浦东机场', lon: 121.81, lat: 31.14 },
        { name: '宁波栎社机场', lon: 121.46, lat: 29.83 },
        { name: '杭州萧山机场', lon: 120.43, lat: 30.23 },
        { name: '南京禄口机场', lon: 118.87, lat: 31.74 },
        { name: '青岛流亭机场', lon: 120.37, lat: 36.27 }
    ];
    
    layers.airport = new Cesium.CustomDataSource('airports');
    
    airports.forEach(airport => {
        layers.airport.entities.add({
            name: airport.name,
            position: Cesium.Cartesian3.fromDegrees(airport.lon, airport.lat),
            point: {
                pixelSize: 10,
                color: Cesium.Color.BLACK,
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 2
            },
            label: {
                text: airport.name,
                font: '12px sans-serif',
                fillColor: Cesium.Color.WHITE,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                outlineWidth: 1,
                outlineColor: Cesium.Color.BLACK,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -12),
                show: false
            }
        });
    });
    
    viewer.dataSources.add(layers.airport);
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

// 加载M1真值轨迹
function loadM1Track(data) {
    if (!data || !data.track_points) {
        console.error('M1数据格式错误');
        return;
    }
    
    if (layers.m1Track) {
        viewer.dataSources.remove(layers.m1Track);
    }
    
    layers.m1Track = new Cesium.CustomDataSource('m1Track');
    
    const coordsWithHeight = [];
    data.track_points.forEach(point => {
        coordsWithHeight.push(point.lon, point.lat, point.alt_m);
    });
    
    layers.m1Track.entities.add({
        name: 'M1真值轨迹',
        polyline: {
            positions: Cesium.Cartesian3.fromDegreesArrayHeights(coordsWithHeight),
            width: 4,  // 增加线宽
            material: new Cesium.PolylineGlowMaterialProperty({
                glowPower: 0.3,  // 增强发光效果
                color: Cesium.Color.RED  // 使用红色，更明显
            }),
            depthFailMaterial: new Cesium.PolylineGlowMaterialProperty({
                glowPower: 0.3,
                color: Cesium.Color.RED
            })  // 确保轨迹在地形后面时也能显示
        }
    });
    
    // 为M1轨迹添加关键轨迹点
    const pointInterval = Math.max(1, Math.floor(data.track_points.length / 50));  // 最多显示50个点
    data.track_points.forEach((point, index) => {
        if (index % pointInterval === 0) {
            layers.m1Track.entities.add({
                name: `M1轨迹点-${index}`,
                position: Cesium.Cartesian3.fromDegrees(point.lon, point.lat, point.alt_m),
                point: {
                    pixelSize: 5,
                    color: Cesium.Color.RED,
                    outlineColor: Cesium.Color.WHITE,
                    outlineWidth: 1
                },
                description: `
                    <div style="font-family: Arial, sans-serif; padding: 10px;">
                        <h3 style="margin: 0 0 10px 0; color: #4fc3f7;">M1轨迹点详细信息</h3>
                        <p><strong>目标批号:</strong> ${data.target_id}</p>
                        <p><strong>时间:</strong> ${point.time}</p>
                        <p><strong>经度:</strong> ${point.lon.toFixed(6)}°</p>
                        <p><strong>纬度:</strong> ${point.lat.toFixed(6)}°</p>
                        <p><strong>高度:</strong> ${point.alt_m.toFixed(1)} m</p>
                        <p><strong>速度:</strong> ${point.speed_ms.toFixed(1)} m/s</p>
                        <p><strong>航向:</strong> ${point.heading_deg.toFixed(1)}°</p>
                        <p><strong>飞行阶段:</strong> ${point.phase}</p>
                    </div>
                `
            });
        }
    });
    
    // 添加轨迹起点和终点标记
    if (data.track_points.length > 0) {
        // 起点
        const startPoint = data.track_points[0];
        layers.m1Track.entities.add({
            name: 'M1轨迹起点',
            position: Cesium.Cartesian3.fromDegrees(startPoint.lon, startPoint.lat, startPoint.alt_m),
            point: {
                pixelSize: 10,
                color: Cesium.Color.GREEN,
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 2
            },
            label: {
                text: '起点',
                font: '12px sans-serif',
                fillColor: Cesium.Color.GREEN,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                outlineWidth: 1,
                outlineColor: Cesium.Color.WHITE,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -12)
            }
        });
        
        // 终点
        const endPoint = data.track_points[data.track_points.length - 1];
        layers.m1Track.entities.add({
            name: 'M1轨迹终点',
            position: Cesium.Cartesian3.fromDegrees(endPoint.lon, endPoint.lat, endPoint.alt_m),
            point: {
                pixelSize: 10,
                color: Cesium.Color.RED,
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 2
            },
            label: {
                text: '终点',
                font: '12px sans-serif',
                fillColor: Cesium.Color.RED,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                outlineWidth: 1,
                outlineColor: Cesium.Color.WHITE,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -12)
            }
        });
    }
    
    viewer.dataSources.add(layers.m1Track);
    console.log('M1轨迹加载完成，共', data.track_points.length, '个点');
}

// 加载M2观测航迹（带断点重构）
function loadM2Track(data) {
    if (!data || !data.network_tracks) {
        console.error('M2数据格式错误');
        return;
    }
    
    if (layers.m2Track) {
        viewer.dataSources.remove(layers.m2Track);
    }
    
    layers.m2Track = new Cesium.CustomDataSource('m2Track');
    
    const trackMap = new Map();
    
    data.network_tracks.forEach(track => {
        const trackId = track.track_id;
        if (!trackMap.has(trackId)) {
            trackMap.set(trackId, []);
        }
        trackMap.get(trackId).push({
            time: new Date(track.time),
            lon: track.obs_lon,
            lat: track.obs_lat,
            alt: track.obs_alt_m,
            speed: track.obs_speed_ms,
            heading: track.obs_heading_deg,
            quality: track.track_quality,
            snr: track.snr_avg_db,
            radars: track.source_radars
        });
    });
    
    trackMap.forEach((points, trackId) => {
        points.sort((a, b) => a.time - b.time);
        
        const coords = [];
        let lastTime = null;
        
        points.forEach(point => {
            if (lastTime !== null) {
                const timeDiff = (point.time - lastTime) / 1000;
                if (timeDiff > 10) {
                    coords.push(null);
                }
            }
            coords.push(point.lon, point.lat);
            lastTime = point.time;
        });
        
        const color = getTrackColor(points[0]?.quality || 'LOW');
        
        console.log(`M2航迹-${trackId}，共${points.length}个点`);
        
        // 为每个观测点添加可点击的点（移除线条，只保留点）
        points.forEach((point, pointIndex) => {
            layers.m2Track.entities.add({
                name: `点迹-${trackId}-${pointIndex}`,
                position: Cesium.Cartesian3.fromDegrees(point.lon, point.lat, point.alt),
                point: {
                    pixelSize: 6,
                    color: color,
                    outlineColor: Cesium.Color.WHITE,
                    outlineWidth: 1
                },
                description: `
                    <div style="font-family: Arial, sans-serif; padding: 10px;">
                        <h3 style="margin: 0 0 10px 0; color: #4fc3f7;">点迹详细信息</h3>
                        <p><strong>航迹ID:</strong> ${trackId}</p>
                        <p><strong>时间:</strong> ${point.time.toLocaleString()}</p>
                        <p><strong>经度:</strong> ${point.lon.toFixed(6)}°</p>
                        <p><strong>纬度:</strong> ${point.lat.toFixed(6)}°</p>
                        <p><strong>高度:</strong> ${point.alt.toFixed(1)} m</p>
                        <p><strong>速度:</strong> ${point.speed.toFixed(1)} m/s</p>
                        <p><strong>航向:</strong> ${point.heading.toFixed(1)}°</p>
                        <p><strong>航迹质量:</strong> ${point.quality}</p>
                        <p><strong>SNR:</strong> ${point.snr.toFixed(1)} dB</p>
                        <p><strong>源雷达:</strong> ${point.radars.join(', ')}</p>
                    </div>
                `
            });
        });
    });
    
    viewer.dataSources.add(layers.m2Track);
    console.log('M2航迹加载完成，共', data.network_tracks.length, '个观测点');
}

// 根据航迹质量获取颜色
function getTrackColor(quality) {
    // 统一使用深蓝色，与M1红色轨迹区分
    return Cesium.Color.DARKBLUE;
}

// 文件加载处理
function handleFileSelect(event, type) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const data = JSON.parse(e.target.result);
            
            // 识别文件格式
            if (data.track_points && data.target_id) {
                // M1格式
                if (type === 'm2') {
                    alert('您选择的是M1文件，请选择M2文件');
                    return;
                }
                m1Data = data;
                console.log('M1数据加载成功，目标批号:', data.target_id);
            } else if (data.network_tracks && data.frame_time) {
                // M2格式
                if (type === 'm1') {
                    alert('您选择的是M2文件，请选择M1文件');
                    return;
                }
                m2Data = data;
                console.log('M2数据加载成功，观测点数量:', data.network_tracks.length);
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

// 渲染态势
function renderSituation() {
    if (m1Data) {
        loadM1Track(m1Data);
    }
    
    if (m2Data) {
        loadM2Track(m2Data);
    }
    
    if (!m1Data && !m2Data) {
        alert('请先选择M1或M2数据文件');
    }
}

// 清除航迹
function clearTracks() {
    if (layers.m1Track) {
        viewer.dataSources.remove(layers.m1Track);
        layers.m1Track = null;
    }
    
    if (layers.m2Track) {
        viewer.dataSources.remove(layers.m2Track);
        layers.m2Track = null;
    }
    
    m1Data = null;
    m2Data = null;
    
    console.log('航迹已清除');
}

// 图层控制
function toggleLayer(layerName, visible) {
    if (!layers[layerName]) return;
    
    if (layers[layerName] instanceof Cesium.CustomDataSource) {
        layers[layerName].show = visible;
    } else if (layers[layerName]) {
        layers[layerName].show = visible;
    }
}

// 初始化事件监听
function initEventListeners() {
    document.getElementById('m1File').addEventListener('change', (e) => handleFileSelect(e, 'm1'));
    document.getElementById('m2File').addEventListener('change', (e) => handleFileSelect(e, 'm2'));
    document.getElementById('renderBtn').addEventListener('click', renderSituation);
    document.getElementById('clearBtn').addEventListener('click', clearTracks);
    
    document.getElementById('adizLayer').addEventListener('change', (e) => toggleLayer('adiz', e.target.checked));
    document.getElementById('territorialSeaLayer').addEventListener('change', (e) => toggleLayer('territorialSea', e.target.checked));
    document.getElementById('provinceLayer').addEventListener('change', (e) => toggleLayer('province', e.target.checked));
    document.getElementById('cityLayer').addEventListener('change', (e) => toggleLayer('city', e.target.checked));
    document.getElementById('airportLayer').addEventListener('change', (e) => toggleLayer('airport', e.target.checked));
    document.getElementById('radarLayer').addEventListener('change', (e) => toggleLayer('radar', e.target.checked));
    document.getElementById('m1TrackLayer').addEventListener('change', (e) => toggleLayer('m1Track', e.target.checked));
    document.getElementById('m2TrackLayer').addEventListener('change', (e) => toggleLayer('m2Track', e.target.checked));
    
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