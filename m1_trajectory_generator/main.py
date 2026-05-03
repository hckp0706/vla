import argparse
import json
import logging
import os
from datetime import datetime

from .trajectory_generator import TrajectoryGenerator
from .knowledge_base import KnowledgeBase
from .parser import IntentParser
from .models import MissionType
from .config import Config

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output', 'm1_trajectories')


def get_output_filename(trajectory, custom_output: str = None) -> str:
    if custom_output:
        output_dir = os.path.dirname(custom_output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        return custom_output
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    target_id = trajectory.target_id if trajectory else 'unknown'
    filename = f"trajectory_{target_id}_{now}.json"
    
    return os.path.join(OUTPUT_DIR, filename)


def main():
    parser = argparse.ArgumentParser(
        description='M1: 意图驱动航迹生成器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法:
  python -m m1_trajectory_generator -i "0001 民航客机 客运航班 于 2026-04-20 09:20:30 从 北京大兴国际机场 起飞，降落 上海虹桥国际机场。"
  python -m m1_trajectory_generator -i "0002 歼-20 低空突防 于 2026-04-20 10:00:00 从 华北基地 起飞，降落 东南沿海。"
  python -m m1_trajectory_generator -i "0003 民航客机 客运航班 于 2026-04-20 09:00:00 从 北京大兴国际机场 起飞，途径 青岛胶东国际机场，降落 上海虹桥国际机场。"
  python -m m1_trajectory_generator -f intent.txt -o output/trajectory.json
  python -m m1_trajectory_generator -i "..." --use-local-route  # 使用本地预设航路，不调用大模型
        '''
    )
    
    parser.add_argument(
        '-i', '--intent',
        type=str,
        help='飞行简令文本'
    )
    parser.add_argument(
        '-f', '--file',
        type=str,
        help='包含飞行简令的文件路径'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='输出JSON文件路径 (默认: output/m1_trajectories/trajectory_{批号}_{时间}.json)'
    )
    parser.add_argument(
        '--list-airports',
        action='store_true',
        help='列出所有可用机场'
    )
    parser.add_argument(
        '--list-aircraft',
        action='store_true',
        help='列出所有可用机型'
    )
    parser.add_argument(
        '--list-routes',
        action='store_true',
        help='列出所有可用航路'
    )
    parser.add_argument(
        '--list-missions',
        action='store_true',
        help='列出所有可用飞行任务类型'
    )
    parser.add_argument(
        '--use-local-route',
        action='store_true',
        help='强制使用本地预设航路，不调用大模型'
    )
    parser.add_argument(
        '--llm-api-key',
        type=str,
        default=None,
        help='大模型API密钥（覆盖配置文件）'
    )
    
    args = parser.parse_args()
    
    # 处理大模型相关参数
    if args.use_local_route:
        Config.LLM_ENABLED = False
        logger.info("已禁用大模型，将使用本地预设航路")
    
    if args.llm_api_key:
        Config.LLM_API_KEY = args.llm_api_key
        logger.info("使用命令行指定的API密钥")
    
    kb = KnowledgeBase()
    
    if args.list_airports:
        print("可用机场列表:")
        for airport in kb.list_airports():
            geo = kb.get_geo_location(airport)
            print(f"  {geo.name}: ({geo.lon:.4f}, {geo.lat:.4f}), 海拔 {geo.alt_m:.1f}m")
        return
    
    if args.list_aircraft:
        print("可用机型列表:")
        for aircraft in kb.list_aircraft():
            perf = kb.get_aircraft_performance(aircraft)
            print(f"  {perf.name}:")
            print(f"    巡航速度: {perf.cruise_speed_ms:.0f} m/s ({perf.cruise_speed_ms * 3.6:.0f} km/h)")
            print(f"    巡航高度: {perf.cruise_alt_m:.0f} m")
            print(f"    机头RCS: {perf.nose_rcs_dbsm:.1f} dBsm")
            print(f"    描述: {perf.description}")
        return
    
    if args.list_routes:
        print("可用航路列表:")
        for route in kb.list_routes():
            route_info = kb.routes[route]
            print(f"  {route} ({route_info['type']}): {' -> '.join(route_info['waypoints'])}")
        return
    
    if args.list_missions:
        print("可用飞行任务类型:")
        for mission in MissionType:
            profile = kb.get_mission_profile(mission)
            if profile:
                print(f"  {mission.value}:")
                print(f"    描述: {profile.description}")
                print(f"    典型高度: {profile.typical_altitude_m:.0f} m")
                print(f"    典型速度: {profile.typical_speed_ms:.0f} m/s")
                print(f"    地形跟随: {'是' if profile.terrain_following else '否'}")
                print(f"    低可探测: {'是' if profile.low_observable else '否'}")
        return
    
    intent_text = None
    if args.intent:
        intent_text = args.intent
    elif args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                intent_text = f.read().strip()
        except FileNotFoundError:
            logger.error(f"文件不存在: {args.file}")
            return
    else:
        parser.print_help()
        return
    
    generator = TrajectoryGenerator(kb)
    
    logger.info(f"开始处理飞行简令: {intent_text}")
    
    trajectory = generator.generate(intent_text)
    
    if trajectory:
        output_file = get_output_filename(trajectory, args.output)
        trajectory.save_to_file(output_file)
        logger.info(f"航迹生成成功，共 {len(trajectory.track_points)} 个轨迹点")
        logger.info(f"输出已保存到: {output_file}")
        
        print(f"\n航迹摘要:")
        print(f"  目标批号: {trajectory.target_id}")
        print(f"  机型: {trajectory.platform_type}")
        if trajectory.mission_type:
            print(f"  飞行任务: {trajectory.mission_type}")
        print(f"  轨迹点数量: {len(trajectory.track_points)}")
        
        if trajectory.track_points:
            first_point = trajectory.track_points[0]
            last_point = trajectory.track_points[-1]
            print(f"  起飞时间: {first_point.time}")
            print(f"  降落时间: {last_point.time}")
            print(f"  起飞位置: ({first_point.lon:.4f}, {first_point.lat:.4f})")
            print(f"  降落位置: ({last_point.lon:.4f}, {last_point.lat:.4f})")
            print(f"  巡航高度: {max(p.alt_m for p in trajectory.track_points):.0f} m")
        print(f"  输出文件: {output_file}")
    else:
        logger.error("航迹生成失败")


if __name__ == '__main__':
    main()
