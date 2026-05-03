import unittest
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from m1_trajectory_generator.parser import IntentParser
from m1_trajectory_generator.knowledge_base import KnowledgeBase
from m1_trajectory_generator.trajectory_generator import TrajectoryGenerator
from m1_trajectory_generator.models import FlightPhase


class TestIntentParser(unittest.TestCase):
    def setUp(self):
        self.parser = IntentParser()
    
    def test_parse_standard_intent(self):
        intent_text = "0001 民航客机 于 2026-04-20 09:20:30 从 北京大兴国际机场 起飞，途径 西安咸阳国际机场 10:20:00，降落 上海虹桥国际机场 12:40:00。"
        intent = self.parser.parse(intent_text)
        
        self.assertIsNotNone(intent)
        self.assertEqual(intent.target_id, "0001")
        self.assertEqual(intent.platform_type, "民航客机")
        self.assertEqual(intent.takeoff_time, datetime(2026, 4, 20, 9, 20, 30))
        self.assertEqual(intent.loc_start, "北京大兴国际机场")
        self.assertEqual(intent.action_mid, "途径")
        self.assertEqual(intent.loc_mid, "西安咸阳国际机场")
        self.assertEqual(intent.time_mid, "10:20:00")
        self.assertEqual(intent.action_end, "降落")
        self.assertEqual(intent.loc_end, "上海虹桥国际机场")
        self.assertEqual(intent.time_end, "12:40:00")
    
    def test_parse_simple_intent(self):
        intent_text = "0002 歼击机 于 2026-04-20 10:00:00 从 北京大兴国际机场 起飞，降落 上海虹桥国际机场 12:00:00。"
        intent = self.parser.parse(intent_text)
        
        self.assertIsNotNone(intent)
        self.assertEqual(intent.target_id, "0002")
        self.assertEqual(intent.platform_type, "歼击机")
        self.assertEqual(intent.loc_start, "北京大兴国际机场")
        self.assertEqual(intent.loc_end, "上海虹桥国际机场")
        self.assertIsNone(intent.loc_mid)
    
    def test_parse_invalid_intent(self):
        intent_text = "这是一条无效的简令"
        intent = self.parser.parse(intent_text)
        self.assertIsNone(intent)
    
    def test_validate_intent(self):
        intent_text = "0001 民航客机 于 2026-04-20 09:20:30 从 北京大兴国际机场 起飞，降落 上海虹桥国际机场 12:40:00。"
        intent, is_valid, errors, warnings = self.parser.parse_and_validate(intent_text)
        
        self.assertIsNotNone(intent)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)


class TestKnowledgeBase(unittest.TestCase):
    def setUp(self):
        self.kb = KnowledgeBase()
    
    def test_get_geo_location_exact(self):
        geo = self.kb.get_geo_location("北京大兴国际机场")
        
        self.assertIsNotNone(geo)
        self.assertEqual(geo.name, "北京大兴国际机场")
        self.assertAlmostEqual(geo.lon, 116.594, places=2)
        self.assertAlmostEqual(geo.lat, 39.509, places=2)
    
    def test_get_geo_location_fuzzy(self):
        geo = self.kb.get_geo_location("大兴")
        
        self.assertIsNotNone(geo)
        self.assertIn("大兴", geo.name)
    
    def test_get_geo_location_not_found(self):
        geo = self.kb.get_geo_location("不存在的机场xyz")
        self.assertIsNone(geo)
    
    def test_get_aircraft_performance(self):
        perf = self.kb.get_aircraft_performance("民航客机")
        
        self.assertIsNotNone(perf)
        self.assertEqual(perf.name, "民航客机")
        self.assertEqual(perf.cruise_speed_ms, 240.0)
        self.assertEqual(perf.cruise_alt_m, 10000.0)
    
    def test_get_aircraft_performance_fighter(self):
        perf = self.kb.get_aircraft_performance("歼击机")
        
        self.assertIsNotNone(perf)
        self.assertEqual(perf.cruise_speed_ms, 280.0)
        self.assertEqual(perf.nose_rcs_dbsm, -2.0)
    
    def test_get_route(self):
        route = self.kb.get_route("北京大兴国际机场", "上海虹桥国际机场", "民航客机")
        
        self.assertIsNotNone(route)
        self.assertIn("北京大兴国际机场", route)
        self.assertIn("上海虹桥国际机场", route)
    
    def test_list_airports(self):
        airports = self.kb.list_airports()
        
        self.assertGreater(len(airports), 0)
        self.assertIn("北京大兴国际机场", airports)
        self.assertIn("上海虹桥国际机场", airports)
    
    def test_list_aircraft(self):
        aircraft = self.kb.list_aircraft()
        
        self.assertGreater(len(aircraft), 0)
        self.assertIn("民航客机", aircraft)
        self.assertIn("歼击机", aircraft)


