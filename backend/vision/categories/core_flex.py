"""코어 굽힘형(core_flex) - 윗몸일으키기/크런치류. 누운 자세에서 힙 각도로
rep을 세고, 힙의 좌우·안정성 지표를 본다. 누운 자세라 좌우 쏠림(load_shift)은
스쿼트만큼 의미 있지 않아 None으로 둔다.

각도 값은 전부 추정치(미실측) - category_tuner.py로 직접 운동하며 튜닝할 것
(plus_exercise.md STEP 2 참고).
"""
from .base import CategoryConfig

CONFIG = CategoryConfig(
    name="core_flex",
    rep_joint_pair=("L_hip", "R_hip"),  # 스쿼트와 같은 관절이지만 누운 자세라 임계값은 완전히 다름
    rep_down_threshold_deg=130.0,  # 크런치 정점(상체가 많이 말림) - leg-raises 실측(2026-07-23)으로 확인
    rep_up_threshold_deg=170.0,    # 완전히 눕는 편한 자세 - 매 rep 도달은 못해도 안전망으로 유지
    rep_rise_margin_deg=65.0,      # sit-ups 실측(2026-07-23) 결과, 매 rep마다 절대각(170)까지
                                    # 못 돌아오고 40~170도 사이를 들쭉날쭉하게 오가는 걸 확인.
                                    # 대신 "내려간 지점 대비 이만큼 다시 올라오면 rep 인정"으로 판정.
                                    # 처음엔 50으로 뒀더니 rep 끝나고 몸이 살짝 튕기는 얕은 반동
                                    # (예: 86->136도, 폭 50.3)까지 rep으로 잡혀서 65로 상향
                                    # — 실측 로그의 "진짜 반등"은 대부분 55~99도였음.
    lr_diff_joints=("hip",),
    stability_joints=("hip",),
    load_shift_joint_pair=None,   # 누운 자세라 좌우 쏠림 신호가 스쿼트만큼 의미 있지 않음
)
