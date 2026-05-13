from typing import List
from m6_semantic_tool.models import TrackFeatures


class FlightCharacteristicInferencer:
    def infer(self, features: TrackFeatures) -> List[str]:
        labels = []
        motion = features.motion_features
        spatial = features.spatial_features
        identity = features.identity_features
        quality = features.quality_features

        if motion.avg_alt_m < 1000:
            labels.append("低空飞行")
        elif motion.avg_alt_m > 12000:
            labels.append("高空飞行")

        if (motion.max_alt_m - motion.min_alt_m) < 500:
            labels.append("平稳巡航")
        else:
            if (motion.max_alt_m - motion.min_alt_m) > 3000:
                labels.append("正常起降")

        if motion.max_speed_kmh > 1500:
            labels.append("超音速飞行")
        elif motion.max_speed_kmh > 900:
            labels.append("高速飞行")

        if motion.avg_speed_kmh < 300:
            labels.append("低速飞行")

        if len(spatial.waypoints) >= 2:
            labels.append("航线机动")

        if identity.identity == "FOE" and "低空飞行" in labels:
            labels.remove("低空飞行")
            labels.append("低空突防")

        if identity.identity == "FOE" and "高空飞行" in labels and "高速飞行" in labels:
            labels.remove("高空飞行")
            labels.append("高空侦察")

        if quality.gap_count > 0:
            labels.append("航迹断续")

        return labels
