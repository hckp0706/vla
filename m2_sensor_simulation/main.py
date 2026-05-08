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
    parser = argparse.ArgumentParser(
        description='M2: 高保真传感器仿真引擎',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法:
  python -m m2_sensor_simulation -i output/m1_trajectories/trajectory.json
  python -m m2_sensor_simulation -i trajectory.json --comprehensive
  python -m m2_sensor_simulation -i trajectory.json --comprehensive --sensors radar ssr iff
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
    parser.add_argument(
        '--comprehensive',
        action='store_true',
        default=False,
        help='运行综合传感器仿真（含SSR/IFF/ESM/ELINT/COMINT）'
    )
    parser.add_argument(
        '--sensors',
        nargs='+',
        choices=['radar', 'ssr', 'iff', 'esm', 'elint', 'comint'],
        default=None,
        help='选择运行的传感器类型（仅综合模式下有效，默认全部）'
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        logger.error(f"输入文件不存在: {args.input}")
        return

    simulation = SensorSimulation()

    if args.comprehensive:
        output = simulation.run_comprehensive_simulation(args.input, args.sensors)
        output_dir = simulation.save_comprehensive_output(output, args.output)

        print(f"\n综合仿真摘要:")
        print(f"  输入文件: {args.input}")
        print(f"  输出文件夹: {output_dir}")

        if 'fused_comprehensive' in output:
            fused = output['fused_comprehensive']
            print(f"  综合融合航迹: {len(fused.network_tracks)} 个点")

        for key in ('ssr_replies', 'iff_replies', 'esm_pdws', 'elint_reports', 'comint_reports'):
            data = output.get(key, [])
            print(f"  {key}: {len(data)} 条记录")

        if 'fused' in output and hasattr(output['fused'], 'network_tracks') and output['fused'].network_tracks:
            avg_snr = sum(t.snr_avg_db for t in output['fused'].network_tracks) / len(output['fused'].network_tracks)
            print(f"  平均SNR: {avg_snr:.1f} dB")

        if 'fused_comprehensive' in output and output['fused_comprehensive'].network_tracks:
            identities = {}
            for t in output['fused_comprehensive'].network_tracks:
                identities[t.identity] = identities.get(t.identity, 0) + 1
            print(f"  敌我属性分布: {identities}")
    else:
        output = simulation.run_simulation(args.input)
        output_dir = simulation.save_output(output, args.output)

        print(f"\n仿真摘要:")
        print(f"  输入文件: {args.input}")
        print(f"  输出文件夹: {output_dir}")
        print(f"  航迹文件数量: {len(output)}")

        for key, tracks in output.items():
            if key == 'fused':
                print(f"  融合航迹: {len(tracks.network_tracks)} 个观测点")
            else:
                print(f"  {key}: {len(tracks.network_tracks)} 个观测点")

        if 'fused' in output and output['fused'].network_tracks:
            avg_snr = sum(track.snr_avg_db for track in output['fused'].network_tracks) / len(output['fused'].network_tracks)
            print(f"  平均SNR: {avg_snr:.1f} dB")


if __name__ == '__main__':
    main()
