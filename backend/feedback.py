"""실시간 피드백 생성 - 특징 요약(FeatureSummary) + 관찰 프로필 -> LLM -> FeedbackResponse.

team_plan.md Phase 2 ②. profile.py와 동일한 설계 원칙(기획.md 10번)을 따른다:
  - '위험/진단' 단어를 쓰지 않는다(패턴 관찰 톤).
  - 제안(suggestion)은 '참고 정보'임을 note_tag로 명시한다.
  - evidence는 실제로 features에 존재하는 키만 인용한다.

LLM에는 messages(관찰/제안 목록)만 생성시키고, session_id / window_end_s는
코드가 summary에서 그대로 채운다(LLM이 바꾸면 안 되는 값).

가드레일 후처리(기획.md 전환7): 프롬프트 지시만으로는 확신형 표현("~하세요",
"위험합니다") 유출을 보장할 수 없으므로, 실제 출력 텍스트를 정규식으로 한 번 더
점검해서 guardrail_passed를 판정한다.

구조화 출력: google-genai의 response_schema로 형식을 강제 -> FeedbackMessage로 검증.
"""
import re

from pydantic import BaseModel
from google.genai import types

from schemas import ObservationProfile, FeatureSummary, FeedbackMessage, FeedbackResponse
from llm import generate

SYSTEM_INSTRUCTION = (
    "너는 운동 중 실시간으로 관찰 피드백을 만드는 도우미야. "
    "사용자의 부상 이력(관찰 프로필)과 방금 몇 초간의 동작 특징 요약을 보고, "
    "화면에 바로 보여줄 피드백 메시지를 만든다. 다음 원칙을 반드시 지켜:\n"
    "1) '위험', '진단', '손상 위험' 같은 의료적 단정 표현을 쓰지 마라. "
    "관찰/주의 톤으로만 쓴다.\n"
    "2) type은 정확히 다음 중 하나다: "
    "'observation'(features에 실제로 관찰된 패턴을 설명), "
    "'suggestion'(참고 정보로서의 제안 — 반드시 단정하지 않는 톤).\n"
    "3) suggestion 메시지에는 note_tag를 '참고 정보입니다'로 채운다. "
    "observation 메시지의 note_tag는 비워둔다(null).\n"
    "4) evidence는 입력으로 주어진 features의 키 중에서 실제로 그 메시지의 "
    "근거가 된 것만 골라 적는다. features에 없는 키를 지어내지 마라.\n"
    "5) area는 관찰 프로필의 focus_areas에 있는 부위 표현을 우선 사용한다. "
    "특정 부위와 관련 없는 메시지는 area를 비워둔다(null).\n"
    "6) 화면에 한 번에 너무 많이 띄우면 산만하니 메시지는 1~3개만 만든다. "
    "features에 특별히 주목할 패턴이 없으면 빈 목록을 반환해도 된다.\n"
    "7) 모든 텍스트는 한국어로, 실시간 운동 중 짧게 읽을 수 있게 간결히 쓴다."
)


# ── LLM이 생성할 부분만 담는 작은 스키마 (response_schema 용) ──────────────
class _FeedbackMessageOut(BaseModel):
    type: str  # observation | suggestion
    text: str
    area: str | None = None
    evidence: list[str] = []
    note_tag: str | None = None


class _FeedbackDraft(BaseModel):
    """LLM 출력 전용. FeedbackResponse의 일부(messages)만."""
    messages: list[_FeedbackMessageOut]


def _build_prompt(profile: ObservationProfile, summary: FeatureSummary) -> str:
    lines = ["다음 관찰 프로필과 방금 관찰된 동작 특징을 바탕으로 피드백을 만들어줘.", ""]

    lines.append("[관찰 프로필]")
    for fa in profile.focus_areas:
        lines.append(f"- {fa.area} ({fa.category}): {fa.reason}")
    if profile.watch_patterns:
        lines.append(f"- 주의 패턴: {[p.value for p in profile.watch_patterns]}")
    lines.append("")

    lines.append("[방금 관찰된 동작 특징]")
    lines.append(f"- 운동: {summary.exercise}")
    lines.append(
        f"- 구간: {summary.window.start_s:.1f}s ~ {summary.window.end_s:.1f}s "
        f"(반복 {summary.window.rep_count}회)"
    )
    lines.append(f"- features: {summary.features}")

    return "\n".join(lines)


