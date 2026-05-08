import math
import random
import logging
from datetime import datetime
from typing import List, Dict, Optional

from .models_ext import IFFConfig, IFFReply
from .models import TargetTruth

logger = logging.getLogger(__name__)

_M_TO_FT = 3.28084


class IFF:
    def __init__(self, config: IFFConfig):
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

    def process_target(self, target: TargetTruth, identity: str) -> Optional[IFFReply]:
        los = self.calculate_line_of_sight(target.alt_m)
        r = self.calculate_range(target.lon, target.lat, target.alt_m)

        if r > los or r > self.config.max_range_km:
            return None

        if not self.config.crypto_valid:
            return IFFReply(
                time=target.time,
                target_id=target.target_id,
                iff_id=self.config.iff_id,
                interrogation_mode="4",
                identity="UNKNOWN",
                reply_received=False,
                crypto_valid=False,
                position_report=None,
                confidence=0.0
            )

        mode = "5" if "5" in self.config.modes else "4" if "4" in self.config.modes else "4"

        if identity == "FRIEND":
            if mode == "5":
                conf = 0.95
                position_report = {
                    "lat": target.lat + random.gauss(0, 0.0001),
                    "lon": target.lon + random.gauss(0, 0.0001),
                    "alt_m": target.alt_m + random.gauss(0, 10.0),
                    "source": "IFF_MODE5_GPS"
                }
            else:
                conf = 0.90
                position_report = None

            return IFFReply(
                time=target.time,
                target_id=target.target_id,
                iff_id=self.config.iff_id,
                interrogation_mode=mode,
                identity="FRIEND",
                reply_received=True,
                crypto_valid=True,
                position_report=position_report,
                confidence=conf
            )

        elif identity == "FOE":
            return IFFReply(
                time=target.time,
                target_id=target.target_id,
                iff_id=self.config.iff_id,
                interrogation_mode=mode,
                identity="FOE",
                reply_received=False,
                crypto_valid=True,
                position_report=None,
                confidence=0.60
            )

        else:
            return IFFReply(
                time=target.time,
                target_id=target.target_id,
                iff_id=self.config.iff_id,
                interrogation_mode=mode,
                identity="UNKNOWN",
                reply_received=False,
                crypto_valid=True,
                position_report=None,
                confidence=0.30
            )

    def process_targets(self, targets: List[TargetTruth],
                        target_identities: Dict[str, str]) -> List[IFFReply]:
        all_replies = []
        sampled = self._sample_by_scan_period(targets, self.config.scan_period)

        for target in sampled:
            identity = target_identities.get(target.target_id, "UNKNOWN")
            reply = self.process_target(target, identity)
            if reply is not None:
                all_replies.append(reply)

        logger.info(f"IFF {self.config.iff_id} 产生 {len(all_replies)} 条识别结果")
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
