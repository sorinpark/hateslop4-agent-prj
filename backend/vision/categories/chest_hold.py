"""선 자세 가슴 운동(A 담당) - 체스트 익스팬션 / 체스트 스퀴즈.

isometric(플랭크 계열)에서 분리한 이유 — 실측(2026-07, 폰 앱 오버레이):

  체스트 익스팬션: 그냥 서 있을 때 ~180°, 가슴 펴고 팔 벌려도 "큰 차이 없음"

trunk = 어깨-힙-발목 각도인데, 이 운동들은 선 자세로 몸통이 계속 직립이라 운동을
하든 안 하든 180° 근처에서 거의 안 움직인다. isometric 범위(160~185°)로는 가만히
서 있기만 해도 IN-RANGE가 떠서 "자세를 유지했다"는 판정이 무의미해진다.

→ 몸통이 아니라 **어깨 각도(팔꿈치-어깨-힙)**로 판정한다. 팔을 내리면 어깨 각도가
   작고, 옆으로 벌리면 커지므로 운동 상태가 실제로 구분된다.

해당 운동(2개): chest-expansions, chest-squeezes

⚠️ 아래 범위는 어깨 각도의 기하만 보고 잡은 1차 추정이다(팔 내림 ~20°, 옆으로
   벌림 ~90°). 폰 앱 오버레이로 실측해 조정할 것:
  - 팔을 벌려 유지하는데 OUT이면 → hold_min_deg 를 내린다
  - 팔을 내린 준비자세인데 IN-RANGE면 → hold_min_deg 를 올린다
"""
from .base import CategoryConfig

CONFIG = CategoryConfig(
    name="chest_hold",
    mode="hold",
    hold_joint_pair=("L_shoulder", "R_shoulder"),
    # 팔을 벌려 든 상태만 "유지 중"으로 본다.
    # 팔을 내린 준비자세(어깨 각도 작음)가 IN 으로 새지 않도록 하한을 잡는다.
    hold_min_deg=55.0,
    hold_max_deg=140.0,
    lr_diff_joints=("shoulder", "elbow"),
    stability_joints=("shoulder",),
    load_shift_joint_pair=None,
)
