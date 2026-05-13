# -*- coding: utf-8 -*-
import unittest
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

from m2_sensor_simulation.models_ext import FusedTrackPoint
from m6_semantic_tool.models import (
    TrackFeatures,
    TimeFeatures,
    SpatialFeatures,
    MotionFeatures,
    QualityFeatures,
    IdentityFeatures,
    TrackDescription,
    SituationSummary,
)
from m6_semantic_tool.geo_data import (
    haversine_distance,
    reverse_lookup_city,
    reverse_lookup_region,
    reverse_lookup_airport,
    reverse_lookup,
)
from m6_semantic_tool.feature_extractor import TrackFeatureExtractor
from m6_semantic_tool.flight_inferencer import FlightCharacteristicInferencer
from m6_semantic_tool.narrative_generator import NarrativeGenerator
from m6_semantic_tool.converter import SemanticConverter


def make_point(track_id="T001", target_id="0001", time=None, lon=120.0, lat=36.0,
               alt=5000, speed=250, heading=90, quality="HIGH", snr=15.0,
               identity="UNKNOWN", confidence=0.0, squawk="", callsign="", icao24="",
               emitter_type="", threat_level=0, comm_activity=""):
    if time is None:
        time = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
    return FusedTrackPoint(
        time=time, track_id=track_id, target_id=target_id,
        obs_lon=lon, obs_lat=lat, obs_alt_m=alt,
        obs_speed_ms=speed, obs_heading_deg=heading,
        track_quality=quality, snr_avg_db=snr,
        source_radars=["RADAR_01"],
        identity=identity, identity_confidence=confidence,
        squawk=squawk, callsign=callsign, icao24=icao24,
        emitter_type=emitter_type, emitter_threat_level=threat_level,
        comm_activity=comm_activity
    )


def make_features(track_id="T001", target_id="0001",
                  identity="UNKNOWN", identity_confidence=0.0,
                  max_speed_kmh=900.0, avg_speed_kmh=900.0,
                  heading_direction="东", heading_deg=90.0,
                  min_alt_m=5000.0, max_alt_m=5000.0, avg_alt_m=5000.0,
                  waypoints=None, sensor_distances=None,
                  gap_count=0, quality_distribution=None,
                  duration_seconds=120.0,
                  squawk="", callsign="", icao24="",
                  emitter_type="", emitter_threat_level=0, comm_activity="",
                  flight_labels=None):
    now = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
    return TrackFeatures(
        track_id=track_id,
        target_id=target_id,
        time_features=TimeFeatures(
            first_seen=now,
            last_seen=now + timedelta(seconds=duration_seconds),
            duration_seconds=duration_seconds,
        ),
        spatial_features=SpatialFeatures(
            start_lon=120.0, start_lat=36.0, start_name="",
            end_lon=121.0, end_lat=36.0, end_name="",
            waypoints=waypoints if waypoints is not None else [],
            sensor_distances=sensor_distances if sensor_distances is not None else {},
        ),
        motion_features=MotionFeatures(
            max_speed_kmh=max_speed_kmh,
            avg_speed_kmh=avg_speed_kmh,
            heading_direction=heading_direction,
            heading_deg=heading_deg,
            min_alt_m=min_alt_m,
            max_alt_m=max_alt_m,
            avg_alt_m=avg_alt_m,
        ),
        quality_features=QualityFeatures(
            quality_distribution=quality_distribution if quality_distribution is not None else {"HIGH": 1.0},
            avg_snr_db=15.0,
            gap_count=gap_count,
            max_continuous_duration=duration_seconds,
        ),
        identity_features=IdentityFeatures(
            identity=identity,
            identity_confidence=identity_confidence,
            squawk=squawk,
            callsign=callsign,
            icao24=icao24,
            emitter_type=emitter_type,
            emitter_threat_level=emitter_threat_level,
            comm_activity=comm_activity,
        ),
        flight_labels=flight_labels if flight_labels is not None else [],
    )


