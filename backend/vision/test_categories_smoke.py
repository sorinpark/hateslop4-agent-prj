"""plus_exercise.md STEP 3의 "42개 슬러그 전체 스모크 테스트"를 자동화한 버전.

실측(웹캠으로 직접 운동하며 임계값 맞추기)은 대체하지 않는다 - 그건 사람이 해야
하는 일이고 이미 STEP 2에서 각 카테고리 담당자가 했다. 여기서는 그 결과물(각
categories/<이름>.py 의 CONFIG)이 서로 안 깨졌는지, merge 이후에도 배선이 전부
맞는지를 웹캠 없이 기계적으로 검증한다:
  - 41개 슬러그 전부가 실제로 구현된 카테고리로 연결되는지(squat 폴백 없이)
  - 각 카테고리가 참조하는 관절 이름이 angles.JOINTS에 실제로 존재하는지
  - rep/hold 임계값이 논리적으로 말이 되는지(down < up, min < max)
  - 그 임계값으로 WindowAccumulator를 실제로 돌리면 rep_count/hold_seconds가
    0이나 이상치로 튀지 않고 정상적으로 잡히는지

실행: cd backend/vision && python -m pytest test_categories_smoke.py -v
"""
import math
from collections import namedtuple

from angles import JOINTS
from feature_extractor import WindowAccumulator
from categories import CATEGORIES, SLUG_TO_CATEGORY, get_category

Landmark = namedtuple("Landmark", ["x", "y", "z", "visibility"])

# 카테고리 이름 -> 그 카테고리로 배정된 슬러그 하나(실제 프로덕션 경로인
# get_category(slug)를 그대로 타게 하기 위함 - CategoryConfig를 직접 주입하지 않는다).
_SLUG_FOR_CATEGORY = {}
for _slug, _cat_name in SLUG_TO_CATEGORY.items():
    _SLUG_FOR_CATEGORY.setdefault(_cat_name, _slug)


def default_landmarks() -> list:
    return [Landmark(i * 0.05 + 0.01, i * 0.03 + 0.02, 0.0, 0.9) for i in range(33)]


def landmarks_with_joint_angle(joint_names, theta_deg: float, visibility: float = 0.9) -> list:
    """지정된 관절(들)의 각도를 전부 theta_deg로 고정한 가짜 랜드마크."""
    lm = default_landmarks()
    theta = math.radians(theta_deg)
    for name in joint_names:
        ia, ib, ic = JOINTS[name]
        lm[ia] = Landmark(1.0, 0.0, 0.0, visibility)
        lm[ib] = Landmark(0.0, 0.0, 0.0, visibility)
        lm[ic] = Landmark(math.cos(theta), math.sin(theta), 0.0, visibility)
    return lm


def test_every_slug_resolves_to_its_own_implemented_category():
    """SLUG_TO_CATEGORY가 가리키는 카테고리 파일이 실제로 존재하는지 - 없으면
    get_category()가 조용히 squat으로 폴백해버려서(의도된 안전장치) 여기서 잡아야
    STEP 2에서 만든 카테고리가 실제로 적용되고 있음을 보장할 수 있다."""
    for slug, expected_name in SLUG_TO_CATEGORY.items():
        actual = get_category(slug)
        assert actual.name == expected_name, (
            f"{slug}: '{expected_name}' 카테고리가 구현 안 돼서 "
            f"'{actual.name}'(폴백)로 대신 잡힘"
        )


def test_every_referenced_joint_exists_in_angles_joints():
    for cat in CATEGORIES.values():
        for pair in (cat.rep_joint_pair, cat.hold_joint_pair, cat.load_shift_joint_pair):
            if pair is None:
                continue
            for joint in pair:
                assert joint in JOINTS, f"{cat.name}: '{joint}'가 angles.JOINTS에 없음"
        for base in set(cat.lr_diff_joints) | set(cat.stability_joints):
            for side in ("L", "R"):
                joint = f"{side}_{base}"
                assert joint in JOINTS, (
                    f"{cat.name}: lr_diff_joints/stability_joints의 '{base}' -> "
                    f"'{joint}'가 angles.JOINTS에 없음"
                )


def test_rep_category_thresholds_are_ordered_sanely():
    for cat in CATEGORIES.values():
        if cat.mode != "rep":
            continue
        assert cat.rep_joint_pair is not None, f"{cat.name}: rep_joint_pair 없음"
        assert cat.rep_down_threshold_deg is not None, f"{cat.name}: rep_down_threshold_deg 없음"
        assert cat.rep_up_threshold_deg is not None, f"{cat.name}: rep_up_threshold_deg 없음"
        assert cat.rep_down_threshold_deg < cat.rep_up_threshold_deg, (
            f"{cat.name}: down({cat.rep_down_threshold_deg}) >= up({cat.rep_up_threshold_deg})"
        )


