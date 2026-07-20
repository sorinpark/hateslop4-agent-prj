"""가슴 앞 모으기(A 담당) - 체스트 스퀴즈 전용.

chest_hold(체스트 익스팬션)에서 분리한 이유 — 실측(2026-07, 폰 앱 오버레이):

  체스트 익스팬션: 팔을 옆으로 '벌림'  → 어깨 각도 큼   (55~140° 범위로 판정 OK)
  체스트 스퀴즈  : 팔을 가슴 앞으로 '모음' → 어깨 각도 20~50°

어깨 각도(팔꿈치-어깨-힙) 기준으로 두 운동이 정반대 방향으로 움직여서, 하나의
범위로는 묶을 수 없다. 익스팬션 범위(하한 55°)를 그대로 쓰면 스퀴즈는 정자세인데도
OUT이 뜬다.

해당 운동(1개): chest-squeezes

⚠️ 주의: 팔을 내린 준비자세도 어깨 각도가 작다(팔이 몸통에 붙어 ~10-20°).
   손바닥을 맞댄 자세(20~50°)와 겹칠 수 있어, 하한을 준비자세보다 위로 잡아야
   구분이 된다. 아래 값은 실측 20~50°를 근거로 한 1차 설정이며, 준비자세 각도를
   확인해 조정할 것:
  - 팔 내린 준비자세인데 IN-RANGE면 → hold_min_deg 를 올린다
  - 손바닥 맞댄 정자세인데 OUT이면   → hold_min_deg 를 내린다
"""
from .base import CategoryConfig

CONFIG = CategoryConfig(
    name="chest_squeeze",
    mode="hold",
    hold_joint_pair=("L_shoulder", "R_shoulder"),
    # 손바닥을 가슴 앞에서 맞댄 상태(20~50°)를 "유지 중"으로 본다.
    hold_min_deg=18.0,
    hold_max_deg=60.0,
    lr_diff_joints=("shoulder", "elbow"),
    stability_joints=("shoulder",),
    load_shift_joint_pair=None,
)
