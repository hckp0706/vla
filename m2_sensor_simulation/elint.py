import math
import random
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from .models_ext import ELINTConfig, ELINTReport, PDWRecord, EmitterParameters

logger = logging.getLogger(__name__)

_FREQUENCY_BANDS = [
    (1.0, 2.0, "L"),
    (2.0, 4.0, "S"),
    (4.0, 8.0, "C"),
    (8.0, 12.0, "X"),
    (12.0, 18.0, "Ku"),
    (18.0, 27.0, "K"),
    (27.0, 40.0, "Ka"),
    (0.3, 1.0, "UHF"),
    (0.0, 0.3, "VHF"),
]


def _get_frequency_band(freq_ghz: float) -> str:
    for low, high, name in _FREQUENCY_BANDS:
        if low <= freq_ghz < high:
            return name
    return "UNKNOWN"


class ELINT:
    def __init__(self, config: ELINTConfig, emitter_database: List[EmitterParameters]):
        self.config = config
        self.emitter_database = emitter_database
        self._last_analysis_time: Optional[datetime] = None

    def _cross_fix(self, pdw_records: List[PDWRecord],
                   esm_locations: Dict[str, Tuple[float, float]]) -> Optional[Tuple[float, float, float]]:
        if len(pdw_records) < self.config.min_stations_for_fix:
            return None

        lines = []
        for pdw in pdw_records:
            if pdw.esm_id not in esm_locations:
                continue
            loc = esm_locations[pdw.esm_id]
            az_rad = math.radians(pdw.aoa_deg)
            lines.append((loc[0], loc[1], az_rad))

        if len(lines) < 2:
            return None

        sum_x = 0.0
        sum_y = 0.0
        count = 0

        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                x1, y1, az1 = lines[i]
                x2, y2, az2 = lines[j]

                dx1 = math.sin(az1)
                dy1 = math.cos(az1)
                dx2 = math.sin(az2)
                dy2 = math.cos(az2)

                det = dx1 * dy2 - dx2 * dy1
                if abs(det) < 1e-10:
                    continue

                t = ((x2 - x1) * dy2 - (y2 - y1) * dx2) / det
                ix = x1 + t * dx1
                iy = y1 + t * dy1

                sum_x += ix
                sum_y += iy
                count += 1

        if count == 0:
            return None

        est_lon = sum_x / count
        est_lat = sum_y / count

        pos_errors = []
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                x1, y1, az1 = lines[i]
                x2, y2, az2 = lines[j]
                dx1, dy1 = math.sin(az1), math.cos(az1)
                dx2, dy2 = math.sin(az2), math.cos(az2)
                det = dx1 * dy2 - dx2 * dy1
                if abs(det) < 1e-10:
                    continue
                t = ((x2 - x1) * dy2 - (y2 - y1) * dx2) / det
                ix = x1 + t * dx1
                iy = y1 + t * dy1
                err_km = math.sqrt(((ix - est_lon) * 111.32)**2 + ((iy - est_lat) * 111.0)**2)
                pos_errors.append(err_km)

        avg_error = sum(pos_errors) / len(pos_errors) if pos_errors else 999.0

        return est_lon, est_lat, avg_error

    def _match_emitter(self, pdw_records: List[PDWRecord]) -> Tuple[str, float]:
        if not pdw_records:
            return "UNKNOWN", 0.0

        avg_rf = sum(p.rf_ghz for p in pdw_records) / len(pdw_records)
        avg_pw = sum(p.pw_us for p in pdw_records) / len(pdw_records)
        avg_pri = sum(p.pri_us for p in pdw_records) / len(pdw_records)

        best_match = "UNKNOWN"
        best_score = 0.0

        for emitter in self.emitter_database:
            if emitter.side != "FOE":
                continue

            rf_err = abs(avg_rf - emitter.frequency_ghz) / max(emitter.frequency_ghz, 0.01)
            pw_err = abs(avg_pw - emitter.pw_us) / max(emitter.pw_us, 0.01)
            pri_err = abs(avg_pri - emitter.pri_us) / max(emitter.pri_us, 0.01)

            score = max(0.0, 1.0 - rf_err) * 0.4 + max(0.0, 1.0 - pw_err) * 0.3 + max(0.0, 1.0 - pri_err) * 0.3
            score *= random.uniform(0.85, 1.0)

            if score > best_score:
                best_score = score
                best_match = emitter.radar_type

        if best_score < self.config.matching_threshold:
            return "UNKNOWN", best_score

        return best_match, best_score

    def _assess_threat(self, radar_type: str, distance_km: float,
                       operating_mode: str) -> int:
        base_threat = 3
        for emitter in self.emitter_database:
            if emitter.radar_type == radar_type:
                base_threat = emitter.threat_level
                break

        if distance_km < 100:
            modifier = 1
        elif distance_km < 200:
            modifier = 0
        elif distance_km < 400:
            modifier = -1
        else:
            modifier = -2

        if operating_mode == "TRACK":
            modifier += 1
        elif operating_mode == "GUIDANCE":
            modifier += 2

        return max(1, min(5, base_threat + modifier))

    def _analyze_operating_mode(self, pdw_records: List[PDWRecord]) -> str:
        if len(pdw_records) < 3:
            return "SEARCH"

        pris = [p.pri_us for p in pdw_records]
        pri_mean = sum(pris) / len(pris)
        pri_var = sum((p - pri_mean)**2 for p in pris) / len(pris)
        pri_cv = math.sqrt(pri_var) / max(pri_mean, 0.01)

        if pri_cv < 0.02:
            return "SEARCH"
        elif pri_cv < 0.1:
            return "TRACK"
        else:
            return "GUIDANCE"

    def analyze(self, pdw_by_emitter: Dict[str, List[PDWRecord]],
                esm_locations: Dict[str, Tuple[float, float]],
                current_time: datetime) -> List[ELINTReport]:
        if self._last_analysis_time is not None:
            elapsed = (current_time - self._last_analysis_time).total_seconds()
            if elapsed < self.config.analysis_period:
                return []

        self._last_analysis_time = current_time

        reports = []
        for emitter_id, pdw_list in pdw_by_emitter.items():
            if not pdw_list:
                continue

            avg_rf = sum(p.rf_ghz for p in pdw_list) / len(pdw_list)
            freq_band = _get_frequency_band(avg_rf)

            fix_result = self._cross_fix(pdw_list, esm_locations)
            if fix_result:
                est_lon, est_lat, pos_error = fix_result
            else:
                est_lon = 0.0
                est_lat = 0.0
                pos_error = 999.0

            radar_type, confidence = self._match_emitter(pdw_list)
            operating_mode = self._analyze_operating_mode(pdw_list)

            distance_km = 0.0
            if fix_result:
                for emitter in self.emitter_database:
                    if emitter.emitter_id == emitter_id:
                        d_lon = (emitter.location[0] - est_lon) * 111.32
                        d_lat = (emitter.location[1] - est_lat) * 111.0
                        distance_km = math.sqrt(d_lon**2 + d_lat**2)
                        break

            threat_level = self._assess_threat(radar_type, distance_km, operating_mode)

            contributing_esm = list(set(p.esm_id for p in pdw_list))

            reports.append(ELINTReport(
                time=current_time,
                emitter_id=emitter_id,
                elint_id=self.config.elint_id,
                radar_type_identified=radar_type,
                identification_confidence=confidence,
                emitter_lon=est_lon,
                emitter_lat=est_lat,
                position_error_km=pos_error,
                threat_level=threat_level,
                operating_mode=operating_mode,
                frequency_band=freq_band,
                contributing_esm=contributing_esm
            ))

        logger.info(f"ELINT {self.config.elint_id} 产生 {len(reports)} 条报告")
        return reports
