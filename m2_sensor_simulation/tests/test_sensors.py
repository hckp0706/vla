import unittest
import math
import random
import json
import os
from datetime import datetime, timedelta
from unittest.mock import patch

from m2_sensor_simulation.models import TargetTruth, TrackPoint, RadarConfig
from m2_sensor_simulation.models_ext import (
    SSRConfig, SSRReply, IFFConfig, IFFReply,
    ESMConfig, EmitterParameters, PDWRecord,
    ELINTConfig, ELINTReport, COMINTConfig, CommEmitter, COMINTReport,
    FusedTrackPoint, FusedNetworkTracks
)
from m2_sensor_simulation.ssr import SSR
from m2_sensor_simulation.iff import IFF
from m2_sensor_simulation.esm import ESM
from m2_sensor_simulation.elint import ELINT
from m2_sensor_simulation.comint import COMINT
from m2_sensor_simulation.fusion import FusionEngine


def _make_target(target_id="0001", lon=121.5, lat=31.0, alt_m=8000,
                 speed_ms=250, heading_deg=90, time=None):
    if time is None:
        time = datetime(2026, 5, 1, 8, 0, 0)
    return TargetTruth(
        target_id=target_id, time=time,
        lon=lon, lat=lat, alt_m=alt_m,
        speed_ms=speed_ms, heading_deg=heading_deg, rcs_dbsm=5.0
    )


def _make_ssr_config():
    return SSRConfig(
        ssr_id="SSR_01", location=[121.47, 31.23], height=50,
        max_range_km=460, modes=["3A", "C", "S"],
        scan_period=10, reply_probability=1.0, fruit_rate=0.0,
        co_located_radar="RADAR_02"
    )


def _make_iff_config():
    return IFFConfig(
        iff_id="IFF_01", location=[121.47, 31.23], height=50,
        max_range_km=460, modes=["4", "5"],
        scan_period=10, crypto_valid=True,
        co_located_radar="RADAR_02"
    )


def _make_esm_config():
    return ESMConfig(
        esm_id="ESM_01", location=[122.10, 30.01], height=80,
        frequency_range_ghz=[0.5, 18.0], sensitivity_dbm=-95,
        df_accuracy_deg=3.0, freq_accuracy_mhz=2.0,
        pri_accuracy_us=0.1, pw_accuracy_us=0.05, scan_period=5
    )


def _make_emitter(side="FOE", freq=2.9, active=True, location=None, height=None):
    return EmitterParameters(
        emitter_id="EMITTER_01",
        location=location or [123.50, 31.50],
        height=height if height is not None else 9000,
        frequency_ghz=freq, pri_us=4000, pw_us=12.0,
        power_dbm=83.0, antenna_gain_db=42.0, scan_period=4.0,
        radar_type="AN/SPY-1D", modulation="LFM",
        threat_level=5, side=side, active=active
    )


def _make_comm_emitter(side="FOE", location=None, height=None):
    return CommEmitter(
        emitter_id="COMM_01",
        location=location or [123.50, 31.50],
        height=height if height is not None else 9000,
        frequency_mhz=150.0, power_dbm=50.0,
        comm_type="VHF", network_id="NET_ALPHA", side=side, active=True
    )


