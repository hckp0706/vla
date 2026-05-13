import json
from collections import defaultdict
from datetime import datetime
from typing import List, Dict

from m2_sensor_simulation.models_ext import FusedTrackPoint
from m6_semantic_tool.feature_extractor import TrackFeatureExtractor
from m6_semantic_tool.flight_inferencer import FlightCharacteristicInferencer
from m6_semantic_tool.models import SituationReport
from m6_semantic_tool.narrative_generator import NarrativeGenerator


class SemanticConverter:
    def __init__(self, radar_config_path: str = None, sensor_config_path: str = None):
        if radar_config_path is None:
            radar_config_path = "m2_sensor_simulation/radar_config.json"
        if sensor_config_path is None:
            sensor_config_path = "m2_sensor_simulation/sensor_config.json"

        self.sensor_positions: Dict[str, tuple] = {}
        self.radar_names: Dict[str, str] = {}

        with open(radar_config_path, "r", encoding="utf-8") as f:
            radar_cfg = json.load(f)
        for radar in radar_cfg["radars"]:
            loc = radar["location"]
            self.sensor_positions[radar["radar_id"]] = (loc[0], loc[1])
            self.radar_names[radar["radar_id"]] = radar["name"]

        with open(sensor_config_path, "r", encoding="utf-8") as f:
            sensor_cfg = json.load(f)
        for station in sensor_cfg.get("ssr_stations", []):
            loc = station["location"]
            self.sensor_positions[station["ssr_id"]] = (loc[0], loc[1])
        for station in sensor_cfg.get("iff_stations", []):
            loc = station["location"]
            self.sensor_positions[station["iff_id"]] = (loc[0], loc[1])
        for station in sensor_cfg.get("esm_stations", []):
            loc = station["location"]
            self.sensor_positions[station["esm_id"]] = (loc[0], loc[1])
        for station in sensor_cfg.get("comint_stations", []):
            loc = station["location"]
            self.sensor_positions[station["comint_id"]] = (loc[0], loc[1])

        self.extractor = TrackFeatureExtractor(self.sensor_positions)
        self.inferencer = FlightCharacteristicInferencer()
        self.generator = NarrativeGenerator(radar_names=self.radar_names)

    def convert(self, fused_tracks: List[FusedTrackPoint]) -> SituationReport:
        tracks_by_id: Dict[str, List[FusedTrackPoint]] = defaultdict(list)
        for point in fused_tracks:
            tracks_by_id[point.track_id].append(point)

        descriptions = []
        for track_id, points in tracks_by_id.items():
            features = self.extractor.extract(points)
            labels = self.inferencer.infer(features)
            features.flight_labels = labels
            desc = self.generator.generate_track_description(features)
            descriptions.append(desc)

        summary = self.generator.generate_situation_summary(descriptions)
        return SituationReport(descriptions=descriptions, summary=summary)

    def convert_from_file(self, fused_track_path: str) -> SituationReport:
        with open(fused_track_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_tracks = []
        if isinstance(data, list):
            for frame in data:
                raw_tracks.extend(frame.get("network_tracks", []))
        elif isinstance(data, dict):
            raw_tracks = data.get("network_tracks", [])

        all_points: List[FusedTrackPoint] = []
        for t in raw_tracks:
            point = FusedTrackPoint(
                time=datetime.fromisoformat(t["time"].replace("Z", "+00:00")),
                track_id=t["track_id"],
                target_id=t["target_id"],
                obs_lon=t["obs_lon"],
                obs_lat=t["obs_lat"],
                obs_alt_m=t["obs_alt_m"],
                obs_speed_ms=t["obs_speed_ms"],
                obs_heading_deg=t["obs_heading_deg"],
                track_quality=t["track_quality"],
                snr_avg_db=t["snr_avg_db"],
                source_radars=t.get("source_radars", []),
                identity=t.get("identity", "UNKNOWN"),
                identity_source=t.get("identity_source", "NONE"),
                identity_confidence=t.get("identity_confidence", 0.0),
                squawk=t.get("squawk", ""),
                callsign=t.get("callsign", ""),
                icao24=t.get("icao24", ""),
                altitude_source=t.get("altitude_source", "RADAR"),
                altitude_ft=t.get("altitude_ft", 0.0),
                emitter_type=t.get("emitter_type", ""),
                emitter_threat_level=t.get("emitter_threat_level", 0),
                comm_activity=t.get("comm_activity", ""),
                position_source=t.get("position_source", "TRUTH"),
                source_sensors=t.get("source_sensors", []),
                sensor_count=t.get("sensor_count", 0),
                fusion_timestamp=t.get("fusion_timestamp", ""),
            )
            all_points.append(point)

        return self.convert(all_points)
