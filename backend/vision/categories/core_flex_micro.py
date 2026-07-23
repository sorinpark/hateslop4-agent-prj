"""코어 굽힘형 - 초소폭 ROM(core_flex_micro). flutter-kicks류.

core_flex_shallow(bicycle-crunches, margin=30)보다도 각도 변화 폭이 훨씬 작은
운동을 위한 카테고리. flutter-kicks 실측(2026-07-23, 정확히 10개 세면서 재테스트):
발을 빠르게 움직이고 허리(몸통)는 거의 안 움직이는 동작이라, 힙 각도(어깨-힙-무릎)
전체 범위가 세션 내내 74~146도 정도로 매우 좁음. margin을 여러 값으로
시뮬레이션한 결과 margin=9일 때 정확히 실제 개수(10개)와 일치.

⚠️ 주의: margin이 이렇게 작으면(9도) 카메라 흔들림 등 다른 노이즈에도
민감하게 반응할 수 있음 - core_flex_shallow(30)나 core_flex(65)보다 훨씬
오탐 위험이 큼. rep_down_threshold_deg(130)는 사실상 거의 항상 이 밑에
머물러서(실측 468프레임 중 463프레임이 130 밑) 의미가 크지 않고, rep 판정은
사실상 margin 하나에 의존하고 있음 - 실제 앱 테스트(작업 순서 7번) 때 오탐이
심하면 margin을 더 올리거나 다른 신호(예: 발목 랜드마크 수직 이동)로 재설계
고려할 것.
"""
from .base import CategoryConfig

CONFIG = CategoryConfig(
    name="core_flex_micro",
    rep_joint_pair=("L_hip", "R_hip"),
    rep_down_threshold_deg=130.0,  # 사실상 거의 항상 이 밑 - 위 docstring 참고
    rep_up_threshold_deg=170.0,    # 안전망(도달 못해도 무방)
    rep_rise_margin_deg=9.0,       # flutter-kicks 실측(2026-07-23) 10개 정확히 일치
    lr_diff_joints=("hip",),
    stability_joints=("hip",),
    load_shift_joint_pair=None,
)
