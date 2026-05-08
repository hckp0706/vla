import math
import random
import logging
from datetime import datetime
from typing import List, Dict, Optional

from .models_ext import ESMConfig, EmitterParameters, PDWRecord
from .models import TargetTruth

logger = logging.getLogger(__name__)

_C = 3e8
_K_BOLTZMANN = 1.38e-23
_SYSTEM_LOSS_DB = 10.0
_ESM_ANTENNA_GAIN_DB = 6.0


class ESM:
    def __init__(self, config: ESMConfig):
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

    def calculate_received_power(self, emitter: EmitterParameters) -> float:
        r = self.calculate_range(emitter.location[0], emitter.location[1], emitter.height)
        if r <= 0:
            return float('inf')

        r_m = r * 1000.0
        freq_hz = emitter.frequency_ghz * 1e9
        if freq_hz <= 0:
            return -999.0
        wavelength_m = _C / freq_hz

        fspl = 20 * math.log10(4 * math.pi * r_m / wavelength_m)

        pr_dbm = (emitter.power_dbm + emitter.antenna_gain_db +
                  _ESM_ANTENNA_GAIN_DB - fspl - _SYSTEM_LOSS_DB)
        return pr_dbm

    def identify_emitter(self, emitter: EmitterParameters) -> tuple:
        rf_match = True
        pw_match = True
        pri_match = True

        score = 0.0
        score += 0.4 if rf_match else 0.0
        score += 0.3 if pw_match else 0.0
        score += 0.3 if pri_match else 0.0

        confidence = score * random.uniform(0.85, 1.0)
        radar_type_est = emitter.radar_type if confidence > 0.5 else "UNKNOWN"

        return radar_type_est, confidence

    def process_emitter(self, emitter: EmitterParameters, current_time: datetime) -> Optional[PDWRecord]:
        if not emitter.active:
            return None

        if emitter.side != "FOE":
            return None

        if emitter.frequency_ghz < self.config.frequency_range_ghz[0] or \
           emitter.frequency_ghz > self.config.frequency_range_ghz[1]:
            return None

        los = self.calculate_line_of_sight(emitter.height)
        r = self.calculate_range(emitter.location[0], emitter.location[1], emitter.height)
        if r > los:
            return None

        pr_dbm = self.calculate_received_power(emitter)
        if pr_dbm < self.config.sensitivity_dbm:
            return None

        true_azimuth = self.calculate_azimuth(emitter.location[0], emitter.location[1])

        measured_rf = emitter.frequency_ghz + random.gauss(0, self.config.freq_accuracy_mhz / 1000.0)
        measured_pw = emitter.pw_us + random.gauss(0, self.config.pw_accuracy_us)
        measured_pri = emitter.pri_us + random.gauss(0, self.config.pri_accuracy_us)
        measured_aoa = (true_azimuth + random.gauss(0, self.config.df_accuracy_deg)) % 360.0
        measured_pa = pr_dbm + random.gauss(0, 1.0)

        radar_type_est, confidence = self.identify_emitter(emitter)

        return PDWRecord(
            time=current_time,
            esm_id=self.config.esm_id,
            emitter_id=emitter.emitter_id,
            rf_ghz=measured_rf,
            pw_us=measured_pw,
            pri_us=measured_pri,
            aoa_deg=measured_aoa,
            pa_dbm=measured_pa,
            modulation=emitter.modulation,
            radar_type_est=radar_type_est,
            confidence=confidence
        )

    def process_emitters(self, emitters: List[EmitterParameters],
                         time_points: List[datetime]) -> List[PDWRecord]:
        all_pdw = []
        sampled_times = self._sample_by_scan_period(time_points, self.config.scan_period)

        for t in sampled_times:
            for emitter in emitters:
                pdw = self.process_emitter(emitter, t)
                if pdw is not None:
                    all_pdw.append(pdw)

        logger.info(f"ESM {self.config.esm_id} 产生 {len(all_pdw)} 条PDW记录")
        return all_pdw

    def process_airborne_emitter(self, emitter_template: EmitterParameters,
                                  targets: List[TargetTruth]) -> List[PDWRecord]:
        all_pdw = []
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

            moving_emitter = EmitterParameters(
                emitter_id=emitter_template.emitter_id,
                location=[target.lon, target.lat],
                height=target.alt_m,
                frequency_ghz=emitter_template.frequency_ghz,
                pri_us=emitter_template.pri_us,
                pw_us=emitter_template.pw_us,
                power_dbm=emitter_template.power_dbm,
                antenna_gain_db=emitter_template.antenna_gain_db,
                scan_period=emitter_template.scan_period,
                radar_type=emitter_template.radar_type,
                modulation=emitter_template.modulation,
                threat_level=emitter_template.threat_level,
                side=emitter_template.side,
                active=emitter_template.active
            )

            pdw = self.process_emitter(moving_emitter, t)
            if pdw is not None:
                all_pdw.append(pdw)

        logger.info(f"ESM {self.config.esm_id} 机载辐射源探测产生 {len(all_pdw)} 条PDW记录")
        return all_pdw

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