class TestModelsExt(unittest.TestCase):
    def test_ssr_config_creation(self):
        config = _make_ssr_config()
        self.assertEqual(config.ssr_id, "SSR_01")
        self.assertEqual(config.modes, ["3A", "C", "S"])
        self.assertEqual(config.co_located_radar, "RADAR_02")

    def test_ssr_reply_to_dict(self):
        reply = SSRReply(
            time=datetime(2026, 5, 1, 8, 0, 0), target_id="0001",
            ssr_id="SSR_01", reply_mode="3A", squawk="2000",
            altitude_ft=26246, icao24="ABC123", callsign="CCA1234",
            reply_valid=True, sls_valid=True, is_fruit=False
        )
        d = reply.to_dict()
        self.assertEqual(d["ssr_id"], "SSR_01")
        self.assertEqual(d["squawk"], "2000")
        self.assertTrue(d["reply_valid"])

    def test_iff_reply_to_dict(self):
        reply = IFFReply(
            time=datetime(2026, 5, 1, 8, 0, 0), target_id="0001",
            iff_id="IFF_01", interrogation_mode="5",
            identity="FRIEND", reply_received=True, crypto_valid=True,
            position_report={"lat": 31.0, "lon": 121.5}, confidence=0.95
        )
        d = reply.to_dict()
        self.assertEqual(d["identity"], "FRIEND")
        self.assertAlmostEqual(d["confidence"], 0.95, places=2)

    def test_pdw_record_to_dict(self):
        pdw = PDWRecord(
            time=datetime(2026, 5, 1, 8, 0, 0), esm_id="ESM_01",
            emitter_id="EMITTER_01", rf_ghz=2.9, pw_us=12.0,
            pri_us=4000, aoa_deg=45.0, pa_dbm=-60.0,
            modulation="LFM", radar_type_est="AN/SPY-1D", confidence=0.85
        )
        d = pdw.to_dict()
        self.assertEqual(d["esm_id"], "ESM_01")
        self.assertAlmostEqual(d["rf_ghz"], 2.9, places=2)

    def test_fused_track_point_defaults(self):
        ftp = FusedTrackPoint(
            time=datetime(2026, 5, 1, 8, 0, 0), track_id="0001",
            target_id="0001", obs_lon=121.5, obs_lat=31.0,
            obs_alt_m=8000, obs_speed_ms=250, obs_heading_deg=90,
            track_quality="HIGH", snr_avg_db=15.0, source_radars=["RADAR_01"]
        )
        self.assertEqual(ftp.identity, "UNKNOWN")
        self.assertEqual(ftp.identity_source, "NONE")
        self.assertEqual(ftp.altitude_source, "RADAR")

    def test_fused_network_tracks_serialization(self):
        ftp = FusedTrackPoint(
            time=datetime(2026, 5, 1, 8, 0, 0), track_id="0001",
            target_id="0001", obs_lon=121.5, obs_lat=31.0,
            obs_alt_m=8000, obs_speed_ms=250, obs_heading_deg=90,
            track_quality="HIGH", snr_avg_db=15.0, source_radars=["RADAR_01"]
        )
        fnt = FusedNetworkTracks(frame_time="2026-05-01T08:00:00Z", network_tracks=[ftp])
        d = fnt.to_dict()
        self.assertEqual(len(d["network_tracks"]), 1)
        json_str = fnt.to_json()
        self.assertIn("network_tracks", json_str)


