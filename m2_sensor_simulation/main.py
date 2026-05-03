import argparse
import os
import logging
from datetime import datetime

from .sensor_simulation import SensorSimulation

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='M2: 高保真传感器仿真引擎',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法:
  python -m m2_sensor_simulation -i output/m1_trajectories/trajectory_0001_20260422_121746.json
  python -m m2_sensor_simulation -i trajectory.json -o output/tracks.json
        '''
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        required=True,
        help='M1输出的真值文件路径'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='输出文件路径 (默认: output/m2_tracks/tracks_xxx.json)'
    )
    
    args = parser.parse_args()
    
    # 验证输入文件
    if not os.path.exists(args.input):
        logger.error(f"输入文件不存在: {args.input}")
        return
    
    # 创建传感器仿真引擎
    simulation = SensorSimulation()
    
    # 运行仿真
    output = simulation.run_simulation(args.input)
    
    # 保存输出
    output_dir = simulation.save_output(output, args.output)
    
    # 打印摘要
    print(f"\n仿真摘要:")
    print(f"  输入文件: {args.input}")
    print(f"  输出文件夹: {output_dir}")
    print(f"  航迹文件数量: {len(output)}")
    
    # 统计各雷达的观测点数
    for key, tracks in output.items():
        if key == 'fused':
            print(f"  融合航迹: {len(tracks.network_tracks)} 个观测点")
        else:
            print(f"  {key}: {len(tracks.network_tracks)} 个观测点")
    
    # 统计融合航迹的平均SNR
    if 'fused' in output and output['fused'].network_tracks:
        avg_snr = sum(track.snr_avg_db for track in output['fused'].network_tracks) / len(output['fused'].network_tracks)
        print(f"  平均SNR: {avg_snr:.1f} dB")


if __name__ == '__main__':
    main()
