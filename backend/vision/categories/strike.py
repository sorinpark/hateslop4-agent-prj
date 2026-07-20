"""타격형(A 담당) - 펀치처럼 팔을 지르고 접는 운동.

팔꿈치 각도가 접힘(down) ↔ 펴짐(up)을 오가는 걸 rep으로 센다.

해당 운동(1개): punches
(backfists 는 실측 결과 인식이 어려워 운동 목록에서 제외했다 — 2026-07)

⚠️ 좌우 번갈아 치는 동작 주의 (plus_exercise.md 268줄):
rep_joint_pair는 좌우 '평균'을 쓴다. 양팔을 동시에 지르면 평균이 크게 움직여서 잘
잡히지만, 한쪽씩 번갈아 치면 한 팔이 펴질 때 다른 팔은 접혀 있어 평균이 중간값에
머물러 rep이 거의 안 세일 수 있다.
  → 실측해서 안 맞으면 feature_extractor.py의 _update_rep_count에 "좌우 중 하나라도
    임계값을 넘으면 카운트" 같은 예외 로직이 필요하다. 이건 공용 파일이라 2단계
    원칙(공용 파일 안 건드림)에 어긋나므로, 손대기 전에 팀에 먼저 공유할 것.

⚠️ 아래 각도는 plus_exercise.md 5절의 추정치 시작점이다. 실측 전이므로 그대로 쓰면
안 되고, category_tuner.py로 직접 해보며 맞춰야 한다.
  cd backend/vision && python category_tuner.py punches
"""
from .base import CategoryConfig

CONFIG = CategoryConfig(
    name="strike",
    rep_joint_pair=("L_elbow", "R_elbow"),
    # 좌우 평균 대신 "더 펴진 쪽"으로 판정 — 번갈아 치기 대응(위 주석 참고).
    rep_use_max_of_pair=True,
    # 실측(2026-07, 측면 촬영): 접으면 40°대까지 내려가고 뻗으면 160° 이상.
    # down 은 접힘을 확실히 잡되 어중간한 자세는 걸리지 않게 여유를 둔다.
    rep_down_threshold_deg=90.0,
    rep_up_threshold_deg=155.0,
    lr_diff_joints=("elbow", "shoulder"),
    stability_joints=("elbow",),
    load_shift_joint_pair=("L_shoulder", "R_shoulder"),
)
