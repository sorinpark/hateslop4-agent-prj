"""복합/전신형(B 담당) - 마운틴 클라이머 / 겟업 / 플랭크 점프인 / 사이드 투 사이드 찹.

해당 운동(4개): climbers, get-ups, plank-jump-ins, side-to-side-chops

⚠️ plus_exercise.md가 미리 경고한 대로, 이 4개는 서로 많이 다른 동작이라 하나의
임계값(심지어 하나의 관절 축)으로 다 안 잡힐 가능성이 높다:
  - climbers(마운틴 클라이머), plank-jump-ins(플랭크 점프인): 플랭크 자세에서
    무릎을 가슴 쪽으로 당겼다 펴는 동작이라 무릎 각도(rep_joint_pair)로 비교적
    잘 잡힐 것으로 예상된다. 아래 값은 이 둘을 기준으로 잡은 시작점.
  - get-ups(겟업): 눕거나 웅크린 자세에서 일어서기까지 여러 관절이 동시에 크게
    바뀌는 전신 동작이라, 무릎 각도 하나로 "1회"의 시작/끝을 안정적으로 잡기
    어려울 수 있다. 실측해서 안 맞으면 hip 등 다른 관절로 바꾸거나, 이 운동만
    별도 카테고리 파일로 분리하는 것도 고려할 것(예: A가 등척성을 실측 후
    chest_hold/chest_squeeze/extension/back_lift로 쪼갠 선례 참고).
  - side-to-side-chops(사이드 투 사이드 찹): 몸통을 좌우로 비트는(회전) 동작인데,
    angles.py의 JOINTS는 전부 굽힘/폄(flexion) 각도만 정의돼 있고 회전(rotation)
    각도는 없다. 무릎/힙 각도로는 이 회전 동작이 거의 안 잡힐 가능성이 크다.
    실측해서 정말 안 맞으면 어깨 좌우 각도차(lr_diff)로 흔들림만 관찰하는 선에서
    타협하거나, angles.py에 회전 각도를 추가하는 논의가 필요하다(공용 파일이라
    손대기 전 팀 공유 원칙 적용 - plus_exercise.md 6절).

⚠️ 아래 각도는 plus_exercise.md 5절의 추정치 시작점이다. 실측 전이므로 그대로 쓰면
안 되고, category_tuner.py로 직접 해보며 맞춰야 한다.
  cd backend/vision && python category_tuner.py climbers
  (나머지도 각각 최소 1회씩: get-ups, plank-jump-ins, side-to-side-chops -
   특히 get-ups/side-to-side-chops는 위 경고대로 이 값이 안 맞을 확률이 높다)
"""
from .base import CategoryConfig

CONFIG = CategoryConfig(
    name="compound",
    rep_joint_pair=("L_knee", "R_knee"),  # 시작점 — climbers/plank-jump-ins 기준
    rep_down_threshold_deg=110.0,
    rep_up_threshold_deg=160.0,
    lr_diff_joints=("knee", "shoulder"),
    stability_joints=("knee", "trunk"),
    load_shift_joint_pair=("L_hip", "R_hip"),
)
