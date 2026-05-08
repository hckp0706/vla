import math
import random
import logging
from datetime import datetime
from typing import List, Dict, Optional

from .models_ext import SSRConfig, SSRReply
from .models import TargetTruth

logger = logging.getLogger(__name__)

_M_TO_FT = 3.28084


class SSR:
    def __init__(self, config: SSRConfig):
        self.config = config

    def calculate_line_of_sight(self, target_alt: float) -> float:
        h1 = self.config.height
        h2 = target_alt
        los = 4.12 * (math.sqrt(h1) + math.sqrt(h2))
        return max(los, 1.0)

    def calculate_range(self, target_lon: float, target_lat: float, target_alt: float) -> float:
        sensor_lon, sensor_lat = self.config.location
        sensor_alt = self.config.height
        delta_lon_km = (target_lon - sensor_lon) * 111.32
        delta_lat_km = (target_lat - sensor_lat) * 111.0
        delta_alt_km = (target_alt - sensor_alt) / 1000.0
        return math.sqrt(delta_lon_km**2 + delta_lat_km**2 + delta_alt_km**2)

    def calculate_azimuth(self, target_lon: float, target_lat: float) -> float:
        sensor_lon, sensor_lat = self.config.location
        delta_lon = target_lon - sensor_lon
        delta_lat = target_lat - sensor_lat
        azimuth = math.degrees(math.atan2(delta_lon, delta_lat))
        return (azimuth + 360.0) % 360.0

    def can_reply(self, target: TargetTruth, has_adsb: bool, identity: str) -> bool:
        if has_adsb:
            return True
        if identity == "FRIEND":
            return False
        return False

    def is_sls_valid(self, target_azimuth: float, beam_azimuth: float) -> bool:
        angle_diff = abs(target_azimuth - beam_azimuth)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        return angle_diff <= 45.0

    def process_target(self, target: TargetTruth, has_adsb: bool,
                       identity: str, adsb_data: Optional[Dict]) -> List[SSRReply]:
        replies = []

        los = self.calculate_line_of_sight(target.alt_m)
        r = self.calculate_range(target.lon, target.lat, target.alt_m)

        if r > los or r > self.config.max_range_km:
            return replies

        if not self.can_reply(target, has_adsb, identity):
            return replies

        target_azimuth = self.calculate_azimuth(target.lon, target.lat)
        sls_valid = self.is_sls_valid(target_azimuth, target_azimuth)

        for mode in self.config.modes:
            if random.random() > self.config.reply_probability:
                replies.append(SSRReply(
                    time=target.time,
                    target_id=target.target_id,
                    ssr_id=self.config.ssr_id,
                    reply_mode=mode,
                    squawk="",
                    altitude_ft=0.0,
                    icao24="",
                    callsign="",
                    reply_valid=False,
                    sls_valid=sls_valid,
                    is_fruit=False
                ))
                continue

            if not sls_valid:
                replies.append(SSRReply(
                    time=target.time,
                    target_id=target.target_id,
                    ssr_id=self.config.ssr_id,
                    reply_mode=mode,
                    squawk="",
                    altitude_ft=0.0,
                    icao24="",
                    callsign="",
                    reply_valid=False,
                    sls_valid=False,
                    is_fruit=False
                ))
                continue

            squawk = ""
            altitude_ft = 0.0
            icao24 = ""
            callsign = ""

            if adsb_data:
                squawk = adsb_data.get("squawk", "2000")
                altitude_ft = adsb_data.get("altitude_ft", target.alt_m * _M_TO_FT)
                icao24 = adsb_data.get("icao24", "")
                callsign = adsb_data.get("callsign", "")
            else:
                altitude_ft = target.alt_m * _M_TO_FT

            if mode == "C":
                altitude_ft = round(altitude_ft / 100.0) * 100.0
                squawk = ""
                icao24 = ""
                callsign = ""
            elif mode == "3A":
                altitude_ft = 0.0
                icao24 = ""
                callsign = ""

            is_fruit = random.random() < self.config.fruit_rate

            replies.append(SSRReply(
                time=target.time,
                target_id=target.target_id,
                ssr_id=self.config.ssr_id,
                reply_mode=mode,
                squawk=squawk,
                altitude_ft=altitude_ft,
                icao24=icao24,
                callsign=callsign,
                reply_valid=True,
                sls_valid=True,
                is_fruit=is_fruit
            ))

        return replies

    def process_targets(self, targets: List[TargetTruth],
                        target_adsb_map: Dict[str, List[Dict]],
                        target_identities: Dict[str, str]) -> List[SSRReply]:
        all_replies = []
        sampled = self._sample_by_scan_period(targets, self.config.scan_period)

        for target in sampled:
            has_adsb = target.target_id in target_adsb_map and len(target_adsb_map[target.target_id]) > 0
            identity = target_identities.get(target.target_id, "UNKNOWN")
            adsb_data = None
            if has_adsb:
                adsb_list = target_adsb_map[target.target_id]
                for ad in adsb_list:
                    ad_time = ad.get("time")
                    if ad_time and abs((target.time - ad_time).total_seconds()) < 2.0:
                        adsb_data = ad
                        break
                if adsb_data is None and adsb_list:
                    adsb_data = adsb_list[0]

            replies = self.process_target(target, has_adsb, identity, adsb_data)
            all_replies.extend(replies)

        logger.info(f"SSR {self.config.ssr_id} 产生 {len(all_replies)} 条应答")
        return all_replies

    def _sample_by_scan_period(self, targets: List[TargetTruth], scan_period: float) -> List[TargetTruth]:
        if not targets:
            return []
        sampled = []
        last_time = None
        for target in targets:
            if last_time is None:
                sampled.append(target)
                last_time = target.time
            else:
                time_diff = (target.time - last_time).total_seconds()
                if time_diff >= scan_period:
                    sampled.append(target)
                    last_time = target.time
        return sampled
