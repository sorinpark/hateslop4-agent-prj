"""Agentic feedback path using LangGraph.

Baseline feedback.py does a single fixed LLM call:
FeatureSummary + ObservationProfile -> FeedbackResponse.

This module adds the HATESLOP-style agent layer around that baseline idea:
state -> tool use -> conditional routing -> grounded generation -> verification.
The real-time path still stays conservative: if a window is low-value, the agent
skips LLM generation; if dependencies fail, main.py can fall back to baseline.
"""
from __future__ import annotations

from typing import Any, Literal, TypedDict

from google.genai import types
from pydantic import BaseModel

try:  # LangGraph is the preferred runner; the fallback keeps local demos robust.
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover - exercised only when dependency is absent
    END = "__end__"
    StateGraph = None

from schemas import FeatureSummary, FeedbackMessage, FeedbackResponse, ObservationProfile
from llm import generate
from feedback import _check_guardrail, _has_banned_expression, _norm_type
from agent_tools import (
    allowed_evidence_keys,
    get_recent_feedback_context,
    has_meaningful_signal,
    retrieve_exercise_guidance,
)


class AgentState(TypedDict, total=False):
    profile: ObservationProfile
    summary: FeatureSummary
    history: list[dict[str, Any]]
    guidance: list[dict[str, str]]
    route: Literal["skip", "generate"]
    messages: list[FeedbackMessage]
    guardrail_passed: bool
    trace: list[str]


class _AgentMessageOut(BaseModel):
    type: str
    text: str
    area: str | None = None
    evidence: list[str] = []
    note_tag: str | None = None


class _AgentDraft(BaseModel):
    messages: list[_AgentMessageOut]


SYSTEM_INSTRUCTION = (
    "너는 운동 중 사용자의 움직임 데이터를 관찰하는 AI Agent야. "
    "너의 목표는 진단이나 처방이 아니라, 현재 관찰값과 최근 기록, 일반 운동 수행 "
    "가이드 근거를 함께 보고 화면에 짧게 보여줄 참고 정보형 피드백을 만드는 것이다.\n"
    "반드시 지킬 규칙:\n"
    "1) '위험', '진단', '손상' 같은 의료적 단정 표현을 쓰지 않는다.\n"
    "2) '~하세요', '~하십시오', '해야 합니다' 같은 명령형 표현을 쓰지 않는다.\n"
    "3) observation은 입력 features 또는 history에서 관찰된 내용만 쓴다.\n"
    "4) suggestion은 guidance 문서 근거가 있을 때만 만들고 note_tag를 '참고 정보입니다'로 둔다.\n"
    "5) evidence에는 제공된 feature key 또는 guidance id만 넣는다. 없는 근거를 만들지 않는다.\n"
    "6) 최근 history와 같은 피드백을 반복하지 말고, 새롭거나 누적 맥락이 있는 내용만 1~3개 만든다.\n"
    "7) 모든 문장은 한국어로, 운동 중 읽을 수 있게 짧게 쓴다."
)


def create_agentic_feedback(
    profile: ObservationProfile, summary: FeatureSummary
) -> FeedbackResponse:
    """Run the agentic feedback graph and return the existing response schema."""
    initial: AgentState = {
        "profile": profile,
        "summary": summary,
        "history": [],
        "guidance": [],
        "route": "generate",
        "messages": [],
        "guardrail_passed": True,
        "trace": [],
    }

    if StateGraph is None:
        final_state = _run_without_langgraph(initial)
    else:
        final_state = _build_graph().invoke(initial)

    return FeedbackResponse(
        session_id=summary.session_id,
        window_end_s=summary.window.end_s,
        messages=final_state.get("messages", []),
        guardrail_passed=final_state.get("guardrail_passed", True),
    )


def _build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("retrieve_context", _retrieve_context)
    graph.add_node("route", _route)
    graph.add_node("retrieve_guidance", _retrieve_guidance)
    graph.add_node("generate", _generate)
    graph.add_node("verify", _verify)
    graph.add_node("finish_empty", _finish_empty)

    graph.set_entry_point("retrieve_context")
    graph.add_edge("retrieve_context", "route")
    graph.add_conditional_edges(
        "route",
        _route_key,
        {"skip": "finish_empty", "generate": "retrieve_guidance"},
    )
    graph.add_edge("retrieve_guidance", "generate")
    graph.add_edge("generate", "verify")
    graph.add_edge("verify", END)
    graph.add_edge("finish_empty", END)
    return graph.compile()


def _run_without_langgraph(state: AgentState) -> AgentState:
    state = _retrieve_context(state)
    state = _route(state)
    if _route_key(state) == "skip":
        return _finish_empty(state)
    state = _retrieve_guidance(state)
    state = _generate(state)
    return _verify(state)


