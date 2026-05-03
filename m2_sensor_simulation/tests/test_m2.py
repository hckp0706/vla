import unittest
import os
import tempfile
import json
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from m2_sensor_simulation import SensorSimulation
from m2_sensor_simulation.models import RadarConfig, TargetTruth


class TestM2SensorSimulation(unittest.TestCase):
    """M2模块测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.simulation = SensorSimulation()
        # 创建测试真值文件
        self.test_truth_file = self._create_test_truth_file()
    
    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.test_truth_file):
            os.remove(self.test_truth_file)
    
    def _create_test_truth_file(self) -> str:
        """创建测试真值文件"""
        truth_data = {
            "target_id": "0001",
            "platform_type": "民航客机",
            "track_points": [
                {
                    "time": "2026-04-20T09:20:30Z",
                    "lon": 120.38,  # 青岛雷达位置
                    "lat": 36.07,
                    "alt_m": 10000,
                    "speed_ms": 250,
                    "heading_deg": 90,
                    "vertical_rate_ms": 0,
                    "rcs_dbsm": 5.0,
                    "phase": "CRUISING"
                }
            ]
        }
        
        fd, path = tempfile.mkstemp(suffix='.json')
        with os.fdopen(fd, 'w') as f:
            json.dump(truth_data, f)
        return path
    
    def test_radar_initialization(self):
        """测试雷达初始化"""
        self.assertEqual(len(self.simulation.radars), 5)
        self.assertEqual(self.simulation.radars[0].config.radar_id, "RADAR_01")
        self.assertEqual(self.simulation.radars[1].config.radar_id, "RADAR_02")
        self.assertEqual(self.simulation.radars[2].config.radar_id, "RADAR_03")
        self.assertEqual(self.simulation.radars[3].config.radar_id, "RADAR_04")
        self.assertEqual(self.simulation.radars[4].config.radar_id, "RADAR_05")
    
    def test_load_truth_data(self):
        """测试加载真值数据"""
        targets = self.simulation.load_truth_data(self.test_truth_file)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].target_id, "0001")
        self.assertAlmostEqual(targets[0].lon, 120.38)
        self.assertAlmostEqual(targets[0].lat, 36.07)
        self.assertEqual(targets[0].alt_m, 10000)
    
    def test_simulation_run(self):
        """测试仿真运行"""
        output = self.simulation.run_simulation(self.test_truth_file)
        self.assertIsNotNone(output)
        self.assertIsInstance(output.frame_time, str)
    
    def test_output_save(self):
        """测试输出保存"""
        output = self.simulation.run_simulation(self.test_truth_file)
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            output_path = f.name
        
        saved_path = self.simulation.save_output(output, output_path)
        self.assertTrue(os.path.exists(saved_path))
        
        # 验证输出文件格式
        with open(saved_path, 'r') as f:
            data = json.load(f)
        
        self.assertIn('frame_time', data)
        self.assertIn('network_tracks', data)
        
        if os.path.exists(saved_path):
            os.remove(saved_path)


if __name__ == '__main__':
    unittest.main()
