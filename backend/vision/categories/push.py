"""팔 밀기형(B 담당) - 팔꿈치를 굽혔다 펴는 밀기 동작.

팔꿈치 각도가 굽힘(down) ↔ 펴짐(up)을 오가는 걸 rep으로 센다.

해당 운동(7개): push-ups, close-grip-push-ups, tricep-dips, tricep-extensions,
pike-push-ups, pseudo-planche, clapping-push-ups

7개 모두 "팔꿈치를 굽혔다 편다"는 동작 축은 같아서 카테고리 하나로 묶였지만,
굽힘 깊이/자세는 종류별로 다를 수 있다:
  - push-ups, close-grip-push-ups, pike-push-ups, clapping-push-ups: 몸통이
    거의 일직선인 플랭크형 자세라 stability_joints에 trunk를 같이 봐서
    허리/골반이 처지는지도 관찰한다.
  - tricep-dips, tricep-extensions: 몸통이 수직/좌식에 가까운 자세라 trunk
    각도의 의미가 플랭크형과 다를 수 있음 - 실측 시 유의.
  - pseudo-planche: 버티는 성격이 강해 rep보다 hold에 가까울 수 있다 - 실측해서
    rep으로 잘 안 잡히면 hold 모드(등척성 카테고리 참고)로 옮기는 것도 고려할 것.

⚠️ 아래 각도는 plus_exercise.md 5절의 추정치 시작점이다. 실측 전이므로 그대로 쓰면
안 되고, category_tuner.py로 직접 해보며 맞춰야 한다.
  cd backend/vision && python category_tuner.py push-ups
  (나머지 6개도 각각 최소 1회씩: close-grip-push-ups, tricep-dips,
   tricep-extensions, pike-push-ups, pseudo-planche, clapping-push-ups)
"""
from .base import CategoryConfig

CONFIG = CategoryConfig(
    name="push",
    rep_joint_pair=("L_elbow", "R_elbow"),
    rep_down_threshold_deg=90.0,   # 팔꿈치 깊게 굽힘 — 튜닝 필요
    rep_up_threshold_deg=160.0,    # 팔 펴짐 — 튜닝 필요
    lr_diff_joints=("elbow", "shoulder"),
    stability_joints=("elbow", "trunk"),   # trunk: 허리/골반 처짐 감지용
    load_shift_joint_pair=("L_shoulder", "R_shoulder"),
)
