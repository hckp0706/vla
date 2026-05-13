# -*- coding: utf-8 -*-
from typing import List, Dict

from m6_semantic_tool import geo_data
from m6_semantic_tool.models import (
    TrackDescription,
    TrackFeatures,
    SituationSummary,
)


class NarrativeGenerator:
    def __init__(self, radar_names: Dict[str, str] = None):
        self.radar_names = radar_names or {}

    def _get_location_name(self, lon: float, lat: float) -> str:
        airport = geo_data.reverse_lookup_airport(lon, lat)
        if airport is not None and "机场" in airport:
            return airport
        return geo_data.reverse_lookup(lon, lat)

    def generate_track_description(self, features: TrackFeatures) -> TrackDescription:
        sp = features.spatial_features
        idf = features.identity_features
        mf = features.motion_features

        if idf.identity == "FRIEND":
            identity_desc = "友方目标"
        elif idf.identity == "FOE":
            identity_desc = f"判断为敌方目标（置信度{idf.identity_confidence:.0%}）"
        elif idf.identity == "NEUTRAL":
            identity_desc = "中立目标"
        else:
            identity_desc = "身份不明目标"

        identity_extra = f"（SSR呼号：{idf.callsign}）" if idf.callsign else ""

        def fmt_time(dt):
            return dt.strftime("%H时%M分%S秒")

        start_time = fmt_time(features.time_features.first_seen)
        end_time = fmt_time(features.time_features.last_seen)

        start_location = self._get_location_name(sp.start_lon, sp.start_lat)
        end_location = self._get_location_name(sp.end_lon, sp.end_lat)

        flight_features = "、".join(features.flight_labels) if features.flight_labels else "常规飞行"

        events = []

        for co in sp.city_overflights:
            events.append((
                co.time,
                f"  {fmt_time(co.time)}，途经{co.city_name}上空（距离{round(co.distance_km, 1)}km）；",
            ))

        for anomaly in sp.altitude_anomalies:
            direction = "骤升至" if anomaly.alt_after_m > anomaly.alt_before_m else "骤降至"
            events.append((
                anomaly.time,
                f"  {fmt_time(anomaly.time)}，高度发生骤变，"
                f"从{int(anomaly.alt_before_m)}米{direction}{int(anomaly.alt_after_m)}米"
                f"（变化率{round(anomaly.change_rate_mps, 1)}米/秒）；",
            ))

        for anomaly in sp.speed_anomalies:
            direction = "增加" if anomaly.speed_after_kmh > anomaly.speed_before_kmh else "降低"
            events.append((
                anomaly.time,
                f"  {fmt_time(anomaly.time)}，速度发生骤变，"
                f"从{int(anomaly.speed_before_kmh)}km/h{direction}至{int(anomaly.speed_after_kmh)}km/h；",
            ))

        events.sort(key=lambda e: e[0])

        segment_lines = []
        event_idx = 0
        for seg in sp.segments:
            if abs(seg.end_alt_m - seg.start_alt_m) > 500:
                if seg.end_alt_m > seg.start_alt_m:
                    alt_desc = f"高度从{int(seg.start_alt_m)}米爬升至{int(seg.end_alt_m)}米"
                else:
                    alt_desc = f"高度从{int(seg.start_alt_m)}米下降至{int(seg.end_alt_m)}米"
            else:
                alt_desc = f"高度维持在{int(seg.avg_alt_m)}米左右"

            seg_desc = (
                f"{fmt_time(seg.start_time)}-{fmt_time(seg.end_time)}，"
                f"朝方位角{int(seg.heading_deg)}°向{seg.heading_direction}方向飞行，"
                f"{alt_desc}；"
            )
            segment_lines.append(seg_desc)

            while event_idx < len(events) and seg.start_time <= events[event_idx][0] <= seg.end_time:
                segment_lines.append(events[event_idx][1])
                event_idx += 1

        flight_path_text = "\n".join(segment_lines)

        sensor_distance_parts = []
        for sensor_id, info in sp.sensor_distances.items():
            if sensor_id.startswith("RADAR_"):
                if sensor_id in self.radar_names:
                    display_name = self.radar_names[sensor_id] + "站"
                else:
                    display_name = sensor_id
                dist = round(info["min_distance_km"], 1)
                nearest_time = info["nearest_time"]
                if "T" in nearest_time:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(nearest_time.replace("Z", "+00:00"))
                        nearest_time = dt.strftime("%H时%M分%S秒")
                    except Exception:
                        nearest_time = nearest_time[11:16]
                sensor_distance_parts.append(
                    f"距{display_name}最近距离为{dist}km（{nearest_time}时刻）"
                )

        sensor_distance_desc = ""
        if sensor_distance_parts:
            sensor_distance_desc = "雷达探测：" + "，".join(sensor_distance_parts) + "。"

        additional_parts = []
        if idf.icao24:
            additional_parts.append(f"ICAO24：{idf.icao24}")
        if idf.squawk:
            additional_parts.append(f"Squawk码：{idf.squawk}")
        if idf.emitter_type:
            additional_parts.append(f"机载辐射源：{idf.emitter_type}")
        if idf.comm_activity:
            additional_parts.append(f"通信活动：{idf.comm_activity}")

        additional_info = ""
        if additional_parts:
            additional_info = "\n另外，" + "，".join(additional_parts)

        max_speed = int(mf.max_speed_kmh)
        avg_speed = int(mf.avg_speed_kmh)
        min_alt = int(mf.min_alt_m)
        max_alt = int(mf.max_alt_m)

        parts = [
            f"目标批号{features.target_id}，{identity_desc}{identity_extra}。",
            "",
            f"起飞信息：于{start_time}从{start_location}起飞。",
            "",
            "飞行航迹：",
            flight_path_text,
            "",
            f"降落信息：于{end_time}降落于{end_location}。",
            "",
            f"飞行特征总结：{flight_features}，最大速度{max_speed}km/h，平均速度约{avg_speed}km/h，",
            f"飞行高度范围{min_alt}-{max_alt}米。",
        ]

        if sensor_distance_desc:
            parts.append(sensor_distance_desc)

        narrative = "\n".join(parts) + additional_info

        return TrackDescription(
            track_id=features.track_id,
            target_id=features.target_id,
            narrative=narrative,
            features=features,
        )

    def generate_situation_summary(self, descriptions: List[TrackDescription]) -> SituationSummary:
        total_tracks = len(descriptions)
        foe_count = 0
        friend_count = 0
        unknown_count = 0
        for desc in descriptions:
            identity = desc.features.identity_features.identity
            if identity == "FOE":
                foe_count += 1
            elif identity == "FRIEND":
                friend_count += 1
            else:
                unknown_count += 1

        nearest_track_id = ""
        nearest_distance_km = 0.0
        nearest_sensor = ""
        global_min_dist = float("inf")
        for desc in descriptions:
            sd = desc.features.spatial_features.sensor_distances
            for sensor_id, info in sd.items():
                d = info["min_distance_km"]
                if d < global_min_dist:
                    global_min_dist = d
                    nearest_track_id = desc.track_id
                    nearest_sensor = sensor_id
                    nearest_distance_km = round(d, 1)

        display_sensor = nearest_sensor
        if nearest_sensor in self.radar_names:
            display_sensor = self.radar_names[nearest_sensor] + "站"

        highest_threat_level = 0
        if descriptions:
            highest_threat_level = max(
                desc.features.identity_features.emitter_threat_level for desc in descriptions
            )

        summary_text = (
            f"态势概况：共发现{total_tracks}个目标，"
            f"其中敌方{foe_count}个、友方{friend_count}个、身份不明{unknown_count}个。"
            f"距我方传感器最近的目标为{nearest_track_id}"
            f"（距{display_sensor}约{nearest_distance_km}km）。"
            f"最高威胁等级为{highest_threat_level}级。"
        )

        return SituationSummary(
            total_tracks=total_tracks,
            foe_count=foe_count,
            friend_count=friend_count,
            unknown_count=unknown_count,
            nearest_track_id=nearest_track_id,
            nearest_distance_km=nearest_distance_km,
            nearest_sensor=display_sensor,
            highest_threat_level=highest_threat_level,
            summary_text=summary_text,
        )