class TestSSR(unittest.TestCase):
    def test_civil_aircraft_replies(self):
        ssr = SSR(_make_ssr_config())
        target = _make_target(target_id="0001")
        adsb_data = {"squawk": "2000", "altitude_ft": 26246, "icao24": "ABC123", "callsign": "CCA1234", "time": target.time}
        replies = ssr.process_target(target, has_adsb=True, identity="NEUTRAL", adsb_data=adsb_data)
        valid_replies = [r for r in replies if r.reply_valid]
        self.assertGreater(len(valid_replies), 0)
        for r in valid_replies:
            self.assertTrue(r.reply_valid)
            self.assertFalse(r.is_fruit)

    def test_military_no_ssr_reply(self):
        ssr = SSR(_make_ssr_config())
        target = _make_target(target_id="0002")
        replies = ssr.process_target(target, has_adsb=False, identity="FOE", adsb_data=None)
        self.assertEqual(len(replies), 0)

    def test_friend_military_no_ssr_reply(self):
        ssr = SSR(_make_ssr_config())
        target = _make_target(target_id="0001")
        replies = ssr.process_target(target, has_adsb=False, identity="FRIEND", adsb_data=None)
        self.assertEqual(len(replies), 0)

    def test_ssr_out_of_range(self):
        config = SSRConfig(
            ssr_id="SSR_FAR", location=[100.0, 20.0], height=50,
            max_range_km=100, modes=["3A", "C"],
            scan_period=10, reply_probability=1.0, fruit_rate=0.0
        )
        ssr = SSR(config)
        target = _make_target(lon=121.5, lat=31.0)
        replies = ssr.process_target(target, has_adsb=True, identity="NEUTRAL", adsb_data={})
        self.assertEqual(len(replies), 0)

    def test_ssr_mode_c_altitude_quantized(self):
        ssr = SSR(_make_ssr_config())
        target = _make_target(alt_m=8046)
        adsb_data = {"squawk": "2000", "altitude_ft": 26397, "icao24": "ABC123", "callsign": "TEST", "time": target.time}
        replies = ssr.process_target(target, has_adsb=True, identity="NEUTRAL", adsb_data=adsb_data)
        mode_c = [r for r in replies if r.reply_mode == "C" and r.reply_valid]
        if mode_c:
            self.assertEqual(mode_c[0].altitude_ft % 100, 0)

    def test_ssr_fruit_rate(self):
        config = SSRConfig(
            ssr_id="SSR_FRUIT", location=[121.47, 31.23], height=50,
            max_range_km=460, modes=["3A"],
            scan_period=1, reply_probability=1.0, fruit_rate=1.0
        )
        ssr = SSR(config)
        target = _make_target()
        adsb_data = {"squawk": "2000", "altitude_ft": 26246, "icao24": "ABC123", "callsign": "TEST", "time": target.time}
        random.seed(42)
        replies = ssr.process_target(target, has_adsb=True, identity="NEUTRAL", adsb_data=adsb_data)
        fruit_count = sum(1 for r in replies if r.is_fruit)
        self.assertGreater(fruit_count, 0)


class TestIFF(unittest.TestCase):
    def test_friend_mode5(self):
        iff = IFF(_make_iff_config())
        target = _make_target(target_id="0001")
        reply = iff.process_target(target, identity="FRIEND")
        self.assertIsNotNone(reply)
        self.assertEqual(reply.identity, "FRIEND")
        self.assertTrue(reply.reply_received)
        self.assertGreaterEqual(reply.confidence, 0.90)
        if reply.interrogation_mode == "5":
            self.assertIsNotNone(reply.position_report)

    def test_foe_no_reply(self):
        iff = IFF(_make_iff_config())
        target = _make_target(target_id="0002")
        reply = iff.process_target(target, identity="FOE")
        self.assertIsNotNone(reply)
        self.assertEqual(reply.identity, "FOE")
        self.assertFalse(reply.reply_received)
        self.assertAlmostEqual(reply.confidence, 0.60, places=2)

    def test_unknown_no_reply(self):
        iff = IFF(_make_iff_config())
        target = _make_target(target_id="0003")
        reply = iff.process_target(target, identity="UNKNOWN")
        self.assertIsNotNone(reply)
        self.assertEqual(reply.identity, "UNKNOWN")
        self.assertFalse(reply.reply_received)
        self.assertAlmostEqual(reply.confidence, 0.30, places=2)

    def test_crypto_invalid_degradation(self):
        config = IFFConfig(
            iff_id="IFF_NO_CRYPTO", location=[121.47, 31.23], height=50,
            max_range_km=460, modes=["4", "5"],
            scan_period=10, crypto_valid=False
        )
        iff = IFF(config)
        target = _make_target(target_id="0001")
        reply = iff.process_target(target, identity="FRIEND")
        self.assertIsNotNone(reply)
        self.assertEqual(reply.identity, "UNKNOWN")
        self.assertFalse(reply.crypto_valid)

    def test_iff_out_of_range(self):
        config = IFFConfig(
            iff_id="IFF_FAR", location=[100.0, 20.0], height=50,
            max_range_km=100, modes=["4", "5"],
            scan_period=10, crypto_valid=True
        )
        iff = IFF(config)
        target = _make_target(lon=121.5, lat=31.0)
        reply = iff.process_target(target, identity="FRIEND")
        self.assertIsNone(reply)


