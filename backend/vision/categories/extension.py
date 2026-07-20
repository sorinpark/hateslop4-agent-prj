"""젖히기 유지형(A 담당) - 브릿지/슈퍼맨/백리프트처럼 몸을 '젖혀서' 버티는 운동.

isometric(플랭크 계열)에서 분리한 이유 — 실측(2026-07, 폰 앱 오버레이)에서
trunk 각도가 정반대로 움직인다는 걸 확인했다:

  플랭크: 정자세일수록 몸이 펴져서 각도가 크다(170°대) → 처지면 작아짐
  브릿지: 준비자세(엉덩이 바닥) 160~170° → 엉덩이를 들면 156° 이하로 '작아짐'
  슈퍼맨: 준비자세(엎드림)  ~180°      → 상체·다리를 들면 ~150°로 '작아짐'

trunk = 어깨-힙-발목 각도인데, 이 운동들은 몸을 젖히면 그 세 점이 만드는 각이
오히려 꺾이기 때문이다. 그래서 isometric의 범위(160~185°)를 그대로 쓰면 쉬는
자세를 "유지 중"으로 세고 정작 버티는 자세를 놓치는 정반대 판정이 나온다.

해당 운동(2개): bridges, superman
(back-lifts 는 다리를 들지 않아 각도가 얕게만 꺾여 이 범위로 안 잡힌다 → back_lift.py 로 분리)

⚠️ 아래 범위는 위 실측값을 근거로 한 1차 추정이다. 정점 각도를 아직 좁게 재지
못했으므로(브릿지 "156° 이하", 슈퍼맨 "150° 부근"), category_tuner.py 또는 폰
앱 오버레이로 각 운동의 '정점에서 안정적으로 유지되는 각도'를 확인하고 조정할 것.
  - 정자세로 버티는데 OUT이면 → hold_max_deg 를 올린다
  - 준비자세(쉼)인데 IN-RANGE면 → hold_max_deg 를 내린다(쉼 각도보다 확실히 아래로)
"""
from .base import CategoryConfig

CONFIG = CategoryConfig(
    name="extension",
    mode="hold",
    hold_joint_pair=("L_trunk", "R_trunk"),
    # 젖힌 상태(각도가 작아진 쪽)를 "유지 중"으로 본다.
    # max 는 쉬는 자세(브릿지 160°, 슈퍼맨 180°)보다 확실히 낮게 잡아야
    # 준비자세가 IN 으로 새지 않는다.
    hold_min_deg=110.0,
    hold_max_deg=158.0,
    lr_diff_joints=("trunk",),
    stability_joints=("trunk",),
    load_shift_joint_pair=None,
)
