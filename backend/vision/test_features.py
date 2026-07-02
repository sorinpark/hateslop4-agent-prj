"""angles.py / feature_extractor.py 로직 검증용 최소 유닛 테스트 (웹캠 불필요).
가짜 랜드마크(namedtuple)로 MediaPipe 출력을 흉내낸다.
실행: python test_features.py (backend/vision 디렉토리에서)
"""
import math
from collections import namedtuple

from angles import calculate_angle, compute_joint_angles
from feature_extractor import WindowAccumulator

Landmark = namedtuple("Landmark", ["x", "y", "z", "visibility"])


def default_landmarks() -> list:
    return [Landmark(i * 0.05 + 0.01, i * 0.03 + 0.02, 0.0, 0.9) for i in range(33)]


def landmarks_with_knee_angle(theta_deg: float, visibility: float = 0.9) -> list:
    """무릎(hip-knee-ankle) 각도를 theta_deg로 고정한 가짜 랜드마크."""
    lm = default_landmarks()
    theta = math.radians(theta_deg)
    for hip_idx, knee_idx, ankle_idx in [(23, 25, 27), (24, 26, 28)]:
        lm[hip_idx] = Landmark(1.0, 0.0, 0.0, visibility)
        lm[knee_idx] = Landmark(0.0, 0.0, 0.0, visibility)
        lm[ankle_idx] = Landmark(math.cos(theta), math.sin(theta), 0.0, visibility)
    return lm


def test_calculate_angle_right_angle():
    angle = calculate_angle((1, 0), (0, 0), (0, 1))
    assert math.isclose(angle, 90.0, abs_tol=1e-6), angle


def test_calculate_angle_straight_line():
    angle = calculate_angle((0, 0), (1, 0), (2, 0))
    assert math.isclose(angle, 180.0, abs_tol=1e-6), angle


def test_calculate_angle_zero_length_vector_safe():
    angle = calculate_angle((0, 0), (0, 0), (1, 0))
    assert angle == 0.0


def test_compute_joint_angles_matches_forced_knee():
    lm = landmarks_with_knee_angle(120.0)
    angles = compute_joint_angles(lm)
    assert math.isclose(angles["L_knee"], 120.0, abs_tol=1e-6)
    assert math.isclose(angles["R_knee"], 120.0, abs_tol=1e-6)


def test_window_accumulator_emits_after_window_seconds():
    acc = WindowAccumulator(window_seconds=1.0)
    assert acc.get_summary_if_ready("s1", "squat") is None

    acc.add_frame(landmarks_with_knee_angle(170.0), timestamp_s=0.0)
    assert acc.get_summary_if_ready("s1", "squat") is None  # 아직 1초 안 지남

    acc.add_frame(landmarks_with_knee_angle(170.0), timestamp_s=1.2)
    summary = acc.get_summary_if_ready("s1", "squat")
    assert summary is not None
    assert summary.session_id == "s1"
    assert summary.exercise == "squat"
    assert set(summary.features.keys()) == {
        "lr_angle_diff", "instability", "rom", "rom_asymmetry", "load_shift",
    }
    assert set(summary.features["lr_angle_diff"].keys()) == {"knee", "ankle", "hip"}
    assert set(summary.features["load_shift"].keys()) == {"trunk_lean_deg", "side_bias"}

    # 소비 후 버퍼가 리셋됐는지 확인
    assert acc.get_summary_if_ready("s1", "squat") is None


def test_rep_count_down_then_up_counts_one():
    acc = WindowAccumulator(window_seconds=1.0)
    acc.add_frame(landmarks_with_knee_angle(170.0), timestamp_s=0.0)   # up
    acc.add_frame(landmarks_with_knee_angle(90.0), timestamp_s=0.3)    # down (<100)
    acc.add_frame(landmarks_with_knee_angle(170.0), timestamp_s=0.6)   # up (>160) -> rep 1
    acc.add_frame(landmarks_with_knee_angle(170.0), timestamp_s=1.1)

    summary = acc.get_summary_if_ready("s1", "squat")
    assert summary is not None
    assert summary.window.rep_count == 1


def test_confidence_below_threshold_flagged():
    acc = WindowAccumulator(window_seconds=1.0)
    acc.add_frame(landmarks_with_knee_angle(170.0, visibility=0.1), timestamp_s=0.0)
    acc.add_frame(landmarks_with_knee_angle(170.0, visibility=0.1), timestamp_s=1.1)

    summary = acc.get_summary_if_ready("s1", "squat")
    assert summary.confidence.below_threshold is True
    assert summary.confidence.interp_ratio == 0.0


def test_lr_angle_diff_detects_asymmetry():
    lm = default_landmarks()
    # 왼쪽 무릎: 90도, 오른쪽 무릎: 170도 -> 좌우 차 발생
    lm[23], lm[25], lm[27] = Landmark(1, 0, 0, 0.9), Landmark(0, 0, 0, 0.9), Landmark(math.cos(math.radians(90)), math.sin(math.radians(90)), 0, 0.9)
    lm[24], lm[26], lm[28] = Landmark(1, 0, 0, 0.9), Landmark(0, 0, 0, 0.9), Landmark(math.cos(math.radians(170)), math.sin(math.radians(170)), 0, 0.9)

    acc = WindowAccumulator(window_seconds=1.0)
    acc.add_frame(lm, timestamp_s=0.0)
    acc.add_frame(lm, timestamp_s=1.1)
    summary = acc.get_summary_if_ready("s1", "squat")
    assert summary.features["lr_angle_diff"]["knee"] > 50.0


def run_all():
    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)}개 테스트 모두 통과")


if __name__ == "__main__":
    run_all()
