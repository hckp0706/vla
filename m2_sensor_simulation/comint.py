import math
import random
import logging
from datetime import datetime
from typing import List, Dict, Optional

from .models_ext import COMINTConfig, CommEmitter, COMINTReport
from .models import TargetTruth

logger = logging.getLogger(__name__)

_SYSTEM_LOSS_DB = 8.0
_COMINT_ANTENNA_GAIN_DB = 3.0
_C = 3e8


class COMINT:
    def __init__(self, config: COMINTConfig):
        self.config = config

    def calculate_line_of_sight(self, emitter_alt: float) -> float:
        h1 = self.config.height
        h2 = emitter_alt
        los = 4.12 * (math.sqrt(h1) + math.sqrt(h2))
        return max(los, 1.0)

    def calculate_range(self, emitter_lon: float, emitter_lat: float, emitter_alt: float) -> float:
        sensor_lon, sensor_lat = self.config.location
        sensor_alt = self.config.height
        delta_lon_km = (emitter_lon - sensor_lon) * 111.32
        delta_lat_km = (emitter_lat - sensor_lat) * 111.0
        delta_alt_km = (emitter_alt - sensor_alt) / 1000.0
        return math.sqrt(delta_lon_km**2 + delta_lat_km**2 + delta_alt_km**2)

    def calculate_azimuth(self, emitter_lon: float, emitter_lat: float) -> float:
        sensor_lon, sensor_lat = self.config.location
        delta_lon = emitter_lon - sensor_lon
        delta_lat = emitter_lat - sensor_lat
        azimuth = math.degrees(math.atan2(delta_lon, delta_lat))
        return (azimuth + 360.0) % 360.0

    def _is_frequency_covered(self, freq_mhz: float) -> bool:
        for freq_range in self.config.frequency_ranges_mhz:
            if freq_range[0] <= freq_mhz <= freq_range[1]:
                return True
        return False

    def _calculate_received_power(self, emitter: CommEmitter) -> float:
        r = self.calculate_range(emitter.location[0], emitter.location[1], emitter.height)
        if r <= 0:
            return float('inf')

        r_m = r * 1000.0
        freq_hz = emitter.frequency_mhz * 1e6
        if freq_hz <= 0:
            return -999.0
        wavelength_m = _C / freq_hz

        fspl = 20 * math.log10(4 * math.pi * r_m / wavelength_m)

        pr_dbm = emitter.power_dbm + _COMINT_ANTENNA_GAIN_DB - fspl - _SYSTEM_LOSS_DB
        return pr_dbm

    def _classify_message_type(self, comm_type: str) -> str:
        if comm_type == "HF":
            return "LONG_RANGE_COMMAND"
        elif comm_type == "VHF":
            return "TACTICAL_COORDINATION"
        elif comm_type == "UHF":
            return "DATA_LINK"
        return "UNKNOWN"

    def process_emitter(self, emitter: CommEmitter, current_time: datetime) -> Optional[COMINTReport]:
        if not emitter.active:
            return None

        if emitter.side != "FOE":
            return None

        if not self._is_frequency_covered(emitter.frequency_mhz):
            return None

        los = self.calculate_line_of_sight(emitter.height)
        r = self.calculate_range(emitter.location[0], emitter.location[1], emitter.height)
        if r > los:
            return None

        pr_dbm = self._calculate_received_power(emitter)
        if pr_dbm < self.config.sensitivity_dbm:
            return None

        true_azimuth = self.calculate_azimuth(emitter.location[0], emitter.location[1])
        measured_aoa = (true_azimuth + random.gauss(0, self.config.df_accuracy_deg)) % 360.0
        measured_freq = emitter.frequency_mhz + random.gauss(0, 0.1)

        message_type = self._classify_message_type(emitter.comm_type)

        return COMINTReport(
            time=current_time,
            comint_id=self.config.comint_id,
            emitter_id=emitter.emitter_id,
            comm_freq_mhz=measured_freq,
            comm_type=emitter.comm_type,
            aoa_deg=measured_aoa,
            intercepted=True,
            network_id=emitter.network_id,
            message_type=message_type
        )

    def process_emitters(self, emitters: List[CommEmitter],
                         time_points: List[datetime]) -> List[COMINTReport]:
        all_reports = []
        sampled_times = self._sample_by_scan_period(time_points, self.config.scan_period)

        for t in sampled_times:
            for emitter in emitters:
                report = self.process_emitter(emitter, t)
                if report is not None:
                    all_reports.append(report)

        logger.info(f"COMINT {self.config.comint_id} 产生 {len(all_reports)} 条截获报告")
        return all_reports

    def process_airborne_emitter(self, emitter_template: CommEmitter,
                                  targets: List[TargetTruth]) -> List[COMINTReport]:
        all_reports = []
        sampled = self._sample_by_scan_period(
            [t.time for t in targets], self.config.scan_period
        )

        time_target_map = {}
        for target in targets:
            time_target_map[target.time] = target

        for t in sampled:
            target = time_target_map.get(t)
            if target is None:
                continue

            moving_emitter = CommEmitter(
                emitter_id=emitter_template.emitter_id,
                location=[target.lon, target.lat],
                height=target.alt_m,
                frequency_mhz=emitter_template.frequency_mhz,
                power_dbm=emitter_template.power_dbm,
                comm_type=emitter_template.comm_type,
                network_id=emitter_template.network_id,
                side=emitter_template.side,
                active=emitter_template.active
            )

            report = self.process_emitter(moving_emitter, t)
            if report is not None:
                all_reports.append(report)

        logger.info(f"COMINT {self.config.comint_id} 机载通信截获产生 {len(all_reports)} 条报告")
        return all_reports

    def _sample_by_scan_period(self, time_points: List[datetime], scan_period: float) -> List[datetime]:
        if not time_points:
            return []
        sampled = []
        last_time = None
        for t in time_points:
            if last_time is None:
                sampled.append(t)
                last_time = t
            else:
                time_diff = (t - last_time).total_seconds()
                if time_diff >= scan_period:
                    sampled.append(t)
                    last_time = t
        return sampled
