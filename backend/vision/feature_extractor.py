"""프레임 단위 랜드마크를 시간 윈도우로 누적해 schemas.FeatureSummary를 조립한다.

"위험"류 판단 표현은 다루지 않음 - 여기서는 측정값만 계산한다 (기획.md 10번 원칙).

plus_exercise.md 1단계: rep 판정에 쓰는 관절/임계값과 feature에 들어갈 관절
목록을 CategoryConfig(categories/)에서 가져온다. 운동마다 어떤 관절을 볼지는
categories/<카테고리>.py 가 결정하고, 여기 로직은 카테고리와 무관하게 공용이다.
"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas import Confidence, FeatureSummary, Window  # noqa: E402

from angles import compute_joint_angles  # noqa: E402
from categories import get_category  # noqa: E402

# 신뢰도 계산에 쓰는 랜드마크: 어깨(11,12) + 힙/무릎/발목/발끝(23~28, 31, 32)
CONFIDENCE_LANDMARK_IDXS = (11, 12, 23, 24, 25, 26, 27, 28, 31, 32)
CONFIDENCE_THRESHOLD = 0.6

REP_VIS_THRESHOLD = 0.5  # 프레임 평균 visibility가 이 아래면 rep 판정에서 제외 (노이즈 오탐 방지)


class WindowAccumulator:
    def __init__(self, window_seconds: float = 5.0, exercise: str = "squat"):
        self.window_seconds = window_seconds
        self.category = get_category(exercise)
        self._frames: list[dict] = []
        self._window_start_s: float | None = None
        self._rep_count = 0
        self._rep_state = "up"  # "up" | "down"
        self._hold_seconds = 0.0  # mode="hold" 전용: 이 윈도우에서 자세 유지한 누적 초
        self._last_frame_t: float | None = None  # hold 누적용 - 직전 프레임 시각

    @property
    def rep_state(self) -> str:
        """디버깅/튜닝 도구용(spike_webcam.py): 지금 rep 판정 상태('up'|'down')."""
        return self._rep_state

    def add_frame(self, landmarks, timestamp_s: float) -> None:
        if self._window_start_s is None:
            self._window_start_s = timestamp_s

        angles = compute_joint_angles(landmarks)

        vis_values = [landmarks[idx].visibility or 0.0 for idx in CONFIDENCE_LANDMARK_IDXS]
        avg_vis = statistics.fmean(vis_values)

        self._frames.append({"t": timestamp_s, "angles": angles, "vis": avg_vis})
        if avg_vis >= REP_VIS_THRESHOLD:
            if self.category.mode == "hold":
                self._update_hold_seconds(angles, timestamp_s)
            else:
                self._update_rep_count(angles)
        self._last_frame_t = timestamp_s

    def _update_rep_count(self, angles: dict) -> None:
        pair = self.category.rep_joint_pair
        if pair is None:
            return

        left, right = angles[pair[0]], angles[pair[1]]
        # 기본은 좌우 평균. 좌우를 번갈아 쓰는 운동(strike)만 "더 펴진 쪽"을 본다
        # — 가려진 반대쪽 팔 각도가 평균을 끌어내려 rep을 놓치는 걸 막기 위함.
        # (자세한 배경은 categories/base.py 의 rep_use_max_of_pair 주석 참고)
        if self.category.rep_use_max_of_pair:
            value = max(left, right)
        else:
            value = (left + right) / 2

        down = self.category.rep_down_threshold_deg
        up = self.category.rep_up_threshold_deg
        if self._rep_state == "up" and value < down:
            self._rep_state = "down"
        elif self._rep_state == "down" and value > up:
            self._rep_state = "up"
            self._rep_count += 1

    def _update_hold_seconds(self, angles: dict, timestamp_s: float) -> None:
        pair = self.category.hold_joint_pair
        if pair is None or self._last_frame_t is None:
            return  # 직전 프레임이 없으면(윈도우 첫 프레임) 구간을 잴 수 없다

        avg = (angles[pair[0]] + angles[pair[1]]) / 2
        in_range = self.category.hold_min_deg <= avg <= self.category.hold_max_deg
        if in_range:
            self._hold_seconds += timestamp_s - self._last_frame_t

    def get_summary_if_ready(self, session_id: str, exercise: str) -> FeatureSummary | None:
        if self._window_start_s is None:
            return None
        if self._frames[-1]["t"] - self._window_start_s < self.window_seconds:
            return None

        summary = self._build_summary(session_id, exercise)
        self._frames.clear()
        self._window_start_s = None
        self._rep_count = 0
        self._hold_seconds = 0.0
        self._last_frame_t = None
        return summary

    def _build_summary(self, session_id: str, exercise: str) -> FeatureSummary:
        cat = self.category

        # 이 카테고리가 실제로 쓰는 관절(L_/R_ 접두어 붙여서)만 모은다.
        needed_bases = set(cat.lr_diff_joints) | set(cat.stability_joints)
        needed_joints = {f"{side}_{base}" for base in needed_bases for side in ("L", "R")}
        if cat.load_shift_joint_pair:
            needed_joints |= set(cat.load_shift_joint_pair)
        if cat.hold_joint_pair:
            needed_joints |= set(cat.hold_joint_pair)

        def series(joint: str) -> list[float]:
            return [f["angles"][joint] for f in self._frames]

        means = {j: statistics.fmean(series(j)) for j in needed_joints}
        stdevs = {j: (statistics.pstdev(series(j)) if len(self._frames) > 1 else 0.0) for j in needed_joints}
        roms = {j: max(series(j)) - min(series(j)) for j in needed_joints}

        features = {
            "lr_angle_diff": {
                base: abs(means[f"L_{base}"] - means[f"R_{base}"]) for base in cat.lr_diff_joints
            },
            "instability": {
                f"{base}_{side}": stdevs[f"{side}_{base}"]
                for base in cat.stability_joints
                for side in ("L", "R")
            },
            "rom": {
                f"{base}_{side}": roms[f"{side}_{base}"]
                for base in cat.stability_joints
                for side in ("L", "R")
            },
            "rom_asymmetry": {
                base: abs(roms[f"L_{base}"] - roms[f"R_{base}"]) for base in cat.stability_joints
            },
        }
        load_shift = self._load_shift(means)
        if load_shift is not None:
            features["load_shift"] = load_shift

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
            hold_seconds=self._hold_seconds if cat.mode == "hold" else None,
        )

        return FeatureSummary(
            session_id=session_id,
            exercise=exercise,
            window=window,
            features=features,
            confidence=confidence,
        )

    def _load_shift(self, means: dict) -> dict | None:
        # 지정된 관절 쌍의 좌우 각도 차를 쏠림의 대리 신호로 사용 (직접적인 상체 각도 측정 아님)
        pair = self.category.load_shift_joint_pair
        if pair is None:
            return None
        diff = means[pair[0]] - means[pair[1]]
        if abs(diff) < 3.0:
            side_bias = "neutral"
        else:
            side_bias = "left" if diff > 0 else "right"
        return {"trunk_lean_deg": abs(diff), "side_bias": side_bias}
