"""운동 카테고리 레지스트리 (plus_exercise.md 1단계).

카테고리를 추가하려면:
1. 이 폴더에 <카테고리>.py 를 만들고, 모듈 최상위에 `CONFIG = CategoryConfig(...)`
   를 정의한다 (squat.py 참고). 이름은 `CONFIG`로 고정 - 아래 자동 스캔이 이
   이름만 찾는다.
2. 끝. 이 파일(__init__.py)은 따로 안 고쳐도 된다 - 폴더를 스캔해서 자동 등록되고,
   그 즉시 SLUG_TO_CATEGORY에 그 카테고리로 배정된 운동들에 실제로 적용된다.
   (기존엔 여기 CATEGORIES 딕셔너리에도 한 줄 추가해야 했는데, 그러면 3명이
   동시에 이 파일을 건드리게 돼서 없앴다 - 파일 하나 추가로 끝나야 충돌이 안 난다.)

아직 파일이 없는(=구현 안 된) 카테고리로 배정된 슬러그는 안전하게 SQUAT(기존
동작)로 폴백한다 - 틀린 값보다 "예전과 동일하게 동작"이 안전하기 때문.
"""
import importlib
import pkgutil

from .base import CategoryConfig
from .squat import SQUAT


def _discover_categories() -> dict[str, CategoryConfig]:
    """이 폴더 안의 모든 <카테고리>.py 를 읽어서, CONFIG를 가진 것만 등록한다."""
    found: dict[str, CategoryConfig] = {}
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        if module_name in ("base",):
            continue
        module = importlib.import_module(f".{module_name}", package=__name__)
        config = getattr(module, "CONFIG", None)
        if isinstance(config, CategoryConfig):
            found[config.name] = config
    return found


CATEGORIES: dict[str, CategoryConfig] = _discover_categories()

# 운동 슬러그(frontend/src/exercises.js 의 slug) -> 카테고리 이름.
# 42개 전부 배정해둔다(아직 구현 안 된 카테고리도 이름은 미리 붙여둔다).
# plus_exercise.md 초안 기준 1차 배정 - 담당자가 실측하면서 관절/배정을 조정해도 된다.
SLUG_TO_CATEGORY: dict[str, str] = {
    # 하체 굽힘형
    "squats": "squat",
    "lunges": "squat",
    "lunges-step-ups": "squat",
    "high-knees": "squat",
    "donkey-kicks": "squat",
    "side-kicks": "squat",
    "jump-knee-tucks": "squat",
    "fly-steps": "squat",
    "side-leg-raises": "squat",
    # 팔 밀기형
    "push-ups": "push",
    "close-grip-push-ups": "push",
    "tricep-dips": "push",
    "tricep-extensions": "push",
    "pike-push-ups": "push",
    "pseudo-planche": "push",
    "clapping-push-ups": "push",
    # 팔 당기기형
    "chin-ups": "pull",
    "pull-ups": "pull",
    "scapular-shrugs": "pull",
    "doorframe-rows": "pull",
    "body-rows": "pull",
    "sitting-pull-ups": "pull",
    "reverse-angels": "pull",
    # 코어 굽힘형
    "sit-ups": "core_flex",
    "reverse-crunches": "core_flex",
    "bicycle-crunches": "core_flex",
    "flutter-kicks": "core_flex",
    "leg-raises": "core_flex",
    # 등척성 유지형 — 몸을 '펴서' 버티는 계열(각도가 클수록 정자세)
    # 선 자세 가슴 운동은 몸통이 계속 직립이라 trunk 로 판정이 안 된다 →
    # 어깨 각도로 보는 chest_hold 로 분리(chest_hold.py 참고).
    "chest-expansions": "chest_hold",
    # 스퀴즈는 팔을 '모으는' 동작이라 어깨 각도가 반대로 작아진다(20~50°) →
    # 익스팬션 범위로는 정자세가 OUT이 떠서 분리(chest_squeeze.py 참고).
    "chest-squeezes": "chest_squeeze",
    "alt-arm-leg-plank": "isometric",
    "shoulder-taps": "isometric",
    "elbow-plank": "isometric",
    # 젖히기 유지형 — 몸을 '젖혀서' 버티는 계열(각도가 작아질수록 정자세).
    # 실측 결과 trunk 각도가 isometric과 정반대로 움직여 분리했다(extension.py 참고).
    "bridges": "extension",
    "superman": "extension",
    # 백리프트는 다리를 들지 않아 각도가 얕게만 꺾여(정점 165°) extension(max 158°)
    # 으로는 안 잡힌다. 자세한 근거는 back_lift.py 참고.
    "back-lifts": "back_lift",
    # 복합/전신형
    "climbers": "compound",
    "get-ups": "compound",
    "plank-jump-ins": "compound",
    "side-to-side-chops": "compound",
    # 타격형
    "punches": "strike",
}


def get_category(exercise_slug: str) -> CategoryConfig:
    """슬러그로 카테고리 설정을 찾는다. 매핑에 없거나, 매핑은 있지만 아직
    구현 안 된 카테고리면 SQUAT(기존 동작)로 폴백한다."""
    name = SLUG_TO_CATEGORY.get(exercise_slug, "squat")
    return CATEGORIES.get(name, SQUAT)
