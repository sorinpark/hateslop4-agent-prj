"""하체 굽힘형(스쿼트류) - 원래 feature_extractor.py에 하드코딩돼 있던 로직을
그대로 옮긴 것. 무릎 각도로 rep을 세고, 무릎/발목의 좌우·안정성 지표 + 힙 기준
쏠림(load_shift)을 본다. 값은 전부 기존과 동일 - 회귀 테스트 기준점.

이 파일이 카테고리 등록의 표준 형태다: 모듈 최상위에 CONFIG 라는 이름으로
CategoryConfig 인스턴스 하나를 두면, categories/__init__.py 가 이 폴더를 스캔해서
자동으로 등록한다 - __init__.py 를 따로 안 고쳐도 된다(2단계 담당자는 이 폴더에
파일 하나만 추가하면 끝).
"""
from .base import CategoryConfig

CONFIG = CategoryConfig(
    name="squat",
    rep_joint_pair=("L_knee", "R_knee"),
    rep_down_threshold_deg=100.0,  # 무릎 평균 각도가 이 아래로 내려가면 "내려감" 상태
    rep_up_threshold_deg=160.0,    # 이 위로 다시 올라오면 1회 카운트
    lr_diff_joints=("knee", "ankle", "hip"),
    stability_joints=("knee", "ankle"),
    load_shift_joint_pair=("L_hip", "R_hip"),
)

SQUAT = CONFIG  # 읽기 편하라고 붙인 별칭(다른 코드에서 이 이름으로 참조 가능)