def test_hold_category_thresholds_are_ordered_sanely():
    for cat in CATEGORIES.values():
        if cat.mode != "hold":
            continue
        assert cat.hold_joint_pair is not None, f"{cat.name}: hold_joint_pair 없음"
        assert cat.hold_min_deg is not None, f"{cat.name}: hold_min_deg 없음"
        assert cat.hold_max_deg is not None, f"{cat.name}: hold_max_deg 없음"
        assert cat.hold_min_deg < cat.hold_max_deg, (
            f"{cat.name}: min({cat.hold_min_deg}) >= max({cat.hold_max_deg})"
        )


def test_rep_category_actually_counts_one_rep_end_to_end():
    """down -> up 왕복 한 번을 실제로 흘려보내 rep_count가 정확히 1로 잡히는지 -
    임계값 자체가 틀렸다는 뜻은 아니지만(그건 실측의 몫), 적어도 카테고리 설정이
    WindowAccumulator 배선과 어긋나 rep이 아예 안 잡히는 경우는 여기서 걸러진다."""
    for cat in CATEGORIES.values():
        if cat.mode != "rep":
            continue
        slug = _SLUG_FOR_CATEGORY[cat.name]
        acc = WindowAccumulator(window_seconds=1.0, exercise=slug)

        joints = cat.rep_joint_pair
        up_angle = cat.rep_up_threshold_deg + 5
        down_angle = cat.rep_down_threshold_deg - 5

        acc.add_frame(landmarks_with_joint_angle(joints, up_angle), timestamp_s=0.0)
        acc.add_frame(landmarks_with_joint_angle(joints, down_angle), timestamp_s=0.3)
        acc.add_frame(landmarks_with_joint_angle(joints, up_angle), timestamp_s=0.6)
        acc.add_frame(landmarks_with_joint_angle(joints, up_angle), timestamp_s=1.1)

        summary = acc.get_summary_if_ready("smoke", slug)
        assert summary is not None, f"{cat.name}({slug}): 윈도우가 안 닫힘"
        assert summary.window.rep_count == 1, (
            f"{cat.name}({slug}): down<->up 한 번 왕복했는데 rep_count={summary.window.rep_count}"
        )
        assert summary.window.hold_seconds is None, f"{cat.name}({slug}): rep 모드인데 hold_seconds가 채워짐"


def test_hold_category_actually_accumulates_hold_seconds_end_to_end():
    for cat in CATEGORIES.values():
        if cat.mode != "hold":
            continue
        slug = _SLUG_FOR_CATEGORY[cat.name]
        acc = WindowAccumulator(window_seconds=1.0, exercise=slug)

        joints = cat.hold_joint_pair
        mid_angle = (cat.hold_min_deg + cat.hold_max_deg) / 2

        acc.add_frame(landmarks_with_joint_angle(joints, mid_angle), timestamp_s=0.0)
        acc.add_frame(landmarks_with_joint_angle(joints, mid_angle), timestamp_s=1.1)

        summary = acc.get_summary_if_ready("smoke", slug)
        assert summary is not None, f"{cat.name}({slug}): 윈도우가 안 닫힘"
        assert summary.window.hold_seconds is not None and summary.window.hold_seconds > 0, (
            f"{cat.name}({slug}): 허용 범위 중앙값을 유지했는데 hold_seconds="
            f"{summary.window.hold_seconds}"
        )
        assert summary.window.rep_count == 0, f"{cat.name}({slug}): hold 모드인데 rep_count가 0이 아님"


def test_every_slug_produces_a_summary_without_crashing():
    """41개 슬러그 전부를 기본(중립) 포즈로 한 윈도우 돌려서 예외 없이 FeatureSummary가
    나오는지 확인 - 실제 카메라 앞에서 안 해봐도 배선 오류(KeyError 등)는 여기서 잡힌다."""
    for slug in SLUG_TO_CATEGORY:
        acc = WindowAccumulator(window_seconds=1.0, exercise=slug)
        acc.add_frame(default_landmarks(), timestamp_s=0.0)
        acc.add_frame(default_landmarks(), timestamp_s=1.1)
        summary = acc.get_summary_if_ready("smoke", slug)
        assert summary is not None, f"{slug}: 윈도우가 안 닫힘"


def run_all():
    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)}개 테스트 모두 통과 (41개 슬러그 x {len(CATEGORIES)}개 카테고리)")


if __name__ == "__main__":
    run_all()
