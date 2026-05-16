# -*- coding: utf-8 -*-
"""
M4 态势可视化服务器 + M6 语义化转换 API
提供静态文件服务及 /api/m6/convert 语义化转换接口
启动: python m4_situation_visualization/server.py [--port 8080]
"""
import os
import sys
import json
import argparse
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

try:
    from flask import Flask, request, jsonify, send_from_directory
except ImportError:
    print("需要安装 Flask: pip install flask")
    sys.exit(1)

from m2_sensor_simulation.models_ext import FusedTrackPoint
from m6_semantic_tool.converter import SemanticConverter

app = Flask(__name__, static_folder=os.path.join(PROJECT_ROOT, "m4_situation_visualization"), static_url_path="")

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output", "m6_semantic_tool")

converter = SemanticConverter(
    radar_config_path=os.path.join(PROJECT_ROOT, "m2_sensor_simulation", "radar_config.json"),
    sensor_config_path=os.path.join(PROJECT_ROOT, "m2_sensor_simulation", "sensor_config.json"),
)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(app.static_folder, path)


@app.route("/api/m6/convert", methods=["POST"])
def m6_convert():
    try:
        data = request.get_json(force=True)
        network_tracks = data.get("network_tracks", [])
        track_id_filter = data.get("track_id", None)

        if not network_tracks:
            return jsonify({"error": "缺少 network_tracks 数据"}), 400

        all_points = []
        for t in network_tracks:
            if track_id_filter and t.get("track_id") != track_id_filter:
                continue
            try:
                time_str = t["time"]
                if time_str.endswith("Z"):
                    time_str = time_str.replace("Z", "+00:00")
                point = FusedTrackPoint(
                    time=datetime.fromisoformat(time_str),
                    track_id=t["track_id"],
                    target_id=t["target_id"],
                    obs_lon=t["obs_lon"],
                    obs_lat=t["obs_lat"],
                    obs_alt_m=t["obs_alt_m"],
                    obs_speed_ms=t["obs_speed_ms"],
                    obs_heading_deg=t["obs_heading_deg"],
                    track_quality=t["track_quality"],
                    snr_avg_db=t["snr_avg_db"],
                    source_radars=t.get("source_radars", []),
                    identity=t.get("identity", "UNKNOWN"),
                    identity_source=t.get("identity_source", "NONE"),
                    identity_confidence=t.get("identity_confidence", 0.0),
                    squawk=t.get("squawk", ""),
                    callsign=t.get("callsign", ""),
                    icao24=t.get("icao24", ""),
                    altitude_source=t.get("altitude_source", "RADAR"),
                    altitude_ft=t.get("altitude_ft", 0.0),
                    emitter_type=t.get("emitter_type", ""),
                    emitter_threat_level=t.get("emitter_threat_level", 0),
                    comm_activity=t.get("comm_activity", ""),
                    position_source=t.get("position_source", "TRUTH"),
                    source_sensors=t.get("source_sensors", []),
                    sensor_count=t.get("sensor_count", 0),
                    fusion_timestamp=t.get("fusion_timestamp", ""),
                )
                all_points.append(point)
            except Exception as e:
                continue

        if not all_points:
            return jsonify({"error": "M6转换失败: 没有有效的航迹点数据"}), 400

        report = converter.convert(all_points)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        track_label = track_id_filter or "all"
        out_filename = f"semantic_{track_label}_{timestamp}.json"
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        out_path = os.path.join(OUTPUT_DIR, out_filename)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2, default=str)

        txt_filename = f"semantic_{track_label}_{timestamp}.txt"
        txt_path = os.path.join(OUTPUT_DIR, txt_filename)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(report.to_text())

        return jsonify({
            "success": True,
            "text": report.to_text(),
            "summary": report.summary.summary_text if report.summary else "",
            "track_count": len({p.track_id for p in all_points}),
            "saved_json": f"output/m6_semantic_tool/{out_filename}",
            "saved_txt": f"output/m6_semantic_tool/{txt_filename}",
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"M6转换失败: {str(e)}"}), 500


@app.route("/api/m6/save", methods=["POST"])
def m6_save():
    try:
        data = request.get_json(force=True)
        text = data.get("text", "")
        summary = data.get("summary", "")

        if not text:
            return jsonify({"error": "缺少文本内容"}), 400

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        txt_filename = f"semantic_manual_{timestamp}.txt"
        txt_path = os.path.join(OUTPUT_DIR, txt_filename)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
            if summary:
                f.write("\n\n" + summary)

        return jsonify({
            "success": True,
            "saved_txt": f"output/m6_semantic_tool/{txt_filename}",
        })
    except Exception as e:
        return jsonify({"error": f"保存失败: {str(e)}"}), 500


def main():
    parser = argparse.ArgumentParser(description="M4 态势可视化服务器")
    parser.add_argument("--port", type=int, default=8080, help="服务器端口 (默认 8080)")
    parser.add_argument("--host", default="0.0.0.0", help="绑定地址 (默认 0.0.0.0)")
    args = parser.parse_args()

    print(f"M4 态势可视化服务器启动中...")
    print(f"  前端页面: http://localhost:{args.port}/")
    print(f"  M6 API:   http://localhost:{args.port}/api/m6/convert")
    print(f"  输出目录: {OUTPUT_DIR}")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
