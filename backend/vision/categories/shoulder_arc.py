"""어깨 원호형(shoulder_arc) - reverse-angels류. 팔을 편 채로 어깨를 축으로
크게 원을 그리는 동작이라, pull(팔꿈치 굽힘) 카테고리와는 관찰 관절이 다르다.

reverse-angels 실측(2026-07-23) 중 발견: 처음엔 pull.py(팔꿈치 기반)를 그대로
썼는데 10회 했더니 22~24회로 카운트됨. 원인 분석 결과 트래킹 글리치(각속도
필터로 일부 개선, feature_extractor.py의 REP_MAX_ANGULAR_VELOCITY_DEG_PER_S
참고)도 있었지만, margin을 90~120까지 올려도 12~15개로 안 줄어드는 걸 보고
"애초에 관찰 관절이 틀렸다"고 판단 - 리버스 엔젤은 팔을 편 채로 유지하는 게
정자세라 팔꿈치가 반복적으로 크게 굽혀질 이유가 없음(그런데도 낮은 값이 자꾸
나온 건 자세 특성상 팔꿈치 각도 자체가 이 동작의 핵심 신호가 아니기 때문으로
추정). pull.py도 이미 `lr_diff_joints`/`stability_joints`/`load_shift_joint_pair`에
어깨를 쓰고 있었지만 rep_joint_pair만 팔꿈치였던 것 - 여기서는 rep_joint_pair도
어깨로 맞춤.

어깨 각도로 바꾼 뒤 재실측(2026-07-23, 정확히 10회 세면서 테스트) 결과 글리치가
거의 사라짐(rep 지속시간이 0.2~4초로 자연스러워짐 - 팔꿈치 기반이었을 때
0.03~0.5초짜리 비정상적으로 빠른 완료가 많았던 것과 대조적). margin을
50~110까지 시뮬레이션한 결과 95~105 구간에서 정확히 10개로 일치 - margin=100으로
확정. down/up 임계값 자체는 margin이 사실상 rep 판정을 전담하고 있어서(다른
core_flex/pull 카테고리와 동일한 패턴) 큰 의미는 없지만, 실측 범위(전체 세션
0.2~160도)에 맞춰 그대로 둠.
"""
from .base import CategoryConfig

CONFIG = CategoryConfig(
    name="shoulder_arc",
    rep_joint_pair=("L_shoulder", "R_shoulder"),  # 팔꿈치-어깨-힙: 팔이 몸통에서 얼마나 벌어졌는지
    rep_down_threshold_deg=20.0,   # 팔이 몸통 옆에 붙은 상태 - 실측 범위와 부합
    rep_up_threshold_deg=120.0,    # 팔이 크게 들린/벌어진 상태 - 안전망(도달 못해도 무방)
    rep_rise_margin_deg=100.0,     # reverse-angels 실측(2026-07-23) 정확히 10개 일치 - 확정
    lr_diff_joints=("elbow", "shoulder"),
    stability_joints=("elbow", "shoulder"),
    load_shift_joint_pair=("L_shoulder", "R_shoulder"),
)
