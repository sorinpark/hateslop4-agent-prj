"""세션 리포트 요약 - 세션 중 쌓인 피드백 메시지(FeedbackMessage[]) -> LLM 1회 호출
-> ReportSummary(총평 + 빈도 정리 + 다음 세션 가이드).

feedback_part3.md B 담당. profile.py/feedback.py와 동일한 설계 원칙(기획.md 10번)을 따른다:
  - '위험/진단' 단어를 쓰지 않는다(패턴 관찰 톤).
  - 실시간 중 여러 번 나온 비슷한 메시지를 하나로 묶고 빈도(count)를 매긴다.
  - 다음 세션에서 확인할 관찰 포인트를 짧게 제안한다.

session_id는 코드가 채운다(LLM이 바꾸면 안 되는 값).

구조화 출력: google-genai의 response_schema로 형식을 강제 -> ReportSummary로 검증.
"""
from pydantic import BaseModel
from google.genai import types

from schemas import FeedbackMessage, ReportSummary, ReportSummaryItem
from llm import generate

SYSTEM_INSTRUCTION = (
    "너는 방금 끝난 운동 세션의 피드백 메시지들을 정리하는 AI Agent야. "
    "실시간 중 여러 번 생성된 관찰/제안 메시지 목록을 받아서, 화면에 보여줄 "
    "세션 리포트와 다음 세션 관찰 계획을 만든다. 다음 원칙을 반드시 지켜:\n"
    "1) '위험', '진단', '손상' 같은 의료적 단정 표현을 쓰지 마라. "
    "관찰/주의 톤으로만 쓴다.\n"
    "2) 의미가 비슷하거나 같은 관찰/제안은 하나의 항목으로 묶고, "
    "그 항목이 몇 번 나왔는지 count로 센다(원본 메시지 개수를 정확히 반영).\n"
    "3) 각 항목의 text는 원문을 다듬어 간결한 한 문장으로 쓴다.\n"
    "4) summary는 이번 세션 전체를 한두 문장으로 정리한 총평이다. "
    "단정하지 않는 관찰 톤을 유지한다.\n"
    "5) next_guidance는 다음 세션에서 사용자가 확인할 관찰 포인트다. "
    "명령형이 아니라 '~을 먼저 관찰해보면 좋을 것 같아요'처럼 참고 정보 톤으로 1~3개만 쓴다.\n"
    "6) 특별히 반복된 패턴이 없으면 items와 next_guidance는 적게 만들어도 된다.\n"
    "7) 모든 텍스트는 한국어로 쓴다."
)


class _ReportItemOut(BaseModel):
    text: str
    count: int


class _ReportDraft(BaseModel):
    """LLM 출력 전용. ReportSummary의 일부(summary, items, next_guidance)만."""
    summary: str
    items: list[_ReportItemOut]
    next_guidance: list[str] = []


def _build_prompt(messages: list[FeedbackMessage]) -> str:
    lines = ["다음은 이번 운동 세션 중 순서대로 생성된 피드백 메시지들이다.", ""]
    for i, m in enumerate(messages, 1):
        area = f" ({m.area})" if m.area else ""
        evidence = f" evidence={m.evidence}" if m.evidence else ""
        lines.append(f"{i}. [{m.type}]{area} {m.text}{evidence}")
    lines.append("")
    lines.append("이걸 총평 + 빈도별 정리 항목 + 다음 세션 관찰 가이드로 요약해줘.")
    return "\n".join(lines)


def create_report_summary(
    session_id: str, messages: list[FeedbackMessage]
) -> ReportSummary:
    """세션의 FeedbackMessage 목록 -> Gemini 호출 1회 -> ReportSummary.

    LLM 호출이 실패하거나 형식이 어긋나면 예외를 그대로 올린다(상위에서 처리).
    빈 메시지 목록 처리(호출하는 쪽의 책임)는 main.py에서 이 함수를 부르기 전에 한다.
    """
    resp = generate(
        contents=_build_prompt(messages),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=_ReportDraft,
        ),
    )

    draft: _ReportDraft = resp.parsed

    items = [
        ReportSummaryItem(text=i.text, count=max(1, i.count)) for i in draft.items
    ]
    next_guidance = draft.next_guidance[:3] or _fallback_next_guidance(messages, items)

    return ReportSummary(
        session_id=session_id,
        summary=draft.summary,
        items=items,
        next_guidance=next_guidance,
    )


def _fallback_next_guidance(
    messages: list[FeedbackMessage], items: list[ReportSummaryItem]
) -> list[str]:
    """Ensure the report screen can always show an agent-like next step.

    Gemini may legally return an empty next_guidance list. For the UX, a report
    with observed feedback should still expose a concrete next-session plan.
    """
    if items:
        top_item = max(items, key=lambda item: item.count)
        return [f"다음 세션 초반에는 '{top_item.text}' 흐름이 다시 보이는지 먼저 관찰해보면 좋을 것 같아요."]

    areas = [message.area for message in messages if message.area]
    if areas:
        area = areas[0]
        return [f"다음 세션에서는 {area} 주변 움직임이 안정적으로 유지되는지 먼저 관찰해보면 좋을 것 같아요."]

    return ["다음 세션에서는 초반과 후반의 움직임 차이가 있는지 먼저 관찰해보면 좋을 것 같아요."]


if __name__ == "__main__":
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    _messages = [
        FeedbackMessage(type="observation", area="오른쪽 발목", text="오른쪽 발목이 살짝 흔들리는 게 보여요."),
        FeedbackMessage(type="observation", area="오른쪽 발목", text="오른쪽 발목 흔들림이 이어지고 있어요."),
        FeedbackMessage(
            type="suggestion",
            area="오른쪽 발목",
            text="속도를 조금 늦추면 좋을 것 같아요.",
            evidence=["instability.ankle_R", "guidance:instability"],
            note_tag="참고 정보입니다",
        ),
    ]

    try:
        result = create_report_summary("s_demo", _messages)
        print(f"[report] summary: {result.summary}")
        for item in result.items:
            print(f"[report] ({item.count}회) {item.text}")
        for guidance in result.next_guidance:
            print(f"[report] next: {guidance}")
    except Exception as e:  # noqa: BLE001
        print(f"[report] 실패: {type(e).__name__}: {e}")
        raise SystemExit(1)