class TestTrajectoryGenerator(unittest.TestCase):
    def setUp(self):
        self.kb = KnowledgeBase()
        self.generator = TrajectoryGenerator(self.kb)
    
    def test_generate_trajectory(self):
        intent_text = "0001 民航客机 于 2026-04-20 09:20:30 从 北京大兴国际机场 起飞，降落 上海虹桥国际机场 12:40:00。"
        trajectory = self.generator.generate(intent_text)
        
        self.assertIsNotNone(trajectory)
        self.assertEqual(trajectory.target_id, "0001")
        self.assertEqual(trajectory.platform_type, "民航客机")
        self.assertGreater(len(trajectory.track_points), 0)
    
    def test_trajectory_time_sequence(self):
        intent_text = "0001 民航客机 于 2026-04-20 09:20:30 从 北京大兴国际机场 起飞，降落 上海虹桥国际机场 12:40:00。"
        trajectory = self.generator.generate(intent_text)
        
        self.assertIsNotNone(trajectory)
        
        for i in range(len(trajectory.track_points) - 1):
            self.assertLess(
                trajectory.track_points[i].time,
                trajectory.track_points[i + 1].time
            )
    
    def test_trajectory_altitude_profile(self):
        intent_text = "0001 民航客机 于 2026-04-20 09:20:30 从 北京大兴国际机场 起飞，降落 上海虹桥国际机场 12:40:00。"
        trajectory = self.generator.generate(intent_text)
        
        self.assertIsNotNone(trajectory)
        
        phases = [p.phase for p in trajectory.track_points]
        self.assertIn(FlightPhase.CLIMBING, phases)
        self.assertIn(FlightPhase.CRUISING, phases)
        self.assertIn(FlightPhase.DESCENDING, phases)
    
    def test_trajectory_heading_continuity(self):
        intent_text = "0001 民航客机 于 2026-04-20 09:20:30 从 北京大兴国际机场 起飞，降落 上海虹桥国际机场 12:40:00。"
        trajectory = self.generator.generate(intent_text)
        
        self.assertIsNotNone(trajectory)
        
        max_heading_change = 0
        for i in range(len(trajectory.track_points) - 1):
            heading_diff = abs(
                trajectory.track_points[i].heading_deg - 
                trajectory.track_points[i + 1].heading_deg
            )
            if heading_diff > 180:
                heading_diff = 360 - heading_diff
            max_heading_change = max(max_heading_change, heading_diff)
        
        self.assertLess(max_heading_change, 180, f"航向突变过大: {max_heading_change}度")
    
    def test_trajectory_rcs_values(self):
        intent_text = "0001 民航客机 于 2026-04-20 09:20:30 从 北京大兴国际机场 起飞，降落 上海虹桥国际机场 12:40:00。"
        trajectory = self.generator.generate(intent_text)
        
        self.assertIsNotNone(trajectory)
        
        for point in trajectory.track_points:
            self.assertGreater(point.rcs_dbsm, -20)
            self.assertLess(point.rcs_dbsm, 50)
    
    def test_trajectory_json_output(self):
        intent_text = "0001 民航客机 于 2026-04-20 09:20:30 从 北京大兴国际机场 起飞，降落 上海虹桥国际机场 12:40:00。"
        trajectory = self.generator.generate(intent_text)
        
        self.assertIsNotNone(trajectory)
        
        json_output = trajectory.to_json()
        self.assertIn("target_id", json_output)
        self.assertIn("platform_type", json_output)
        self.assertIn("track_points", json_output)
    
    def test_fighter_trajectory(self):
        intent_text = "0002 歼击机 于 2026-04-20 10:00:00 从 北京大兴国际机场 起飞，降落 上海虹桥国际机场 12:00:00。"
        trajectory = self.generator.generate(intent_text)
        
        self.assertIsNotNone(trajectory)
        self.assertEqual(trajectory.platform_type, "歼击机")


class TestIntegration(unittest.TestCase):
    def test_full_workflow(self):
        kb = KnowledgeBase()
        generator = TrajectoryGenerator(kb)
        
        intent_text = "0001 民航客机 于 2026-04-20 09:20:30 从 北京大兴国际机场 起飞，途径 西安咸阳国际机场 10:20:00，降落 上海虹桥国际机场 12:40:00。"
        
        trajectory = generator.generate(intent_text)
        
        self.assertIsNotNone(trajectory)
        self.assertEqual(trajectory.target_id, "0001")
        self.assertGreater(len(trajectory.track_points), 0)
        
        first_point = trajectory.track_points[0]
        last_point = trajectory.track_points[-1]
        
        self.assertEqual(first_point.time.strftime('%Y-%m-%d %H:%M:%S'), "2026-04-20 09:20:30")
        self.assertGreater(first_point.alt_m, 0)
        self.assertGreater(first_point.speed_ms, 0)
        
        self.assertIn(last_point.phase, [FlightPhase.DESCENDING, FlightPhase.LANDING])


if __name__ == '__main__':
    unittest.main()