class TestGeoData(unittest.TestCase):

    def test_haversine_known_distance(self):
        d = haversine_distance(116.41, 39.90, 121.47, 31.23)
        self.assertAlmostEqual(d, 1068, delta=10)

    def test_reverse_lookup_city(self):
        result = reverse_lookup_city(120.38, 36.07)
        self.assertEqual(result, "青岛附近")

    def test_reverse_lookup_airport(self):
        result = reverse_lookup_airport(116.58, 40.08)
        self.assertEqual(result, "北京首都国际机场附近")

    def test_reverse_lookup_region(self):
        result = reverse_lookup_region(123.0, 36.0)
        self.assertEqual(result, "黄海海域上空")

    def test_reverse_lookup_fallback(self):
        result = reverse_lookup(100.0, 10.0)
        self.assertEqual(result, "坐标(100.0,10.0)附近")

    def test_reverse_lookup_city_none(self):
        result = reverse_lookup_city(0, 0)
        self.assertIsNone(result)


class TestFeatureExtractor(unittest.TestCase):

    def test_extract_time_features(self):
        t0 = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        points = [
            make_point(time=t0),
            make_point(time=t0 + timedelta(minutes=1)),
            make_point(time=t0 + timedelta(minutes=2)),
        ]
        extractor = TrackFeatureExtractor(sensor_positions={})
        features = extractor.extract(points)
        self.assertEqual(features.time_features.first_seen, t0)
        self.assertEqual(features.time_features.last_seen, t0 + timedelta(minutes=2))
        self.assertAlmostEqual(features.time_features.duration_seconds, 120)

    def test_extract_motion_features(self):
        points = [
            make_point(speed=250, heading=90),
            make_point(speed=250, heading=90),
            make_point(speed=250, heading=90),
        ]
        extractor = TrackFeatureExtractor(sensor_positions={})
        features = extractor.extract(points)
        self.assertAlmostEqual(features.motion_features.max_speed_kmh, 900, delta=1)
        self.assertAlmostEqual(features.motion_features.avg_speed_kmh, 900, delta=1)
        self.assertEqual(features.motion_features.heading_direction, "东")

    def test_extract_spatial_features_sensor_distance(self):
        sensor_positions = {"RADAR_01": (120.38, 36.07)}
        points = [
            make_point(lon=120.0, lat=36.0),
            make_point(lon=120.0, lat=36.0),
            make_point(lon=120.0, lat=36.0),
        ]
        extractor = TrackFeatureExtractor(sensor_positions=sensor_positions)
        features = extractor.extract(points)
        self.assertGreater(features.spatial_features.sensor_distances["RADAR_01"]["min_distance_km"], 0)

    def test_extract_quality_features(self):
        t0 = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        points = [
            make_point(time=t0, quality="HIGH"),
            make_point(time=t0 + timedelta(minutes=1), quality="HIGH"),
            make_point(time=t0 + timedelta(minutes=2), quality="LOST"),
        ]
        extractor = TrackFeatureExtractor(sensor_positions={})
        features = extractor.extract(points)
        self.assertAlmostEqual(features.quality_features.quality_distribution["HIGH"], 0.667, delta=0.01)
        self.assertEqual(features.quality_features.gap_count, 1)

    def test_extract_identity_features(self):
        points = [
            make_point(identity="FOE", confidence=0.85),
            make_point(identity="FOE", confidence=0.85),
            make_point(identity="FOE", confidence=0.85),
        ]
        extractor = TrackFeatureExtractor(sensor_positions={})
        features = extractor.extract(points)
        self.assertEqual(features.identity_features.identity, "FOE")
        self.assertAlmostEqual(features.identity_features.identity_confidence, 0.85, delta=0.01)

    def test_waypoint_detection(self):
        points = [
            make_point(heading=0),
            make_point(heading=10),
            make_point(heading=50),
            make_point(heading=60),
            make_point(heading=70),
        ]
        extractor = TrackFeatureExtractor(sensor_positions={})
        features = extractor.extract(points)
        self.assertGreaterEqual(len(features.spatial_features.waypoints), 1)


