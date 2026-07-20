"""상체만 젖히기(A 담당) - 백리프트 전용.

extension(브릿지/슈퍼맨)에서 다시 분리한 이유 — 실측(2026-07, 폰 앱 오버레이):

  슈퍼맨   준비 180°  → 정점 150°   (상체 + 다리를 둘 다 듦)
  브릿지   준비 160~170° → 정점 156°
  백리프트 준비 180°  → 정점 165°   (상체만 듦, 다리는 바닥 고정)

trunk = 어깨-힙-발목 각도인데, 백리프트는 다리를 들지 않아 발목이 바닥에 고정된
채라 각도가 얕게(165°까지만) 꺾인다. extension의 max(158°)로는 정점에서도 OUT이
뜬다. 그렇다고 max를 165° 위로 올리면 브릿지의 준비자세(160~170°)가 IN으로 새서
브릿지 판정이 망가지므로, 같은 카테고리로 묶을 수 없다.

해당 운동(1개): back-lifts

범위 근거: 정점 165° / 준비 180°. 그 사이인 172°를 경계로 잡아 양쪽을 가른다.
  - 정점에서 OUT이면 → hold_max_deg 를 올린다(단 180°에 너무 가까우면 준비자세가 샌다)
  - 누운 준비자세인데 IN-RANGE면 → hold_max_deg 를 내린다
"""
from .base import CategoryConfig

CONFIG = CategoryConfig(
    name="back_lift",
    mode="hold",
    hold_joint_pair=("L_trunk", "R_trunk"),
    # 상체를 든 상태(165° 부근)만 "유지 중"으로 본다.
    # 누운 상태(180°)와 확실히 갈리도록 상한을 172°로 잡았다.
    hold_min_deg=140.0,
    hold_max_deg=172.0,
    lr_diff_joints=("trunk",),
    stability_joints=("trunk",),
    load_shift_joint_pair=None,
)
