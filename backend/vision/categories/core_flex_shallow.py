"""코어 굽힘형 - 얕은 ROM(core_flex_shallow). bicycle-crunches류.

core_flex(sit-ups/reverse-crunches/leg-raises)와 관찰 관절(힙 각도)은 같지만,
각도 변화 폭이 훨씬 작아서 core_flex와 같은 CONFIG를 못 씀 - 별도 카테고리로 분리.

bicycle-crunches 실측(2026-07-23) 중 발견: 처음엔 core_flex와 같은 CONFIG를
썼는데(rep_rise_margin_deg=65), 10회 넘게 했는데 2번만 카운트됨. 로그 확인 결과
좌우(L_hip/R_hip)가 반대로 움직여 평균이 상쇄되는 문제가 아니라(오히려 거의
동조해서 움직임 - rep_use_max_of_pair는 효과 없음), 무릎을 크게 안 벌리는
동작 특성상 진짜 반등 폭 자체가 대부분 15~50도로 sit-ups(55~99도)보다 훨씬
작은 게 원인이었음. margin을 여러 값으로 시뮬레이션한 결과:
  margin=20 -> 19개 / 25 -> 16개 / 30 -> 10개 / 40 -> 7개
실제 반복 수가 "10번 넘게"였다는 진술 기준으로 30 근처로 잡음 - 정확한 개수
세면서 재검증 필요.
"""
from .base import CategoryConfig

CONFIG = CategoryConfig(
    name="core_flex_shallow",
    rep_joint_pair=("L_hip", "R_hip"),
    rep_down_threshold_deg=130.0,  # core_flex와 동일 - 트로프는 여전히 130 밑으로 잘 내려감
    rep_up_threshold_deg=170.0,    # 안전망(도달 못해도 무방) - core_flex와 동일
    rep_rise_margin_deg=30.0,      # bicycle-crunches 실측(2026-07-23) 기반 - 위 docstring 참고.
                                    # core_flex의 65보다 훨씬 낮음 - 정확한 개수로 재검증 전까지 잠정치.
    lr_diff_joints=("hip",),
    stability_joints=("hip",),
    load_shift_joint_pair=None,
)