def create_feedback(
    profile: ObservationProfile, summary: FeatureSummary
) -> FeedbackResponse:
    """관찰 프로필 + 특징 요약 -> Gemini 호출 -> FeedbackResponse.

    LLM 호출이 실패하거나 형식이 어긋나면 예외를 그대로 올린다(상위에서 처리).
    카메라 가드(confidence.below_threshold) 체크는 호출하는 쪽(main.py)의 책임.
    """
    resp = generate(
        contents=_build_prompt(profile, summary),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=_FeedbackDraft,
        ),
    )

    # response.parsed: response_schema(_FeedbackDraft)로 파싱된 객체
    draft: _FeedbackDraft = resp.parsed

    messages = [
        FeedbackMessage(
            type=_norm_type(m.type),
            text=m.text,
            area=m.area,
            evidence=[e for e in m.evidence if e in summary.features],
            note_tag=m.note_tag,
        )
        for m in draft.messages
    ]

    return FeedbackResponse(
        session_id=summary.session_id,
        window_end_s=summary.window.end_s,
        messages=messages,
        guardrail_passed=_check_guardrail(messages),
    )


def _norm_type(value: str) -> str:
    """LLM이 살짝 다르게 줘도 허용값으로 정규화. 모르면 'observation'으로 둠."""
    v = (value or "").strip().lower()
    return v if v in {"observation", "suggestion"} else "observation"


# ── 가드레일 후처리 (기획.md 전환7) ──────────────────────────────────────
# 프롬프트에서 이미 금지했지만, 실제 출력에 새는지 텍스트 레벨에서 한 번 더 점검.
_BANNED_PATTERNS = [
    re.compile(r"위험"),          # "위험합니다" 등 단정형 위험 표현
    re.compile(r"진단"),
    re.compile(r"손상"),
    re.compile(r"세요"),          # 명령형 어미 전체("하세요","넓히세요","바꾸세요" 등)
    re.compile(r"십시오"),
    re.compile(r"해야\s?합니다"),  # 확신형 지시
    re.compile(r"해야\s?해요"),
]


def _has_banned_expression(text: str) -> bool:
    return any(p.search(text) for p in _BANNED_PATTERNS)


def _check_guardrail(messages: list[FeedbackMessage]) -> bool:
    """메시지 중 하나라도 확신형 표현을 담고 있으면 False."""
    return not any(_has_banned_expression(m.text) for m in messages)


if __name__ == "__main__":
    # Windows 콘솔(cp949)에서도 한글이 깨지지 않도록 출력 인코딩을 UTF-8로.
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 - 재설정 불가 환경이면 그냥 진행
        pass

    from schemas import InjuryInput, FocusArea, Pattern, Window, Confidence

    # 목(mock) 데이터: 온보딩/비전 팀 결과물이 없어도 이 파일만으로 바로 확인 가능.
    _profile = ObservationProfile(
        user_id="u_demo",
        injuries=[InjuryInput(part="발목", side="right", condition="염좌", discomfort=3)],
        focus_areas=[FocusArea(area="오른쪽 발목", category="input", reason="입력된 부위")],
        watch_patterns=[Pattern.LOAD_SHIFT, Pattern.LR_IMBALANCE],
    )
    _summary = FeatureSummary(
        session_id="s_demo",
        exercise="squat",
        window=Window(start_s=0.0, end_s=8.0, rep_count=4),
        features={"load_shift": 0.62, "lr_angle_diff.ankle": 11.4},
        confidence=Confidence(overall=0.9, interp_ratio=0.1, below_threshold=False),
    )

    try:
        result = create_feedback(_profile, _summary)
        print(f"[feedback] guardrail_passed: {result.guardrail_passed}")
        for msg in result.messages:
            print(f"[feedback] ({msg.type}) {msg.area or '-'}: {msg.text}")
            print(f"           evidence={msg.evidence} note_tag={msg.note_tag}")
    except Exception as e:  # noqa: BLE001 - 연결 확인 단계라 모든 예외를 사용자에게 보여줌
        print(f"[feedback] 실패: {type(e).__name__}: {e}")
        raise SystemExit(1)
