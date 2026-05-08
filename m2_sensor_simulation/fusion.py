import logging
import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from .models import TrackPoint, TargetTruth
from .models_ext import (
    SSRReply, IFFReply, PDWRecord, ELINTReport, COMINTReport,
    FusedTrackPoint, FusedNetworkTracks
)

logger = logging.getLogger(__name__)

_M_TO_FT = 3.28084


class FusionEngine:
    def __init__(self):
        pass

    def fuse_identity(self, iff_replies: List[IFFReply],
                      ssr_replies: List[SSRReply],
                      esm_pdws: List[PDWRecord]) -> Tuple[str, str, float]:
        iff_foe = False
        iff_foe_conf = 0.0
        iff_foe_source = ""
        iff_no_reply = False
        iff_no_reply_conf = 0.0
        iff_no_reply_source = ""
        iff_friend = False
        iff_friend_conf = 0.0
        iff_friend_source = ""

        if iff_replies:
            friend_replies = [r for r in iff_replies if r.identity == "FRIEND" and r.reply_received]
            foe_replies = [r for r in iff_replies if r.identity == "FOE"]
            unknown_replies = [r for r in iff_replies if r.identity == "UNKNOWN" and r.reply_received is False and r.crypto_valid]

            if friend_replies:
                best = max(friend_replies, key=lambda r: r.confidence)
                iff_friend = True
                iff_friend_conf = best.confidence
                iff_friend_source = f"IFF_MODE{best.interrogation_mode}"

            if foe_replies:
                best = max(foe_replies, key=lambda r: r.confidence)
                iff_foe = True
                iff_foe_conf = best.confidence
                iff_foe_source = f"IFF_MODE{best.interrogation_mode}"

            if unknown_replies:
                count = len(unknown_replies)
                iff_ids = list(set(r.iff_id for r in unknown_replies))
                iff_no_reply = True
                iff_no_reply_conf = min(0.30 + 0.10 * count, 0.70)
                iff_no_reply_source = f"IFF_NO_REPLY({'+'.join(iff_ids)})"

        esm_foe = False
        esm_foe_conf = 0.0
        esm_foe_source = ""
        if esm_pdws:
            esm_foe = True
            esm_foe_conf = 0.50
            esm_foe_source = "ESM_INFERENCE"
            esm_ids = list(set(p.esm_id for p in esm_pdws))
            if len(esm_ids) >= 2:
                esm_foe_conf = 0.60
                esm_foe_source = f"ESM_CROSS_FIX({'+'.join(esm_ids)})"

        if iff_friend:
            return "FRIEND", iff_friend_source, iff_friend_conf

        if iff_foe and esm_foe:
            combined = min(iff_foe_conf + esm_foe_conf * 0.3, 0.95)
            return "FOE", f"{iff_foe_source}+{esm_foe_source}", combined

        if iff_foe:
            return "FOE", iff_foe_source, iff_foe_conf

        if iff_no_reply and esm_foe:
            combined = min(iff_no_reply_conf + esm_foe_conf * 0.3, 0.90)
            return "FOE", f"{iff_no_reply_source}+{esm_foe_source}", combined

        if iff_no_reply:
            return "FOE", iff_no_reply_source, iff_no_reply_conf

        if esm_foe:
            return "FOE", esm_foe_source, esm_foe_conf

        if ssr_replies:
            valid_ssr = [r for r in ssr_replies if r.reply_valid and not r.is_fruit]
            if valid_ssr:
                mode_s = [r for r in valid_ssr if r.reply_mode == "S" and r.icao24]
                if mode_s:
                    return "NEUTRAL", "SSR_MODE_S", 0.80
                mode_3a = [r for r in valid_ssr if r.reply_mode == "3A"]
                if mode_3a:
                    return "NEUTRAL", "SSR_MODE_3A", 0.70

        no_sensor_data = not iff_replies and not ssr_replies and not esm_pdws
        if no_sensor_data:
            return "UNKNOWN", "NONE", 0.10

        return "UNKNOWN", "IFF_NO_DATA", 0.20

    def fuse_altitude(self, ssr_replies: List[SSRReply],
                      radar_alt_m: float) -> Tuple[float, str, float]:
        if ssr_replies:
            valid_c = [r for r in ssr_replies if r.reply_mode == "C" and r.reply_valid and not r.is_fruit]
            if valid_c:
                avg_alt_ft = sum(r.altitude_ft for r in valid_c) / len(valid_c)
                return avg_alt_ft, "SSR_MODE_C", avg_alt_ft / _M_TO_FT

            valid_s = [r for r in ssr_replies if r.reply_mode == "S" and r.reply_valid and not r.is_fruit]
            if valid_s:
                avg_alt_ft = sum(r.altitude_ft for r in valid_s) / len(valid_s)
                return avg_alt_ft, "SSR_MODE_S", avg_alt_ft / _M_TO_FT

        alt_ft = radar_alt_m * _M_TO_FT
        return alt_ft, "RADAR", radar_alt_m

    def fuse_ssridentity_info(self, ssr_replies: List[SSRReply]) -> Tuple[str, str, str]:
        valid = [r for r in ssr_replies if r.reply_valid and not r.is_fruit]
        squawk = ""
        icao24 = ""
        callsign = ""

        for r in valid:
            if r.squawk and not squawk:
                squawk = r.squawk
            if r.icao24 and not icao24:
                icao24 = r.icao24
            if r.callsign and not callsign:
                callsign = r.callsign

        return squawk, icao24, callsign

    def fuse_elint_info(self, elint_reports: List[ELINTReport],
                        target_id: str) -> Tuple[str, int]:
        if not elint_reports:
            return "", 0

        best = max(elint_reports, key=lambda r: r.identification_confidence)
        return best.radar_type_identified, best.threat_level

    def fuse_comm_info(self, comint_reports: List[COMINTReport],
                       target_id: str) -> str:
        if not comint_reports:
            return ""

        networks = set(r.network_id for r in comint_reports if r.intercepted)
        if networks:
            return f"ACTIVE_COMM:{','.join(networks)}"
        return ""

    def fuse_track(self, radar_track: TrackPoint,
                   iff_replies: List[IFFReply],
                   ssr_replies: List[SSRReply],
                   esm_pdws: List[PDWRecord],
                   elint_reports: List[ELINTReport],
                   comint_reports: List[COMINTReport]) -> FusedTrackPoint:
        identity, identity_source, identity_confidence = self.fuse_identity(
            iff_replies, ssr_replies, esm_pdws
        )

        altitude_ft, altitude_source, alt_m = self.fuse_altitude(
            ssr_replies, radar_track.obs_alt_m
        )

        squawk, icao24, callsign = self.fuse_ssridentity_info(ssr_replies)

        emitter_type, emitter_threat_level = self.fuse_elint_info(elint_reports, radar_track.target_id)

        comm_activity = self.fuse_comm_info(comint_reports, radar_track.target_id)

        source_sensors = list(radar_track.source_radars)
        for r in ssr_replies:
            if r.ssr_id not in source_sensors:
                source_sensors.append(r.ssr_id)
        for r in iff_replies:
            if r.iff_id not in source_sensors:
                source_sensors.append(r.iff_id)
        for p in esm_pdws:
            if p.esm_id not in source_sensors:
                source_sensors.append(p.esm_id)
        for r in elint_reports:
            if r.elint_id not in source_sensors:
                source_sensors.append(r.elint_id)
        for r in comint_reports:
            if r.comint_id not in source_sensors:
                source_sensors.append(r.comint_id)

        return FusedTrackPoint(
            time=radar_track.time,
            track_id=radar_track.track_id,
            target_id=radar_track.target_id,
            obs_lon=radar_track.obs_lon,
            obs_lat=radar_track.obs_lat,
            obs_alt_m=alt_m,
            obs_speed_ms=radar_track.obs_speed_ms,
            obs_heading_deg=radar_track.obs_heading_deg,
            track_quality=radar_track.track_quality,
            snr_avg_db=radar_track.snr_avg_db,
            source_radars=radar_track.source_radars,
            identity=identity,
            identity_source=identity_source,
            identity_confidence=identity_confidence,
            squawk=squawk,
            callsign=callsign,
            icao24=icao24,
            altitude_source=altitude_source,
            altitude_ft=altitude_ft,
            emitter_type=emitter_type,
            emitter_threat_level=emitter_threat_level,
            comm_activity=comm_activity,
            source_sensors=source_sensors,
            sensor_count=len(source_sensors),
            fusion_timestamp=datetime.now().isoformat() + 'Z'
        )

    def fuse_all(self, radar_fused_tracks: List[TrackPoint],
                 ssr_replies_by_time: Dict[datetime, List[SSRReply]],
                 iff_replies_by_time: Dict[datetime, List[IFFReply]],
                 esm_pdws_by_time: Dict[datetime, List[PDWRecord]],
                 elint_reports_by_time: Dict[datetime, List[ELINTReport]],
                 comint_reports_by_time: Dict[datetime, List[COMINTReport]],
                 time_window_seconds: float = 5.0) -> FusedNetworkTracks:
        fused_points = []

        for track in radar_fused_tracks:
            t = track.time
            window_start = t - timedelta(seconds=time_window_seconds)
            window_end = t + timedelta(seconds=time_window_seconds)

            matching_ssr = self._collect_in_window(ssr_replies_by_time, t, window_start, window_end, "target_id", track.target_id)
            matching_iff = self._collect_in_window(iff_replies_by_time, t, window_start, window_end, "target_id", track.target_id)
            matching_esm = self._collect_in_window(esm_pdws_by_time, t, window_start, window_end)
            matching_elint = self._collect_in_window(elint_reports_by_time, t, window_start, window_end)
            matching_comint = self._collect_in_window(comint_reports_by_time, t, window_start, window_end)

            fused = self.fuse_track(track, matching_iff, matching_ssr, matching_esm, matching_elint, matching_comint)
            fused_points.append(fused)

        logger.info(f"融合引擎产生 {len(fused_points)} 条综合航迹点")
        return FusedNetworkTracks(
            frame_time=datetime.now().isoformat() + 'Z',
            network_tracks=fused_points
        )

    def fuse_comprehensive(self, targets: List[TargetTruth],
                           radar_observations_by_time: Dict[datetime, List[dict]],
                           ssr_replies_by_time: Dict[datetime, List[SSRReply]],
                           iff_replies_by_time: Dict[datetime, List[IFFReply]],
                           esm_pdws_by_time: Dict[datetime, List[PDWRecord]],
                           elint_reports_by_time: Dict[datetime, List[ELINTReport]],
                           comint_reports_by_time: Dict[datetime, List[COMINTReport]],
                           time_window_seconds: float = 5.0) -> FusedNetworkTracks:
        fused_points = []
        target_id = targets[0].target_id if targets else "0000"

        last_known_pos = None

        for target in targets:
            t = target.time
            window_start = t - timedelta(seconds=time_window_seconds)
            window_end = t + timedelta(seconds=time_window_seconds)

            matching_radar_obs = self._collect_in_window(
                radar_observations_by_time, t, window_start, window_end
            )
            matching_radar_for_target = [
                obs for obs in matching_radar_obs
                if obs.get('target_id') == target.target_id
            ]

            matching_ssr = self._collect_in_window(
                ssr_replies_by_time, t, window_start, window_end, "target_id", target.target_id
            )
            matching_iff = self._collect_in_window(
                iff_replies_by_time, t, window_start, window_end, "target_id", target.target_id
            )
            matching_esm = self._collect_in_window(
                esm_pdws_by_time, t, window_start, window_end
            )
            matching_elint = self._collect_in_window(
                elint_reports_by_time, t, window_start, window_end
            )
            matching_comint = self._collect_in_window(
                comint_reports_by_time, t, window_start, window_end
            )

            obs_lon, obs_lat, obs_alt, obs_speed, obs_heading, position_source = self._fuse_position(
                target, matching_radar_for_target, matching_iff, matching_ssr, last_known_pos
            )

            if matching_radar_for_target:
                last_known_pos = (obs_lon, obs_lat, obs_alt)

            identity, identity_source, identity_confidence = self.fuse_identity(
                matching_iff, matching_ssr, matching_esm
            )

            radar_alt_m = obs_alt
            if matching_radar_for_target:
                radar_alt_m = matching_radar_for_target[0]['obs_alt']
            altitude_ft, altitude_source, alt_m = self.fuse_altitude(
                matching_ssr, radar_alt_m
            )

            squawk, icao24, callsign = self.fuse_ssridentity_info(matching_ssr)
            emitter_type, emitter_threat_level = self.fuse_elint_info(matching_elint, target.target_id)
            comm_activity = self.fuse_comm_info(matching_comint, target.target_id)

            source_sensors = []
            source_radars = []
            snr_avg = 0.0
            track_quality = "LOST"

            if matching_radar_for_target:
                source_radars = list(set(obs['radar_id'] for obs in matching_radar_for_target))
                snr_avg = sum(obs['snr'] for obs in matching_radar_for_target) / len(matching_radar_for_target)
                source_sensors.extend(source_radars)

            ssr_ids = list(set(r.ssr_id for r in matching_ssr))
            iff_ids = list(set(r.iff_id for r in matching_iff))
            esm_ids = list(set(p.esm_id for p in matching_esm))
            elint_ids = list(set(r.elint_id for r in matching_elint))
            comint_ids = list(set(r.comint_id for r in matching_comint))

            for sid in ssr_ids:
                if sid not in source_sensors:
                    source_sensors.append(sid)
            for sid in iff_ids:
                if sid not in source_sensors:
                    source_sensors.append(sid)
            for sid in esm_ids:
                if sid not in source_sensors:
                    source_sensors.append(sid)
            for sid in elint_ids:
                if sid not in source_sensors:
                    source_sensors.append(sid)
            for sid in comint_ids:
                if sid not in source_sensors:
                    source_sensors.append(sid)

            total_sensor_count = (
                len(source_radars) + len(ssr_ids) + len(iff_ids)
                + len(esm_ids) + len(elint_ids) + len(comint_ids)
            )

            if len(source_radars) >= 3:
                track_quality = "HIGH"
            elif len(source_radars) >= 2:
                track_quality = "MEDIUM"
            elif len(source_radars) == 1:
                track_quality = "MEDIUM" if total_sensor_count >= 3 else "LOW"
            elif total_sensor_count >= 3:
                track_quality = "MEDIUM"
            elif total_sensor_count >= 2:
                track_quality = "LOW"
            elif total_sensor_count == 1:
                track_quality = "LOW"
            else:
                track_quality = "LOST"

            fused_point = FusedTrackPoint(
                time=t,
                track_id=target_id,
                target_id=target.target_id,
                obs_lon=obs_lon,
                obs_lat=obs_lat,
                obs_alt_m=alt_m if matching_ssr else obs_alt,
                obs_speed_ms=obs_speed,
                obs_heading_deg=obs_heading,
                track_quality=track_quality,
                snr_avg_db=snr_avg,
                source_radars=source_radars,
                identity=identity,
                identity_source=identity_source,
                identity_confidence=identity_confidence,
                squawk=squawk,
                callsign=callsign,
                icao24=icao24,
                altitude_source=altitude_source,
                altitude_ft=altitude_ft,
                emitter_type=emitter_type,
                emitter_threat_level=emitter_threat_level,
                comm_activity=comm_activity,
                position_source=position_source,
                source_sensors=source_sensors,
                sensor_count=len(source_sensors),
                fusion_timestamp=datetime.now().isoformat() + 'Z'
            )
            fused_points.append(fused_point)

        logger.info(f"综合融合引擎产生 {len(fused_points)} 条完整航迹点")
        return FusedNetworkTracks(
            frame_time=datetime.now().isoformat() + 'Z',
            network_tracks=fused_points
        )

    def _fuse_position(self, target: TargetTruth,
                       radar_obs: List[dict],
                       iff_replies: List[IFFReply],
                       ssr_replies: List[SSRReply],
                       last_known_pos: Optional[Tuple[float, float, float]]) -> Tuple[float, float, float, float, float, str]:
        lon = target.lon
        lat = target.lat
        alt = target.alt_m
        speed = target.speed_ms
        heading = target.heading_deg
        pos_source = "TRUTH"

        if radar_obs:
            total_snr = sum(obs['snr'] for obs in radar_obs)
            if total_snr == 0:
                total_snr = 1
            lon = sum(obs['obs_lon'] * obs['snr'] for obs in radar_obs) / total_snr
            lat = sum(obs['obs_lat'] * obs['snr'] for obs in radar_obs) / total_snr
            alt = sum(obs['obs_alt'] * obs['snr'] for obs in radar_obs) / total_snr
            speed = sum(obs['obs_speed'] * obs['snr'] for obs in radar_obs) / total_snr
            heading = sum(obs['obs_heading'] * obs['snr'] for obs in radar_obs) / total_snr
            return lon, lat, alt, speed, heading, "RADAR"

        iff_with_pos = [r for r in iff_replies if r.reply_received and r.position_report]
        if iff_with_pos:
            best_iff = max(iff_with_pos, key=lambda r: r.confidence)
            pr = best_iff.position_report
            lon = pr.get('lon', lon) + 0.0
            lat = pr.get('lat', lat) + 0.0
            alt = pr.get('alt_m', alt) + 0.0
            return lon, lat, alt, speed, heading, "IFF_MODE5"

        valid_ssr = [r for r in ssr_replies if r.reply_valid and not r.is_fruit and r.altitude_ft > 0]
        if valid_ssr and last_known_pos:
            alt = valid_ssr[0].altitude_ft / _M_TO_FT
            lon = last_known_pos[0]
            lat = last_known_pos[1]
            return lon, lat, alt, speed, heading, "SSR_ALT"

        if last_known_pos:
            return last_known_pos[0], last_known_pos[1], alt, speed, heading, "LAST_KNOWN"

        return lon, lat, alt, speed, heading, "TRUTH"

    def _collect_in_window(self, data_by_time: Dict, target_time: datetime,
                           window_start: datetime, window_end: datetime,
                           filter_field: str = None, filter_value: str = None) -> list:
        results = []
        for t, records in data_by_time.items():
            if window_start <= t <= window_end:
                if filter_field and filter_value:
                    filtered = [r for r in records if getattr(r, filter_field, None) == filter_value]
                    results.extend(filtered)
                else:
                    results.extend(records)
        return results
