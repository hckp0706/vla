from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict


@dataclass
class FlightSegment:
    start_time: datetime
    end_time: datetime
    heading_deg: float
    heading_direction: str
    start_alt_m: float
    end_alt_m: float
    avg_alt_m: float
    start_speed_kmh: float
    end_speed_kmh: float
    avg_speed_kmh: float
    start_lon: float
    start_lat: float
    end_lon: float
    end_lat: float


@dataclass
class AltitudeAnomaly:
    time: datetime
    alt_before_m: float
    alt_after_m: float
    change_rate_mps: float


@dataclass
class SpeedAnomaly:
    time: datetime
    speed_before_kmh: float
    speed_after_kmh: float
    change_rate_kmhps: float


@dataclass
class CityOverflight:
    time: datetime
    city_name: str
    distance_km: float
    lon: float
    lat: float


@dataclass
class TimeFeatures:
    first_seen: datetime
    last_seen: datetime
    duration_seconds: float


@dataclass
class SpatialFeatures:
    start_lon: float
    start_lat: float
    start_name: str
    end_lon: float
    end_lat: float
    end_name: str
    waypoints: List[Dict] = field(default_factory=list)
    sensor_distances: Dict[str, Dict] = field(default_factory=dict)
    segments: List[FlightSegment] = field(default_factory=list)
    altitude_anomalies: List[AltitudeAnomaly] = field(default_factory=list)
    speed_anomalies: List[SpeedAnomaly] = field(default_factory=list)
    city_overflights: List[CityOverflight] = field(default_factory=list)


@dataclass
class MotionFeatures:
    max_speed_kmh: float
    avg_speed_kmh: float
    heading_direction: str
    heading_deg: float
    min_alt_m: float
    max_alt_m: float
    avg_alt_m: float


@dataclass
class QualityFeatures:
    quality_distribution: Dict[str, float] = field(default_factory=dict)
    avg_snr_db: float = 0.0
    gap_count: int = 0
    max_continuous_duration: float = 0.0


@dataclass
class IdentityFeatures:
    identity: str = ''
    identity_confidence: float = 0.0
    squawk: str = ''
    callsign: str = ''
    icao24: str = ''
    emitter_type: str = ''
    emitter_threat_level: int = 0
    comm_activity: str = ''


@dataclass
class TrackFeatures:
    track_id: str
    target_id: str
    time_features: TimeFeatures
    spatial_features: SpatialFeatures
    motion_features: MotionFeatures
    quality_features: QualityFeatures
    identity_features: IdentityFeatures
    flight_labels: List[str] = field(default_factory=list)


@dataclass
class TrackDescription:
    track_id: str
    target_id: str
    narrative: str
    features: TrackFeatures


@dataclass
class SituationSummary:
    total_tracks: int
    foe_count: int
    friend_count: int
    unknown_count: int
    nearest_track_id: str
    nearest_distance_km: float
    nearest_sensor: str
    highest_threat_level: int
    summary_text: str


@dataclass
class SituationReport:
    descriptions: List[TrackDescription] = field(default_factory=list)
    summary: SituationSummary = None

    def to_text(self) -> str:
        parts = []
        for desc in self.descriptions:
            parts.append(desc.narrative)
        if self.summary:
            parts.append(self.summary.summary_text)
        return '\n'.join(parts)

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)
