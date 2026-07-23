"""팔 당기기형(pull) - 친업/풀업/로우류. 팔꿈치 각도로 rep을 세고,
팔꿈치/어깨의 좌우·안정성 지표 + 어깨 기준 쏠림(load_shift)을 본다.

각도 값은 문헌 기반 추정치(미실측) - 담당자(C) 손목 부상으로 category_tuner.py
실측을 못 해서 대신 채워넣음(2026-07-23). 아래 5개 슬러그에는 적용 가능:
chin-ups, pull-ups, doorframe-rows, body-rows, sitting-pull-ups
(전부 팔꿈치를 굽혔다 펴는 게 핵심 동작 - 표준 풀업/친업 팔꿈치 가동범위인
데드행(완전히 폄) ~160도 / 완전히 당긴 상태 ~60~70도를 기준으로 잡음.
어시스트/시티드/도어프레임처럼 풀 ROM이 안 나올 수 있는 변형 동작을 대비해
rep_rise_margin_deg를 안전망으로 추가함 - core_flex/sit-ups 튜닝(2026-07-23)에서
같은 문제를 겪고 만든 필드, 자세한 배경은 categories/base.py 주석 참고).

**scapular-shrugs(견갑 슈러그)는 이 CONFIG로 카운트가 안 됨** - 철봉에 매달려
팔은 편 채로 어깨뼈만 위아래로 움직이는 동작이라 팔꿈치 각도가 거의 안 바뀜.
문헌값을 넣어도 애초에 관찰 관절이 틀려서 못 고침 - 나중에 카테고리 분리하거나
다른 신호(예: 어깨 랜드마크 수직 이동량)로 새로 설계 필요. 지금은 다른 pull
운동과 같은 CONFIG를 쓰고 있어 사실상 rep이 거의 안 잡힐 것으로 예상됨.

실측 전이라 6개 전부(scapular-shrugs 포함) 실제 앱 테스트(작업 순서 7번) 전
반드시 category_tuner.py로 검증 필요 (plus_exercise.md STEP 2 참고).
"""
from .base import CategoryConfig

CONFIG = CategoryConfig(
    name="pull",
    rep_joint_pair=("L_elbow", "R_elbow"),
    rep_down_threshold_deg=70.0,   # 완전히 당긴 상태(친업/풀업 표준 ROM) - 문헌 기반 추정치, 실측 필요
    rep_up_threshold_deg=160.0,    # 데드행(팔 폄) - 문헌 기반 추정치, 실측 필요
    rep_rise_margin_deg=60.0,      # 어시스트/시티드/도어프레임류가 데드행까지 안 돌아올 걸 대비한 안전망
    lr_diff_joints=("elbow", "shoulder"),
    stability_joints=("elbow", "shoulder"),
    load_shift_joint_pair=("L_shoulder", "R_shoulder"),
)
