from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
import json


@dataclass
class SSRConfig:
    ssr_id: str
    location: List[float]
    height: float
    max_range_km: float
    modes: List[str]
    scan_period: float
    reply_probability: float
    fruit_rate: float
    co_located_radar: Optional[str] = None


@dataclass
class SSRReply:
    time: datetime
    target_id: str
    ssr_id: str
    reply_mode: str
    squawk: str
    altitude_ft: float
    icao24: str
    callsign: str
    reply_valid: bool
    sls_valid: bool
    is_fruit: bool

    def to_dict(self) -> Dict:
        return {
            "time": self.time.isoformat() + 'Z' if self.time.tzinfo is None else self.time.isoformat(),
            "target_id": self.target_id,
            "ssr_id": self.ssr_id,
            "reply_mode": self.reply_mode,
            "squawk": self.squawk,
            "altitude_ft": round(self.altitude_ft, 1),
            "icao24": self.icao24,
            "callsign": self.callsign,
            "reply_valid": self.reply_valid,
            "sls_valid": self.sls_valid,
            "is_fruit": self.is_fruit
        }


@dataclass
class IFFConfig:
    iff_id: str
    location: List[float]
    height: float
    max_range_km: float
    modes: List[str]
    scan_period: float
    crypto_valid: bool
    co_located_radar: Optional[str] = None


@dataclass
class IFFReply:
    time: datetime
    target_id: str
    iff_id: str
    interrogation_mode: str
    identity: str
    reply_received: bool
    crypto_valid: bool
    position_report: Optional[Dict]
    confidence: float

    def to_dict(self) -> Dict:
        return {
            "time": self.time.isoformat() + 'Z' if self.time.tzinfo is None else self.time.isoformat(),
            "target_id": self.target_id,
            "iff_id": self.iff_id,
            "interrogation_mode": self.interrogation_mode,
            "identity": self.identity,
            "reply_received": self.reply_received,
            "crypto_valid": self.crypto_valid,
            "position_report": self.position_report,
            "confidence": round(self.confidence, 3)
        }


@dataclass
class ESMConfig:
    esm_id: str
    location: List[float]
    height: float
    frequency_range_ghz: List[float]
    sensitivity_dbm: float
    df_accuracy_deg: float
    freq_accuracy_mhz: float
    pri_accuracy_us: float
    pw_accuracy_us: float
    scan_period: float


@dataclass
class EmitterParameters:
    emitter_id: str
    location: List[float]
    height: float
    frequency_ghz: float
    pri_us: float
    pw_us: float
    power_dbm: float
    antenna_gain_db: float
    scan_period: float
    radar_type: str
    modulation: str
    threat_level: int
    side: str
    active: bool = True


@dataclass
class PDWRecord:
    time: datetime
    esm_id: str
    emitter_id: str
    rf_ghz: float
    pw_us: float
    pri_us: float
    aoa_deg: float
    pa_dbm: float
    modulation: str
    radar_type_est: str
    confidence: float

    def to_dict(self) -> Dict:
        return {
            "time": self.time.isoformat() + 'Z' if self.time.tzinfo is None else self.time.isoformat(),
            "esm_id": self.esm_id,
            "emitter_id": self.emitter_id,
            "rf_ghz": round(self.rf_ghz, 4),
            "pw_us": round(self.pw_us, 3),
            "pri_us": round(self.pri_us, 3),
            "aoa_deg": round(self.aoa_deg, 2),
            "pa_dbm": round(self.pa_dbm, 1),
            "modulation": self.modulation,
            "radar_type_est": self.radar_type_est,
            "confidence": round(self.confidence, 3)
        }


@dataclass
class ELINTConfig:
    elint_id: str
    min_stations_for_fix: int
    matching_threshold: float
    analysis_period: float