class TestESM(unittest.TestCase):
    def test_intercept_foe_emitter(self):
        esm = ESM(_make_esm_config())
        emitter = _make_emitter(side="FOE")
        pdw = esm.process_emitter(emitter, datetime(2026, 5, 1, 8, 0, 0))
        if pdw is not None:
            self.assertEqual(pdw.esm_id, "ESM_01")
            self.assertEqual(pdw.emitter_id, "EMITTER_01")
            self.assertGreater(pdw.confidence, 0)

    def test_no_intercept_friend_emitter(self):
        esm = ESM(_make_esm_config())
        emitter = _make_emitter(side="FRIEND")
        pdw = esm.process_emitter(emitter, datetime(2026, 5, 1, 8, 0, 0))
        self.assertIsNone(pdw)

    def test_no_intercept_inactive_emitter(self):
        esm = ESM(_make_esm_config())
        emitter = _make_emitter(side="FOE", active=False)
        pdw = esm.process_emitter(emitter, datetime(2026, 5, 1, 8, 0, 0))
        self.assertIsNone(pdw)

    def test_no_intercept_out_of_band(self):
        esm = ESM(_make_esm_config())
        emitter = _make_emitter(side="FOE", freq=30.0)
        pdw = esm.process_emitter(emitter, datetime(2026, 5, 1, 8, 0, 0))
        self.assertIsNone(pdw)

    def test_pdw_measurement_errors(self):
        random.seed(42)
        esm = ESM(_make_esm_config())
        emitter = _make_emitter(side="FOE", freq=3.0)
        pdws = []
        for _ in range(100):
            pdw = esm.process_emitter(emitter, datetime(2026, 5, 1, 8, 0, 0))
            if pdw:
                pdws.append(pdw)
        if pdws:
            avg_rf = sum(p.rf_ghz for p in pdws) / len(pdws)
            self.assertAlmostEqual(avg_rf, 3.0, delta=0.5)

    def test_esm_longer_range_than_radar(self):
        esm = ESM(_make_esm_config())
        emitter_far = EmitterParameters(
            emitter_id="EMITTER_FAR", location=[125.0, 33.0], height=9000,
            frequency_ghz=3.0, pri_us=4000, pw_us=12.0,
            power_dbm=83.0, antenna_gain_db=42.0, scan_period=4.0,
            radar_type="远距雷达", modulation="LFM",
            threat_level=3, side="FOE", active=True
        )
        pdw = esm.process_emitter(emitter_far, datetime(2026, 5, 1, 8, 0, 0))
        los = esm.calculate_line_of_sight(emitter_far.height)
        r = esm.calculate_range(emitter_far.location[0], emitter_far.location[1], emitter_far.height)
        if r <= los:
            pr = esm.calculate_received_power(emitter_far)
            if pr >= esm.config.sensitivity_dbm:
                self.assertIsNotNone(pdw)