class TestFlightInferencer(unittest.TestCase):

    def setUp(self):
        self.inferencer = FlightCharacteristicInferencer()

    def test_low_altitude_foe(self):
        features = make_features(identity="FOE", avg_alt_m=500, min_alt_m=300, max_alt_m=700)
        labels = self.inferencer.infer(features)
        self.assertIn("低空突防", labels)

    def test_high_altitude_high_speed_foe(self):
        features = make_features(identity="FOE", avg_alt_m=15000, min_alt_m=14000, max_alt_m=16000,
                                 max_speed_kmh=1200, avg_speed_kmh=1000)
        labels = self.inferencer.infer(features)
        self.assertIn("高空侦察", labels)

    def test_smooth_cruise(self):
        features = make_features(min_alt_m=9900, max_alt_m=10000, avg_alt_m=9950)
        labels = self.inferencer.infer(features)
        self.assertIn("平稳巡航", labels)

    def test_supersonic(self):
        features = make_features(max_speed_kmh=2000)
        labels = self.inferencer.infer(features)
        self.assertIn("超音速飞行", labels)

    def test_low_speed(self):
        features = make_features(avg_speed_kmh=200)
        labels = self.inferencer.infer(features)
        self.assertIn("低速飞行", labels)

    def test_track_gap(self):
        features = make_features(gap_count=5)
        labels = self.inferencer.infer(features)
        self.assertIn("航迹断续", labels)


class TestNarrativeGenerator(unittest.TestCase):

    def setUp(self):
        self.generator = NarrativeGenerator()

    def test_generate_foe_description(self):
        features = make_features(
            identity="FOE",
            identity_confidence=0.85,
            waypoints=[{
                "time": "2025-01-01T08:01:00+00:00",
                "lon": 120.5, "lat": 36.0, "name": "",
            }],
            sensor_distances={"RADAR_01": {"min_distance_km": 10.0, "nearest_time": "2025-01-01T08:00:00Z"}},
        )
        desc = self.generator.generate_track_description(features)
        self.assertIn("判断为敌方目标", desc.narrative)
        self.assertIn("置信度85%", desc.narrative)

    def test_generate_friend_description(self):
        features = make_features(identity="FRIEND")
        desc = self.generator.generate_track_description(features)
        self.assertIn("友方目标", desc.narrative)

    def test_generate_summary(self):
        features_foe = make_features(track_id="T001", target_id="0001", identity="FOE",
                                     sensor_distances={"RADAR_01": {"min_distance_km": 10.0, "nearest_time": ""}})
        features_friend = make_features(track_id="T002", target_id="0002", identity="FRIEND",
                                        sensor_distances={"RADAR_01": {"min_distance_km": 20.0, "nearest_time": ""}})
        desc_foe = self.generator.generate_track_description(features_foe)
        desc_friend = self.generator.generate_track_description(features_friend)
        summary = self.generator.generate_situation_summary([desc_foe, desc_friend])
        self.assertEqual(summary.total_tracks, 2)
        self.assertEqual(summary.foe_count, 1)


class TestConverter(unittest.TestCase):

    def test_convert_from_synthetic_data(self):
        t0 = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        points = []
        for i in range(10):
            points.append(make_point(
                track_id="T001",
                target_id="0001",
                time=t0 + timedelta(minutes=i),
                lon=120.0 + i * 0.1,
                lat=36.0,
                speed=250,
                heading=90,
            ))
        converter = SemanticConverter()
        report = converter.convert(points)
        self.assertEqual(len(report.descriptions), 1)
        self.assertIn("目标批号", report.descriptions[0].narrative)
        self.assertTrue(len(report.descriptions[0].narrative) > 0)

    def test_convert_multi_track(self):
        t0 = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        points = []
        for i in range(5):
            points.append(make_point(
                track_id="T001",
                target_id="0001",
                time=t0 + timedelta(minutes=i),
                lon=120.0 + i * 0.1,
                lat=36.0,
            ))
        for i in range(5):
            points.append(make_point(
                track_id="T002",
                target_id="0002",
                time=t0 + timedelta(minutes=i),
                lon=117.0 + i * 0.1,
                lat=39.0,
            ))
        converter = SemanticConverter()
        report = converter.convert(points)
        self.assertEqual(len(report.descriptions), 2)
        self.assertEqual(report.summary.total_tracks, 2)


if __name__ == "__main__":
    unittest.main()