@dataclass
class ELINTReport:
    time: datetime
    emitter_id: str
    elint_id: str
    radar_type_identified: str
    identification_confidence: float
    emitter_lon: float
    emitter_lat: float
    position_error_km: float
    threat_level: int
    operating_mode: str
    frequency_band: str
    contributing_esm: List[str]

    def to_dict(self) -> Dict:
        return {
            "time": self.time.isoformat() + 'Z' if self.time.tzinfo is None else self.time.isoformat(),
            "emitter_id": self.emitter_id,
            "elint_id": self.elint_id,
            "radar_type_identified": self.radar_type_identified,
            "identification_confidence": round(self.identification_confidence, 3),
            "emitter_lon": round(self.emitter_lon, 4),
            "emitter_lat": round(self.emitter_lat, 4),
            "position_error_km": round(self.position_error_km, 2),
            "threat_level": self.threat_level,
            "operating_mode": self.operating_mode,
            "frequency_band": self.frequency_band,
            "contributing_esm": self.contributing_esm
        }


@dataclass
class COMINTConfig:
    comint_id: str
    location: List[float]
    height: float
    frequency_ranges_mhz: List[List[float]]
    sensitivity_dbm: float
    df_accuracy_deg: float
    scan_period: float


@dataclass
class CommEmitter:
    emitter_id: str
    location: List[float]
    height: float
    frequency_mhz: float
    power_dbm: float
    comm_type: str
    network_id: str
    side: str
    active: bool = True


@dataclass
class COMINTReport:
    time: datetime
    comint_id: str
    emitter_id: str
    comm_freq_mhz: float
    comm_type: str
    aoa_deg: float
    intercepted: bool
    network_id: str
    message_type: str

    def to_dict(self) -> Dict:
        return {
            "time": self.time.isoformat() + 'Z' if self.time.tzinfo is None else self.time.isoformat(),
            "comint_id": self.comint_id,
            "emitter_id": self.emitter_id,
            "comm_freq_mhz": round(self.comm_freq_mhz, 2),
            "comm_type": self.comm_type,
            "aoa_deg": round(self.aoa_deg, 2),
            "intercepted": self.intercepted,
            "network_id": self.network_id,
            "message_type": self.message_type
        }


@dataclass
class FusedTrackPoint:
    time: datetime
    track_id: str
    target_id: str
    obs_lon: float
    obs_lat: float
    obs_alt_m: float
    obs_speed_ms: float
    obs_heading_deg: float
    track_quality: str
    snr_avg_db: float
    source_radars: List[str]
    identity: str = "UNKNOWN"
    identity_source: str = "NONE"
    identity_confidence: float = 0.0
    squawk: str = ""
    callsign: str = ""
    icao24: str = ""
    altitude_source: str = "RADAR"
    altitude_ft: float = 0.0
    emitter_type: str = ""
    emitter_threat_level: int = 0
    comm_activity: str = ""
    position_source: str = "TRUTH"
    source_sensors: List[str] = field(default_factory=list)
    sensor_count: int = 0
    fusion_timestamp: str = ""

    def to_dict(self) -> Dict:
        return {
            "time": self.time.isoformat() + 'Z' if self.time.tzinfo is None else self.time.isoformat(),
            "track_id": self.track_id,
            "target_id": self.target_id,
            "obs_lon": round(self.obs_lon, 6),
            "obs_lat": round(self.obs_lat, 6),
            "obs_alt_m": round(self.obs_alt_m, 1),
            "obs_speed_ms": round(self.obs_speed_ms, 2),
            "obs_heading_deg": round(self.obs_heading_deg, 2),
            "track_quality": self.track_quality,
            "snr_avg_db": round(self.snr_avg_db, 2),
            "source_radars": self.source_radars,
            "identity": self.identity,
            "identity_source": self.identity_source,
            "identity_confidence": round(self.identity_confidence, 3),
            "squawk": self.squawk,
            "callsign": self.callsign,
            "icao24": self.icao24,
            "altitude_source": self.altitude_source,
            "altitude_ft": round(self.altitude_ft, 1),
            "emitter_type": self.emitter_type,
            "emitter_threat_level": self.emitter_threat_level,
            "comm_activity": self.comm_activity,
            "position_source": self.position_source,
            "source_sensors": self.source_sensors,
            "sensor_count": self.sensor_count,
            "fusion_timestamp": self.fusion_timestamp
        }


@dataclass
class FusedNetworkTracks:
    frame_time: str
    network_tracks: List[FusedTrackPoint]

    def to_dict(self) -> Dict:
        return {
            "frame_time": self.frame_time,
            "network_tracks": [t.to_dict() for t in self.network_tracks]
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def save_to_file(self, file_path: str) -> None:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