class TestELINT(unittest.TestCase):
    def test_cross_fix_two_stations(self):
        config = ELINTConfig(
            elint_id="ELINT_01", min_stations_for_fix=2,
            matching_threshold=0.7, analysis_period=0
        )
        emitter_db = [_make_emitter(side="FOE")]
        elint = ELINT(config, emitter_db)

        pdw_records = [
            PDWRecord(time=datetime(2026, 5, 1, 8, 0, 0), esm_id="ESM_01",
                      emitter_id="EMITTER_01", rf_ghz=2.9, pw_us=12.0,
                      pri_us=4000, aoa_deg=30.0, pa_dbm=-60.0,
                      modulation="LFM", radar_type_est="AN/SPY-1D", confidence=0.8),
            PDWRecord(time=datetime(2026, 5, 1, 8, 0, 0), esm_id="ESM_02",
                      emitter_id="EMITTER_01", rf_ghz=2.9, pw_us=12.0,
                      pri_us=4000, aoa_deg=200.0, pa_dbm=-55.0,
                      modulation="LFM", radar_type_est="AN/SPY-1D", confidence=0.8),
        ]

        esm_locations = {
            "ESM_01": (122.10, 30.01),
            "ESM_02": (121.47, 31.23),
        }

        reports = elint.analyze(
            {"EMITTER_01": pdw_records},
            esm_locations,
            datetime(2026, 5, 1, 8, 0, 0)
        )
        self.assertGreater(len(reports), 0)
        if reports:
            self.assertLess(reports[0].position_error_km, 50)

    def test_single_station_no_fix(self):
        config = ELINTConfig(
            elint_id="ELINT_01", min_stations_for_fix=2,
            matching_threshold=0.7, analysis_period=0
        )
        emitter_db = [_make_emitter(side="FOE")]
        elint = ELINT(config, emitter_db)

        pdw_records = [
            PDWRecord(time=datetime(2026, 5, 1, 8, 0, 0), esm_id="ESM_01",
                      emitter_id="EMITTER_01", rf_ghz=2.9, pw_us=12.0,
                      pri_us=4000, aoa_deg=30.0, pa_dbm=-60.0,
                      modulation="LFM", radar_type_est="AN/SPY-1D", confidence=0.8),
        ]

        esm_locations = {"ESM_01": (122.10, 30.01)}
        reports = elint.analyze(
            {"EMITTER_01": pdw_records},
            esm_locations,
            datetime(2026, 5, 1, 8, 0, 0)
        )
        if reports:
            self.assertEqual(reports[0].position_error_km, 999.0)

    def test_emitter_identification(self):
        config = ELINTConfig(
            elint_id="ELINT_01", min_stations_for_fix=2,
            matching_threshold=0.5, analysis_period=0
        )
        emitter_db = [_make_emitter(side="FOE")]
        elint = ELINT(config, emitter_db)

        pdw_records = [
            PDWRecord(time=datetime(2026, 5, 1, 8, 0, 0), esm_id="ESM_01",
                      emitter_id="EMITTER_01", rf_ghz=2.9, pw_us=12.0,
                      pri_us=4000, aoa_deg=30.0, pa_dbm=-60.0,
                      modulation="LFM", radar_type_est="AN/SPY-1D", confidence=0.9),
            PDWRecord(time=datetime(2026, 5, 1, 8, 0, 0), esm_id="ESM_02",
                      emitter_id="EMITTER_01", rf_ghz=2.9, pw_us=12.0,
                      pri_us=4000, aoa_deg=200.0, pa_dbm=-55.0,
                      modulation="LFM", radar_type_est="AN/SPY-1D", confidence=0.9),
        ]
        esm_locations = {"ESM_01": (122.10, 30.01), "ESM_02": (121.47, 31.23)}
        reports = elint.analyze(
            {"EMITTER_01": pdw_records}, esm_locations,
            datetime(2026, 5, 1, 8, 0, 0)
        )
        if reports:
            self.assertNotEqual(reports[0].radar_type_identified, "UNKNOWN")

    def test_analysis_period_gate(self):
        config = ELINTConfig(
            elint_id="ELINT_01", min_stations_for_fix=2,
            matching_threshold=0.7, analysis_period=30
        )
        emitter_db = [_make_emitter(side="FOE")]
        elint = ELINT(config, emitter_db)

        pdws = [
            PDWRecord(time=datetime(2026, 5, 1, 8, 0, 0), esm_id="ESM_01",
                      emitter_id="EMITTER_01", rf_ghz=2.9, pw_us=12.0,
                      pri_us=4000, aoa_deg=30.0, pa_dbm=-60.0,
                      modulation="LFM", radar_type_est="AN/SPY-1D", confidence=0.9),
            PDWRecord(time=datetime(2026, 5, 1, 8, 0, 0), esm_id="ESM_02",
                      emitter_id="EMITTER_01", rf_ghz=2.9, pw_us=12.0,
                      pri_us=4000, aoa_deg=200.0, pa_dbm=-55.0,
                      modulation="LFM", radar_type_est="AN/SPY-1D", confidence=0.9),
        ]
        esm_locations = {"ESM_01": (122.10, 30.01), "ESM_02": (121.47, 31.23)}
        reports1 = elint.analyze({"EMITTER_01": pdws}, esm_locations, datetime(2026, 5, 1, 8, 0, 0))
        reports2 = elint.analyze({"EMITTER_01": pdws}, esm_locations, datetime(2026, 5, 1, 8, 0, 10))
        self.assertGreater(len(reports1), 0)
        self.assertEqual(len(reports2), 0)


