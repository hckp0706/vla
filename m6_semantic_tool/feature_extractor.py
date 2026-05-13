# -*- coding: utf-8 -*-
import math
import statistics
from collections import Counter
from typing import List, Dict

from m6_semantic_tool.models import (
    TrackFeatures,
    TimeFeatures,
    SpatialFeatures,
    MotionFeatures,
    QualityFeatures,
    IdentityFeatures,
    FlightSegment,
    AltitudeAnomaly,
    SpeedAnomaly,
    CityOverflight,
)
from m6_semantic_tool.geo_data import haversine_distance, MAJOR_CITIES
from m2_sensor_simulation.models_ext import FusedTrackPoint


class TrackFeatureExtractor:
    def __init__(self, sensor_positions: Dict[str, tuple]):
        self.sensor_positions = sensor_positions

    def extract(self, track_points: List[FusedTrackPoint]) -> TrackFeatures:
        if not track_points:
            raise ValueError("track_points 不能为空")

        points = sorted(track_points, key=lambda p: p.time)

        return TrackFeatures(
            track_id=points[0].track_id,
            target_id=points[0].target_id,
            time_features=self._extract_time_features(points),
            spatial_features=self._extract_spatial_features(points),
            motion_features=self._extract_motion_features(points),
            quality_features=self._extract_quality_features(points),
            identity_features=self._extract_identity_features(points),
        )

    def _extract_time_features(self, points: List[FusedTrackPoint]) -> TimeFeatures:
        first_seen = points[0].time
        last_seen = points[-1].time
        duration_seconds = (last_seen - first_seen).total_seconds()
        return TimeFeatures(
            first_seen=first_seen,
            last_seen=last_seen,
            duration_seconds=duration_seconds,
        )

    def _extract_spatial_features(self, points: List[FusedTrackPoint]) -> SpatialFeatures:
        start_lon = points[0].obs_lon
        start_lat = points[0].obs_lat
        end_lon = points[-1].obs_lon
        end_lat = points[-1].obs_lat

        waypoints = []
        for i in range(1, len(points) - 1):
            prev_heading = points[i - 1].obs_heading_deg
            curr_heading = points[i].obs_heading_deg
            diff = abs(curr_heading - prev_heading)
            if diff > 180:
                diff = 360 - diff
            if diff > 30:
                t = points[i].time
                time_str = t.strftime("%Y-%m-%dT%H:%M:%SZ")
                waypoints.append({
                    "time": time_str,
                    "lon": points[i].obs_lon,
                    "lat": points[i].obs_lat,
                    "name": "",
                })

        sensor_distances = {}
        for sensor_id, (s_lon, s_lat) in self.sensor_positions.items():
            min_dist = float("inf")
            nearest_time = None
            for p in points:
                d = haversine_distance(p.obs_lon, p.obs_lat, s_lon, s_lat)
                if d < min_dist:
                    min_dist = d
                    nearest_time = p.time.strftime("%Y-%m-%dT%H:%M:%SZ")
            sensor_distances[sensor_id] = {
                "min_distance_km": min_dist,
                "nearest_time": nearest_time,
            }

        def _heading_diff(h1, h2):
            d = abs(h1 - h2)
            return min(d, 360 - d)

        segments = []
        seg_start_idx = 0
        for i in range(1, len(points)):
            if _heading_diff(points[seg_start_idx].obs_heading_deg, points[i].obs_heading_deg) > 15:
                seg_points = points[seg_start_idx:i]
                seg = FlightSegment(
                    start_time=seg_points[0].time,
                    end_time=seg_points[-1].time,
                    heading_deg=seg_points[0].obs_heading_deg,
                    heading_direction=self._heading_to_direction(seg_points[0].obs_heading_deg),
                    start_alt_m=seg_points[0].obs_alt_m,
                    end_alt_m=seg_points[-1].obs_alt_m,
                    avg_alt_m=sum(p.obs_alt_m for p in seg_points) / len(seg_points),
                    start_speed_kmh=seg_points[0].obs_speed_ms * 3.6,
                    end_speed_kmh=seg_points[-1].obs_speed_ms * 3.6,
                    avg_speed_kmh=sum(p.obs_speed_ms for p in seg_points) / len(seg_points) * 3.6,
                    start_lon=seg_points[0].obs_lon,
                    start_lat=seg_points[0].obs_lat,
                    end_lon=seg_points[-1].obs_lon,
                    end_lat=seg_points[-1].obs_lat,
                )
                segments.append(seg)
                seg_start_idx = i

        if seg_start_idx < len(points):
            seg_points = points[seg_start_idx:]
            seg = FlightSegment(
                start_time=seg_points[0].time,
                end_time=seg_points[-1].time,
                heading_deg=seg_points[0].obs_heading_deg,
                heading_direction=self._heading_to_direction(seg_points[0].obs_heading_deg),
                start_alt_m=seg_points[0].obs_alt_m,
                end_alt_m=seg_points[-1].obs_alt_m,
                avg_alt_m=sum(p.obs_alt_m for p in seg_points) / len(seg_points),
                start_speed_kmh=seg_points[0].obs_speed_ms * 3.6,
                end_speed_kmh=seg_points[-1].obs_speed_ms * 3.6,
                avg_speed_kmh=sum(p.obs_speed_ms for p in seg_points) / len(seg_points) * 3.6,
                start_lon=seg_points[0].obs_lon,
                start_lat=seg_points[0].obs_lat,
                end_lon=seg_points[-1].obs_lon,
                end_lat=seg_points[-1].obs_lat,
            )
            segments.append(seg)

        altitude_anomalies = []
        if len(points) >= 3:
            alt_rates = []
            for i in range(1, len(points)):
                dt = (points[i].time - points[i - 1].time).total_seconds()
                if dt > 0:
                    rate = (points[i].obs_alt_m - points[i - 1].obs_alt_m) / dt
                    alt_rates.append((i, rate))

            if alt_rates:
                rates_only = [r for _, r in alt_rates]
                mean_rate = statistics.mean(rates_only)
                std_rate = statistics.stdev(rates_only) if len(rates_only) > 1 else 0

                threshold = mean_rate + 2 * std_rate if std_rate > 0 else abs(mean_rate) * 2
                if threshold == 0:
                    threshold = 50

                for idx, rate in alt_rates:
                    dt = (points[idx].time - points[idx - 1].time).total_seconds()
                    alt_delta = abs(points[idx].obs_alt_m - points[idx - 1].obs_alt_m)
                    if abs(rate) > threshold and dt > 0 and alt_delta > 200:
                        anomaly = AltitudeAnomaly(
                            time=points[idx].time,
                            alt_before_m=points[idx - 1].obs_alt_m,
                            alt_after_m=points[idx].obs_alt_m,
                            change_rate_mps=round(rate, 1),
                        )
                        altitude_anomalies.append(anomaly)

        speed_anomalies = []
        if len(points) >= 3:
            speed_rates = []
            for i in range(1, len(points)):
                dt = (points[i].time - points[i - 1].time).total_seconds()
                if dt > 0:
                    speed_before = points[i - 1].obs_speed_ms * 3.6
                    speed_after = points[i].obs_speed_ms * 3.6
                    rate = (speed_after - speed_before) / dt
                    speed_rates.append((i, rate))

            if speed_rates:
                rates_only = [r for _, r in speed_rates]
                mean_rate = statistics.mean(rates_only)
                std_rate = statistics.stdev(rates_only) if len(rates_only) > 1 else 0

                threshold = mean_rate + 2 * std_rate if std_rate > 0 else abs(mean_rate) * 2
                if threshold == 0:
                    threshold = 30

                for idx, rate in speed_rates:
                    speed_delta = abs(points[idx].obs_speed_ms * 3.6 - points[idx - 1].obs_speed_ms * 3.6)
                    if abs(rate) > threshold and speed_delta > 50:
                        anomaly = SpeedAnomaly(
                            time=points[idx].time,
                            speed_before_kmh=round(points[idx - 1].obs_speed_ms * 3.6, 1),
                            speed_after_kmh=round(points[idx].obs_speed_ms * 3.6, 1),
                            change_rate_kmhps=round(rate, 1),
                        )
                        speed_anomalies.append(anomaly)

        city_overflights = []
        visited_cities = set()
        for p in points:
            for city_name, city_lon, city_lat in MAJOR_CITIES:
                d = haversine_distance(p.obs_lon, p.obs_lat, city_lon, city_lat)
                if d <= 100 and city_name not in visited_cities:
                    co = CityOverflight(
                        time=p.time,
                        city_name=city_name,
                        distance_km=round(d, 1),
                        lon=p.obs_lon,
                        lat=p.obs_lat,
                    )
                    city_overflights.append(co)
                    visited_cities.add(city_name)
                    break

        return SpatialFeatures(
            start_lon=start_lon,
            start_lat=start_lat,
            start_name="",
            end_lon=end_lon,
            end_lat=end_lat,
            end_name="",
            waypoints=waypoints,
            sensor_distances=sensor_distances,
            segments=segments,
            altitude_anomalies=altitude_anomalies,
            speed_anomalies=speed_anomalies,
            city_overflights=city_overflights,
        )

    def _extract_motion_features(self, points: List[FusedTrackPoint]) -> MotionFeatures:
        max_speed_kmh = max(p.obs_speed_ms for p in points) * 3.6
        avg_speed_kmh = sum(p.obs_speed_ms for p in points) / len(points) * 3.6

        sin_sum = sum(math.sin(math.radians(p.obs_heading_deg)) for p in points)
        cos_sum = sum(math.cos(math.radians(p.obs_heading_deg)) for p in points)
        heading_deg = math.degrees(math.atan2(sin_sum, cos_sum)) % 360
        heading_direction = self._heading_to_direction(heading_deg)

        min_alt_m = min(p.obs_alt_m for p in points)
        max_alt_m = max(p.obs_alt_m for p in points)
        avg_alt_m = sum(p.obs_alt_m for p in points) / len(points)

        return MotionFeatures(
            max_speed_kmh=max_speed_kmh,
            avg_speed_kmh=avg_speed_kmh,
            heading_direction=heading_direction,
            heading_deg=heading_deg,
            min_alt_m=min_alt_m,
            max_alt_m=max_alt_m,
            avg_alt_m=avg_alt_m,
        )

    def _extract_quality_features(self, points: List[FusedTrackPoint]) -> QualityFeatures:
        counter = Counter(p.track_quality for p in points)
        total = len(points)
        quality_distribution = {k: v / total for k, v in counter.items()}

        avg_snr_db = sum(p.snr_avg_db for p in points) / total

        gap_count = sum(1 for p in points if p.track_quality == "LOST")

        max_continuous_duration = 0.0
        seg_start = None
        for p in points:
            if p.track_quality != "LOST":
                if seg_start is None:
                    seg_start = p.time
            else:
                if seg_start is not None:
                    dur = (p.time - seg_start).total_seconds()
                    if dur > max_continuous_duration:
                        max_continuous_duration = dur
                    seg_start = None
        if seg_start is not None:
            dur = (points[-1].time - seg_start).total_seconds()
            if dur > max_continuous_duration:
                max_continuous_duration = dur

        return QualityFeatures(
            quality_distribution=quality_distribution,
            avg_snr_db=avg_snr_db,
            gap_count=gap_count,
            max_continuous_duration=max_continuous_duration,
        )

    def _extract_identity_features(self, points: List[FusedTrackPoint]) -> IdentityFeatures:
        non_unknown = [p.identity for p in points if p.identity != "UNKNOWN"]
        if non_unknown:
            identity = Counter(non_unknown).most_common(1)[0][0]
            identity_confidence = sum(
                p.identity_confidence for p in points if p.identity == identity
            ) / sum(1 for p in points if p.identity == identity)
        else:
            identity = "UNKNOWN"
            identity_confidence = 0.0

        squawk = self._most_common([p.squawk for p in points])
        callsign = self._most_common([p.callsign for p in points])
        icao24 = self._most_common([p.icao24 for p in points])
        emitter_type = self._most_common([p.emitter_type for p in points])
        emitter_threat_level = max(p.emitter_threat_level for p in points)
        comm_activity = self._most_common([p.comm_activity for p in points])

        return IdentityFeatures(
            identity=identity,
            identity_confidence=identity_confidence,
            squawk=squawk,
            callsign=callsign,
            icao24=icao24,
            emitter_type=emitter_type,
            emitter_threat_level=emitter_threat_level,
            comm_activity=comm_activity,
        )

    def _most_common(self, values: List[str]) -> str:
        non_empty = [v for v in values if v]
        if not non_empty:
            return ""
        return Counter(non_empty).most_common(1)[0][0]

    def _heading_to_direction(self, deg: float) -> str:
        directions = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
        idx = round(deg / 45) % 8
        return directions[idx]
