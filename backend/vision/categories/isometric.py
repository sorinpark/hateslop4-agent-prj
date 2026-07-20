"""등척성 유지형(A 담당) - 플랭크/브릿지/슈퍼맨처럼 '버티는' 운동.

rep(횟수)이 아니라 mode="hold"로 자세 유지 시간을 잰다. 몸통(trunk = 어깨-힙-발목)
각도가 hold_min~hold_max 범위 안에 있는 동안만 시간이 누적된다. 플랭크에서 엉덩이가
처지거나(각도 커짐) 솟으면(각도 작아짐) 범위를 벗어나 누적이 멈추는 구조.

해당 운동(3개): elbow-plank, alt-arm-leg-plank, shoulder-taps
(원래 8개였으나 실측 결과 trunk 거동이 달라 분리됨:
 bridges/superman → extension.py, back-lifts → back_lift.py,
 chest-expansions/chest-squeezes → chest_hold.py)

⚠️ 아래 각도는 plus_exercise.md 5절의 추정치 시작점이다. 실측 전이므로 그대로 쓰면
안 되고, category_tuner.py로 8개 운동을 직접 해보며 맞춰야 한다.
  cd backend/vision && python category_tuner.py elbow-plank
"""
from .base import CategoryConfig

CONFIG = CategoryConfig(
    name="isometric",
    mode="hold",
    hold_joint_pair=("L_trunk", "R_trunk"),
    # 몸통이 일직선에 가까울 때만 "유지 중"으로 본다.
    # TODO(실측): 플랭크를 정자세로 잡았을 때 화면에 뜨는 trunk 각도를 보고 조정.
    #   - 정자세인데 OUT이 뜨면 범위를 넓히고(min 낮추기 / max 높이기)
    #   - 엉덩이를 처지게/솟게 했는데도 IN-RANGE면 범위를 좁힌다
    hold_min_deg=160.0,
    hold_max_deg=185.0,
    lr_diff_joints=("trunk",),
    stability_joints=("trunk",),  # 처짐/솟음(피케) 흔들림 감지
    load_shift_joint_pair=None,   # 버티는 자세라 좌우 쏠림 신호가 의미 약함
)