class TestCOMINT(unittest.TestCase):
    def test_intercept_foe_comm(self):
        config = COMINTConfig(
            comint_id="COMINT_01", location=[122.10, 30.01], height=30,
            frequency_ranges_mhz=[[30, 88], [108, 174], [225, 400]],
            sensitivity_dbm=-100, df_accuracy_deg=5.0, scan_period=10
        )
        comint = COMINT(config)
        emitter = _make_comm_emitter(side="FOE")
        report = comint.process_emitter(emitter, datetime(2026, 5, 1, 8, 0, 0))
        self.assertIsNotNone(report)
        self.assertTrue(report.intercepted)
        self.assertEqual(report.comm_type, "VHF")

    def test_no_intercept_friend_comm(self):
        config = COMINTConfig(
            comint_id="COMINT_01", location=[122.10, 30.01], height=30,
            frequency_ranges_mhz=[[30, 88], [108, 174]],
            sensitivity_dbm=-100, df_accuracy_deg=5.0, scan_period=10
        )
        comint = COMINT(config)
        emitter = _make_comm_emitter(side="FRIEND")
        report = comint.process_emitter(emitter, datetime(2026, 5, 1, 8, 0, 0))
        self.assertIsNone(report)

    def test_no_intercept_out_of_band(self):
        config = COMINTConfig(
            comint_id="COMINT_01", location=[122.10, 30.01], height=30,
            frequency_ranges_mhz=[[225, 400]],
            sensitivity_dbm=-100, df_accuracy_deg=5.0, scan_period=10
        )
        comint = COMINT(config)
        emitter = _make_comm_emitter(side="FOE")
        report = comint.process_emitter(emitter, datetime(2026, 5, 1, 8, 0, 0))
        self.assertIsNone(report)

    def test_comm_message_type_classification(self):
        config = COMINTConfig(
            comint_id="COMINT_01", location=[122.10, 30.01], height=30,
            frequency_ranges_mhz=[[30, 88], [108, 174], [225, 400]],
            sensitivity_dbm=-100, df_accuracy_deg=5.0, scan_period=10
        )
        comint = COMINT(config)
        emitter = _make_comm_emitter(side="FOE")
        report = comint.process_emitter(emitter, datetime(2026, 5, 1, 8, 0, 0))
        if report:
            self.assertIn(report.message_type, ["TACTICAL_COORDINATION", "LONG_RANGE_COMMAND", "DATA_LINK", "UNKNOWN"])


