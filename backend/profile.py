"""관찰 프로필 생성 - 온보딩 입력(InjuryInput) -> LLM -> ObservationProfile.

team_plan.md Phase 2 ②. 핵심 설계 원칙(기획.md 10번):
  - 병명은 '관찰 우선순위 컨텍스트'일 뿐, 진단 근거가 아니다.
  - '위험/진단' 단어를 쓰지 않는다(패턴 관찰 톤).
  - focus_areas는 category(input|linked|compensatory)와 reason을 함께 생성.

LLM에는 focus_areas / watch_patterns 두 가지만 생성시키고(LLM이 도메인 판단을
하는 부분), 나머지(user_id, injuries, disclaimer)는 코드가 채운다.
  - injuries: 입력 그대로 보존(LLM이 바꾸면 안 됨)
  - disclaimer: 고정 문구(schemas 기본값)
  - user_id: 서버가 관리(지금은 데모용 고정)

구조화 출력: google-genai의 response_schema로 형식을 강제 -> ObservationProfile로 검증.
"""
from pydantic import BaseModel
from google.genai import types

from schemas import InjuryInput, ObservationProfile, FocusArea, Pattern
from llm import generate

# Pattern enum 값 목록(프롬프트에 그대로 노출 — LLM이 이 중에서만 고르게)
_PATTERN_VALUES = [p.value for p in Pattern]

SYSTEM_INSTRUCTION = (
    "너는 부상 이력 기반 운동 관찰 프로필을 만드는 도우미야. "
    "사용자가 입력한 부위/병명은 '진단'이 아니라 '어디를 더 주의 깊게 관찰할지' 정하는 "
    "컨텍스트로만 쓴다. 다음 원칙을 반드시 지켜:\n"
    "1) '위험', '진단', '손상 위험' 같은 의료적 단정 표현을 쓰지 마라. "
    "관찰/주의 톤으로만 쓴다.\n"
    "2) 병명 자체를 설명하지 마라. 입력된 부위를 중심으로 관찰 부위를 정한다.\n"
    "3) focus_areas의 category는 정확히 다음 중 하나다: "
    "'input'(사용자가 직접 입력한 부위), 'linked'(그 부위와 함께 부담이 가는 인접 부위), "
    "'compensatory'(보상 움직임이 생길 수 있는 부위).\n"
    "4) reason은 한 줄로 짧게, 단정 대신 가능성 톤으로 쓴다.\n"
    "5) watch_patterns는 반드시 다음 값들 중에서만 고른다: "
    f"{_PATTERN_VALUES}. 입력 부위에 의미 있는 패턴을 1~4개 고른다.\n"
    "모든 텍스트는 한국어로 쓴다."
)


# ── LLM이 생성할 부분만 담는 작은 스키마 (response_schema 용) ──────────────
class _FocusAreaOut(BaseModel):
    area: str
    category: str  # input | linked | compensatory
    reason: str


class _ProfileDraft(BaseModel):
    """LLM 출력 전용. ObservationProfile 의 일부(focus_areas, watch_patterns)만."""
    focus_areas: list[_FocusAreaOut]
    watch_patterns: list[str]  # Pattern.value 문자열


def _build_prompt(injuries: list[InjuryInput]) -> str:
    lines = ["다음 부상 이력을 바탕으로 관찰 프로필을 만들어줘.", ""]
    for i, inj in enumerate(injuries, 1):
        side = {"left": "왼쪽", "right": "오른쪽", "both": "양쪽"}.get(inj.side, inj.side)
        cond = f" / 추정 병명: {inj.condition}" if inj.condition else ""
        lines.append(
            f"{i}. 부위: {side} {inj.part}{cond} / 불편감: {inj.discomfort}/5"
        )
    return "\n".join(lines)


def create_profile(injuries: list[InjuryInput], user_id: str = "u_demo") -> ObservationProfile:
    """온보딩 입력 -> Gemini 호출 -> ObservationProfile.

    LLM 호출이 실패하거나 형식이 어긋나면 예외를 그대로 올린다(상위에서 처리).
    """
    resp = generate(
        contents=_build_prompt(injuries),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=_ProfileDraft,
        ),
    )

    # response.parsed: response_schema(_ProfileDraft)로 파싱된 객체
    draft: _ProfileDraft = resp.parsed

    # 코드가 검증/정규화: category와 watch_patterns가 허용값인지 확인
    focus_areas = [
        FocusArea(area=fa.area, category=_norm_category(fa.category), reason=fa.reason)
        for fa in draft.focus_areas
    ]
    watch_patterns = [Pattern(p) for p in draft.watch_patterns if p in _PATTERN_VALUES]

    return ObservationProfile(
        user_id=user_id,
        injuries=injuries,          # 입력 그대로 보존
        focus_areas=focus_areas,
        watch_patterns=watch_patterns,
        # disclaimer: schemas 기본값 사용
    )


def _norm_category(value: str) -> str:
    """LLM이 살짝 다르게 줘도 허용값으로 정규화. 모르면 'linked'로 둠."""
    v = (value or "").strip().lower()
    return v if v in {"input", "linked", "compensatory"} else "linked"
