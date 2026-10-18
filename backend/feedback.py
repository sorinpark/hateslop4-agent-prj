"""실시간 피드백 생성 - 특징 요약(FeatureSummary) + 관찰 프로필 -> LLM -> FeedbackResponse.

기본 진입점 create_feedback()은 agentic-v2 경로를 우선 사용한다. Agent 경로는
LangGraph 기반 상태/Tool/RAG/검증 흐름을 거치며, 의존성이나 LLM 호출 문제로
실패하면 기존 단일 LLM 호출 baseline으로 자동 fallback한다.

baseline 설계 원칙:
  - '위험/진단' 단어를 쓰지 않는다(패턴 관찰 톤).
  - 제안(suggestion)은 '참고 정보'임을 note_tag로 명시한다.
  - evidence는 실제로 features에 존재하는 키만 인용한다.

구조화 출력: google-genai의 response_schema로 형식을 강제 -> FeedbackMessage로 검증.
"""
import logging
import os
import re

from pydantic import BaseModel
from google.genai import types

from schemas import ObservationProfile, FeatureSummary, FeedbackMessage, FeedbackResponse
from llm import generate

logger = logging.getLogger(__name__)

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
    "7) 모든 텍스트는 한국어로, 실시간 운동 중 짧게 읽을 수 있게 간결히 쓴다.\n"
    "8) suggestion 메시지는 화면에 팝업으로도 노출된다. '~하세요', '~십시오' 같은 "
    "명령형 어미 대신 '~하면 좋을 것 같아요', '~것 같아요' 같은 완곡한 어미를 쓴다."
)


class _FeedbackMessageOut(BaseModel):
    type: str  # observation | suggestion
    text: str
    area: str | None = None
    evidence: list[str] = []
    note_tag: str | None = None


class _FeedbackDraft(BaseModel):
    """LLM 출력 전용. FeedbackResponse의 일부(messages)만."""
    messages: list[_FeedbackMessageOut]


def create_feedback(
    profile: ObservationProfile, summary: FeatureSummary
) -> FeedbackResponse:
    """관찰 프로필 + 특징 요약 -> FeedbackResponse.

    기본값은 Agentic V2를 사용한다. 데모 중 LangGraph 의존성, DB 히스토리 조회,
    LLM 호출 등의 문제가 생기면 baseline으로 내려가서 실시간 루프가 끊기지 않게 한다.
    USE_AGENTIC_FEEDBACK=0 으로 두면 기존 baseline만 실행할 수 있다.
    """
    use_agentic = os.environ.get("USE_AGENTIC_FEEDBACK", "1") != "0"
    if use_agentic:
        try:
            from agentic_feedback import create_agentic_feedback

            return create_agentic_feedback(profile, summary)
        except Exception:
            logger.exception("agentic feedback failed; falling back to baseline")

    return create_baseline_feedback(profile, summary)


def create_baseline_feedback(
    profile: ObservationProfile, summary: FeatureSummary
) -> FeedbackResponse:
    """기존 단일 LLM 호출 baseline.

    Agentic V2와 비교하기 위해 별도 함수로 보존한다.
    """
    resp = generate(
        contents=_build_prompt(profile, summary),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=_FeedbackDraft,
        ),
    )

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
        agent_trace=["baseline:single_llm_call"],
    )


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
    if summary.window.hold_seconds is not None:
        progress = f"유지 {summary.window.hold_seconds:.1f}초"
    else:
        progress = f"반복 {summary.window.rep_count}회"
    lines.append(
        f"- 구간: {summary.window.start_s:.1f}s ~ {summary.window.end_s:.1f}s ({progress})"
    )
    lines.append(f"- features: {summary.features}")

    return "\n".join(lines)


def _norm_type(value: str) -> str:
    """LLM이 살짝 다르게 줘도 허용값으로 정규화. 모르면 'observation'으로 둠."""
    v = (value or "").strip().lower()
    return v if v in {"observation", "suggestion"} else "observation"


_BANNED_PATTERNS = [
    re.compile(r"위험"),
    re.compile(r"진단"),
    re.compile(r"손상"),
    re.compile(r"세요"),
    re.compile(r"십시오"),
    re.compile(r"해야\s?합니다"),
    re.compile(r"해야\s?해요"),
]


def _has_banned_expression(text: str) -> bool:
    return any(p.search(text) for p in _BANNED_PATTERNS)


def _check_guardrail(messages: list[FeedbackMessage]) -> bool:
    """메시지 중 하나라도 확신형 표현을 담고 있으면 False."""
    return not any(_has_banned_expression(m.text) for m in messages)


if __name__ == "__main__":
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    from schemas import InjuryInput, FocusArea, Pattern, Window, Confidence

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
        features={"load_shift": {"trunk_lean_deg": 6.2, "side_bias": "right"}, "lr_angle_diff": {"ankle": 11.4}},
        confidence=Confidence(overall=0.9, interp_ratio=0.1, below_threshold=False),
    )

    try:
        result = create_feedback(_profile, _summary)
        print(f"[feedback] guardrail_passed: {result.guardrail_passed}")
        print(f"[feedback] trace: {result.agent_trace}")
        for msg in result.messages:
            print(f"[feedback] ({msg.type}) {msg.area or '-'}: {msg.text}")
            print(f"           evidence={msg.evidence} note_tag={msg.note_tag}")
    except Exception as e:  # noqa: BLE001
        print(f"[feedback] 실패: {type(e).__name__}: {e}")
        raise SystemExit(1)