class TestFusionEngine(unittest.TestCase):
    def test_fuse_identity_iff_priority(self):
        engine = FusionEngine()
        iff_replies = [IFFReply(
            time=datetime(2026, 5, 1, 8, 0, 0), target_id="0001",
            iff_id="IFF_01", interrogation_mode="5",
            identity="FRIEND", reply_received=True, crypto_valid=True,
            position_report=None, confidence=0.95
        )]
        identity, source, conf = engine.fuse_identity(iff_replies, [], [])
        self.assertEqual(identity, "FRIEND")
        self.assertIn("IFF", source)
        self.assertGreaterEqual(conf, 0.90)

    def test_fuse_identity_ssr_fallback(self):
        engine = FusionEngine()
        ssr_replies = [SSRReply(
            time=datetime(2026, 5, 1, 8, 0, 0), target_id="0001",
            ssr_id="SSR_01", reply_mode="S", squawk="2000",
            altitude_ft=26246, icao24="ABC123", callsign="CCA1234",
            reply_valid=True, sls_valid=True, is_fruit=False
        )]
        identity, source, conf = engine.fuse_identity([], ssr_replies, [])
        self.assertEqual(identity, "NEUTRAL")
        self.assertIn("SSR", source)

    def test_fuse_identity_esm_fallback(self):
        engine = FusionEngine()
        pdws = [PDWRecord(
            time=datetime(2026, 5, 1, 8, 0, 0), esm_id="ESM_01",
            emitter_id="EMITTER_01", rf_ghz=2.9, pw_us=12.0,
            pri_us=4000, aoa_deg=30.0, pa_dbm=-60.0,
            modulation="LFM", radar_type_est="AN/SPY-1D", confidence=0.8
        )]
        identity, source, conf = engine.fuse_identity([], [], pdws)
        self.assertEqual(identity, "FOE")
        self.assertEqual(source, "ESM_INFERENCE")

    def test_fuse_identity_default_unknown(self):
        engine = FusionEngine()
        identity, source, conf = engine.fuse_identity([], [], [])
        self.assertEqual(identity, "UNKNOWN")
        self.assertAlmostEqual(conf, 0.30)

    def test_fuse_altitude_ssr_mode_c(self):
        engine = FusionEngine()
        ssr_replies = [SSRReply(
            time=datetime(2026, 5, 1, 8, 0, 0), target_id="0001",
            ssr_id="SSR_01", reply_mode="C", squawk="",
            altitude_ft=26200, icao24="", callsign="",
            reply_valid=True, sls_valid=True, is_fruit=False
        )]
        alt_ft, source, alt_m = engine.fuse_altitude(ssr_replies, 8000)
        self.assertEqual(source, "SSR_MODE_C")
        self.assertAlmostEqual(alt_ft, 26200, delta=100)

    def test_fuse_altitude_radar_fallback(self):
        engine = FusionEngine()
        alt_ft, source, alt_m = engine.fuse_altitude([], 8000)
        self.assertEqual(source, "RADAR")

    def test_fuse_ssr_identity_info(self):
        engine = FusionEngine()
        ssr_replies = [
            SSRReply(time=datetime(2026, 5, 1, 8, 0, 0), target_id="0001",
                     ssr_id="SSR_01", reply_mode="3A", squawk="2000",
                     altitude_ft=0, icao24="", callsign="",
                     reply_valid=True, sls_valid=True, is_fruit=False),
            SSRReply(time=datetime(2026, 5, 1, 8, 0, 0), target_id="0001",
                     ssr_id="SSR_01", reply_mode="S", squawk="2000",
                     altitude_ft=26246, icao24="ABC123", callsign="CCA1234",
                     reply_valid=True, sls_valid=True, is_fruit=False),
        ]
        squawk, icao24, callsign = engine.fuse_ssridentity_info(ssr_replies)
        self.assertEqual(squawk, "2000")
        self.assertEqual(icao24, "ABC123")
        self.assertEqual(callsign, "CCA1234")

    def test_fuse_track_complete(self):
        engine = FusionEngine()
        radar_track = TrackPoint(
            time=datetime(2026, 5, 1, 8, 0, 0), track_id="0001",
            target_id="0001", source_radars=["RADAR_01", "RADAR_02"],
            obs_lon=121.5, obs_lat=31.0, obs_alt_m=8000,
            obs_speed_ms=250, obs_heading_deg=90,
            track_quality="HIGH", snr_avg_db=15.0
        )
        iff_replies = [IFFReply(
            time=datetime(2026, 5, 1, 8, 0, 0), target_id="0001",
            iff_id="IFF_01", interrogation_mode="5",
            identity="FRIEND", reply_received=True, crypto_valid=True,
            position_report=None, confidence=0.95
        )]
        ssr_replies = [SSRReply(
            time=datetime(2026, 5, 1, 8, 0, 0), target_id="0001",
            ssr_id="SSR_01", reply_mode="S", squawk="2000",
            altitude_ft=26246, icao24="ABC123", callsign="CCA1234",
            reply_valid=True, sls_valid=True, is_fruit=False
        )]
        fused = engine.fuse_track(radar_track, iff_replies, ssr_replies, [], [], [])
        self.assertEqual(fused.identity, "FRIEND")
        self.assertEqual(fused.icao24, "ABC123")
        self.assertEqual(fused.callsign, "CCA1234")
        self.assertEqual(fused.altitude_source, "SSR_MODE_S")
        self.assertGreater(fused.sensor_count, 0)
        self.assertIn("IFF_01", fused.source_sensors)
        self.assertIn("SSR_01", fused.source_sensors)


