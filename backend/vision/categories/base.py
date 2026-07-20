"""카테고리 설정의 공통 형태 (plus_exercise.md 1단계).

카테고리 하나 = "이 운동 묶음은 어떤 관절로 rep(또는 유지 시간)을 판정하고,
어떤 관절로 좌우/안정성 지표를 뽑을지"를 담은 설정값. 코드가 아니라 데이터라서,
2단계에서 새 카테고리를 추가할 땐 이 dataclass의 인스턴스 하나만 만들면 된다
(feature_extractor.py 쪽 로직은 건드릴 필요 없음 - rep 모드/hold 모드 둘 다).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryConfig:
    name: str

    # "rep": down/up 각도를 오가는 반복 횟수로 판정.
    # "hold": 각도가 허용 범위 안에 머무른 누적 시간으로 판정(등척성 유지형).
    mode: str = "rep"

    # ── mode="rep" 전용: 반복 횟수 판정 ─────────────────────────────────
    # 좌우 평균을 낼 관절 쌍. mode="hold"면 안 쓴다(None으로 둔다).
    rep_joint_pair: tuple[str, str] | None = None
    rep_down_threshold_deg: float | None = None
    rep_up_threshold_deg: float | None = None

    # 좌우를 평균내지 않고 "더 펴진 쪽(각도가 큰 쪽)"만 보고 판정할지 여부.
    # 기본값 False = 기존과 동일(좌우 평균) — 다른 카테고리는 영향 없음.
    #
    # True 로 두는 경우: 좌우를 번갈아 쓰는 운동(펀치/백피스트).
    # 측면 촬영에서 카메라 먼 쪽 팔은 몸통에 가려(오클루전) 각도가 제대로 안 잡히는데,
    # 평균을 쓰면 그 값이 발목을 잡아 가까운 팔을 다 뻗어도 up 임계값을 못 넘긴다.
    # 그래서 "좌우 중 하나라도 뻗었으면 뻗은 것"으로 보도록 max 를 쓴다.
    # (plus_exercise.md 268줄이 예고한 예외 케이스)
    rep_use_max_of_pair: bool = False

    # ── mode="hold" 전용: 자세 유지 시간 판정 ───────────────────────────
    # 좌우 평균을 낼 관절 쌍(예: 플랭크의 trunk). mode="rep"이면 안 쓴다.
    hold_joint_pair: tuple[str, str] | None = None
    # 이 범위 안이면 "자세 유지 중"으로 본다 (예: 몸통 일직선 165~180도).
    hold_min_deg: float | None = None
    hold_max_deg: float | None = None

    # ── feature 계산에 쓸 관절 베이스 이름들 (angles.py의 "L_"/"R_" 접두어 제외한 이름) ──
    # lr_angle_diff에 들어갈 관절들 (좌우 차이)
    lr_diff_joints: tuple[str, ...] = ()
    # instability/rom/rom_asymmetry에 들어갈 관절들 (흔들림/가동범위)
    stability_joints: tuple[str, ...] = ()
    # load_shift(쏠림) 판정에 쓸 관절 쌍. 이 카테고리에서 의미가 없으면 None.
    load_shift_joint_pair: tuple[str, str] | None = ("L_hip", "R_hip")