def _append_trace(state: AgentState, item: str) -> list[str]:
    return [*state.get("trace", []), item]


def _retrieve_context(state: AgentState) -> AgentState:
    profile = state["profile"]
    summary = state["summary"]
    history = get_recent_feedback_context(profile, summary)
    return {**state, "history": history, "trace": _append_trace(state, "tool:history")}


def _route(state: AgentState) -> AgentState:
    summary = state["summary"]
    if summary.confidence.below_threshold:
        route: Literal["skip", "generate"] = "skip"
        reason = "route:skip:low_confidence"
    elif not has_meaningful_signal(summary):
        route = "skip"
        reason = "route:skip:no_meaningful_signal"
    else:
        route = "generate"
        reason = "route:generate"
    return {**state, "route": route, "trace": _append_trace(state, reason)}


def _route_key(state: AgentState) -> str:
    return state.get("route", "generate")


def _retrieve_guidance(state: AgentState) -> AgentState:
    profile = state["profile"]
    summary = state["summary"]
    guidance = retrieve_exercise_guidance(profile, summary)
    return {**state, "guidance": guidance, "trace": _append_trace(state, "tool:guidance_rag")}


def _generate(state: AgentState) -> AgentState:
    profile = state["profile"]
    summary = state["summary"]
    prompt = _build_prompt(profile, summary, state.get("history", []), state.get("guidance", []))
    resp = generate(
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=_AgentDraft,
        ),
    )
    draft: _AgentDraft = resp.parsed
    messages = [
        FeedbackMessage(
            type=_norm_type(message.type),
            text=message.text,
            area=message.area,
            evidence=message.evidence,
            note_tag=("참고 정보입니다" if _norm_type(message.type) == "suggestion" else message.note_tag),
        )
        for message in draft.messages[:3]
    ]
    return {**state, "messages": messages, "trace": _append_trace(state, "llm:generate")}


def _verify(state: AgentState) -> AgentState:
    summary = state["summary"]
    allowed = allowed_evidence_keys(summary, state.get("guidance", []))
    verified: list[FeedbackMessage] = []

    for message in state.get("messages", []):
        if _has_banned_expression(message.text):
            continue
        evidence = [item for item in message.evidence if item in allowed]
        if message.type == "suggestion" and not any(item.startswith("guidance:") for item in evidence):
            continue
        verified.append(message.model_copy(update={"evidence": evidence}))

    guardrail_passed = _check_guardrail(verified)
    return {
        **state,
        "messages": verified if guardrail_passed else [],
        "guardrail_passed": guardrail_passed,
        "trace": _append_trace(state, "verify:evidence_guardrail"),
    }


def _finish_empty(state: AgentState) -> AgentState:
    return {
        **state,
        "messages": [],
        "guardrail_passed": True,
        "trace": _append_trace(state, "finish:empty"),
    }


def _build_prompt(
    profile: ObservationProfile,
    summary: FeatureSummary,
    history: list[dict[str, Any]],
    guidance: list[dict[str, str]],
) -> str:
    lines = [
        "다음 상태를 보고 이번 5초 윈도우에 필요한 피드백만 생성해줘.",
        "",
        "[관찰 프로필]",
    ]
    for focus in profile.focus_areas:
        lines.append(f"- {focus.area} ({focus.category}): {focus.reason}")
    lines.append(f"- 주의 패턴: {[pattern.value for pattern in profile.watch_patterns]}")
    lines.append("")

    lines.extend(
        [
            "[현재 윈도우]",
            f"- session_id: {summary.session_id}",
            f"- exercise: {summary.exercise}",
            f"- time: {summary.window.start_s:.1f}s~{summary.window.end_s:.1f}s",
            f"- rep_count: {summary.window.rep_count}",
            f"- hold_seconds: {summary.window.hold_seconds}",
            f"- confidence: {summary.confidence.model_dump()}",
            f"- features: {summary.features}",
            "",
            "[최근 같은 사용자/운동 피드백]",
        ]
    )
    if history:
        for item in history:
            lines.append(
                f"- {item.get('date', '-')}: [{item.get('type')}] {item.get('area') or '-'} / "
                f"{item.get('text')} / evidence={item.get('evidence')}"
            )
    else:
        lines.append("- 없음")
    lines.append("")

    lines.append("[검색된 일반 운동 가이드]")
    if guidance:
        for doc in guidance:
            lines.append(f"- {doc['id']} | {doc['title']}: {doc['text']}")
    else:
        lines.append("- 없음")

    lines.extend(
        [
            "",
            "출력은 messages 배열만 포함한다.",
            "evidence에는 반드시 현재 features key 또는 guidance id만 사용한다.",
        ]
    )
    return "\n".join(lines)
