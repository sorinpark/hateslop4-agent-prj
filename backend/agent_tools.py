"""Tool layer for the agentic feedback path.

These helpers keep the LangGraph nodes small and explicit. They are intentionally
plain Python functions first: if this grows into a separate Tool server later,
these function boundaries are the natural MCP migration points.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from schemas import FeatureSummary, ObservationProfile
from db import repository as db_repo


@dataclass(frozen=True)
class GuidanceDoc:
    doc_id: str
    title: str
    text: str
    exercises: tuple[str, ...]
    feature_keywords: tuple[str, ...]
    area_keywords: tuple[str, ...]


_GUIDANCE_DOCS = [
    GuidanceDoc(
        doc_id="guidance:lr-imbalance",
        title="Left-right balance cue",
        text=(
            "좌우 차이가 반복될 때는 속도를 낮추고 양발 지지감과 내려가는 깊이가 "
            "비슷한지 관찰하는 것이 일반적인 운동 수행 점검에 도움이 된다."
        ),
        exercises=("squat", "lunge", "bridge"),
        feature_keywords=("lr_angle_diff", "rom_asymmetry"),
        area_keywords=("무릎", "발목", "고관절", "골반"),
    ),
    GuidanceDoc(
        doc_id="guidance:instability",
        title="Instability cue",
        text=(
            "흔들림이 커지는 구간에서는 반복 속도나 유지 시간을 잠시 줄이고, "
            "관절이 한쪽으로 급하게 이동하는지 확인하는 접근이 자주 쓰인다."
        ),
        exercises=("squat", "lunge", "plank", "bridge", "wall_pushup"),
        feature_keywords=("instability",),
        area_keywords=("무릎", "발목", "손목", "어깨", "허리"),
    ),
    GuidanceDoc(
        doc_id="guidance:load-shift",
        title="Load shift cue",
        text=(
            "부하가 한쪽으로 쏠려 보일 때는 발 위치, 체중 중심, 상체 기울기를 "
            "함께 관찰하면 원인을 좁혀 보는 데 도움이 된다."
        ),
        exercises=("squat", "lunge", "bridge"),
        feature_keywords=("load_shift",),
        area_keywords=("무릎", "발목", "고관절", "허리"),
    ),
    GuidanceDoc(
        doc_id="guidance:hold-fatigue",
        title="Hold exercise fatigue cue",
        text=(
            "유지형 운동에서는 시간이 지날수록 자세가 무너지거나 흔들림이 늘 수 "
            "있으므로, 유지 시간과 흔들림 변화를 함께 보는 것이 좋다."
        ),
        exercises=("plank", "bridge", "superman"),
        feature_keywords=("late_fatigue", "instability", "rom"),
        area_keywords=("허리", "골반", "어깨", "고관절"),
    ),
]


def flatten_feature_keys(features: dict[str, Any], prefix: str = "") -> set[str]:
    """Return both top-level and dotted feature keys.

    Example: {"lr_angle_diff": {"knee": 12}} ->
    {"lr_angle_diff", "lr_angle_diff.knee"}
    """
    keys: set[str] = set()
    for key, value in features.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)
        keys.add(full_key)
        if isinstance(value, dict):
            keys.update(flatten_feature_keys(value, full_key))
    return keys


def has_meaningful_signal(summary: FeatureSummary) -> bool:
    """Gate low-value windows before spending LLM calls.

    The thresholds are deliberately light. The goal is not medical judgement; it
    is only to skip windows where every measured value is effectively quiet.
    """
    if summary.confidence.below_threshold:
        return False

    def numeric_values(value: Any):
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            yield abs(float(value))
        elif isinstance(value, dict):
            for child in value.values():
                yield from numeric_values(child)
        elif isinstance(value, list):
            for child in value:
                yield from numeric_values(child)

    return any(value >= 3.0 for value in numeric_values(summary.features))


def retrieve_exercise_guidance(
    profile: ObservationProfile, summary: FeatureSummary, limit: int = 3
) -> list[dict[str, str]]:
    """Small local RAG tool over curated exercise guidance snippets.

    This is intentionally a tiny deterministic retriever instead of a vector DB:
    it gives the agent grounding and evidence IDs without adding deployment
    weight to the real-time path. The interface can later be backed by Chroma or
    pgvector without changing the LangGraph node.
    """
    feature_keys = flatten_feature_keys(summary.features)
    focus_text = " ".join(area.area for area in profile.focus_areas)
    scored: list[tuple[int, GuidanceDoc]] = []

    for doc in _GUIDANCE_DOCS:
        score = 0
        if summary.exercise in doc.exercises:
            score += 2
        score += sum(2 for keyword in doc.feature_keywords if keyword in feature_keys)
        score += sum(1 for keyword in doc.area_keywords if keyword in focus_text)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {"id": doc.doc_id, "title": doc.title, "text": doc.text}
        for _, doc in scored[:limit]
    ]


def get_recent_feedback_context(
    profile: ObservationProfile, summary: FeatureSummary, limit: int = 6
) -> list[dict[str, Any]]:
    """History tool: recent feedback for the same user/exercise.

    If the database is unavailable during a demo, return an empty history rather
    than breaking the real-time feedback loop.
    """
    try:
        return db_repo.get_recent_feedback_for_user(
            user_id=profile.user_id,
            exercise=summary.exercise,
            exclude_session_id=summary.session_id,
            limit=limit,
        )
    except Exception:
        return []


def allowed_evidence_keys(summary: FeatureSummary, guidance: list[dict[str, str]]) -> set[str]:
    return flatten_feature_keys(summary.features) | {doc["id"] for doc in guidance}
