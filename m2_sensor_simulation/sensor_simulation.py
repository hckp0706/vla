import os
import json
import math
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor
import numpy as np
try:
    from filterpy.kalman import KalmanFilter
except ImportError:
    KalmanFilter = None

from .models import RadarConfig, TargetTruth, TrackPoint, NetworkTracks
from .radar import Radar
from .models_ext import (
    SSRConfig, SSRReply, IFFConfig, IFFReply,
    ESMConfig, EmitterParameters, PDWRecord,
    ELINTConfig, ELINTReport, COMINTConfig, CommEmitter, COMINTReport,
    FusedTrackPoint, FusedNetworkTracks
)
from .ssr import SSR
from .iff import IFF
from .esm import ESM
from .elint import ELINT
from .comint import COMINT
from .fusion import FusionEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output', 'm2_tracks')


class SensorSimulation:
    """传感器仿真引擎
    
    功能：
    1. 管理多部雷达
    2. 处理M1输入的目标真值
    3. 并行计算各雷达的观测
    4. 生成系统级组网观测航迹
    """
    
    def __init__(self):
        """初始化传感器仿真引擎"""
        self.radars = self._init_radar_network()
        self.track_pool: Dict[str, dict] = {}  # 系统级航迹池
        self.executor = ThreadPoolExecutor(max_workers=5)
        self._current_platform_type = ""
        self._current_target_id = ""
    
    def _init_radar_network(self) -> List[Radar]:
        """初始化雷达网络
        
        返回：
            雷达列表
        """
        config_file = os.path.join(os.path.dirname(__file__), 'radar_config.json')
        
        if os.path.exists(config_file):
            logger.info(f"从配置文件加载雷达参数: {config_file}")
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            radar_configs = []
            for radar_data in config_data.get('radars', []):
                config = RadarConfig(
                    radar_id=radar_data['radar_id'],
                    location=radar_data['location'],
                    height=radar_data['height'],
                    max_range=radar_data['max_range'],
                    beam_width=radar_data['beam_width'],
                    scan_period=radar_data['scan_period'],
                    tactical_role=radar_data['tactical_role']
                )
                radar_configs.append(config)
        else:
            logger.warning(f"雷达配置文件不存在: {config_file}，使用默认配置")
            radar_configs = [
                RadarConfig(
                    radar_id="RADAR_01",
                    location=[120.38, 36.07],
                    height=100,
                    max_range=500,
                    beam_width=4.5,
                    scan_period=10,
                    tactical_role="远程对空警戒"
                ),
                RadarConfig(
                    radar_id="RADAR_02",
                    location=[121.47, 31.23],
                    height=50,
                    max_range=400,
                    beam_width=2.0,
                    scan_period=6,
                    tactical_role="精密引导测高三坐标雷达"
                ),
                RadarConfig(
                    radar_id="RADAR_03",
                    location=[121.54, 29.86],
                    height=30,
                    max_range=350,
                    beam_width=1.5,
                    scan_period=4,
                    tactical_role="近海低空补盲快扫雷达"
                ),
                RadarConfig(
                    radar_id="RADAR_04",
                    location=[118.78, 32.06],
                    height=80,
                    max_range=450,
                    beam_width=3.0,
                    scan_period=8,
                    tactical_role="内陆纵深节点"
                ),
                RadarConfig(
                    radar_id="RADAR_05",
                    location=[117.27, 31.86],
                    height=50,
                    max_range=400,
                    beam_width=2.0,
                    scan_period=6,
                    tactical_role="二线拦截引导雷达"
                )
            ]
        
        return [Radar(config) for config in radar_configs]
    
    def load_truth_data(self, truth_file: str) -> List[TargetTruth]:
        """加载真值数据
        
        参数：
            truth_file: 真值文件路径
            
        返回：
            目标真值列表（包含所有轨迹点）
        """
        with open(truth_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        targets = []
        track_points = data.get('track_points', [])
        
        for point in track_points:
            target = TargetTruth(
                target_id=data.get('target_id', ''),
                time=datetime.fromisoformat(point.get('time', '').replace('Z', '+00:00')),
                lon=point.get('lon', 0.0),
                lat=point.get('lat', 0.0),
                alt_m=point.get('alt_m', 0.0),
                speed_ms=point.get('speed_ms', 0.0),
                heading_deg=point.get('heading_deg', 0.0),
                rcs_dbsm=point.get('rcs_dbsm', 0.0)
            )
            targets.append(target)
        
        return targets
    
    def process_radar(self, radar: Radar, targets: List[TargetTruth], current_time: datetime) -> Dict[str, dict]:
        """处理单个雷达的观测
        
        参数：
            radar: 雷达对象
            targets: 目标真值列表
            current_time: 当前时间
            
        返回：
            雷达观测结果
        """
        radar.update_scan_angle(current_time)
        observations = {}
        
        print(f"\n=== 处理雷达: {radar.config.radar_id} ===")
        print(f"当前波束指向: {radar.current_scan_angle:.2f}度")
        
        for target in targets:
            print(f"\n处理目标: {target.target_id}")
            print(f"目标位置: 经度={target.lon:.4f}, 纬度={target.lat:.4f}, 高度={target.alt_m:.0f}m")
            
            # 第一关：视距判定
            los = radar.calculate_line_of_sight(target.alt_m)
            r = radar.calculate_range(target.lon, target.lat, target.alt_m)
            print(f"距离雷达: {r:.2f} km, 视距: {los:.2f} km, 最大探测距离: {radar.config.max_range} km")
            if r > los or r > radar.config.max_range:
                print(f"❌ 超出视距或最大探测距离")
                continue
            
            # 第二关：波束驻留判定 - 强制波束指向目标
            azimuth = radar.calculate_azimuth(target.lon, target.lat)
            # 强制波束指向目标，用于测试
            radar.current_scan_angle = azimuth
            angle_diff = 0.0
            print(f"目标方位角: {azimuth:.2f}度, 波束指向: {radar.current_scan_angle:.2f}度, 角度差: {angle_diff:.2f}度, 波束宽度: {radar.config.beam_width}度")
            # 跳过波束驻留判定，直接通过
            
            # 第三关：SNR计算
            snr = radar.calculate_snr(target)
            print(f"基础SNR: {snr:.2f} dB")
            
            # 第四关：杂波抑制和CFAR检测
            radial_velocity = radar.calculate_radial_velocity(target)
            snr_actual = radar.apply_clutter_suppression(snr, radial_velocity)
            print(f"径向速度: {radial_velocity:.2f} m/s, 实际SNR: {snr_actual:.2f} dB")
            if not radar.cfar_detection(snr_actual):
                print(f"❌ 未通过CFAR检测")
                continue
            
            # 第五关：测量误差注入
            # 使用雷达的测量误差模型，从球坐标系转换到地理坐标系
            obs_lon, obs_lat, obs_alt = radar.measure_target(target)
            
            # 速度和航向的测量误差（简化模型）
            speed_error = np.random.normal(0, 5.0)  # 速度误差约5米/秒
            heading_error = np.random.normal(0, 1.0)  # 航向误差约1度
            obs_speed = target.speed_ms + speed_error
            obs_heading = (target.heading_deg + heading_error) % 360
            
            observations[target.target_id] = {
                'radar_id': radar.config.radar_id,
                'snr': snr_actual,
                'obs_lon': obs_lon,
                'obs_lat': obs_lat,
                'obs_alt': obs_alt,
                'obs_speed': obs_speed,
                'obs_heading': obs_heading
            }
            print(f"✅ 成功观测到目标")
            print(f"   测量位置: 经度={obs_lon:.4f}, 纬度={obs_lat:.4f}, 高度={obs_alt:.0f}m")
            print(f"   位置误差: Δlon={abs(obs_lon-target.lon)*111320:.1f}m, Δlat={abs(obs_lat-target.lat)*111000:.1f}m, Δalt={abs(obs_alt-target.alt_m):.1f}m")
        
        print(f"\n=== 雷达 {radar.config.radar_id} 观测结果: {len(observations)} 个目标 ===")
        return observations
    
    def run_simulation(self, truth_file: str) -> Dict[str, NetworkTracks]:
        """运行仿真
        
        参数：
            truth_file: 真值文件路径
            
        返回：
            字典，包含单雷达航迹和融合航迹
        """
        logger.info(f"开始处理真值文件: {truth_file}")
        
        # 加载真值数据
        targets = self.load_truth_data(truth_file)
        if not targets:
            logger.error("未加载到目标数据")
            return {}
        
        # 按照时间排序
        targets.sort(key=lambda t: t.time)
        
        logger.info(f"加载了 {len(targets)} 个轨迹点")
        
        # 收集所有雷达的观测结果，按雷达分组
        radar_observations = {}
        
        # 对于每个雷达，按照其扫描周期进行采样
        for radar in self.radars:
            logger.info(f"处理雷达 {radar.config.radar_id}，扫描周期: {radar.config.scan_period}秒")
            
            # 按照雷达扫描周期采样
            sampled_targets = self._sample_by_scan_period(targets, radar.config.scan_period)
            logger.info(f"雷达 {radar.config.radar_id} 采样了 {len(sampled_targets)} 个点")
            
            # 对每个采样点进行雷达观测仿真
            radar_obs = []
            for target in sampled_targets:
                obs = self._process_single_target(radar, target)
                if obs:
                    radar_obs.append(obs)
            
            if radar_obs:
                radar_observations[radar.config.radar_id] = radar_obs
                logger.info(f"雷达 {radar.config.radar_id} 观测到 {len(radar_obs)} 个点")
        
        # 生成单雷达航迹
        result = {}
        target_id = targets[0].target_id if targets else "0000"
        
        for radar_id, observations in radar_observations.items():
            # 提取雷达编号
            radar_num = radar_id.split('_')[1]
            track_id = f"{target_id}_{radar_num}"
            
            # 创建航迹点
            track_points = []
            for obs in observations:
                track_point = TrackPoint(
                    time=obs['time'],
                    track_id=track_id,
                    target_id=obs['target_id'],
                    source_radars=[obs['radar_id']],
                    obs_lon=obs['obs_lon'],
                    obs_lat=obs['obs_lat'],
                    obs_alt_m=obs['obs_alt'],
                    obs_speed_ms=obs['obs_speed'],
                    obs_heading_deg=obs['obs_heading'],
                    track_quality="LOW",
                    snr_avg_db=obs['snr']
                )
                track_points.append(track_point)
            
            # 创建单雷达航迹
            result[radar_id] = NetworkTracks(
                frame_time=datetime.now().isoformat() + 'Z',
                network_tracks=track_points
            )
        
        # 生成融合航迹
        all_observations = []
        for observations in radar_observations.values():
            all_observations.extend(observations)
        
        # 按时间排序所有观测
        all_observations.sort(key=lambda x: x['time'])
        
        # 打印观测时间分布（前10个）
        if all_observations:
            logger.info("前10个观测时间点:")
            for i, obs in enumerate(all_observations[:10]):
                logger.info(f"  {i+1}. 时间: {obs['time']}, 雷达: {obs['radar_id']}")
        
        # 使用滑动时间窗口进行融合
        fused_track_points = []
        i = 0
        n = len(all_observations)
        
        while i < n:
            current_time = all_observations[i]['time']
            window_start = current_time - timedelta(seconds=5)
            window_end = current_time + timedelta(seconds=5)
            
            # 收集时间窗口内的所有观测
            window_observations = []
            j = i
            while j < n and window_start <= all_observations[j]['time'] <= window_end:
                window_observations.append(all_observations[j])
                j += 1
            
            if window_observations:
                # 打印窗口内的观测
                if len(window_observations) > 1:
                    logger.info(f"时间窗口 {current_time} 内有 {len(window_observations)} 个观测:")
                    for obs in window_observations:
                        logger.info(f"  雷达: {obs['radar_id']}, 时间: {obs['time']}")
                
                # 融合多个雷达的观测
                total_snr = sum(obs['snr'] for obs in window_observations)
                if total_snr == 0:
                    total_snr = 1  # 避免除零
                
                weighted_lon = sum(obs['obs_lon'] * obs['snr'] for obs in window_observations) / total_snr
                weighted_lat = sum(obs['obs_lat'] * obs['snr'] for obs in window_observations) / total_snr
                weighted_alt = sum(obs['obs_alt'] * obs['snr'] for obs in window_observations) / total_snr
                weighted_speed = sum(obs['obs_speed'] * obs['snr'] for obs in window_observations) / total_snr
                weighted_heading = sum(obs['obs_heading'] * obs['snr'] for obs in window_observations) / total_snr
                
                # 收集所有雷达源
                source_radars = list(set(obs['radar_id'] for obs in window_observations))
                avg_snr = total_snr / len(window_observations)
                
                # 确定航迹质量
                track_quality = "LOW"
                if len(source_radars) >= 3:
                    track_quality = "HIGH"
                elif len(source_radars) >= 2:
                    track_quality = "MEDIUM"
                
                # 创建融合航迹点
                track_point = TrackPoint(
                    time=current_time,
                    track_id=target_id,
                    target_id=window_observations[0]['target_id'],
                    source_radars=source_radars,
                    obs_lon=weighted_lon,
                    obs_lat=weighted_lat,
                    obs_alt_m=weighted_alt,
                    obs_speed_ms=weighted_speed,
                    obs_heading_deg=weighted_heading,
                    track_quality=track_quality,
                    snr_avg_db=avg_snr
                )
                fused_track_points.append(track_point)
                
                i = j
            else:
                # 没有观测，移动到下一个点
                i += 1
        
        # 创建融合航迹
        result['fused'] = NetworkTracks(
            frame_time=datetime.now().isoformat() + 'Z',
            network_tracks=fused_track_points
        )
        
        logger.info(f"仿真完成，生成 {len(result)} 个航迹文件")
        return result
    
    def _sample_by_scan_period(self, targets: List[TargetTruth], scan_period: float) -> List[TargetTruth]:
        """按照雷达扫描周期采样轨迹点
        
        参数：
            targets: 目标真值列表
            scan_period: 雷达扫描周期（秒）
            
        返回：
            采样后的目标真值列表
        """
        if not targets:
            return []
        
        sampled = []
        last_time = None
        
        for target in targets:
            if last_time is None:
                sampled.append(target)
                last_time = target.time
            else:
                time_diff = (target.time - last_time).total_seconds()
                if time_diff >= scan_period:
                    sampled.append(target)
                    last_time = target.time
        
        return sampled
    
    def _process_single_target(self, radar: Radar, target: TargetTruth) -> Optional[dict]:
        """处理单个目标的雷达观测
        
        参数：
            radar: 雷达对象
            target: 目标真值
            
        返回：
            观测结果字典，如果未观测到则返回None
        """
        # 第一关：视距判定
        los = radar.calculate_line_of_sight(target.alt_m)
        r = radar.calculate_range(target.lon, target.lat, target.alt_m)
        
        # 调试日志：输出距离和视距
        if target.time.minute == 30 and target.time.second == 0:
            logger.info(f"雷达 {radar.config.radar_id}，目标位置: ({target.lon:.2f}, {target.lat:.2f})，高度: {target.alt_m:.0f}m，距离: {r:.1f}km，视距: {los:.1f}km，最大探测距离: {radar.config.max_range}km")
        
        if r > los or r > radar.config.max_range:
            return None
        
        # 第二关：波束驻留判定 - 强制波束指向目标
        azimuth = radar.calculate_azimuth(target.lon, target.lat)
        radar.current_scan_angle = azimuth
        
        # 第三关：SNR计算
        snr = radar.calculate_snr(target)
        
        # 第四关：杂波抑制和CFAR检测
        radial_velocity = radar.calculate_radial_velocity(target)
        snr_actual = radar.apply_clutter_suppression(snr, radial_velocity)
        
        # 调试日志：输出SNR
        if target.time.minute == 30 and target.time.second == 0:
            logger.info(f"雷达 {radar.config.radar_id}，SNR: {snr:.1f}dB，实际SNR: {snr_actual:.1f}dB，径向速度: {radial_velocity:.1f}m/s")
        
        if not radar.cfar_detection(snr_actual):
            return None
        
        # 第五关：量测噪声注入
        noise_std = 10.0 / max(0.1, snr_actual / 10)
        noise_std = max(0.1, noise_std)
        
        obs_lon = target.lon + np.random.normal(0, noise_std / 111320)
        obs_lat = target.lat + np.random.normal(0, noise_std / 111000)
        obs_alt = target.alt_m + np.random.normal(0, noise_std * 0.1)
        obs_speed = target.speed_ms + np.random.normal(0, noise_std * 0.01)
        obs_heading = (target.heading_deg + np.random.normal(0, noise_std * 0.1)) % 360
        
        logger.info(f"雷达 {radar.config.radar_id} 观测到目标 {target.target_id}，时间: {target.time}，位置: ({obs_lon:.2f}, {obs_lat:.2f})")
        
        return {
            'time': target.time,
            'target_id': target.target_id,
            'radar_id': radar.config.radar_id,
            'snr': snr_actual,
            'obs_lon': obs_lon,
            'obs_lat': obs_lat,
            'obs_alt': obs_alt,
            'obs_speed': obs_speed,
            'obs_heading': obs_heading
        }
    
    def _update_track_pool(self, current_tracks: List[TrackPoint]) -> None:
        """更新航迹池
        
        参数：
            current_tracks: 当前帧的航迹
        """
        current_track_ids = {track.track_id for track in current_tracks}
        
        # 更新现有航迹
        for track_id in list(self.track_pool.keys()):
            if track_id in current_track_ids:
                # 航迹继续存在
                self.track_pool[track_id]['miss_count'] = 0
            else:
                # 航迹漏检
                self.track_pool[track_id]['miss_count'] += 1
                if self.track_pool[track_id]['miss_count'] >= 3:
                    # 连续3个周期漏检，删除航迹
                    del self.track_pool[track_id]
        
        # 添加新航迹
        for track in current_tracks:
            if track.track_id not in self.track_pool:
                self.track_pool[track.track_id] = {
                    'miss_count': 0
                }
    
    def save_output(self, output: Dict[str, NetworkTracks], custom_output: str = None) -> str:
        """保存输出
        
        参数：
            output: 字典，包含单雷达航迹和融合航迹
            custom_output: 自定义输出路径
            
        返回：
            输出文件夹路径
        """
        if not output:
            logger.error("没有输出数据")
            return ""
        
        # 创建输出文件夹
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        if custom_output:
            output_dir = custom_output
        else:
            output_dir = os.path.join(OUTPUT_DIR, f"tracks_{now}")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 保存各个航迹文件
        for key, tracks in output.items():
            if key == 'fused':
                filename = "fused_tracks.json"
            else:
                # 提取雷达编号
                radar_num = key.split('_')[1]
                filename = f"radar_{radar_num}_tracks.json"
            
            output_path = os.path.join(output_dir, filename)
            tracks.save_to_file(output_path)
            logger.info(f"保存航迹文件: {output_path}")
        
        logger.info(f"输出已保存到文件夹: {output_dir}")
        return output_dir

    def load_sensor_config(self) -> Dict:
        config_file = os.path.join(os.path.dirname(__file__), 'sensor_config.json')
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        logger.warning(f"传感器配置文件不存在: {config_file}")
        return {}

    def _load_platform_type(self, truth_file: str) -> str:
        try:
            with open(truth_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('platform_type', '')
        except Exception:
            return ''

    def _load_flight_phases(self, truth_file: str) -> Dict[str, str]:
        phase_map = {}
        try:
            with open(truth_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for point in data.get('track_points', []):
                t = point.get('time', '')
                phase = point.get('phase', '')
                if t and phase:
                    phase_map[t] = phase
        except Exception:
            pass
        return phase_map

    def _get_airborne_radar_template(self, sensor_config: Dict,
                                      target_identities: Dict[str, str]) -> Optional[EmitterParameters]:
        airborne_config = sensor_config.get("airborne_emitters", {})
        if not airborne_config or not self._current_platform_type:
            return None

        target_id = self._current_target_id or ""
        identity = target_identities.get(target_id, "UNKNOWN")
        if identity != "FOE":
            return None

        platform_data = airborne_config.get(self._current_platform_type)
        if not platform_data:
            return None

        radar_cfg = platform_data.get("radar")
        if not radar_cfg:
            return None

        return EmitterParameters(
            emitter_id=radar_cfg["emitter_id"],
            location=[0, 0],
            height=0,
            frequency_ghz=radar_cfg["frequency_ghz"],
            pri_us=radar_cfg["pri_us"],
            pw_us=radar_cfg["pw_us"],
            power_dbm=radar_cfg["power_dbm"],
            antenna_gain_db=radar_cfg["antenna_gain_db"],
            scan_period=radar_cfg["scan_period"],
            radar_type=radar_cfg["radar_type"],
            modulation=radar_cfg["modulation"],
            threat_level=radar_cfg["threat_level"],
            side="FOE",
            active=True
        )

    def _get_airborne_comm_template(self, sensor_config: Dict,
                                     target_identities: Dict[str, str]) -> Optional[CommEmitter]:
        airborne_config = sensor_config.get("airborne_emitters", {})
        if not airborne_config or not self._current_platform_type:
            return None

        target_id = self._current_target_id or ""
        identity = target_identities.get(target_id, "UNKNOWN")
        if identity != "FOE":
            return None

        platform_data = airborne_config.get(self._current_platform_type)
        if not platform_data:
            return None

        comm_cfg = platform_data.get("comm")
        if not comm_cfg:
            return None

        return CommEmitter(
            emitter_id=comm_cfg["emitter_id"],
            location=[0, 0],
            height=0,
            frequency_mhz=comm_cfg["frequency_mhz"],
            power_dbm=comm_cfg["power_dbm"],
            comm_type=comm_cfg["comm_type"],
            network_id=comm_cfg["network_id"],
            side="FOE",
            active=True
        )

    def load_emitter_database(self) -> Tuple[List[EmitterParameters], List[CommEmitter]]:
        db_file = os.path.join(os.path.dirname(__file__), 'emitter_database.json')
        radar_emitters = []
        comm_emitters = []
        if os.path.exists(db_file):
            with open(db_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for rd in data.get('radar_emitters', []):
                radar_emitters.append(EmitterParameters(
                    emitter_id=rd['emitter_id'],
                    location=rd['location'],
                    height=rd['height'],
                    frequency_ghz=rd['frequency_ghz'],
                    pri_us=rd['pri_us'],
                    pw_us=rd['pw_us'],
                    power_dbm=rd['power_dbm'],
                    antenna_gain_db=rd['antenna_gain_db'],
                    scan_period=rd['scan_period'],
                    radar_type=rd['radar_type'],
                    modulation=rd['modulation'],
                    threat_level=rd['threat_level'],
                    side=rd['side'],
                    active=rd.get('active', True)
                ))
            for cd in data.get('comm_emitters', []):
                comm_emitters.append(CommEmitter(
                    emitter_id=cd['emitter_id'],
                    location=cd['location'],
                    height=cd['height'],
                    frequency_mhz=cd['frequency_mhz'],
                    power_dbm=cd['power_dbm'],
                    comm_type=cd['comm_type'],
                    network_id=cd['network_id'],
                    side=cd['side'],
                    active=cd.get('active', True)
                ))
        else:
            logger.warning(f"辐射源数据库不存在: {db_file}")
        return radar_emitters, comm_emitters

    def _load_adsb_map(self, truth_file: str) -> Dict[str, List[Dict]]:
        adsb_map: Dict[str, List[Dict]] = {}
        try:
            with open(truth_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            has_adsb = data.get('has_adsb', False)
            if not has_adsb:
                return adsb_map
            target_id = data.get('target_id', '')
            track_points = data.get('track_points', [])
            for point in track_points:
                adsb = point.get('adsb')
                if adsb:
                    if target_id not in adsb_map:
                        adsb_map[target_id] = []
                    t = point.get('time', '')
                    try:
                        adsb_time = datetime.fromisoformat(t.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        adsb_time = None
                    adsb_map[target_id].append({
                        "time": adsb_time,
                        "squawk": adsb.get("squawk", "2000"),
                        "altitude_ft": adsb.get("altitude_ft", 0.0),
                        "icao24": adsb.get("icao24", ""),
                        "callsign": adsb.get("callsign", "")
                    })
        except Exception as e:
            logger.warning(f"加载ADS-B数据失败: {e}")
        return adsb_map

    def run_comprehensive_simulation(self, truth_file: str,
                                     sensors: List[str] = None) -> Dict:
        logger.info(f"开始综合传感器仿真: {truth_file}")

        targets = self.load_truth_data(truth_file)
        if not targets:
            logger.error("未加载到目标数据")
            return {}

        targets.sort(key=lambda t: t.time)
        logger.info(f"加载了 {len(targets)} 个轨迹点")

        if sensors is None:
            sensors = ["radar", "ssr", "iff", "esm", "elint", "comint"]

        sensor_config = self.load_sensor_config()
        emitter_db, comm_db = self.load_emitter_database()
        target_identities = sensor_config.get("target_identities", {})
        adsb_map = self._load_adsb_map(truth_file)

        self._current_platform_type = self._load_platform_type(truth_file)
        self._current_target_id = targets[0].target_id if targets else ""

        radar_result = self.run_simulation(truth_file)

        radar_obs_by_time: Dict[datetime, List[dict]] = {}
        for radar in self.radars:
            sampled = self._sample_by_scan_period(targets, radar.config.scan_period)
            for target in sampled:
                obs = self._process_single_target(radar, target)
                if obs:
                    t = obs['time']
                    if t not in radar_obs_by_time:
                        radar_obs_by_time[t] = []
                    radar_obs_by_time[t].append(obs)

        all_ssr_replies: List[SSRReply] = []
        all_iff_replies: List[IFFReply] = []
        all_esm_pdws: List[PDWRecord] = []
        all_elint_reports: List[ELINTReport] = []
        all_comint_reports: List[COMINTReport] = []

        if "ssr" in sensors and "ssr_stations" in sensor_config:
            for sc in sensor_config["ssr_stations"]:
                config = SSRConfig(
                    ssr_id=sc["ssr_id"], location=sc["location"], height=sc["height"],
                    max_range_km=sc["max_range_km"], modes=sc["modes"],
                    scan_period=sc["scan_period"], reply_probability=sc["reply_probability"],
                    fruit_rate=sc["fruit_rate"], co_located_radar=sc.get("co_located_radar")
                )
                ssr = SSR(config)
                replies = ssr.process_targets(targets, adsb_map, target_identities)
                all_ssr_replies.extend(replies)

        if "iff" in sensors and "iff_stations" in sensor_config:
            for ic in sensor_config["iff_stations"]:
                config = IFFConfig(
                    iff_id=ic["iff_id"], location=ic["location"], height=ic["height"],
                    max_range_km=ic["max_range_km"], modes=ic["modes"],
                    scan_period=ic["scan_period"], crypto_valid=ic["crypto_valid"],
                    co_located_radar=ic.get("co_located_radar")
                )
                iff = IFF(config)
                replies = iff.process_targets(targets, target_identities)
                all_iff_replies.extend(replies)

        if "esm" in sensors and "esm_stations" in sensor_config:
            time_points = [t.time for t in targets]
            for ec in sensor_config["esm_stations"]:
                config = ESMConfig(
                    esm_id=ec["esm_id"], location=ec["location"], height=ec["height"],
                    frequency_range_ghz=ec["frequency_range_ghz"],
                    sensitivity_dbm=ec["sensitivity_dbm"], df_accuracy_deg=ec["df_accuracy_deg"],
                    freq_accuracy_mhz=ec["freq_accuracy_mhz"], pri_accuracy_us=ec["pri_accuracy_us"],
                    pw_accuracy_us=ec["pw_accuracy_us"], scan_period=ec["scan_period"]
                )
                esm = ESM(config)
                pdws = esm.process_emitters(emitter_db, time_points)
                all_esm_pdws.extend(pdws)

            airborne_radar_template = self._get_airborne_radar_template(
                sensor_config, target_identities
            )
            if airborne_radar_template:
                for ec in sensor_config["esm_stations"]:
                    config = ESMConfig(
                        esm_id=ec["esm_id"], location=ec["location"], height=ec["height"],
                        frequency_range_ghz=ec["frequency_range_ghz"],
                        sensitivity_dbm=ec["sensitivity_dbm"], df_accuracy_deg=ec["df_accuracy_deg"],
                        freq_accuracy_mhz=ec["freq_accuracy_mhz"], pri_accuracy_us=ec["pri_accuracy_us"],
                        pw_accuracy_us=ec["pw_accuracy_us"], scan_period=ec["scan_period"]
                    )
                    esm = ESM(config)
                    pdws = esm.process_airborne_emitter(airborne_radar_template, targets)
                    all_esm_pdws.extend(pdws)

        if "elint" in sensors and "elint_config" in sensor_config:
            ec = sensor_config["elint_config"]
            config = ELINTConfig(
                elint_id=ec["elint_id"], min_stations_for_fix=ec["min_stations_for_fix"],
                matching_threshold=ec["matching_threshold"], analysis_period=ec["analysis_period"]
            )
            elint = ELINT(config, emitter_db)

            pdw_by_emitter: Dict[str, List[PDWRecord]] = {}
            for pdw in all_esm_pdws:
                if pdw.emitter_id not in pdw_by_emitter:
                    pdw_by_emitter[pdw.emitter_id] = []
                pdw_by_emitter[pdw.emitter_id].append(pdw)

            esm_locations: Dict[str, Tuple[float, float]] = {}
            for ec_data in sensor_config.get("esm_stations", []):
                esm_locations[ec_data["esm_id"]] = (ec_data["location"][0], ec_data["location"][1])

            last_time = targets[-1].time if targets else datetime.now()
            reports = elint.analyze(pdw_by_emitter, esm_locations, last_time)
            all_elint_reports.extend(reports)

        if "comint" in sensors and "comint_stations" in sensor_config:
            time_points = [t.time for t in targets]
            for cc in sensor_config["comint_stations"]:
                config = COMINTConfig(
                    comint_id=cc["comint_id"], location=cc["location"], height=cc["height"],
                    frequency_ranges_mhz=cc["frequency_ranges_mhz"],
                    sensitivity_dbm=cc["sensitivity_dbm"], df_accuracy_deg=cc["df_accuracy_deg"],
                    scan_period=cc["scan_period"]
                )
                comint = COMINT(config)
                reports = comint.process_emitters(comm_db, time_points)
                all_comint_reports.extend(reports)

            airborne_comm_template = self._get_airborne_comm_template(
                sensor_config, target_identities
            )
            if airborne_comm_template:
                for cc in sensor_config["comint_stations"]:
                    config = COMINTConfig(
                        comint_id=cc["comint_id"], location=cc["location"], height=cc["height"],
                        frequency_ranges_mhz=cc["frequency_ranges_mhz"],
                        sensitivity_dbm=cc["sensitivity_dbm"], df_accuracy_deg=cc["df_accuracy_deg"],
                        scan_period=cc["scan_period"]
                    )
                    comint = COMINT(config)
                    reports = comint.process_airborne_emitter(airborne_comm_template, targets)
                    all_comint_reports.extend(reports)

        ssr_by_time: Dict[datetime, List[SSRReply]] = {}
        for r in all_ssr_replies:
            t = r.time
            if t not in ssr_by_time:
                ssr_by_time[t] = []
            ssr_by_time[t].append(r)

        iff_by_time: Dict[datetime, List[IFFReply]] = {}
        for r in all_iff_replies:
            t = r.time
            if t not in iff_by_time:
                iff_by_time[t] = []
            iff_by_time[t].append(r)

        esm_by_time: Dict[datetime, List[PDWRecord]] = {}
        for p in all_esm_pdws:
            t = p.time
            if t not in esm_by_time:
                esm_by_time[t] = []
            esm_by_time[t].append(p)

        elint_by_time: Dict[datetime, List[ELINTReport]] = {}
        for r in all_elint_reports:
            t = r.time
            if t not in elint_by_time:
                elint_by_time[t] = []
            elint_by_time[t].append(r)

        comint_by_time: Dict[datetime, List[COMINTReport]] = {}
        for r in all_comint_reports:
            t = r.time
            if t not in comint_by_time:
                comint_by_time[t] = []
            comint_by_time[t].append(r)

        fusion_engine = FusionEngine()

        sampled_targets = self._sample_by_scan_period(targets, 6.0)
        logger.info(f"综合融合采样: {len(targets)} -> {len(sampled_targets)} 个时间点")

        comprehensive_tracks = fusion_engine.fuse_comprehensive(
            sampled_targets, radar_obs_by_time,
            ssr_by_time, iff_by_time,
            esm_by_time, elint_by_time, comint_by_time
        )

        result = dict(radar_result)
        result['ssr_replies'] = all_ssr_replies
        result['iff_replies'] = all_iff_replies
        result['esm_pdws'] = all_esm_pdws
        result['elint_reports'] = all_elint_reports
        result['comint_reports'] = all_comint_reports
        result['fused_comprehensive'] = comprehensive_tracks

        logger.info(f"综合仿真完成: SSR={len(all_ssr_replies)}, IFF={len(all_iff_replies)}, "
                     f"ESM={len(all_esm_pdws)}, ELINT={len(all_elint_reports)}, "
                     f"COMINT={len(all_comint_reports)}, "
                     f"综合融合航迹={len(comprehensive_tracks.network_tracks)}")

        return result

    def save_comprehensive_output(self, output: Dict, custom_output: str = None) -> str:
        if not output:
            logger.error("没有输出数据")
            return ""

        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        if custom_output:
            output_dir = custom_output
        else:
            output_dir = os.path.join(OUTPUT_DIR, f"comprehensive_{now}")

        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        for key, value in output.items():
            if key in ('ssr_replies', 'iff_replies', 'esm_pdws', 'elint_reports', 'comint_reports'):
                data_list = value
                if not data_list:
                    continue
                output_path = os.path.join(output_dir, f"{key}.json")
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump([item.to_dict() for item in data_list], f, ensure_ascii=False, indent=2)
                logger.info(f"保存文件: {output_path}")
            elif key == 'fused_comprehensive':
                output_path = os.path.join(output_dir, "fused_comprehensive.json")
                value.save_to_file(output_path)
                logger.info(f"保存综合融合航迹: {output_path}")
            elif isinstance(value, NetworkTracks):
                if key == 'fused':
                    filename = "fused_tracks.json"
                else:
                    radar_num = key.split('_')[1]
                    filename = f"radar_{radar_num}_tracks.json"
                output_path = os.path.join(output_dir, filename)
                value.save_to_file(output_path)
                logger.info(f"保存航迹文件: {output_path}")

        logger.info(f"综合仿真输出已保存到: {output_dir}")
        return output_dir
