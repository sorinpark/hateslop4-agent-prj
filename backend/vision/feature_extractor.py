"""프레임 단위 랜드마크를 시간 윈도우로 누적해 schemas.FeatureSummary를 조립한다.

"위험"류 판단 표현은 다루지 않음 - 여기서는 측정값만 계산한다 (기획.md 10번 원칙).
"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas import Confidence, FeatureSummary, Window  # noqa: E402

from angles import JOINTS, compute_joint_angles  # noqa: E402

# 신뢰도 계산에 쓰는 랜드마크: 어깨(11,12) + 힙/무릎/발목/발끝(23~28, 31, 32)
CONFIDENCE_LANDMARK_IDXS = (11, 12, 23, 24, 25, 26, 27, 28, 31, 32)
CONFIDENCE_THRESHOLD = 0.6

REP_DOWN_THRESHOLD_DEG = 100.0  # 무릎 평균 각도가 이 아래로 내려가면 "내려감" 상태
REP_UP_THRESHOLD_DEG = 160.0    # 이 위로 다시 올라오면 1회 카운트
REP_VIS_THRESHOLD = 0.5         # 프레임 평균 visibility가 이 아래면 rep 판정에서 제외 (노이즈 오탐 방지)


class WindowAccumulator:
    def __init__(self, window_seconds: float = 5.0):
        self.window_seconds = window_seconds
        self._frames: list[dict] = []
        self._window_start_s: float | None = None
        self._rep_count = 0
        self._rep_state = "up"  # "up" | "down"

    def add_frame(self, landmarks, timestamp_s: float) -> None:
        if self._window_start_s is None:
            self._window_start_s = timestamp_s

        angles = compute_joint_angles(landmarks)

        vis_values = [landmarks[idx].visibility or 0.0 for idx in CONFIDENCE_LANDMARK_IDXS]
        avg_vis = statistics.fmean(vis_values)

        self._frames.append({"t": timestamp_s, "angles": angles, "vis": avg_vis})
        if avg_vis >= REP_VIS_THRESHOLD:
            self._update_rep_count(angles)

    def _update_rep_count(self, angles: dict) -> None:
        knee_avg = (angles["L_knee"] + angles["R_knee"]) / 2
        if self._rep_state == "up" and knee_avg < REP_DOWN_THRESHOLD_DEG:
            self._rep_state = "down"
        elif self._rep_state == "down" and knee_avg > REP_UP_THRESHOLD_DEG:
            self._rep_state = "up"
            self._rep_count += 1

    def get_summary_if_ready(self, session_id: str, exercise: str) -> FeatureSummary | None:
        if self._window_start_s is None:
            return None
        if self._frames[-1]["t"] - self._window_start_s < self.window_seconds:
            return None

        summary = self._build_summary(session_id, exercise)
        self._frames.clear()
        self._window_start_s = None
        self._rep_count = 0
        return summary

    def _build_summary(self, session_id: str, exercise: str) -> FeatureSummary:
        def series(joint: str) -> list[float]:
            return [f["angles"][joint] for f in self._frames]

        means = {j: statistics.fmean(series(j)) for j in JOINTS}
        stdevs = {j: (statistics.pstdev(series(j)) if len(self._frames) > 1 else 0.0) for j in JOINTS}
        roms = {j: max(series(j)) - min(series(j)) for j in JOINTS}

        features = {
            "lr_angle_diff": {
                "knee": abs(means["L_knee"] - means["R_knee"]),
                "ankle": abs(means["L_ankle"] - means["R_ankle"]),
                "hip": abs(means["L_hip"] - means["R_hip"]),
            },
            "instability": {
                "knee_L": stdevs["L_knee"], "knee_R": stdevs["R_knee"],
                "ankle_L": stdevs["L_ankle"], "ankle_R": stdevs["R_ankle"],
            },
            "rom": {
                "knee_L": roms["L_knee"], "knee_R": roms["R_knee"],
                "ankle_L": roms["L_ankle"], "ankle_R": roms["R_ankle"],
            },
            "rom_asymmetry": {
                "knee": abs(roms["L_knee"] - roms["R_knee"]),
                "ankle": abs(roms["L_ankle"] - roms["R_ankle"]),
            },
            "load_shift": self._load_shift(means),
        }

        overall_vis = statistics.fmean(f["vis"] for f in self._frames)
        confidence = Confidence(
            overall=overall_vis,
            interp_ratio=0.0,  # TODO: 보간(추정 프레임) 미구현 - 항상 0
            below_threshold=overall_vis < CONFIDENCE_THRESHOLD,
        )
        window = Window(
            start_s=self._frames[0]["t"],
            end_s=self._frames[-1]["t"],
            rep_count=self._rep_count,
        )

        return FeatureSummary(
            session_id=session_id,
            exercise=exercise,
            window=window,
            features=features,
            confidence=confidence,
        )

    @staticmethod
    def _load_shift(means: dict) -> dict:
        # hip 각도 좌우 차를 상체 쏠림의 대리 신호로 사용 (직접적인 상체 각도 측정 아님)
        hip_diff = means["L_hip"] - means["R_hip"]
        if abs(hip_diff) < 3.0:
            side_bias = "neutral"
        else:
            side_bias = "left" if hip_diff > 0 else "right"
        return {"trunk_lean_deg": abs(hip_diff), "side_bias": side_bias}