class TestSensorAvailability(unittest.TestCase):
    def test_ssr_civil_available_military_not(self):
        ssr = SSR(_make_ssr_config())
        target = _make_target()
        civil_replies = ssr.process_target(target, has_adsb=True, identity="NEUTRAL", adsb_data={"squawk": "2000", "altitude_ft": 26000, "icao24": "ABC", "callsign": "TEST", "time": target.time})
        mil_replies = ssr.process_target(target, has_adsb=False, identity="FOE", adsb_data=None)
        self.assertGreater(len(civil_replies), 0)
        self.assertEqual(len(mil_replies), 0)

    def test_iff_crypto_degradation(self):
        config_valid = _make_iff_config()
        config_invalid = IFFConfig(
            iff_id="IFF_BAD", location=[121.47, 31.23], height=50,
            max_range_km=460, modes=["4", "5"],
            scan_period=10, crypto_valid=False
        )
        iff_valid = IFF(config_valid)
        iff_invalid = IFF(config_invalid)
        target = _make_target(target_id="0001")
        reply_valid = iff_valid.process_target(target, identity="FRIEND")
        reply_invalid = iff_invalid.process_target(target, identity="FRIEND")
        self.assertEqual(reply_valid.identity, "FRIEND")
        self.assertEqual(reply_invalid.identity, "UNKNOWN")

    def test_esm_only_intercepts_foe(self):
        esm = ESM(_make_esm_config())
        foe_emitter = _make_emitter(side="FOE")
        friend_emitter = _make_emitter(side="FRIEND")
        foe_pdw = esm.process_emitter(foe_emitter, datetime(2026, 5, 1, 8, 0, 0))
        friend_pdw = esm.process_emitter(friend_emitter, datetime(2026, 5, 1, 8, 0, 0))
        self.assertIsNotNone(foe_pdw)
        self.assertIsNone(friend_pdw)

    def test_elint_single_station_no_fix(self):
        config = ELINTConfig(
            elint_id="ELINT_01", min_stations_for_fix=2,
            matching_threshold=0.7, analysis_period=0
        )
        elint = ELINT(config, [_make_emitter(side="FOE")])
        pdws_single = [PDWRecord(
            time=datetime(2026, 5, 1, 8, 0, 0), esm_id="ESM_01",
            emitter_id="EMITTER_01", rf_ghz=2.9, pw_us=12.0,
            pri_us=4000, aoa_deg=30.0, pa_dbm=-60.0,
            modulation="LFM", radar_type_est="AN/SPY-1D", confidence=0.9
        )]
        esm_locations = {"ESM_01": (122.10, 30.01)}
        reports = elint.analyze({"EMITTER_01": pdws_single}, esm_locations, datetime(2026, 5, 1, 8, 0, 0))
        if reports:
            self.assertEqual(reports[0].position_error_km, 999.0)


if __name__ == '__main__':
    unittest.main()
